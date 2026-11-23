import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Acquire and verify the independent Argentina-France recording and event reference."""
import hashlib,json,subprocess
from pathlib import Path
from urllib.parse import quote
import requests
from prepare import ROOT,OUT,REVISION
FOLDER=ROOT/'datasets/final_external'
VIDEO=FOLDER/'second_half.mp4'
ITEM='argentina-vs-france-fifa-world-cup-2022-final'
NAME='3 - 3 ARG vs FRA - Second-Half - Bein.ia.mp4'
def main():
    FOLDER.mkdir(parents=True,exist_ok=True)
    meta=requests.get(f'https://archive.org/metadata/{ITEM}',timeout=30).json()
    record=next(r for r in meta['files'] if r['name']==NAME)
    url=f'https://archive.org/download/{ITEM}/'+quote(NAME)
    if not VIDEO.exists():
        temp=VIDEO.with_suffix('.part')
        with requests.get(url,stream=True,timeout=(20,90)) as response:
            response.raise_for_status()
            with temp.open('wb') as f:
                for chunk in response.iter_content(1024*1024):f.write(chunk)
        with temp.open('rb') as f: checksum=hashlib.file_digest(f,'sha1').hexdigest()
        if checksum!=record['sha1']:raise ValueError('File checksum differs from archive')
        temp.replace(VIDEO)
    events=subprocess.check_output(['git','-C',str(OUT/'statsbomb_repo'),'show',f'{REVISION}:data/events/3869685.json'])
    (FOLDER/'events.json').write_bytes(events)
    (FOLDER/'source.json').write_text(json.dumps(dict(url=url,bytes=int(record['size']),sha1=record['sha1'],match_id=3869685),indent=2))
if __name__=='__main__':main()

