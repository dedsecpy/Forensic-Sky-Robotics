import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""The same pre-contact scorer and targeting rule run in replay and evaluation."""
import joblib
from collections import deque
import numpy as np
from prepare import ROOT
from anticipation import PairHistory
from in_play import BroadcastFeatures,Alarm,TargetHold

class VideoController:
    def __init__(self):
        artifact=joblib.load(ROOT/'models/video_anticipation.joblib')
        self.model=artifact['model']
        self.ranker=artifact['ranker']
        self.name=artifact['name']
        self.threshold=artifact['threshold']
        self.history=PairHistory()
        self.match_model=None
        match_path=ROOT/'models/match_anticipation.joblib'
        if match_path.exists():
            final=joblib.load(match_path)
            self.match_model=final['model'];self.threshold=final['threshold'];self.name=final['name']
        self.context=BroadcastFeatures()
        self.sequence=deque(maxlen=5)
        self.alarm=Alarm(self.threshold)
        self.target=TargetHold()
    def reset(self):
        self.sequence.clear()
        self.history=PairHistory()
        self.context=BroadcastFeatures()
        self.alarm=Alarm(self.threshold)
        self.target=TargetHold()
    def score(self,t,players):
        pairs,bag,scene=self.history.step(t,players)
        state=self.context.step(t,players,pairs,bag,scene)
        temporal=self.match_model.predict_step(state,self.sequence) if hasattr(self.match_model,'predict_step') else None
        if not pairs or t<.4:return None,[]
        z=self.ranker.scores(bag)
        pair=list(pairs[int(np.argmax(z))])
        if self.match_model is not None:
            if temporal is not None:return temporal,pair
            return float(self.match_model.predict_proba(state[None,:])[0,1]),pair
        if self.name=='pose-MIL':
            return self.ranker.predict(bag),pair
        return float(self.model.predict_proba(scene[None,:])[0,1]),pair

