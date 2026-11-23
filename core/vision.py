import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
import cv2
import mediapipe as mp
import numpy as np
import onnxruntime as ort
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from prepare import ROOT

BONES=[(5,6),(5,7),(7,9),(6,8),(8,10),(5,11),(6,12),(11,12),(11,13),(13,15),(12,14),(14,16),(0,5),(0,6)]
MP_IDS=[0,2,5,7,8,11,12,13,14,15,16,23,24,25,26,27,28]

class Pose:
    def __init__(self):
        self.net=None
        self.landmarker=mp.tasks.vision.PoseLandmarker.create_from_options(mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(ROOT/'models/landmark.task')),
            min_pose_detection_confidence=.30,min_pose_presence_confidence=.35))
    def close(self): self.landmarker.close()
    def people(self,im):
        if self.net is None:
            opt=ort.SessionOptions()
            opt.intra_op_num_threads=4
            self.net=ort.InferenceSession(str(ROOT/'models/pose.onnx'),opt,providers=['CPUExecutionProvider'])
        h,w=im.shape[:2]
        # Overlap square tiles so distant players reach the detector at a useful scale.
        side=min(w,h,320)
        xs=np.linspace(0,w-side,int(np.ceil((w-side)/(side*.86)))+1).astype(int)
        ys=np.linspace(0,h-side,int(np.ceil((h-side)/(side*.86)))+1).astype(int)
        boxes=[]; scores=[]; joints=[]
        for y in ys:
            for x in xs:
                tile=im[y:y+side,x:x+side]
                blob=cv2.dnn.blobFromImage(tile,1/255,(640,640),swapRB=True)
                pred=self.net.run(None,{'input':blob})[0][0].T
                for row in pred[pred[:,4]>.18]:
                    cx,cy,bw,bh=row[:4]*side/640
                    boxes.append([float(x+cx-bw/2),float(y+cy-bh/2),float(bw),float(bh)])
                    scores.append(float(row[4]))
                    k=row[5:].reshape(17,3).copy()
                    k[:,:2]=k[:,:2]*side/640+[x,y]
                    joints.append(k)
        return [(np.array(boxes[i]),joints[i]) for i in np.asarray(cv2.dnn.NMSBoxes(boxes,scores,.18,.45)).flatten()]
    def body3d(self,im,box,with_image=False):
        x,y,w,h=box
        size=int(max(h,w)*1.5)
        if size<16: return None
        crop=cv2.getRectSubPix(im,(size,size),(float(x+w/2),float(y+h/2)))
        rgb=cv2.cvtColor(cv2.resize(crop,(256,256)),cv2.COLOR_BGR2RGB)
        result=self.landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb))
        if result.pose_world_landmarks:
            # MediaPipe camera axes -> virtual scene lateral, forward, vertical.
            pts=result.pose_world_landmarks[0]
            world=np.array([[pts[i].x,pts[i].z,-pts[i].y,pts[i].visibility] for i in MP_IDS])
            if with_image:
                landmarks=result.pose_landmarks[0]
                image_xy=np.array([[landmarks[i].x,landmarks[i].y] for i in MP_IDS])*size+[x+w/2-size/2,y+h/2-size/2]
                return world,image_xy
            return world

class Tracker:
    def __init__(self):
        self.tracks={}
        self.counter=0
    def update(self,detections,t,shape,homography=None):
        h,w=shape[:2]
        visible=[]
        for box,joints in detections:
            x,y,bw,bh=box
            foot=np.array([x+bw/2,y+bh])
            ankles=joints[15:17]
            reliable=ankles[ankles[:,2]>.55]
            if len(reliable): foot=np.mean(reliable[:,:2],axis=0)
            if homography is None:
                # Uncalibrated local patch of the pitch. Depth increases away from camera.
                loc=np.array([(foot[0]/w-.5)*65,(1-foot[1]/h)*36])
            else:
                loc=cv2.perspectiveTransform(foot.reshape(1,1,2),homography)[0,0]
            visible.append(dict(box=box,joints=joints,xy=loc))
        self.tracks={i:p for i,p in self.tracks.items() if t-p['time']<=.8}
        old=list(self.tracks.values())
        assigned={}
        if old and visible:
            distance=cdist([p['xy']+p['v']*(t-p['time']) for p in old],[p['xy'] for p in visible])
            for i,j in zip(*linear_sum_assignment(distance)):
                if distance[i,j]<3.5: assigned[j]=old[i]
        shifts=[]
        for j,p in enumerate(visible):
            prev=assigned.get(j)
            if prev is None:
                self.counter+=1
                p.update(id=self.counter,v=np.zeros(2),time=t)
            else:
                v=(p['xy']-prev['xy'])/max(.01,t-prev['time'])
                shifts.append(v)
                p.update(id=prev['id'],v=.55*v+.45*prev['v'],time=t)
            self.tracks[p['id']]=p
        pan=np.median(shifts,axis=0) if len(shifts)>=4 and homography is None else np.zeros(2)
        for p in visible:
            v=p['v']-pan
            p['future']=p['xy']+v*min(1.2,9/max(.01,np.linalg.norm(v)))
        return visible

