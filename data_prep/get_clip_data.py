import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Fetch the two pinned short-video corpora in their original directory layouts."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
import requests
from prepare import ROOT,download

def fetch_set(repository,revision,folder):
    base=f'https://huggingface.co/datasets/{repository}/resolve/{revision}/'
    folder.mkdir(parents=True,exist_ok=True)
    def get(name):
        download(base+quote(name),folder/name)
    if repository.endswith('/sportsd'):
        get('manifest.csv')
        with (folder/'manifest.csv').open(encoding='utf8') as f:files=[r['clip'] for r in csv.DictReader(f) if r['split']=='men']
        files+=['answer_key/men_ground_truth.csv','answer_key/men_options.csv','README.md']
    else:
        r=requests.get(f'https://huggingface.co/api/datasets/{repository}/revision/{revision}',timeout=45)
        r.raise_for_status()
        files=[p['rfilename'] for p in r.json()['siblings'] if p['rfilename'].lower().endswith('.mp4') or p['rfilename']=='README.md']
    with ThreadPoolExecutor(4) as pool:list(pool.map(get,files))
    print(repository,len(files),'files verified present',flush=True)

if __name__=='__main__':
    fetch_set('addisonwu05/sportsd','ad8c7fa7adf5c5868e3fbd2a74c8abb9dda13aef',ROOT/'datasets/sportsd_2022_men')
    fetch_set('jahid114593/foul-vs-dive-dataset','6332515871c6428dfaff9880c35d85bea1b6e9e7',ROOT/'datasets/cas_fd')

