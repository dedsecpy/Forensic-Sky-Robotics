import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Five-observation causal temporal-convolution benchmark for match forecasting."""
from collections import deque
import numpy as np
import torch
from torch import nn
from sklearn.preprocessing import StandardScaler

class CausalTemporalForecast:
    def __init__(self):
        self.scale=StandardScaler()
        self.length=5
    def windows(self,x,t,cuts):
        left=0
        scaled=self.scale.transform(x[:,:109]).astype(np.float32).clip(-7,7)
        out=[]
        for i in range(len(t)):
            if cuts[i] or (i and t[i]-t[i-1]>1.):left=i
            idx=np.maximum(left,np.arange(i-4,i+1))
            out.append(scaled[idx])
        return np.stack(out)
    def fit_games(self,games):
        torch.manual_seed(101)
        torch.set_num_threads(3)
        self.scale.fit(np.vstack([g['x'][:,:109] for g in games]))
        x=torch.from_numpy(np.concatenate([self.windows(g['x'],g['t'],g['cut']) for g in games])).transpose(1,2)
        y=torch.from_numpy(np.concatenate([g['y'] for g in games])).float()
        self.net=nn.Sequential(nn.Conv1d(109,32,1),nn.ReLU(),nn.Dropout(.18),
            nn.Conv1d(32,24,3),nn.ReLU(),nn.Conv1d(24,1,3),nn.Flatten())
        opt=torch.optim.AdamW(self.net.parameters(),lr=.00065,weight_decay=.02)
        rng=np.random.default_rng(101);pp=np.flatnonzero(y.numpy());nnn=np.flatnonzero(y.numpy()==0)
        self.net.train()
        for _ in range(220):
            ids=np.r_[rng.choice(pp,16),rng.choice(nnn,112)]
            loss=nn.functional.binary_cross_entropy_with_logits(self.net(x[ids]).flatten(),y[ids])
            opt.zero_grad();loss.backward();opt.step()
        self.net.eval()
        self.prior_offset=float(np.log(y.mean().item()/(1-y.mean().item()))-np.log(16/112))
        return self
    def _predict(self,windows):
        with torch.inference_mode():
            x=torch.from_numpy(windows).transpose(1,2)
            return torch.cat([torch.sigmoid(self.net(b).flatten()+self.prior_offset) for b in x.split(256)]).numpy()
    def predict_series(self,x,t,cut):
        return self._predict(self.windows(x,t,cut))
    def predict_step(self,x,buffer):
        buffer.append(x)
        xs=np.stack(list(buffer))
        window=self.scale.transform(xs[:,:109]).clip(-7,7).astype(np.float32)
        window=np.pad(window,((self.length-len(window),0),(0,0)),mode='edge')
        return float(self._predict(window[None,:,:])[0])

