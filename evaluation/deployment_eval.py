import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Score every available clip with the continuous-match model at the app cadence."""
import json
import joblib
import numpy as np
from fit_video import RESULT,group_info,metrics,read_rows,save_rows
from anticipation import cached_states
from video_pose import CACHE,ROOT,OUT,sources
from in_play import BroadcastFeatures,Alarm

def clip_features(uid):
    dest=OUT/'clip_context'/f'{uid}.npz'
    if not dest.exists():
        dest.parent.mkdir(exist_ok=True)
        path=CACHE/f'{uid}.npz'
        with np.load(path) as obs:cuts=obs['cut'];duration=float(obs['duration'])
        history=BroadcastFeatures()
        ts=[];xs=[];valid=[]
        for cut,(t,players,pairs,b,x) in zip(cuts,cached_states(path)):
            if cut:history=BroadcastFeatures()
            ts.append(t);xs.append(history.step(t,players,pairs,b,x));valid.append(bool(pairs) and t>=.4)
        np.savez_compressed(dest,t=ts,x=np.asarray(xs,np.float32),valid=valid,cut=cuts,duration=duration)
    with np.load(dest) as z:return dict(z)

def main(cache_only):
    if not cache_only:
        art=joblib.load(ROOT/'models/match_anticipation.joblib');model=art['model'];th=art['threshold']
        quiet={r['uid'] for r in read_rows(OUT/'cup_audit.csv') if r['quiet']=='1'}
        groups=group_info()
    records=[];minutes=0;false=0;y=[];s=[]
    for uid,path,split,label in sources():
        z=clip_features(uid)
        if cache_only:continue
        prob=model.predict_series(z['x'],z['t'],z['cut']) if hasattr(model,'predict_series') else model.predict_proba(z['x'])[:,1]
        scores=np.where(z['valid'],prob,0.)
        alarm=Alarm(th);alerts=[]
        for cut,t,v in zip(z['cut'],z['t'],scores):
            if cut:alarm=Alarm(th)
            onset,_=alarm.step(t,v)
            if onset:alerts.append(round(float(t),3))
        if uid in quiet and split=='test':
            minutes+=float(z['duration'])/60;false+=len(alerts)
        i=np.argmin(abs(z['t']-1.5));prefix=float(scores[i])
        if uid in groups and groups[uid]['keep']=='1' and split=='test':y.append(int(label=='foul'));s.append(prefix)
        records.append(dict(uid=uid,split=split,label=label,seconds=float(z['duration']),observations=len(scores),
            score_at_1_5s=prefix,max_score=float(scores.max()),alarm_times_s=json.dumps(alerts)))
    if records:
        save_rows(RESULT/'deployment_clips.csv',records)
        (RESULT/'deployment_clips_metrics.json').write_text(json.dumps(dict(clips=len(records),clip_prefix=metrics(y,s,th),
            quiet_test_minutes=minutes,quiet_test_alarms=false,quiet_test_alarms_per_min=false/minutes),indent=2))

if __name__=='__main__':
    import sys
    main('--cache-only' in sys.argv)

