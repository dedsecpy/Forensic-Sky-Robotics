import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Learn which visible region will be closest to a forthcoming recorded foul."""
import bisect
import csv
import json
import subprocess
from collections import defaultdict
import joblib
import numpy as np
from scipy.spatial.distance import cdist
from sklearn.ensemble import HistGradientBoostingClassifier
from prepare import OUT, ROOT, REVISION, seconds

def neighborhoods(xy):
    xy=np.asarray(xy)
    offsets=xy[:,None,:]-xy[None,:,:]
    distances=np.linalg.norm(offsets,axis=2)
    np.fill_diagonal(distances,np.inf)
    sorted_dist=np.sort(distances,axis=1)
    features=[np.minimum(40,sorted_dist[:,min(i,len(xy)-2)]) for i in (0,1,2,4)]
    features.extend((distances<r).sum(axis=1) for r in (2,5,10))
    features.append(np.linalg.norm(xy-np.median(xy,axis=0),axis=1))
    # Rotationally invariant dispersion of nearby directions.
    weight=np.exp(-np.minimum(distances,150)/6)
    direction=offsets/np.maximum(1e-5,distances[:,:,None])
    features.append(np.linalg.norm((weight[:,:,None]*direction).sum(axis=1),axis=1)/(weight.sum(axis=1)+1e-8))
    return np.column_stack(features)

def main():
    rows=list(csv.DictReader((OUT/'clips.csv').open(encoding='utf8')))
    groups=defaultdict(list)
    for mid,split in sorted({(r['match_id'],r['split']) for r in rows}):
        es=json.loads((OUT/f'statsbomb/{mid}.json').read_bytes())
        lookup={e['id']:e for e in es}
        frames=json.loads(subprocess.check_output(['git','-C',str(OUT/'statsbomb_repo'),'show',f'{REVISION}:data/three-sixty/{mid}.json']))
        fouls=defaultdict(list)
        for e in es:
            if e['type']['name']=='Foul Committed' and 'location' in e:
                fouls[e['period']].append((seconds(e),e))
        for f in frames:
            e=lookup.get(f['event_uuid'])
            if e is None or len(f['freeze_frame'])<4: continue
            t=seconds(e); ff=fouls[e['period']]
            ix=bisect.bisect_left(ff,t,key=lambda item:item[0])
            if ix==len(ff) or not .5<=ff[ix][0]-t<=2: continue
            foul=ff[ix][1]
            loc=np.array(foul['location'][:2])
            if foul['team']['id']!=e['team']['id']: loc=[120,80]-loc
            xy=np.array([p['location'] for p in f['freeze_frame']])*[105/120,68/80]
            ds=np.linalg.norm(xy-np.asarray(loc)*[105/120,68/80],axis=1)
            if ds.min()>8: continue
            groups[split].append((neighborhoods(xy),ds,xy))
    train=groups['train']
    model=HistGradientBoostingClassifier(max_iter=80,max_leaf_nodes=12,l2_regularization=3,random_state=42)
    model.fit(np.vstack([x for x,d,xy in train]),np.concatenate([np.arange(len(d))==d.argmin() for x,d,xy in train]))
    joblib.dump(model,ROOT/'models/targets.joblib')
    report={}
    for split in ('validation','test'):
        hits=[]; baseline=[]; errors=[]
        for x,d,xy in groups[split]:
            pred=np.argsort(model.predict_proba(x)[:,1])[-2:]
            hits.append(d.argmin() in pred)
            distances=cdist(xy,xy);np.fill_diagonal(distances,np.inf)
            baseline.append(d.argmin() in np.unravel_index(distances.argmin(),distances.shape))
            errors.append(d[pred].min())
        report[split]=dict(scenes=len(hits),top2_location_hit=float(np.mean(hits)),closest_pair_baseline=float(np.mean(baseline)),median_distance_m=float(np.median(errors)))
    (OUT/'target_evaluation.json').write_text(json.dumps(report,indent=2))
    print(report)
if __name__=='__main__': main()

