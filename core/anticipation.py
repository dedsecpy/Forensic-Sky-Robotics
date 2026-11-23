import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Causal player-pair pose and motion representation shared by training and the demo."""
from collections import deque
from itertools import combinations
import numpy as np
from scipy.spatial.distance import cdist
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

def body(p):
    k=p['joints']
    scale=max(8.,p['box'][3])
    def displacement(i,j):
        if min(k[i,2],k[j,2])<.25:return np.zeros(2)
        return (k[i,:2]-k[j,:2])/scale
    def angle(i,j,l):
        a,b=displacement(i,j),displacement(l,j)
        return float(np.clip((a@b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-6),-1,1))
    return np.array([angle(11,13,15),angle(12,14,16),
        np.linalg.norm(displacement(15,16)),abs(displacement(5,11)[0])+abs(displacement(6,12)[0]),
        np.linalg.norm(displacement(9,10)), min(2.,p['box'][2]/scale),
        np.median(k[5:,2])])

class PairHistory:
    def __init__(self):self.history=deque()
    def step(self,t,players):
        while self.history and self.history[0][0]<t-1.2:self.history.popleft()
        # Choose the newest observation at least 0.4 seconds old for fixed physical-time deltas.
        past=next(((s,h) for s,h in reversed(self.history) if t-s>=.4),None)
        current={p['id']:(p['xy'],body(p)) for p in players}
        self.history.append((t,current))
        pairs=[];vectors=[]
        for a,b in combinations(players,2):
            pa,fa=current[a['id']];pb,fb=current[b['id']]
            sep=pb-pa;dist=np.linalg.norm(sep)
            if dist>12:continue
            closing=0.;rel=0.;changes=np.zeros_like(fa)
            if past and a['id'] in past[1] and b['id'] in past[1]:
                dt=t-past[0];oa,ka=past[1][a['id']];ob,kb=past[1][b['id']]
                prev=ob-oa;closing=(np.linalg.norm(prev)-dist)/dt
                rel=np.linalg.norm(prev-sep)/dt
                changes=np.maximum(abs(fa-ka),abs(fb-kb))/dt
            approach=max(0,dist-max(0,closing)*1.)
            # Pair order independent, with no team, clock, pixels or clip ID as input.
            vec=np.r_[dist,abs(sep),np.clip(closing,-12,12),min(15,rel),approach,
                np.minimum(fa,fb),np.maximum(fa,fb),np.clip(changes,0,5)]
            pairs.append((a,b));vectors.append(vec)
        if not pairs:return [],np.zeros((0,27)),np.zeros(81)
        order=np.argsort([v[5]+.3*v[0] for v in vectors])[:8]
        v=np.stack(vectors)[order];pairs=[pairs[i] for i in order]
        return pairs,v,np.r_[v[0],np.mean(v[:3],axis=0),np.max(v,axis=0)]

class SoftEnsemble:
    """Average probabilities from several fitted estimators."""
    def __init__(self,members):self.members=list(members)
    def fit(self,x,y):return self
    def predict_proba(self,x):
        p=np.mean([m.predict_proba(x)[:,1] for m in self.members],axis=0)
        return np.c_[1-p,p]

class MIL:
    """Regularized multiple-instance logistic model with soft attention over candidate pairs."""
    def fit(self,bags,y):
        self.scale=StandardScaler().fit(np.vstack([b for b in bags if len(b)]))
        transformed=[self.scale.transform(b).clip(-6,6) if len(b) else np.zeros((1,27)) for b in bags]
        self.net=LogisticRegression(C=.05,class_weight='balanced',max_iter=300)
        pooled=np.stack([b.mean(0) for b in transformed])
        for _ in range(4):
            self.net.fit(pooled,y)
            pooled=[]
            for b in transformed:
                z=self.net.decision_function(b);w=np.exp(z-z.max())
                pooled.append(np.average(b,axis=0,weights=w))
        return self
    def scores(self,bag):
        if not len(bag):return np.array([])
        return self.net.decision_function(self.scale.transform(bag).clip(-6,6))
    def predict(self,bag):
        z=self.scores(bag)
        if not len(z):return 0.
        w=np.exp(z-z.max())
        return float(1/(1+np.exp(-np.average(z,weights=w))))

def cached_states(path):
    from vision import Tracker
    tracker=Tracker(); history=PairHistory()
    with np.load(path) as z:
        packed=z['people']; offsets=z['offsets']; shape=z['size']; times=z['t']; cuts=z['cut']
    for i,t in enumerate(times):
        if cuts[i]:tracker.tracks.clear();history=PairHistory()
        det=[(r[:4],r[4:].reshape(17,3)) for r in packed[offsets[i]:offsets[i+1]]]
        players=tracker.update(det,t,shape)
        pairs,features,pooled=history.step(t,players)
        yield float(t),players,pairs,features,pooled

