import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""KTH Multiview Football II, player 2 sequence 1. External pose evaluation."""
import json
import zipfile
from collections import defaultdict
import cv2
import numpy as np
from prepare import ROOT,download
from fit_video import RESULT,save_rows
from vision import Pose
from video_pose import Scout
from display_pose import combine,iou

DATA=ROOT/'datasets/kth_pose'
BASE='https://www.csc.kth.se/cvap/cvg/MultiViewFootballData/'
# KTH's first 12 joints in the app's COCO order. Head definitions differ.
JOINTS=[16,14,12,11,13,15,10,8,6,5,7,9]

def pose_errors(pred,xy,true2,true3,cam):
    p=pred[JOINTS][:,[0,2,1]].copy();p[:,1]*=-1
    rot=cam[:,:3]/np.linalg.norm(cam[:,:3],axis=1,keepdims=True)
    r=np.vstack([rot,np.cross(*rot)])
    g=true3[:12]@r.T
    def torso(a):return np.linalg.norm(a[[8,9]].mean(0)-a[[2,3]].mean(0))
    p=(p-p[[2,3]].mean(0))/torso(p)
    g=(g-g[[2,3]].mean(0))/torso(g)
    error=np.linalg.norm(p-g,axis=1)
    # Similarity Procrustes fit, excluding mirror reflections.
    a=p-p.mean(0);b=g-g.mean(0)
    u,sv,vt=np.linalg.svd(a.T@b)
    sign=np.array([1,1,np.sign(np.linalg.det(u@vt))])
    pa=(a@(u@np.diag(sign)@vt))*(sv@sign)/(a*a).sum()
    img_error=np.linalg.norm(xy[JOINTS]-true2[:12],axis=1)
    return dict(torso_MPJPE=float(error.mean()),torso_PA_MPJPE=float(np.linalg.norm(pa-b,axis=1).mean()),
        PCK20_torso=float(np.mean(img_error<=.2*torso(true2))),mean_2d_px=float(img_error.mean()))

def evaluate(sequence):
    name=f'player2sequence{sequence}.zip'
    for n in [name,'code3d.zip']:download(BASE+n,DATA/n)
    pose=Pose()
    try:scout=Scout('GPU')
    except RuntimeError:scout=Scout('CPU')
    rows=[];reproj=[];matched=0
    with zipfile.ZipFile(DATA/name) as z:
        names=z.namelist()
        def path(s):return next(n for n in names if n.endswith('/'+s))
        def points(s):return np.loadtxt(z.open(path(s)))
        p2=points('positions2d.txt').reshape(-1,3,14,2)
        p3=points('positions3d.txt').reshape(-1,14,3)
        cams=points('cameras.txt').reshape(-1,3,4,2).transpose(0,1,3,2)
        pictures=sorted(n for n in names if n.lower().endswith('.png'))
        for name in pictures:
            camera=int(name.split('/')[-2].split()[-1])-1
            frame=int(name.split('/')[-1].split('.')[0])-1
            im=cv2.imdecode(np.frombuffer(z.read(name),np.uint8),cv2.IMREAD_COLOR)
            joints=p2[frame,camera];cam=cams[frame,camera];gt=p3[frame]
            reproj.extend(np.linalg.norm(np.c_[gt,np.ones(14)]@cam.T-joints,axis=1))
            lo=joints.min(0)-1;hi=joints.max(0)-1
            box=np.r_[lo,hi-lo]
            def tracks(dets):return [dict(id=i,box=b,joints=k) for i,(b,k) in enumerate(dets)]
            wide=tracks(scout.detect(im));merged=combine(wide,tracks(scout.close_players(im)))
            def nearest(tracks):return max((p['box'] for p in tracks),key=lambda b:iou(b,box),default=None)
            for mode,bbox in [('annotated_crop',box),('wide_only',nearest(wide)),('pipeline',nearest(merged))]:
                rec=dict(mode=mode,camera=camera+1,frame=frame+1,detected=0,torso_MPJPE=None,torso_PA_MPJPE=None,PCK20_torso=None,mean_2d_px=None)
                if bbox is not None and (mode=='annotated_crop' or iou(bbox,box)>=.30):
                    if mode=='pipeline':matched+=1
                    out=pose.body3d(im,bbox,with_image=True)
                    if out is not None:
                        rec.update(pose_errors(*out,joints-1,gt,cam));rec['detected']=1
                rows.append(rec)
    pose.close()
    save_rows(RESULT/f'pose_images_{sequence}.csv',rows)
    report=dict(sequence=f'KTH player 2 sequence {sequence}',images=len(pictures),frames=len(p2),views=3,
        joints=12,matched_boxes_at_IoU_030=matched,mean_reference_reprojection_px=float(np.mean(reproj)))
    for mode in ['annotated_crop','wide_only','pipeline']:
        part=[r for r in rows if r['mode']==mode];ok=[r for r in part if r['detected']]
        report[mode]=dict(returned=len(ok),coverage=len(ok)/len(part),PCK20_including_misses=sum(r['PCK20_torso'] for r in ok)/len(part))
        if ok:report[mode].update({k:float(np.mean([r[k] for r in ok])) for k in ['torso_MPJPE','torso_PA_MPJPE','PCK20_torso','mean_2d_px']})
    print(report,flush=True)
    return report
if __name__=='__main__':
    results={}
    for sequence in (1,2):
        results[str(sequence)]=evaluate(sequence)
    (RESULT/'pose_metrics.json').write_text(json.dumps(results,indent=2))

