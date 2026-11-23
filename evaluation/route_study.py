import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Evaluate pre-contact camera framing at visually reviewed future contact locations."""
import json
import joblib
import numpy as np
from camera import Camera,blockage
from video_pose import CACHE,OUT,ROOT
from fit_video import RESULT,group_info,save_rows,read_rows
from anticipation import cached_states
from deployment_eval import clip_features
from in_play import Alarm,TargetHold

def point_on_view(cam,point):
    ray=cam.aim-cam.xyz;ray/=np.linalg.norm(ray)+1e-9
    right=np.cross(ray,[0,0,1]);right/=np.linalg.norm(right)+1e-9
    up=np.cross(right,ray)
    v=point-cam.xyz;depth=v@ray
    angle=np.degrees(np.arccos(np.clip(depth/np.linalg.norm(v),-1,1)))
    framed=depth>.4 and abs(440*v@right/depth)<=320 and abs(440*v@up/depth)<=180
    return int(framed),float(angle)

def run(uid,rows,art,ranker):
    path=CACHE/f'{uid}.npz'
    if uid.startswith('half_'):
        with np.load(OUT/'half_features'/f'{uid[5:]}.npz') as f:z=dict(f)
        with np.load(path) as f:z['cut']=f['cut']
    else:z=clip_features(uid)
    ts=z['t'];cuts=z['cut']
    model=art['model']
    prob=model.predict_series(z['x'],ts,cuts) if hasattr(model,'predict_series') else model.predict_proba(z['x'])[:,1]
    scores=np.where(z['valid'],prob,0.)
    cases=[]
    for row in rows:
        lo,hi,x,y=[float(row[k]) for k in ('lo_s','hi_s','x_frac','y_frac')]
        before=np.flatnonzero(ts<=lo-.5+1e-5)
        if not len(before):continue
        cutoff=int(before[-1]);contact=int(np.argmin(abs(ts-hi)))
        same_shot=not np.any(cuts[cutoff+1:contact+1])
        if uid=='half_ARG_FRA' and row['event_index']=='11':same_shot=False
        cases.append(dict(uid=uid,event=row.get('action',row.get('event_index')),lo=lo,hi=hi,fx=x,fy=y,
            cutoff=cutoff,contact=contact,same_shot=same_shot,target=np.array([(x-.5)*65,(1-y)*36,1.])))
    if not cases:return []
    fixed=Camera();alarm=Alarm(art['threshold']);hold=TargetHold();planned=Camera();survey=Camera()
    history=[];results=[];last=None;max_speed=max_accel=0.
    for i,(t,players,pairs,b,_) in enumerate(cached_states(path)):
        if cuts[i]:
            alarm=Alarm(art['threshold']);hold=TargetHold();planned=Camera();survey=Camera()
            history=[];max_speed=max_accel=0.
        onset,_=alarm.step(t,scores[i])
        pair=list(pairs[int(np.argmax(ranker.scores(b)))]) if onset and pairs else []
        if pair:history.append((t,np.mean([p['future'] for p in pair],axis=0)))
        selected=hold.step(t,players,pair,onset)
        dt=0 if last is None else t-last;v=planned.v.copy();last=t
        planned.step(players,selected,bool(selected),dt);survey.step(players,[],False,dt)
        max_speed=max(max_speed,float(np.linalg.norm(planned.v)))
        if dt:max_accel=max(max_accel,float(np.linalg.norm(planned.v-v)/dt))
        for c in cases:
            if i==c['cutoff']:
                alarms=[(a,p) for a,p in history if c['hi']-3.5<=a<=t]
                result=dict(uid=uid,event=c['event'],onset_lower_s=c['lo'],onset_upper_s=c['hi'],decision_s=t,
                    alert_before_contact=int(bool(alarms)),target_error_diagonal=None,lead_lower_s=None,
                    same_source_shot=int(c['same_shot']),max_speed_to_cutoff=max_speed,max_accel_to_cutoff=max_accel)
                if alarms:
                    a,p=alarms[-1]
                    result['lead_lower_s']=c['lo']-a
                    result['target_error_diagonal']=float(np.linalg.norm((p-c['target'][:2])/[65,36])/np.sqrt(2))
                c['poses']={}
                for label,cam in [('planned',planned),('survey',survey),('fixed',fixed)]:
                    framed,angle=point_on_view(cam,c['target'])
                    result[label+'_framed']=framed;result[label+'_angle_deg']=angle
                    c['poses'][label]=cam.xyz.copy()
                c['result']=result
            if i==c['contact']:
                res=c['result']
                # Treat the nearest detected person within a small radius as the subject.
                pos=[p['xy'] for p in players]
                if pos:
                    d=np.linalg.norm(np.asarray(pos)-c['target'][:2],axis=1)
                    if d.min()<2.:pos.pop(int(d.argmin()))
                for label,xyz in c['poses'].items():
                    res[label+'_framed_clear']=int(res[label+'_framed'] and blockage(xyz,c['target'],pos)<1e-6)
                results.append(res)
        if i>=max(c['contact'] for c in cases):break
    return results

def main():
    art=joblib.load(ROOT/'models/match_anticipation.joblib')
    ranker=joblib.load(ROOT/'models/video_anticipation.joblib')['ranker']
    groups=group_info();rows=[]
    for r in read_rows(OUT/'test_contact_review.csv'):
        uid=f"cas_test_foul_action_{r['action']}_clip_0"
        if groups[uid]['keep']=='1':rows.extend(run(uid,[r],art,ranker))
    rows+=run('half_ARG_FRA',read_rows(OUT/'final_contact_review.csv'),art,ranker)
    save_rows(RESULT/'camera_events.csv',rows)
    summary={}
    for name,sub in [('clip_review',[r for r in rows if r['uid'].startswith('cas_')]),('final_review',[r for r in rows if r['uid']=='half_ARG_FRA'])]:
        stable=[r for r in sub if r['same_source_shot']]
        alerted=[r for r in stable if r['alert_before_contact']]
        s=dict(events=len(sub),same_shot_events=len(stable),early_alerts=sum(r['alert_before_contact'] for r in sub),same_shot_alerts=len(alerted),target_within_10pct=sum(r['target_error_diagonal']<=.1 for r in alerted),
            median_target_error_diagonal=float(np.median([r['target_error_diagonal'] for r in alerted])) if alerted else None,
            max_speed=max(r['max_speed_to_cutoff'] for r in sub),max_accel=max(r['max_accel_to_cutoff'] for r in sub))
        for k in ('planned','fixed','survey'):
            s[k]=dict(framed=sum(r[k+'_framed'] for r in stable),framed_clear=sum(r[k+'_framed_clear'] for r in stable),
                median_angle_deg=float(np.median([r[k+'_angle_deg'] for r in stable])))
        summary[name]=s
    (RESULT/'camera_metrics.json').write_text(json.dumps(summary,indent=2))
    print(summary)
if __name__=='__main__':main()

