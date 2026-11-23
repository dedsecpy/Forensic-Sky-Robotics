import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Use event clocks only to retrieve candidate clips for visual review, never as input."""
import csv,json,bisect
from collections import defaultdict
from pathlib import Path
import cv2,numpy as np
from prepare import ROOT,OUT,seconds
def candidates():
    rows=list(csv.DictReader((OUT/'clips.csv').open(encoding='utf8')))
    events={}; fouls=defaultdict(list)
    for mid in {r['match_id'] for r in rows}:
        for e in json.loads((OUT/f'statsbomb/{mid}.json').read_bytes()):
            events[e['id']]=e
            if e['type']['name']=='Foul Committed':fouls[mid,e['period']].append(seconds(e))
    result=[]
    for r in rows:
        e=events[r['event_uuid']]; cap=cv2.VideoCapture(str(ROOT/r['clip']))
        dur=cap.get(7)/cap.get(5);cap.release()
        anchor=seconds(e)
        delta=[s-anchor for s in fouls[r['match_id'],e['period']]]
        nearest=min(delta,key=abs,default=1e4)
        prior=[d for d in delta if -dur-1<d<=1]
        result.append(dict(uid=r['uid'],split=r['split'],duration=dur,nearest_foul_delta=nearest,review_candidate=int(bool(prior)),quiet=int(all(abs(d)>dur+5 for d in delta))))
    with (OUT/'cup_audit.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
    return rows,result
if __name__=='__main__':
    rows,records=candidates();print('candidates',sum(r['review_candidate'] for r in records),'quiet',sum(r['quiet'] for r in records))
    folder=OUT/'audit';folder.mkdir(exist_ok=True)
    keep=[(i,r) for i,r in enumerate(records) if r['review_candidate']]
    for start in range(0,len(keep),5):
        strips=[]
        for i,r in keep[start:start+5]:
            cap=cv2.VideoCapture(str(ROOT/rows[i]['clip']));cells=[]
            for t in np.linspace(.5,r['duration']-.3,8):
                cap.set(0,t*1000);ok,frame=cap.read()
                im=cv2.resize(frame,(190,110))
                cv2.putText(im,f'{i} {t:.1f}s',(1,12),0,.38,(0,255,255),1)
                cells.append(im)
            cap.release();strips.append(np.hstack(cells))
        cv2.imwrite(str(folder/f'cup{start}.jpg'),np.vstack(strips))

