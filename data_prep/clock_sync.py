import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Build inspection sheets from the original broadcast clocks before event alignment."""
import argparse
import cv2,numpy as np
from prepare import OUT
from match_corpus import BASE
from final_half import VIDEO

def paths():
    for p in sorted(BASE.glob('*/second.mp4')):yield p.parent.name,p
    if VIDEO.exists():yield 'ARG_FRA',VIDEO
def sheet(name,path,times,box=None):
    cap=cv2.VideoCapture(str(path));tiles=[]
    for t in times:
        cap.set(0,t*1000);ok,f=cap.read()
        if not ok:continue
        if box:
            h,w=f.shape[:2]; x1,y1,x2,y2=box
            f=f[round(h*y1):round(h*y2),round(w*x1):round(w*x2)]
        scale=(410 if box else 450)/f.shape[1]
        tile=cv2.resize(f,None,fx=scale,fy=scale)
        tile=cv2.copyMakeBorder(tile,19,0,0,0,cv2.BORDER_CONSTANT)
        cv2.putText(tile,f'{name}  {t:.2f} s',(5,14),0,.44,(0,225,255),1)
        tiles.append(tile)
    cap.release()
    if len(tiles)%2:tiles.append(np.zeros_like(tiles[0]))
    dest=OUT/'audit'/f'clock_{name}.jpg'
    cv2.imwrite(str(dest),np.vstack([np.hstack(tiles[i:i+2]) for i in range(0,len(tiles),2)]))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--box',nargs=4,type=float);p.add_argument('--times',nargs='+',type=float,default=[480,700,1500,2300,2800,3060]);p.add_argument('--game')
    a=p.parse_args()
    for name,path in paths():
        if a.game in (None,name):sheet(name,path,a.times,a.box)

