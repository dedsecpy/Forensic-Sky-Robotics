import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Outcome-side inspection only. Never import this module when scoring video."""
import argparse,json
import cv2,numpy as np
from prepare import OUT
from clock_sync import paths
from half_features import reference
from align_halves import map_clock

def generate(name,path):
    ref,end=reference(name)
    sync=json.loads((OUT/'alignment'/f'{name}.json').read_text())
    tt=np.arange(0,sync['duration'],.05)
    cc=map_clock(sync,tt)
    cap=cv2.VideoCapture(str(path));folder=OUT/'audit';rows=[]
    for i,event in enumerate(ref):
        if np.nanmin(abs(cc-event))>.15:continue
        vt=tt[np.nanargmin(abs(cc-event))];cells=[]
        for delta in [-2,-1.5,-1,-.5,0,.5,1]:
            cap.set(0,(vt+delta)*1000);ok,im=cap.read()
            if not ok:raise RuntimeError(name)
            thumb=cv2.resize(im,(210,120))
            cv2.putText(thumb,f'{i} {delta:+.1f}',(1,117),0,.42,(0,255,255),1)
            cells.append(thumb)
        rows.append(np.hstack(cells))
    cap.release()
    for start in range(0,len(rows),4):cv2.imwrite(str(folder/f'{name}_{start}.jpg'),np.vstack(rows[start:start+4]))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('games',nargs='*');args=p.parse_args()
    for n,path in paths():
        if n in args.games:generate(n,path)

