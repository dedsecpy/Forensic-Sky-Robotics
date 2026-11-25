import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))
import bootstrap  # noqa: E402
import itertools
import cv2
import numpy as np
from vision import BONES

def focus(players):
    if len(players)<2: return players
    def interaction(pair):
        a,b=pair
        now=np.linalg.norm(a['xy']-b['xy'])
        future=np.linalg.norm(a['future']-b['future'])
        motion=max(a.get('leg_motion',0.),b.get('leg_motion',0.))
        return future+.22*now-.45*np.clip(now-future,-3,3)-.3*min(3,motion)
    return list(min(itertools.combinations(players,2),key=interaction))

def blockage(camera, target, others):
    # Shortest distance from standing bodies to the 3D sightline at their depth.
    ray=target-camera
    denom=ray[:2]@ray[:2]+1e-8
    penalty=0.
    for pos in others:
        t=(pos-camera[:2])@ray[:2]/denom
        if 0<t<1:
            point=camera+t*ray
            penalty+=max(0,1-np.linalg.norm(pos-point[:2])/.85)*np.clip((2.1-point[2])/.6,0,1)
    return penalty

class Camera:
    def __init__(self):
        self.xyz=np.array([0.,-9.,13.])
        self.v=np.zeros(3)
        self.aim=np.array([0.,18.,1.])
        self.dest=np.array([0.,-9.,13.])
        self.trail=[]
    def step(self,players,pair,alert,dt):
        active=bool(pair) and alert
        if active:
            targets=[np.r_[p['future'],1.] for p in pair]
            center=np.mean(targets,axis=0)
            choices=[center+np.array([np.cos(a)*15,np.sin(a)*15,z]) for a in np.linspace(0,2*np.pi,16,endpoint=False) for z in (7.,12.)]
            ids={p['id'] for p in pair}
            others=[p['future'] for p in players if p['id'] not in ids]
            choices=np.asarray(choices)
            blocked=np.zeros(len(choices))
            if others:
                offsets=np.asarray(others)[None,:,:]-choices[:,None,:2]
                for target in targets:
                    ray=target-choices
                    along=(offsets*ray[:,None,:2]).sum(2)/((ray[:,:2]**2).sum(1)[:,None]+1e-8)
                    distance=np.linalg.norm(offsets-along[:,:,None]*ray[:,None,:2],axis=2)
                    height=choices[:,2,None]+along*ray[:,2,None]
                    blocked+=(np.maximum(0,1-distance/.85)*np.clip((2.1-height)/.6,0,1)*(along>0)*(along<1)).sum(1)
            direction=center[:2]-choices[:,:2]
            direction/=np.linalg.norm(direction,axis=1)[:,None]+1e-8
            delta=targets[0]-targets[-1]
            separation=np.abs(direction[:,0]*delta[1]-direction[:,1]*delta[0])
            cost=12*blocked+.12*np.linalg.norm(choices-self.xyz,axis=1)-.6*np.minimum(4,separation)
            dest=choices[np.argmin(cost)]
        else:
            center=np.r_[np.median([p['xy'] for p in players],axis=0),1.] if players else self.aim
            dest=center+[0,-25,14]
        self.dest=np.asarray(dest,dtype=float)
        delta=self.dest-self.xyz
        desired=delta*min(1.,7/(np.linalg.norm(delta)+1e-8))
        accel=desired-self.v
        self.v+=accel*min(1.,4*dt/(np.linalg.norm(accel)+1e-8))
        self.xyz+=self.v*dt
        self.trail=(self.trail+[self.xyz[:2].copy()])[-80:]
        self.aim+=(center-self.aim)*(1-np.exp(-dt*3))
    def render(self,players,pair,bodies):
        w,h=640,360
        im=np.full((h,w,3),(43,83,46),np.uint8)
        forward=self.aim-self.xyz; forward/=np.linalg.norm(forward)+1e-8
        right=np.cross(forward,[0,0,1]); right/=np.linalg.norm(right)+1e-8
        up=np.cross(right,forward)
        def project(pt):
            q=pt-self.xyz; depth=q@forward
            if depth<=.4: return None
            return tuple(np.clip([w/2+440*(q@right)/depth,h/2-440*(q@up)/depth],-4096,4096).astype(int))
        def line(a,b,color,width):
            a,b=project(a),project(b)
            if a is not None and b is not None: cv2.line(im,a,b,color,width,cv2.LINE_AA)
        for x in np.arange(-55,56,5): line(np.array([x,-5,0]),np.array([x,68,0]),(63,112,69),1)
        for y in np.arange(0,70,5): line(np.array([-55,y,0]),np.array([55,y,0]),(63,112,69),1)
        for p in sorted(players,key=lambda p:-np.linalg.norm(p['xy']-self.xyz[:2])):
            pos=np.r_[p['xy'],0.]
            color=(70,197,250) if p['id'] in pair else (221,223,214)
            foot,head=project(pos),project(pos+[0,0,1.7])
            if foot is None or head is None: continue
            body=bodies.get(p['id'])
            if body is None:
                cv2.line(im,foot,head,color,4,cv2.LINE_AA)
            else:
                pts=body[:,:3]+pos+[0,0,.92]
                for a,b in BONES:
                    if min(body[a,3],body[b,3])>.35: line(pts[a],pts[b],color,2)
            cv2.circle(im,head,3,color,-1)
            if p['id'] in pair:
                cv2.putText(im,f"#{p['id']}",(head[0]+5,head[1]-4),0,.38,color,1,cv2.LINE_AA)
        # Overhead inset retains camera position and recent path while the perspective view pans.
        cv2.rectangle(im,(467,7),(634,113),(29,48,31),-1)
        cv2.rectangle(im,(473,27),(627,106),(105,139,101),1)
        cv2.putText(im,'CAMERA PATH',(476,21),0,.36,(219,230,222),1,cv2.LINE_AA)
        def map_point(pos):
            return (int(np.clip(550+pos[0]*1.35,474,626)),int(np.clip(85-pos[1]*1.05,28,105)))
        for a,b in zip(self.trail,self.trail[1:]):
            cv2.line(im,map_point(a),map_point(b),(235,179,70),2)
        for p in players:
            cv2.circle(im,map_point(p['xy']),2,(50,198,251) if p['id'] in pair else (192,207,194),-1)
        cv2.drawMarker(im,map_point(self.xyz),(255,211,95),cv2.MARKER_DIAMOND,8,2)
        subject=next((i for i in sorted(pair) if i in bodies),next(iter(bodies),None))
        if subject is not None:
            cv2.rectangle(im,(8,8),(108,119),(29,48,31),-1)
            cv2.putText(im,f'3D POSE #{subject}',(12,23),0,.33,(227,237,228),1,cv2.LINE_AA)
            b=bodies[subject]
            side=b[:,0]*.85+b[:,1]*.52
            pts=np.column_stack([58+side*46,72-b[:,2]*46]).astype(int)
            for a,c in BONES:
                if min(b[a,3],b[c,3])>.35:
                    cv2.line(im,tuple(pts[a]),tuple(pts[c]),(100,209,235),2,cv2.LINE_AA)
        return im

