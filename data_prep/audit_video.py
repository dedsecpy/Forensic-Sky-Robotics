import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Render a blind contact sheet with frame times and normalized coordinate guides."""
from pathlib import Path
import argparse,cv2,numpy as np
from prepare import ROOT,OUT
def sheet(folder,start):
    files=sorted(folder.glob('*.mp4'),key=lambda p:int(p.stem.split('_')[1]))[start:start+5]
    rows=[]
    for p in files:
        cap=cv2.VideoCapture(str(p));cells=[]
        for t in [1,1.5,2,2.5,3,3.5,4]:
            cap.set(0,t*1000);ok,im=cap.read()
            im=cv2.resize(im,(205,116)) if ok else np.zeros((116,205,3),np.uint8)
            cv2.putText(im,f'{p.stem.split("_")[1]} @{t:g}',(2,13),0,.40,(0,255,255),1)
            for i in range(1,10):
                col=(230,180,135)
                cv2.line(im,(i*20,109),(i*20,115),col,1)
                cv2.line(im,(200,i*11),(204,i*11),col,1)
            cells.append(im)
        cap.release();rows.append(np.hstack(cells))
    out=OUT/'audit';out.mkdir(exist_ok=True)
    dest=out/f'{folder.parent.name}_{folder.name}_{start}.jpg'
    cv2.imwrite(str(dest),np.vstack(rows))
    return dest
if __name__=='__main__':
    for i in range(0,50,5):sheet(ROOT/'datasets/cas_fd/test/foul',i)

