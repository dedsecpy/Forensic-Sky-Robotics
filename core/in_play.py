import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Past-only broadcast features and the causal alarm state machine."""
from collections import deque
import numpy as np
from anticipation import PairHistory

class BroadcastFeatures:
    def __init__(self):self.history=deque()
    def step(self,t,players,pairs,bag,x):
        # View-relative location helps distinguish incidental off-ball crowding.
        if pairs:
            centers=np.array([(a['xy']+b['xy'])/2 for a,b in pairs])
            order=np.argmin(np.linalg.norm((centers-[0,18])/[32.5,18],axis=1))
            central=bag[order]
            contexts=np.r_[centers[0],centers[order],central[:6],central[6:20]]
        else:contexts=np.zeros(24)
        speed=[np.linalg.norm(p['future']-p['xy'])/1.2 for p in players]
        static=np.r_[x,contexts,len(players),np.percentile(speed,[25,50,90]) if speed else [0,0,0]]
        while self.history and t-self.history[0][0]>2.1:self.history.popleft()
        self.history.append((t,static))
        recent=np.stack([s for _,s in self.history])
        return np.r_[static,recent.mean(0),recent.max(0)-recent.min(0)]

class Alarm:
    def __init__(self,threshold):
        self.threshold=threshold;self.last=-100.;self.armed=True
    def step(self,t,score):
        if score<self.threshold:self.armed=True
        onset=self.armed and score>=self.threshold and t-self.last>=2.
        if onset:self.last=t;self.armed=False
        return onset,t-self.last<.75

class TransferForecast:
    """Fine-tune the decision on continuous match examples using a frozen clip-level score."""
    def __init__(self,clip_model,match_model):
        self.clip_model=clip_model
        self.match_model=match_model
    def inputs(self,x):
        return np.column_stack([x,self.clip_model.predict_proba(x[:,:81])[:,1]])
    def fit(self,x,y):
        self.match_model.fit(self.inputs(x),y)
        return self
    def predict_proba(self,x):
        return self.match_model.predict_proba(self.inputs(x))

class TargetHold:
    """Retain the threatened pair long enough to cover the forecast horizon."""
    def __init__(self):
        self.saved=[];self.until=-1.
    def step(self,t,players,pair,onset):
        if onset and pair:
            self.saved=[dict(p) for p in pair];self.until=t+2.
        if t>self.until:return []
        visible={p['id']:p for p in players}
        # Preserve the last predicted waypoint through a brief loss of the original track.
        self.saved=[dict(visible.get(p['id'],p)) for p in self.saved]
        return self.saved

