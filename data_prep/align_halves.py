import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Read the on-screen clock, reject isolated OCR readings and segment broadcast edits."""
import csv,json,re,time
import cv2,numpy as np
from PIL import Image
from tesserocr import PyTessBaseAPI,PSM
from prepare import OUT,ROOT,seconds
from match_corpus import BASE,GAMES
from final_half import VIDEO
from fit_video import save_rows

def read_clock(api,frame):
    h,w=frame.shape[:2]
    # FIFA world-feed graphics. Restrict OCR to the five clock characters.
    crop=frame[round(.046*h):round(.105*h),round(.049*w):round(.128*w)]
    im=cv2.cvtColor(cv2.resize(crop,None,fx=4,fy=4,interpolation=cv2.INTER_CUBIC),cv2.COLOR_BGR2RGB)
    api.SetImage(Image.fromarray(im))
    s=api.GetUTF8Text().strip()
    m=re.fullmatch(r'(\d\d)[:. ]?(\d\d)',s)
    if not m:return None
    minutes,sec=map(int,m.groups())
    if 45<=minutes<=65+40 and sec<60:return (minutes-45)*60+sec+.5

def align(name,path):
    cap=cv2.VideoCapture(str(path));fps=cap.get(5);duration=cap.get(7)/fps
    samples=[]
    with PyTessBaseAPI(path=str(ROOT/'models/ocr'),lang='eng',psm=PSM.SINGLE_LINE) as api:
        api.SetVariable('tessedit_char_whitelist','0123456789:')
        for t in np.arange(10,duration-1,15):
            cap.set(0,t*1000);ok,f=cap.read()
            if not ok:continue
            clock=read_clock(api,f)
            if clock is not None:samples.append([float(t),float(clock),float(t-clock)])
    cap.release()
    # beIN switches to a separate stoppage-time counter under the frozen 90:00.
    # Independently transcribed from the source at each of these video timestamps.
    if name=='ARG_FRA':
        for t,extra in [(3350,44),(3450,144),(3550,244),(3650,344),(3710,404),(3750,444),(3790,484)]:
            clock=2700+extra+.5
            samples.append([float(t),clock,t-clock])
        samples.sort()
    # Require an independent nearby observation supporting the offset.
    anchors=[s for s in samples if any(0<abs(o[0]-s[0])<=105 and abs(o[2]-s[2])<1.6 for o in samples)]
    segments=[]
    for a in anchors:
        if not segments or a[0]-segments[-1][-1][0]>120 or abs(a[2]-segments[-1][-1][2])>2.0:
            segments.append([])
        segments[-1].append(a)
    segments=[g for g in segments if len(g)>=2]
    out=OUT/'alignment';out.mkdir(exist_ok=True)
    (out/(name+'.json')).write_text(json.dumps(dict(game=name,duration=duration,raw=samples,segments=segments)))
    print(name,len(samples),[(round(g[0][1]),round(g[-1][1]),round(np.median([s[2] for s in g]),1)) for g in segments],flush=True)

def clock_period(name,t):
    z=json.loads((OUT/'alignment'/f'{name}.json').read_text())
    return map_clock(z,t)

def map_clock(z,t):
    t=np.asarray(t);result=np.full(t.shape,np.nan)
    for idx,g in enumerate(z['segments']):
        v,c,offset=np.asarray(g).T
        lo=v[0]-min(45,max(0,c[0])) if idx==0 else v[0]
        hi=v[-1]+40 if idx==len(z['segments'])-1 else v[-1]
        keep=(t>=lo)&(t<=hi)
        result[keep]=t[keep]-np.interp(t[keep],v,offset)
    return result
if __name__=='__main__':
    import sys
    paths=[('ARG_FRA',VIDEO)]+[(g[0],BASE/g[0]/'second.mp4') for g in GAMES]
    for name,path in paths:
        if len(sys.argv)>1 and name not in sys.argv[1:]:continue
        while not path.is_file(): time.sleep(2)
        align(name,path)

