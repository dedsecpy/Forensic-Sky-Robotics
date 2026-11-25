import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
import argparse
import json
import math
from pathlib import Path
from datetime import datetime
import subprocess
import shutil
import cv2
import joblib
import numpy as np
from prepare import ROOT
from learning import History
from vision import Pose,Tracker,BONES
from camera import Camera,focus,blockage
from video_pose import Scout,HZ
from video_controller import VideoController
from display_pose import combine

def fit_image(im,w,h):
    sf=min(w/im.shape[1],h/im.shape[0])
    small=cv2.resize(im,None,fx=sf,fy=sf)
    canvas=np.zeros((h,w,3),np.uint8)
    y=(h-small.shape[0])//2; x=(w-small.shape[1])//2
    canvas[y:y+small.shape[0],x:x+small.shape[1]]=small
    return canvas

def annotate(im,players,ids):
    out=im.copy()
    for p in players:
        color=(60,202,255) if p['id'] in ids else (223,220,92)
        x,y,w,h=p['box'].astype(int)
        cv2.rectangle(out,(x,y),(x+w,y+h),color,1)
        cv2.putText(out,str(p['id']),(x,y-3),0,.44,color,1,cv2.LINE_AA)
        k=p['joints']
        for a,b in BONES:
            if min(k[a,2],k[b,2])>.35:
                cv2.line(out,tuple(k[a,:2].astype(int)),tuple(k[b,:2].astype(int)),color,2)
    return fit_image(out,640,360)

