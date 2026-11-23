import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Two-frame player graph network. Nodes represent visible players in each snapshot."""
from collections import deque
import numpy as np
import torch
from torch import nn
from targets import neighborhoods

MAX=24

def encode(xy):
    xy=np.asarray(xy)[:MAX]
    k=len(xy)
    f=np.zeros((MAX,10),dtype='float32')
    f[:k,:9]=np.log1p(neighborhoods(xy))
    f[:k,9]=1
    adj=np.zeros((MAX,MAX),dtype='float32')
    d=np.linalg.norm(xy[:,None]-xy[None,:],axis=2)
    edges=np.exp(-d/5)*(d<15)
    adj[:k,:k]=edges/edges.sum(axis=1,keepdims=True)
    return f,adj

class GraphHistory:
    def __init__(self): self.q=deque()
    def features(self,t,points):
        while self.q and self.q[0][0]<t-1.5: self.q.popleft()
        cur=encode(points)
        old=self.q[0][1] if self.q and t-self.q[0][0]>=.25 else cur
        self.q.append((t,cur))
        return tuple(np.stack([a,b]) for a,b in zip(old,cur))

class GraphForecast(nn.Module):
    def __init__(self):
        super().__init__()
        self.node=nn.Sequential(nn.Linear(10,20),nn.ReLU())
        self.message=nn.Sequential(nn.Linear(40,20),nn.ReLU())
        self.temporal=nn.Sequential(nn.Linear(80,32),nn.ReLU(),nn.Dropout(.15),nn.Linear(32,1))
    def forward(self,f,a):
        h=self.node(f)
        h=self.message(torch.cat([h,a@h],dim=-1))
        mask=f[:,:,:,9:10]
        mean=(h*mask).sum(dim=2)/mask.sum(dim=2).clamp_min(1)
        peak=h.masked_fill(mask==0,-1000).amax(dim=2)
        z=torch.cat([mean,peak],dim=-1)
        return self.temporal(torch.cat([z[:,1],z[:,1]-z[:,0]],dim=-1)).flatten()

