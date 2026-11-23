import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Fit on full halves from four matches, tune on two matches, test once on the final."""
import json
import joblib
import numpy as np
from catboost import CatBoostClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from prepare import ROOT,OUT
from half_features import aligned
from match_corpus import GAMES
from fit_video import RESULT,metrics,save_rows
from in_play import Alarm,TransferForecast
from temporal_forecast import CausalTemporalForecast

def alarms(game,scores,threshold):
    state=Alarm(threshold);ts=[];prev=None
    for t,c,s,cut in zip(game['t'],game['clock'],scores,game['cut']):
        if prev is None or t-prev>1 or cut:state=Alarm(threshold)
        onset,_=state.step(t,s)
        if onset:ts.append(float(c))
        prev=t
    return np.array(ts)
def event_metrics(sets,scores,threshold,lo=.75,hi=2.):
    false=tp=total=0;leads=[];minutes=0.
    for g,s in zip(sets,scores):
        ev=g['events']
        alerts=alarms(g,s,threshold);used=set();total+=len(ev);minutes+=len(s)/120
        for a in alerts:
            found=next((i for i,t in enumerate(ev) if i not in used and lo<=t-a<=hi),None)
            if found is None:false+=1
            else:
                tp+=1;used.add(found);leads.append(float(ev[found]-a))
    p=tp/max(1,tp+false);r=tp/max(1,total)
    return dict(events=total,minutes=minutes,TP=tp,FP=false,FN=total-tp,precision=p,recall=r,F1=2*p*r/(p+r) if p+r else 0.,
        false_alarms_per_min=false/minutes,median_lead_seconds=float(np.median(leads)) if leads else None,matched_leads=leads)
def scores(model,g):
    # Enforce the same missing-person and cut handling as the player-pair runtime.
    prob=model.predict_series(g['x'],g['t'],g['cut']) if hasattr(model,'predict_series') else model.predict_proba(g['x'])[:,1]
    return np.where(g['valid'],prob,0.)
def main():
    training=[aligned(g[0]) for g in GAMES if g[3]=='train'];validation=[aligned(g[0]) for g in GAMES if g[3]=='val']
    x=np.vstack([g['x'] for g in training]);y=np.concatenate([g['y'] for g in training])
    # Keep the original logistic grid (best historical event F1) and stronger tree / transfer probes.
    models={f'L2-{c}':make_pipeline(StandardScaler(),LogisticRegression(C=c,max_iter=900)) for c in (.0005,.005,.05,.2)}
    for depth in (3,5):
        models[f'Boost-{depth}']=CatBoostClassifier(iterations=220,depth=depth,learning_rate=.045,l2_leaf_reg=8,auto_class_weights='Balanced',thread_count=4,verbose=False,allow_writing_files=False,random_seed=42)
    clip=joblib.load(ROOT/'models/video_anticipation.joblib')
    if clip['name']!='pose-MIL':
        models['clip-transfer']=TransferForecast(clip['model'],make_pipeline(StandardScaler(),LogisticRegression(C=.005,max_iter=700)))
    models['causal-temporal-CNN']=CausalTemporalForecast()
    validation_results={};best=None
    val_y=np.concatenate([g['y'] for g in validation])
    for name,model in models.items():
        if hasattr(model,'fit_games'):model.fit_games(training)
        else:model.fit(x,y)
        sv=[scores(model,g) for g in validation];all_s=np.concatenate(sv)
        ap=float(average_precision_score(val_y,all_s))
        # Select a useful event operating point under an explicit one-false-alarm/minute budget.
        options=[]
        for th in np.unique(np.r_[np.quantile(all_s,np.linspace(.50,.9995,75)),1.00001]):
            m=event_metrics(validation,sv,th)
            if m['false_alarms_per_min']<=1:options.append((m['F1'],m['recall'],th,m))
        f1,rec,th,em=max(options,key=lambda q:q[:3])
        validation_results[name]=dict(AP=ap,threshold=float(th),event=em)
        key=(f1,ap)
        if best is None or key>best[0]:best=(key,name,model,float(th))
    _,name,model,th=best
    joblib.dump(dict(name=name,model=model,threshold=th),ROOT/'models/match_anticipation.joblib')
    test=aligned('ARG_FRA');st=scores(model,test)
    report=dict(selected=name,threshold=th,validation_candidates=validation_results,
        training={g['game']:dict(frames=len(g['y']),events=len(g['events']),positives=int(g['y'].sum())) for g in training},
        validation={g['game']:dict(frames=len(g['y']),events=len(g['events'])) for g in validation},
        test=metrics(test['y'],st,th),test_prevalence=float(np.mean(test['y'])),test_events=event_metrics([test],[st],th))
    # Stability of official event-clock timing. Shift the labels, never the predictions.
    report['event_clock_shift_sensitivity']={}
    for shift in (-1.,-.5,0.,.5,1.):
        shifted=dict(test,events=test['events']+shift)
        report['event_clock_shift_sensitivity'][str(shift)]=event_metrics([shifted],[st],th)
    # Consecutive one-minute blocks preserve local dependence in uncertainty estimates.
    rng=np.random.default_rng(42);blocks=np.unique(test['clock'].astype(int)//60)
    groups=[np.where(test['clock'].astype(int)//60==b)[0] for b in blocks]
    from sklearn.metrics import roc_auc_score
    ci=[]
    for _ in range(800):
        i=np.concatenate([groups[k] for k in rng.integers(0,len(blocks),len(blocks))])
        if len(np.unique(test['y'][i]))==2:
            ci.append([average_precision_score(test['y'][i],st[i]),roc_auc_score(test['y'][i],st[i])])
    report['test_block_95_AP_AUROC']=np.quantile(ci,[.025,.975],axis=0).tolist()
    for g in [*training,*validation,test]:
        pred=scores(model,g)
        save_rows(RESULT/f"half_{g['game']}.csv",[dict(video_s=t,period_s=c,label=int(y),score=s) for t,c,y,s in zip(g['t'],g['clock'],g['y'],pred)])
    # Validation-selected threshold for the proximity and closing-speed comparator.
    rule=lambda g:np.where(g['valid'],-g['x'][:,0]+g['x'][:,3],-100.)
    vs=[rule(g) for g in validation];best_rule=None
    for q in np.quantile(np.concatenate(vs),np.linspace(.5,1,64)):
        m=event_metrics(validation,vs,q)
        if m['false_alarms_per_min']<=1 and (best_rule is None or m['F1']>best_rule[0]):best_rule=(m['F1'],q)
    rt=best_rule[1] if best_rule else 101.
    report['closing_baseline']=dict(test_AP=float(average_precision_score(test['y'],rule(test))),threshold=float(rt),test_events=event_metrics([test],[rule(test)],rt))
    (RESULT/'continuous_metrics.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(selected=name,threshold=th,test=report['test'],test_events=report['test_events']),indent=2))
if __name__=='__main__':main()