def analyze(clip, hz=HZ, calibration=None, progress=print):
    clip=Path(clip).resolve()
    cap=cv2.VideoCapture(str(clip))
    fps=cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or not math.isfinite(fps) or fps<=0: raise ValueError('Cannot read video or its frame rate.')
    interval=fps/min(fps,hz); dt=interval/fps
    frame_count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out=ROOT/'runs'/(clip.parent.name[:45]+'_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    out.mkdir(parents=True)
    H=None
    if calibration:
        c=json.loads(Path(calibration).read_text())
        H=cv2.getPerspectiveTransform(np.float32(c['image_xy']),np.float32(c['pitch_xy_m']))
    pose=Pose()
    try: scout=Scout('GPU')
    except RuntimeError: scout=Scout('CPU')
    controller=VideoController()
    selected='video pose / '+controller.name;threshold=controller.threshold
    camera=Camera();tracker=Tracker();close_tracker=Tracker()
    previous_bodies={}
    hold_until=-1.
    writer=cv2.VideoWriter(str(out/'replay.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),1/dt,(1280,418))
    if not writer.isOpened(): raise RuntimeError('Cannot create replay.mp4')
    n=frames=pose3=alerts=people=0
    last_hist=None; peak=None; hits=[]
    try:
        with (out/'telemetry.jsonl').open('w',encoding='utf8') as log:
            while cap.grab():
                if n!=round(frames*interval):
                    n+=1
                    continue
                ok,im=cap.retrieve()
                if not ok: raise ValueError(f'Cannot decode frame {n}')
                t=n/fps
                step_dt=(n-round((frames-1)*interval))/fps if frames else 0.
                signature=cv2.calcHist([cv2.resize(im,(96,54))],[0,1],None,[12,12],[0,256,0,256])
                cv2.normalize(signature,signature)
                if last_hist is not None and cv2.compareHist(signature,last_hist,cv2.HISTCMP_BHATTACHARYYA)>.55:
                    tracker.tracks.clear();controller.reset();camera=Camera()
                    close_tracker.tracks.clear()
                    previous_bodies={}; hold_until=-1.
                last_hist=signature
                players=tracker.update(scout.detect(im),t,im.shape)
                close=close_tracker.update(scout.close_players(im),t,im.shape)
                display_players=combine(players,close)
                score,pair=controller.score(t,players)
                onset,alarm_hold=controller.alarm.step(t,score if score is not None else 0.)
                pair=controller.target.step(t,players,pair,onset)
                alert=bool(pair)
                ids={p['id'] for p in pair} if alert else set()
                if H is not None:
                    # Preserve the score's training coordinate system; map only the simulator's copy.
                    def mapped(player):
                        p=dict(player)
                        for key in ('xy','future'):
                            x,y=p[key]
                            px=np.array([[(x/65+.5)*im.shape[1],(1-y/36)*im.shape[0]]])
                            p[key]=cv2.perspectiveTransform(px.reshape(1,1,2),H)[0,0]
                        return p
                    players=[mapped(p) for p in players]
                    pair=[mapped(p) for p in pair]
                    display_players=[mapped(p) for p in display_players]
                bodies={}
                for p in display_players:
                    body=pose.body3d(im,p['box'])
                    if body is not None:
                        bodies[p['id']]=body
                        prev=previous_bodies.get(p['id'])
                        if prev is not None:
                            good=(body[13:,3]>.55)&(prev[13:,3]>.55)
                            if good.any():
                                p['leg_motion']=float(np.max(np.linalg.norm((body[13:,:3]-prev[13:,:3])[good],axis=1))/dt)
                previous_bodies=bodies
                camera.step(players,pair,alert,step_dt)
                sim=camera.render(display_players,ids,bodies)
                a=annotate(im,display_players,ids)
                panel=np.zeros((418,1280,3),np.uint8)
                panel[:360]=np.hstack([a,sim])
                state='ANTICIPATE CONTACT' if alert else 'SURVEY'
                cv2.putText(panel,f'BROADCAST   {t:05.2f}s    {len(display_players)} tracks',(12,383),0,.58,(230,230,230),1,cv2.LINE_AA)
                risk=f'{score:.3f}' if score is not None else 'insufficient tracks'
                cv2.putText(panel,f'Scene score {risk}    Trigger {threshold:.3f}',(12,405),0,.53,(195,195,195),1,cv2.LINE_AA)
                cv2.putText(panel,'VIRTUAL SKYCAM   '+state,(652,383),0,.60,(80,205,255),1,cv2.LINE_AA)
                cv2.putText(panel,f'{len(bodies)} estimated 3D poses   |   '+('calibrated plane' if H is not None else 'approximate pitch layout'),(652,405),0,.5,(200,200,200),1,cv2.LINE_AA)
                writer.write(panel)
                obs=[p['xy'] for p in players if p['id'] not in ids]
                blocked=[blockage(camera.xyz,np.r_[p['xy'],1.],obs) for p in pair] if alert else []
                fixed=[blockage(np.array([0.,-9.,13.]),np.r_[p['xy'],1.],obs) for p in pair] if alert else []
                if alert: hits.append([float(np.mean(np.array(blocked)==0)),float(np.mean(np.array(fixed)==0))])
                cam_speed=float(np.linalg.norm(camera.v))
                rec=dict(time=t,score=score,alert=alert,alarm_onset=bool(onset),alarm_hold=bool(alarm_hold),
                         threshold=float(threshold),target_ids=sorted(ids),
                         camera_xyz=camera.xyz.tolist(),camera_dest=camera.dest.tolist(),
                         camera_speed=cam_speed,look_at=camera.aim.tolist(),players=[
                    dict(id=p['id'],forecast_track=p['id']<1000000,xy=p['xy'].tolist(),future_xy=p['future'].tolist(),leg_motion_mps=p.get('leg_motion'),joints_2d=p['joints'].tolist(),hip_relative_3d=bodies[p['id']].tolist() if p['id'] in bodies else None) for p in display_players])
                log.write(json.dumps(rec)+'\n')
                if onset and score is not None and (peak is None or score>peak[0]): peak=(score,t)
                frames+=1; people+=len(display_players); pose3+=len(bodies); alerts+=alert
                ui=dict(time=t,score=score,alert=alert,alarm_onset=bool(onset),alarm_hold=bool(alarm_hold),
                        threshold=float(threshold),target_ids=sorted(ids),
                        camera_xyz=camera.xyz.tolist(),camera_dest=camera.dest.tolist(),
                        camera_speed=cam_speed,look_at=camera.aim.tolist(),
                        players_xy=[p['xy'].tolist() for p in display_players[:16]],
                        pair_xy=[p['xy'].tolist() for p in pair] if pair else [])
                try:
                    progress(f'{min(n+1,frame_count)}/{frame_count} frames  |  {state}',telemetry=ui,frame=panel)
                except TypeError:
                    progress(f'{min(n+1,frame_count)}/{frame_count} frames  |  {state}')
                n+=1
    finally:
        cap.release(); writer.release(); pose.close()
    if not frames: raise ValueError('Clip contains no readable frames')
    summary=dict(source=str(clip),model=selected,threshold=threshold,source_fps=fps,analysis_hz=1/dt,analyzed_frames=frames,player_observations=people,estimated_3d_poses=pose3,alerts=alerts,peak_alert=peak,
                 simulated_visibility_planned_fixed=np.mean(hits,axis=0).tolist() if hits else None)
    if peak and shutil.which('ffmpeg'):
        start=max(0,peak[1]-2)
        subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-ss',str(start),'-i',str(clip),'-t',str(peak[1]+2-start),'-map','0:v:0','-an','-c:v','libx264','-crf','18',str(out/'incident.mp4')],check=True)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('clip',type=Path)
    parser.add_argument('--hz',type=float,default=HZ,choices=[2,4,6,10,15,30])
    parser.add_argument('--calibration',type=Path)
    args=parser.parse_args()
    print(analyze(args.clip,args.hz,args.calibration))

