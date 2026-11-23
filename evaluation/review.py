import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Manually review contact times and compare event timing with a completed analysis."""
import argparse
import json
from pathlib import Path
import cv2
from prepare import ROOT

def evaluate(times, timeline):
    # One alarm per continuous alert episode. Match at most one event and alarm.
    previous=False
    onsets=[]
    for row in timeline:
        if row.get('alarm_onset',row['alert'] and not previous):onsets.append(row['time'])
        previous=row['alert']
    leads=[]
    used=set()
    for t in sorted(times):
        candidates=[(i,a) for i,a in enumerate(onsets) if i not in used and .5<=t-a<=2]
        if candidates:
            i,a=candidates[0];used.add(i);leads.append(t-a)
    return dict(reviewed_fouls=len(times),alert_episodes=len(onsets),matched=len(leads),
                precision=len(leads)/len(onsets) if onsets else None,
                recall=len(leads)/len(times) if times else None,lead_seconds=leads)

def main(run):
    info=json.loads((run/'summary.json').read_text())
    cap=cv2.VideoCapture(info['source'])
    fps=cap.get(5); count=int(cap.get(7))
    if not cap.isOpened() or count<1:raise ValueError('Cannot open source footage')
    path=run/'review.json'
    times=set(json.loads(path.read_text())['contact_times']) if path.exists() else set()
    i=0
    try:
        while True:
            cap.set(1,i);ok,frame=cap.read()
            if not ok:raise ValueError(f'Cannot decode frame {i}')
            im=cv2.resize(frame,(960,540))
            cv2.rectangle(im,(0,0),(960,56),(25,25,25),-1)
            cv2.putText(im,'A/D frame   J/L second   F toggle contact   S save complete review   Esc cancel',(10,22),0,.58,(255,255,255),1)
            cv2.putText(im,f'{i/fps:.2f}s  |  {len(times)} fouls marked  |  '+('CONTACT' if i/fps in times else ''),(10,47),0,.6,(80,200,255),1)
            cv2.imshow('Review source footage',im);key=cv2.waitKey(0)&255
            if key==27:return
            if key==ord('s'):
                timeline=[json.loads(l) for l in (run/'telemetry.jsonl').read_text().splitlines()]
                path.write_text(json.dumps(dict(contact_times=sorted(times),metrics=evaluate(times,timeline)),indent=2))
                return
            if key==ord('f'):times.symmetric_difference_update({i/fps})
            i=max(0,min(count-1,i+{97:-1,100:1,106:-round(fps),108:round(fps)}.get(key,0)))
    finally:cap.release();cv2.destroyAllWindows()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path)
    main(parser.parse_args().run)

