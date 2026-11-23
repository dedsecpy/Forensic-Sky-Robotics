import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Fit and evaluate a causal two-second scene forecaster on World Cup 360 snapshots."""
import bisect
import csv
import json
import subprocess
from pathlib import Path
import joblib
import numpy as np
from scipy.spatial.distance import pdist, squareform
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score, precision_recall_curve, precision_score, recall_score, confusion_matrix
from prepare import ROOT, OUT, REVISION, seconds

def geometry(points):
    """Permutation and orientation invariant summaries of the local player graph, in metres."""
    xy=np.asarray(points,float)
    d=squareform(pdist(xy))
    np.fill_diagonal(d,np.inf)
    nearest=np.sort(d,axis=1)
    return np.r_[len(xy),np.percentile(nearest[:,0],[0,10,50,90]),
                 np.percentile(nearest[:,min(2,len(xy)-2)],[10,50]),
                 np.mean(nearest[:,0]<2),np.mean(nearest[:,0]<4),
                 np.sqrt(np.sum(np.var(xy,axis=0)))]

class History:
    def __init__(self):
        self.samples=[]
    def features(self,t,points):
        g=geometry(points)
        self.samples=[(s,a) for s,a in self.samples if 0<=t-s<=1.5]
        old=next(((s,a) for s,a in self.samples if t-s>=0.25),None)
        delta=(g-old[1])/(t-old[0]) if old else np.zeros_like(g)
        self.samples.append((t,g))
        return np.r_[g,delta]

def training_data(graph=False):
    repo=OUT/'statsbomb_repo'
    if not repo.is_dir():
        subprocess.run(['git','clone','--depth','1','--filter=blob:none','--no-checkout','https://github.com/statsbomb/open-data.git',str(repo)],check=True)
    rows=list(csv.DictReader((OUT/'clips.csv').open(encoding='utf8')))
    splits={r['match_id']:r['split'] for r in rows}
    features=[]; labels=[]; groups=[]; ids=[]; match_ids=[]
    for mid,split in sorted(splits.items()):
        if not mid: continue
        raw=subprocess.check_output(['git','-C',str(repo),'show',f'{REVISION}:data/three-sixty/{mid}.json'])
        frames={r['event_uuid']:r['freeze_frame'] for r in json.loads(raw)}
        events=json.loads((OUT/f'statsbomb/{mid}.json').read_bytes())
        for period in sorted({e['period'] for e in events}):
            es=sorted((e for e in events if e['period']==period),key=seconds)
            fouls=sorted(seconds(e) for e in es if e['type']['name']=='Foul Committed')
            if graph:
                from graph_model import GraphHistory
                hist=GraphHistory()
            else:
                hist=History()
            last=-5
            for e in es:
                t=seconds(e)
                frame=frames.get(e['id'],[])
                if len(frame)<3 or t-last<0.24: continue
                if e['type']['name'] in ('Foul Committed','Foul Won','Injury Stoppage','Half End'): continue
                if t+2>seconds(es[-1]): continue
                ix=bisect.bisect_left(fouls,t-2)
                xy=np.array([f['location'] for f in frame])*[105/120,68/80]
                state=hist.features(t,xy)
                last=t
                if ix<len(fouls) and fouls[ix]<t+0.5: continue
                features.append(state)
                labels.append(int(ix<len(fouls) and fouls[ix]<=t+2))
                groups.append(split)
                if not graph:
                    ids.append(e['id'])
                    match_ids.append(mid)
    if not graph:
        np.savez_compressed(OUT/'forecast_examples.npz',features=np.asarray(features,dtype=np.float32),
                 foul=np.asarray(labels,dtype=np.uint8),split=np.asarray(groups),event_uuid=np.asarray(ids),match_id=np.asarray(match_ids))
    return features if graph else np.asarray(features),np.asarray(labels),np.asarray(groups)

def main():
    x,y,group=training_data()
    train=group=='train'; val=group=='validation'; test=group=='test'
    candidates={'logistic':make_pipeline(StandardScaler(),LogisticRegression(max_iter=500)),
                'boosted trees':HistGradientBoostingClassifier(max_iter=110,max_leaf_nodes=15,l2_regularization=4,random_state=42)}
    scores={}
    for name,model in candidates.items():
        model.fit(x[train],y[train])
        scores[name]=float(average_precision_score(y[val],model.predict_proba(x[val])[:,1]))
    name=max(scores,key=scores.get)
    model=candidates[name]
    p,r,thresholds=precision_recall_curve(y[val],model.predict_proba(x[val])[:,1])
    threshold=float(thresholds[np.argmax((2*p*r/(p+r+1e-12))[:-1])])
    pred=model.predict_proba(x[test])[:,1]
    report=dict(source='StatsBomb 360 event snapshots; 0.5 to 2 seconds before recorded foul',selected=name,validation_AP=scores,threshold=threshold,
        split_counts={s:{'examples':int(sum(group==s)),'positives':int(sum(y[group==s]))} for s in ('train','validation','test')},
        test_average_precision=float(average_precision_score(y[test],pred)),test_prevalence=float(y[test].mean()),
        test_precision=float(precision_score(y[test],pred>=threshold,zero_division=0)),test_recall=float(recall_score(y[test],pred>=threshold)),test_confusion_matrix=confusion_matrix(y[test],pred>=threshold).tolist(),
        statsbomb_revision=REVISION)
    joblib.dump((model,threshold),ROOT/'models/forecast.joblib')
    (OUT/'evaluation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
if __name__=='__main__': main()

