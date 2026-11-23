import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
import json,time
from pathlib import Path
import numpy as np
from prepare import OUT, seconds
from match_corpus import GAMES,BASE
from final_half import FOLDER
from video_pose import CACHE
from anticipation import cached_states
from in_play import BroadcastFeatures
from align_halves import map_clock

def events(name):
    folder=FOLDER if name=='ARG_FRA' else BASE/name
    return [e for e in json.loads((folder/'events.json').read_bytes()) if e['period']==2]

def reference(name):
    es=events(name)
    # Merge duplicate foul reports at identical times. Keep handballs and offensive fouls.
    times=sorted(set(seconds(e) for e in es if e['type']['name']=='Foul Committed'))
    return np.array(times),max(seconds(e) for e in es if e['type']['name']=='Half End')

def build(name):
    path=CACHE/f'half_{name}.npz'
    out=OUT/'half_features';out.mkdir(exist_ok=True)
    dest=out/f'{name}.npz'
    if dest.exists():return
    while not path.exists():time.sleep(2)
    hist=BroadcastFeatures();ts=[];features=[];valid=[]
    with np.load(path) as z:cuts=z['cut']
    for i,(t,players,pairs,b,x) in enumerate(cached_states(path)):
        if cuts[i]:hist=BroadcastFeatures()
        features.append(hist.step(t,players,pairs,b,x))
        ts.append(t);valid.append(bool(pairs))
    np.savez_compressed(dest,t=ts,x=np.asarray(features,np.float32),valid=valid)
    print('features ready',name,len(ts),flush=True)

def aligned(name):
    z=np.load(OUT/'half_features'/f'{name}.npz');t=z['t']
    alignment=json.loads((OUT/'alignment'/f'{name}.json').read_text())
    c=map_clock(alignment,t);ev,end=reference(name)
    mask=np.isfinite(c)&(c>=0)&(c<=end)
    # Only test events for which a pre-event observation window exists in the broadcast.
    ev=np.array([s for s in ev if np.any(mask&(c<=s-.75)&(c>=s-2.))])
    diffs=ev[None,:]-c[:,None]
    y=np.any((diffs>=.75)&(diffs<=2),axis=1)
    with np.load(CACHE/f'half_{name}.npz') as poses:cuts=poses['cut'][mask]
    return dict(game=name,t=t[mask],clock=c[mask],cut=cuts,x=z['x'][mask],valid=z['valid'][mask],y=y[mask].astype(int),events=ev)

if __name__=='__main__':
    # Process finished broadcasts as they arrive.
    names=['ARG_FRA']+[g[0] for g in GAMES]
    while names:
        for name in list(names):
            if (CACHE/f'half_{name}.npz').exists():
                build(name);names.remove(name)
        if names:time.sleep(2)

