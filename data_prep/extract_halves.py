import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
"""Cache all source frames sampled at two hertz. Reuse the clip pose pipeline."""
import concurrent.futures as cf
import time
from pathlib import Path
from match_corpus import GAMES,BASE
from final_half import VIDEO
from video_pose import Scout,extract,CACHE
import cv2
def one(item):
    name,path=item
    if (CACHE/f'half_{name}.npz').exists():return
    try:pose=Scout('GPU')
    except RuntimeError:pose=Scout('CPU')
    extract(pose,'half_'+name,path)
    print('finished',name,flush=True)
if __name__=='__main__':
    cv2.setNumThreads(1)
    paths=[('ARG_FRA',VIDEO)]+[(g[0],BASE/g[0]/'second.mp4') for g in GAMES]
    # Only verified, atomically renamed recordings are submitted.
    with cf.ThreadPoolExecutor(2) as pool:
        futures=[]
        for name,path in paths:
            until=time.monotonic()+900
            while not path.exists() and time.monotonic()<until:time.sleep(2)
            if not path.exists():raise FileNotFoundError(path)
            futures.append(pool.submit(one,(name,path)))
        for task in cf.as_completed(futures):task.result()

