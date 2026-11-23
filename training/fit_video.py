import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Model selection and held-out evaluation for video-prefix anticipation."""
import csv,json
from collections import Counter
import joblib
import numpy as np
from catboost import CatBoostClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import ExtraTreesClassifier,HistGradientBoostingClassifier
from sklearn.metrics import (average_precision_score,roc_auc_score,precision_score,recall_score,
    f1_score,balanced_accuracy_score,accuracy_score,brier_score_loss,confusion_matrix)
from anticipation import MIL,SoftEnsemble,cached_states
from video_pose import OUT,ROOT,CACHE,sources

RESULT=ROOT/'research_results'
# Official evaluation uses ≥1 s of observed play so closing-speed features are defined.
CUTOFFS=(1.,1.5,2.)
PROBE_CUTOFFS=(.5,1.,1.5,2.)

def read_rows(path):
    with path.open(encoding='utf8') as f:return list(csv.DictReader(f))
def save_rows(path,rows):
    with path.open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def metrics(y,s,th):
    y=np.asarray(y);s=np.asarray(s);p=s>=th
    return dict(n=len(y),positives=int(y.sum()),AP=float(average_precision_score(y,s)),AUROC=float(roc_auc_score(y,s)),
        accuracy=float(accuracy_score(y,p)),balanced_accuracy=float(balanced_accuracy_score(y,p)),precision=float(precision_score(y,p,zero_division=0)),
        recall=float(recall_score(y,p)),F1=float(f1_score(y,p)),Brier=float(brier_score_loss(y,s)),confusion=confusion_matrix(y,p,labels=[0,1]).tolist())
def group_info():
    return {r['uid']:r for r in read_rows(OUT/'video_groups.csv')}
def feature_data(skip_missing=False):
    dst=OUT/'prefix_features';dst.mkdir(exist_ok=True)
    data={}
    for uid,path,split,label in sources():
        if skip_missing and not (CACHE/(uid+'.npz')).is_file():continue
        dest=dst/(uid+'.npz')
        if not dest.exists():
            ts=[];pooled=[];bags=[];offset=[0];coverage=[]
            for t,players,pairs,b,x in cached_states(CACHE/(uid+'.npz')):
                ts.append(t);pooled.append(x);bags.extend(b);offset.append(len(bags));coverage.append(len(players))
            np.savez_compressed(dest,t=ts,x=np.array(pooled,np.float32),b=np.array(bags,np.float32).reshape(-1,27),off=offset,count=coverage)
        with np.load(dest) as f:
            t=f['t'];x=f['x'];b=f['b'];o=f['off'];count=f['count']
        data[uid]=(t,x,[b[i:j] for i,j in zip(o,o[1:])],count)
    return data
def prefix(data,uid,t):
    ts,x,b,_=data[uid]
    i=int(np.argmin(abs(ts-t)))
    return x[i],b[i]
def output_scores(name,model,x,b):
    if name=='pose-MIL':return np.array([model.predict(v) for v in b])
    return np.where([len(v)>0 for v in b],model.predict_proba(x)[:,1],0.)
def operating_stats(y,s,th):
    m=metrics(y,s,th)
    floor=min(m['accuracy'],m['balanced_accuracy'],m['F1'],m['precision'],m['recall'])
    return floor,m
def best_threshold(y,s):
    # Raise the worst of accuracy / balanced accuracy / F1 / precision / recall.
    def key(q):
        floor,m=operating_stats(y,s,q)
        return (floor,m['F1'],m['balanced_accuracy'],m['accuracy'],m['AUROC'],q)
    return float(max(np.unique(s),key=key))

def catboost(name,iterations,depth,lr,l2,seed,weights='Balanced'):
    return name,CatBoostClassifier(iterations=iterations,depth=depth,learning_rate=lr,l2_leaf_reg=l2,
        auto_class_weights=weights,verbose=False,allow_writing_files=False,thread_count=4,random_seed=seed)

def build_models():
    models={
        'logistic':make_pipeline(StandardScaler(),LogisticRegression(C=.05,class_weight='balanced',max_iter=800,solver='lbfgs')),
        'logistic-strong':make_pipeline(StandardScaler(),LogisticRegression(C=.25,class_weight='balanced',max_iter=1200,solver='lbfgs')),
        'logistic-wide':make_pipeline(StandardScaler(),LogisticRegression(C=1.,class_weight='balanced',max_iter=1500,solver='lbfgs')),
        'pose-MIL':MIL(),
        'extra-trees':ExtraTreesClassifier(n_estimators=500,min_samples_leaf=2,max_features=.9,class_weight='balanced_subsample',n_jobs=4,random_state=41),
        'extra-trees-reg':ExtraTreesClassifier(n_estimators=350,min_samples_leaf=5,max_features=.7,class_weight='balanced',n_jobs=4,random_state=17),
        'hist-boost':make_pipeline(StandardScaler(),HistGradientBoostingClassifier(max_depth=6,learning_rate=.045,max_iter=360,l2_regularization=.08,class_weight='balanced',random_state=41)),
        'hist-boost-deep':make_pipeline(StandardScaler(),HistGradientBoostingClassifier(max_depth=8,learning_rate=.035,max_iter=420,l2_regularization=.05,class_weight='balanced',random_state=12)),
    }
    for spec in (
        catboost('boosted-trees',420,5,.03,4,41),
        catboost('boosted-deep',560,6,.025,3,7,'SqrtBalanced'),
        catboost('boost-ft-a',480,5,.035,3,101),
        catboost('boost-ft-b',520,4,.04,5,202),
        catboost('boost-ft-c',600,6,.02,2,303,'SqrtBalanced'),
        catboost('boost-ft-d',450,5,.028,6,404),
        catboost('boost-ft-e',500,7,.022,4,505,'Balanced'),
    ):
        models[spec[0]]=spec[1]
    return models

def main():
    RESULT.mkdir(exist_ok=True)
    data=feature_data()
    groups=group_info()
    quiet={r['uid'] for r in read_rows(OUT/'cup_audit.csv') if r['quiet']=='1'}
    # Training uses several early prefixes so the scorer sees pre-contact variation.
    train_samples=[]
    for u,g in groups.items():
        if g['keep']!='1' or g['split']!='train':continue
        pos=int(g['label']=='foul')
        for t in (1.,1.5,2.):train_samples.append((u,t,pos,'incident'))
        if pos:train_samples.append((u,.5,0,'early'))
    for r in read_rows(OUT/'clips.csv'):
        if r['split']=='train' and r['uid'] in quiet:train_samples.append((r['uid'],1.5,0,'ordinary'))
    xt,bt=zip(*(prefix(data,u,t) for u,t,_,_ in train_samples))
    xt=np.stack(xt);bt=list(bt);yt=np.array([a[2] for a in train_samples])

    models=build_models()
    for name,model in models.items():
        model.fit(bt if name=='pose-MIL' else xt,yt)
    # Ensembles of complementary learners (validation chooses among them).
    ens_a=['boosted-trees','boost-ft-a','boost-ft-b','extra-trees','logistic-strong']
    ens_b=['boosted-deep','boost-ft-c','boost-ft-e','hist-boost','extra-trees-reg']
    ens_c=['boost-ft-a','boost-ft-d','boosted-trees','hist-boost-deep','logistic-wide']
    models['soft-ensemble-a']=SoftEnsemble([models[n] for n in ens_a])
    models['soft-ensemble-b']=SoftEnsemble([models[n] for n in ens_b])
    models['soft-ensemble-c']=SoftEnsemble([models[n] for n in ens_c])
    models['soft-ensemble']=SoftEnsemble([models[n] for n in sorted(set(ens_a+ens_b+ens_c))])

    val_clips=[(u,int(g['label']=='foul')) for u,g in groups.items() if g['keep']=='1' and g['split']=='val']
    test_clips=[(u,int(g['label']=='foul')) for u,g in groups.items() if g['keep']=='1' and g['split']=='test']

    # Score every model@cutoff on validation only.
    candidates=[];val_ap={}
    for name,model in models.items():
        for cutoff in CUTOFFS:
            xv,bv=zip(*(prefix(data,u,cutoff) for u,_ in val_clips))
            yv=np.array([y for _,y in val_clips])
            score=output_scores(name,model,np.stack(xv),list(bv))
            ap=float(average_precision_score(yv,score));auc=float(roc_auc_score(yv,score))
            th=best_threshold(yv,score);floor,m=operating_stats(yv,score,th)
            val_ap[f'{name}@{cutoff}']=ap
            candidates.append(dict(name=name,cutoff=cutoff,model=model,th=th,score=score,y=yv,ap=ap,auc=auc,floor=floor,f1=m['F1']))
    # Finalists: CatBoost variants and soft ensembles (best held-out stability in tuning).
    pool=[c for c in candidates if c['name'].startswith(('boost','soft-ensemble'))]
    best_ap=max(c['ap'] for c in pool)
    near=[c for c in pool if c['ap']>=best_ap-0.035]
    # Composite: balanced operating point first, then ranking quality.
    winner=max(near,key=lambda c:(c['floor'],c['f1'],c['ap'],c['auc']))
    name,cutoff,model,th,vscore,yv=winner['name'],winner['cutoff'],winner['model'],winner['th'],winner['score'],winner['y']

    payload=dict(name=name,model=model,ranker=models['pose-MIL'],threshold=float(th),hz=2,cutoff=float(cutoff))
    joblib.dump(payload,ROOT/'models/video_anticipation.joblib')

    xe,be=zip(*(prefix(data,u,cutoff) for u,_ in test_clips))
    ye=np.array([y for _,y in test_clips]);testrows=[(u,cutoff,y,'incident') for u,y in test_clips]
    se=output_scores(name,model,np.stack(xe),list(be))
    report=dict(validation_AP=val_ap,selected=name,threshold=float(th),cutoff=float(cutoff),training_samples=len(yt),
        selection=dict(best_validation_AP=best_ap,ap_band=0.035,family='boost+soft-ensemble',rule='max floor among AP within 0.035 of best'),
        validation=metrics(yv,vscore,th),test=metrics(ye,se,th),counts=dict(Counter(g['split']+'_'+g['label'] for g in groups.values() if g['keep']=='1')))
    rng=np.random.default_rng(2022);cis=[]
    for _ in range(1500):
        idx=rng.integers(0,len(ye),len(ye))
        if len(np.unique(ye[idx]))==2:cis.append([average_precision_score(ye[idx],se[idx]),roc_auc_score(ye[idx],se[idx]),balanced_accuracy_score(ye[idx],se[idx]>=th)])
    report['clip_bootstrap_95_AP_AUROC_balacc']=np.quantile(cis,[.025,.975],axis=0).tolist()
    report['prefix_sensitivity']={}
    for c in PROBE_CUTOFFS:
        xf,bf=zip(*(prefix(data,u,c) for u,_ in test_clips))
        report['prefix_sensitivity'][str(c)]=metrics(ye,output_scores(name,model,np.stack(xf),list(bf)),th)
    early_x,early_b=zip(*(prefix(data,u,.5) for u,y in test_clips if y))
    earlier=output_scores(name,model,np.stack(early_x),list(early_b))
    report['within_foul_later_ranks_above_early']=float(np.mean((se[ye==1]>earlier)+.5*(se[ye==1]==earlier)))
    save_rows(RESULT/'test_prefix_predictions.csv',[dict(uid=u,time=t,label=y,score=s) for (u,t,y,_),s in zip(testrows,se)])
    baseline=lambda x: -x[:,0]+x[:,3]
    report['proximity_closing_baseline_test_AP']=float(average_precision_score(ye,baseline(np.stack(xe))))
    report['test_prevalence']=float(ye.mean())
    (RESULT/'video_metrics.json').write_text(json.dumps(report,indent=2))
    summaries=[];timelines=[]
    for uid,path,split,label in sources():
        ts,x,b,count=data[uid]
        ss=output_scores(name,model,x,b)
        ss=np.where((ts>=.4)&(count>=2),ss,0.)
        active=ss>=th
        with np.load(CACHE/(uid+'.npz')) as z:dur=float(z['duration'])
        summaries.append(dict(uid=uid,split=split,label=label,seconds=dur,observations=len(ts),pose_observations=int(count.sum()),frames_with_pairs=int(sum(map(lambda q:len(q)>0,b))),alerts=int(sum(active&~np.r_[False,active[:-1]])),max_score=float(ss.max())))
        timelines.extend(dict(uid=uid,t=t,score=s,active=int(a)) for t,s,a in zip(ts,ss,active))
    save_rows(RESULT/'all_clips.csv',summaries);save_rows(RESULT/'timeline.csv',timelines)
    print(json.dumps({k:report[k] for k in ('selected','cutoff','threshold','selection','validation','test')},indent=2))
if __name__=='__main__':main()
