import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Associate close-up display detections with the wide-field forecast tracks."""
import numpy as np
from scipy.optimize import linear_sum_assignment

def iou(a,b):
    low=np.maximum(a[:2],b[:2]);high=np.minimum(a[:2]+a[2:],b[:2]+b[2:])
    overlap=np.prod(np.maximum(high-low,0))
    return overlap/(np.prod(a[2:])+np.prod(b[2:])-overlap+1e-8)

def combine(tracks,close):
    result=[dict(p) for p in tracks];used=set()
    if tracks and close:
        overlap=np.array([[iou(p['box'],q['box']) for q in close] for p in tracks])
        for i,j in zip(*linear_sum_assignment(1-overlap)):
            if overlap[i,j]>=.25:
                result[i].update(box=close[j]['box'],joints=close[j]['joints'])
                used.add(j)
    for i,p in enumerate(close):
        if i not in used:result.append(dict(p,id=1000000+p['id']))
    return result

