import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Download and verify separate 2022 World Cup broadcast halves for in-domain fitting."""
import concurrent.futures as cf
import hashlib,json,re
from urllib.parse import quote
from pathlib import Path
import requests
from prepare import ROOT,OUT,REVISION
import subprocess
from final_half import VIDEO
GAMES=[
 ('BRA_SUI','Brazil','Switzerland','train','brasil-vs-suiza-fecha-2-qatar-2022-1'),
 ('ESP_CRC','Spain','Costa Rica','train','espana-vs-costa-rica-fecha-1-qatar-2022-1'),
 ('FRA_AUS','France','Australia','train','francia-vs-australia-fecha-1-qatar-2022-1'),
 ('SRB_SUI','Serbia','Switzerland','train','serbia-vs-suiza-fecha-3-qatar-2022-2'),
 ('FRA_DEN','France','Denmark','val','francia-vs-dinamarca-fecha-2-qatar-2022-1'),
 ('CRC_GER','Costa Rica','Germany','val','costa-rica-vs-alemania-fecha-3-qatar-2022-2')]
BASE=ROOT/'datasets/broadcast_halves'
def record(g):
    name,a,b,split,item=g
    meta=requests.get('https://archive.org/metadata/'+item,timeout=30).json()
    opts=[f for f in meta['files'] if re.search(r'2\.ia\.mp4$',f['name'],re.I)]
    if len(opts)!=1:raise ValueError((name,[f['name'] for f in meta['files'] if f['name'].endswith('.ia.mp4')]))
    f=opts[0];url='https://archive.org/download/'+item+'/'+quote(f['name'])
    ms=json.loads((OUT/'statsbomb/matches.json').read_bytes())
    m=next(m for m in ms if {m['home_team']['home_team_name'],m['away_team']['away_team_name']}=={a,b})
    return dict(game=name,split=split,url=url,sha1=f['sha1'],size=int(f['size']),match_id=m['match_id'])
def get(r):
    folder=BASE/r['game'];folder.mkdir(parents=True,exist_ok=True)
    p=folder/'second.mp4'
    if not p.exists():
        tmp=p.with_suffix('.part')
        for attempt in range(4):
            try:
                start=tmp.stat().st_size if tmp.exists() else 0
                if start<r['size']:
                    with requests.get(r['url'],stream=True,headers={'Range':f'bytes={start}-'} if start else {},timeout=(20,60)) as resp:
                        resp.raise_for_status()
                        with tmp.open('ab' if start and resp.status_code==206 else 'wb') as f:
                            for chunk in resp.iter_content(2**20):f.write(chunk)
                with tmp.open('rb') as f:
                    if hashlib.file_digest(f,'sha1').hexdigest()!=r['sha1']:raise ValueError('checksum mismatch')
                tmp.replace(p);break
            except requests.RequestException:
                if attempt==3:raise
    events=subprocess.check_output(['git','-C',str(OUT/'statsbomb_repo'),'show',f'{REVISION}:data/events/{r["match_id"]}.json'])
    (folder/'events.json').write_bytes(events);(folder/'source.json').write_text(json.dumps(r,indent=2))
    return r['game']
if __name__=='__main__':
    import sys
    with cf.ThreadPoolExecutor(6) as pool: rows=list(pool.map(record,GAMES))
    BASE.mkdir(exist_ok=True,parents=True)
    (BASE/'manifest.json').write_text(json.dumps(rows,indent=2))
    print('MB',sum(r['size'] for r in rows)/1e6,flush=True)
    if '--sizes' not in sys.argv:
        with cf.ThreadPoolExecutor(4) as pool:
            for name in pool.map(get,rows):print(name,flush=True)

