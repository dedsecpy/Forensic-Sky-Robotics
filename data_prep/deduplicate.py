import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Cluster matching files and near-identical multi-frame fingerprints before training."""
import csv
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import cv2
import numpy as np
from scipy.spatial.distance import pdist,squareform
from video_pose import sources,OUT

def fingerprint(row):
    uid,path,split,label=row
    cap=cv2.VideoCapture(str(path))
    n=cap.get(cv2.CAP_PROP_FRAME_COUNT)
    views=[]
    for fraction in (.15,.38,.65,.84):
        cap.set(1,int(n*fraction));ok,f=cap.read()
        if not ok:raise ValueError(path)
        # Remove letterboxing and logos at edges. Compare spatial gradients at four times.
        h,w=f.shape[:2]; center=f[int(.13*h):int(.89*h),int(.06*w):int(.94*w)]
        image=cv2.resize(cv2.cvtColor(center,cv2.COLOR_BGR2GRAY),(25,16),interpolation=cv2.INTER_AREA)
        views.append((image[:,1:]>image[:,:-1]).flatten())
    cap.release()
    return hashlib.sha256(path.read_bytes()).hexdigest(),np.concatenate(views)

def main():
    rows=[r for r in sources() if r[3]!='worldcup']
    with ThreadPoolExecutor(3) as pool:prints=list(pool.map(fingerprint,rows))
    distances=squareform(pdist(np.array([x for _,x in prints]),'hamming'))
    parent=list(range(len(rows)))
    def root(i):
        while parent[i]!=i:i=parent[i]
        return i
    for i,j in zip(*np.where(np.triu(distances<.17,1))):
        parent[root(j)]=root(i)
    groups={}
    for i in range(len(rows)):groups.setdefault(root(i),[]).append(i)
    records=[]
    for group in groups.values():
        order={'test':0,'val':1,'train':2}
        rep=min(group,key=lambda i:(order[rows[i][2]],int(rows[i][1].stem.split('_')[1])))
        conflict=len({rows[i][3] for i in group})>1
        for i in group:
            uid,path,split,label=rows[i]
            records.append(dict(uid=uid,split=split,label=label,group=rows[rep][0],sha256=prints[i][0],keep=int(i==rep and not conflict),conflict=int(conflict)))
    with (OUT/'video_groups.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    print('unique groups',len(groups),'kept',sum(r['keep'] for r in records))
if __name__=='__main__':main()

