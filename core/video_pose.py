import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""CPU-friendly pitch proposals, pose inference and reproducible per-video cache."""
import argparse
import csv
import time
from pathlib import Path
import cv2
import numpy as np
import openvino as ov
from prepare import ROOT, OUT

HZ=2
CACHE=OUT/'video_pose_v1'

class Scout:
    def __init__(self,device='CPU'):
        core=ov.Core()
        net=core.read_model(str(ROOT/'models/scout.onnx'))
        net.reshape([1,3,640,640])
        self.net=core.compile_model(net,device,{'INFERENCE_NUM_THREADS':4} if device=='CPU' else {})
    def close_players(self,frame):
        h,w=frame.shape[:2]
        scale=640/max(w,h);rw,rh=round(w*scale),round(h*scale)
        x0=(640-rw)//2;y0=(640-rh)//2
        tile=np.full((640,640,3),114,np.uint8)
        tile[y0:y0+rh,x0:x0+rw]=cv2.resize(frame,(rw,rh))
        raw=self.net(cv2.dnn.blobFromImage(tile,1/255,swapRB=True))[0][0].T
        boxes=[];scores=[];landmarks=[]
        for row in raw[(raw[:,4]>.25)&(raw[:,3]>=.14*h*scale)]:
            x,y,bw,bh=row[:4]
            boxes.append([(x-bw/2-x0)/scale,(y-bh/2-y0)/scale,bw/scale,bh/scale])
            k=row[5:].reshape(17,3).copy()
            k[:,:2]=(k[:,:2]-[x0,y0])/scale
            landmarks.append(k);scores.append(float(row[4]))
        return [(np.asarray(boxes[i]),landmarks[i]) for i in np.asarray(cv2.dnn.NMSBoxes(boxes,scores,.25,.45)).flatten()]

    def detect(self,frame):
        h,w=frame.shape[:2]
        # Segment players against local turf; aggregate crops into one neural inference.
        small=cv2.resize(frame,(800,round(800*h/w)))
        hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
        grass=cv2.inRange(hsv,(24,37,35),(96,255,255))
        pitch=cv2.morphologyEx(grass,cv2.MORPH_CLOSE,np.ones((17,17),np.uint8))
        pitch=cv2.erode(pitch,np.ones((5,5),np.uint8))
        fg=cv2.bitwise_and(pitch,cv2.bitwise_not(grass))
        fg=cv2.morphologyEx(fg,cv2.MORPH_CLOSE,np.ones((5,3),np.uint8))
        contours,_=cv2.findContours(fg,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        rects=[]
        for contour in contours:
            x,y,bw,bh=cv2.boundingRect(contour)
            if 6<=bh<=125 and 2<=bw<=1.6*bh and bw*bh>23:
                rects.append((x+bw/2,y+bh/2,max(14,bh*1.7,bw*1.7)))
        rects=sorted(rects,key=lambda p:-p[2])[:36]
        side=640//max(1,int(np.ceil(np.sqrt(len(rects)))))
        canvas=np.full((640,640,3),114,np.uint8)
        mapping=[]
        for i,(x,y,sz) in enumerate(rects):
            sz=max(8,round(sz*w/800))
            cx,cy=x*w/800,y*w/800
            tile=cv2.getRectSubPix(frame,(sz,sz),(cx,cy))
            col=i%(640//side)*side; row=i//(640//side)*side
            canvas[row:row+side,col:col+side]=cv2.resize(tile,(side,side))
            mapping.append((col,row,cx-sz/2,cy-sz/2,sz/side))
        if not mapping:return []
        blob=cv2.dnn.blobFromImage(canvas,1/255,swapRB=True)
        pred=self.net(blob)[0][0].T
        boxes=[];joints=[];scores=[]
        for r in pred[pred[:,4]>.18]:
            x,y,bw,bh=r[:4]
            idx=int(y//side)*(640//side)+int(x//side)
            if not 0<=idx<len(mapping):continue
            col,row,ox,oy,scale=mapping[idx]
            if abs(x-col-side/2)>side*.36 or abs(y-row-side/2)>side*.37:continue
            box=[ox+(x-col-bw/2)*scale,oy+(y-row-bh/2)*scale,bw*scale,bh*scale]
            k=r[5:].reshape(17,3).copy()
            k[:,:2]=(k[:,:2]-[col,row])*scale+[ox,oy]
            boxes.append(box);joints.append(k);scores.append(float(r[4]))
        return [(np.array(boxes[i]),joints[i]) for i in np.asarray(cv2.dnn.NMSBoxes(boxes,scores,.18,.45)).flatten()]

def sources():
    for p in sorted((ROOT/'datasets/cas_fd').glob('*/*/*.mp4')):
        partition=p.parent.parent.name
        yield 'cas_'+partition+'_'+p.parent.name+'_'+p.stem,p,('val' if partition=='valid' else partition),p.parent.name
    with (OUT/'clips.csv').open(encoding='utf8') as f:
        for r in csv.DictReader(f):
            yield r['uid'],ROOT/r['clip'],r['split'],'worldcup'

def extract(det,uid,path):
    dest=CACHE/(uid+'.npz')
    if dest.exists():return
    cap=cv2.VideoCapture(str(path))
    fps=cap.get(5)
    if fps<=0:raise ValueError(str(path))
    idx=0;ts=[];packed=[];offsets=[0];cuts=[];prev=None
    while cap.grab():
        if idx==round(len(ts)*fps/HZ):
            ok,im=cap.retrieve()
            if not ok:raise ValueError(str(path))
            h,w=im.shape[:2]
            sig=cv2.calcHist([cv2.resize(im,(96,54))],[0,1],None,[12,12],[0,256,0,256])
            cv2.normalize(sig,sig)
            cuts.append(prev is not None and cv2.compareHist(sig,prev,cv2.HISTCMP_BHATTACHARYYA)>.55)
            prev=sig
            for box,k in det.detect(im):packed.append(np.r_[box,k.flatten()])
            ts.append(idx/fps);offsets.append(len(packed))
        idx+=1
    cap.release()
    if not ts:raise ValueError(str(path))
    tmp=dest.with_suffix('.part.npz')
    np.savez_compressed(tmp,t=ts,offsets=offsets,people=np.asarray(packed,np.float32).reshape(-1,55),size=[h,w],cut=cuts,duration=idx/fps)
    tmp.replace(dest)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--device',default='CPU')
    parser.add_argument('--subset',choices=['all','cas','worldcup'],default='all')
    args=parser.parse_args()
    cv2.setNumThreads(1)
    CACHE.mkdir(parents=True,exist_ok=True)
    det=Scout(args.device)
    files=[r for r in sources() if args.subset=='all' or (r[3]=='worldcup')==(args.subset=='worldcup')]
    for i,(uid,path,split,label) in enumerate(files):
        extract(det,uid,path)
        if i%50==0:print(i,len(files),flush=True)

