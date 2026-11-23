"""Build a match-disjoint SportsD index using StatsBomb's period-local event clocks."""
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
import csv
import json
import hashlib
import subprocess
from concurrent.futures import ThreadPoolExecutor
import requests

# Project root (parent of core/), not the package folder.
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'datasets/sportsd_2022_men'
OUT = ROOT / 'prepared'
BASE = 'https://cdn.jsdelivr.net/gh/statsbomb/open-data@master/data/'
REVISION='4b73468fc5b0f1950f9f66fada70ad3a4f9327cb'
WEIGHTS = {
    'scout.onnx': 'https://huggingface.co/mobilint/YOLO11n-pose/resolve/b7515e6c4ff0d30d5b3893dd668df2b2570fb581/yolo11n-pose.onnx',
    'ocr/eng.traineddata': 'https://cdn.jsdelivr.net/gh/tesseract-ocr/tessdata_fast@4.1.0/eng.traineddata',
    'pose.onnx': 'https://huggingface.co/mobilint/YOLO11s-pose/resolve/103bb1e0b9fc5316d0f21ee678178d0229666dd0/yolo11s-pose.onnx',
    'landmark.task': 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task',
}

def download(url, path):
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    with requests.Session() as session:
        session.mount('https://', HTTPAdapter(max_retries=Retry(total=4, backoff_factor=1, status_forcelist=[429,500,502,503,504])))
        response = session.get(url, timeout=45,headers={'Accept':'application/vnd.github.raw+json'} if 'api.github.com' in url else {})
        response.raise_for_status()
    tmp = path.with_suffix('.part')
    tmp.write_bytes(response.content)
    tmp.replace(path)

def seconds(e):
    h, m, s = e['timestamp'].split(':')
    return 3600 * int(h) + 60 * int(m) + float(s)

def main():
    OUT.mkdir(exist_ok=True)
    for name, url in WEIGHTS.items():
        download(url, ROOT / 'models' / name)
    rows = list(csv.DictReader((DATA / 'answer_key/men_ground_truth.csv').open(encoding='utf8')))
    ids = {r['event_uuid'] for r in rows}
    matchfile = OUT / 'statsbomb/matches.json'
    repo=OUT/'statsbomb_repo'
    if not repo.exists():
        subprocess.run(['git','init','--quiet',str(repo)],check=True)
        subprocess.run(['git','-C',str(repo),'remote','add','origin','https://github.com/statsbomb/open-data.git'],check=True)
    if subprocess.run(['git','-C',str(repo),'cat-file','-e',REVISION],capture_output=True).returncode:
        subprocess.run(['git','-C',str(repo),'fetch','--depth','1','--filter=blob:none','origin',REVISION],check=True)
    def git_data(name):
        return subprocess.check_output(['git','-C',str(repo),'show',f'{REVISION}:data/{name}.json'])
    matchfile.parent.mkdir(parents=True,exist_ok=True)
    if not matchfile.exists(): matchfile.write_bytes(git_data('matches/43/106'))
    def match(m):
        mid = m['match_id']
        path = OUT / f'statsbomb/{mid}.json'
        if not path.exists(): path.write_bytes(git_data(f'events/{mid}'))
        es = json.loads(path.read_bytes())
        fouls = [(e['period'], seconds(e)) for e in es if e['type']['name']=='Foul Committed']
        return {e['id']:(mid, min((s-seconds(e) for period,s in fouls if period==e['period'] and s>=seconds(e)),default=None)) for e in es if e['id'] in ids}
    anchors = {}
    names='Argentina|Australia|Belgium|Brazil|Cameroon|Canada|Costa Rica|Croatia|Denmark|Ecuador|England|France|Germany|Ghana|Iran|Japan|Mexico|Morocco|Netherlands|Poland|Portugal|Qatar|Saudi Arabia|Senegal|Serbia|South Korea|Spain|Switzerland|Tunisia|United States|Uruguay|Wales'
    codes=dict(zip(names.split('|'),'ARG AUS BEL BRA CMR CAN CRC CRO DEN ECU ENG FRA GER GHA IRN JPN MEX MAR NED POL POR QAT KSA SEN SRB KOR ESP SUI TUN USA URU WAL'.split(),strict=True))
    pairs={frozenset(r['game'].split('_')[:2]) for r in rows}
    matches=[m for m in json.loads(matchfile.read_bytes()) if frozenset(codes[m[t][t+'_name']] for t in ('home_team','away_team')) in pairs]
    with ThreadPoolExecutor(4) as pool:
        for items in pool.map(match,matches):
            anchors.update(items)
    games = sorted({r['game'] for r in rows}, key=lambda g: hashlib.sha256(g.encode()).digest())
    with (OUT/'clips.csv').open('w',newline='',encoding='utf8') as f:
        writer = csv.DictWriter(f,fieldnames=['uid','game','split','clip','event_uuid','match_id','next_foul_seconds','foul_within_2s','decision'])
        writer.writeheader()
        for r in rows:
            g=games.index(r['game'])
            mid,dt=anchors.get(r['event_uuid'],('',None))
            clip= DATA / 'data/men' / r['uid'] / 'clip.mp4'
            if not clip.is_file(): raise FileNotFoundError(clip)
            writer.writerow(dict(uid=r['uid'],game=r['game'],split='test' if g<8 else 'validation' if g<16 else 'train',clip=clip.relative_to(ROOT).as_posix(),event_uuid=r['event_uuid'],match_id=mid,next_foul_seconds=dt,foul_within_2s=int(dt is not None and dt<=2) if mid else '',decision=r['human_took']))
    print('Matched events',len(anchors),'of',len(rows))

if __name__=='__main__':
    main()

