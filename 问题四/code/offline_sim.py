"""In-process synthetic fixture. Separate from official simulator; no HTTP fidelity claim."""
import math,random,time
from geometry import dist,bearing,unit,dot,sub

class OfflineClient:
    def __init__(self,mode,seed,count=12):
        rng=random.Random(seed);self.sources=[];self.err={};self.rng=random.Random(seed+777)
        for ch in rng.sample(range(1,21),count):
            r=math.sqrt(rng.random())*1800;t=rng.uniform(0,360);u=unit(t)
            self.sources.append(dict(channel=ch,x=r*u[0],y=r*u[1],radius=rng.uniform(1000,1500),
                                     direction=rng.uniform(0,360) if mode=='q4' and rng.random()<0.5 else None,cleared=False))
        self.position=(0.,0.);self.channel=1;self.virtual_time=0.;self.started=time.monotonic()
    def time_left(self): return 1200-(time.monotonic()-self.started)
    def source(self,c):return next((s for s in self.sources if s['channel']==c and not s['cleared']),None)
    def move(self,x,y):
        self.virtual_time+=dist(self.position,(x,y))/5;self.position=(x,y)
    def measure(self,x,y,c):
        self.move(x,y);self.virtual_time+=5+(c!=self.channel);self.channel=c;s=self.source(c)
        result='no_signal';angle=None
        if s:
            g=(s['x'],s['y']);r=dist(g,(x,y))
            visible=s['direction'] is None or dot(sub((x,y),g),unit(s['direction']))>=0
            if r<=s['radius'] and visible:
                result='near' if r<=5 else 'direction'
                if result=='direction':
                    key=(c,round(x,6),round(y,6))
                    if key not in self.err:self.err[key]=self.rng.uniform(-1,1)
                    angle=round((bearing((x,y),g)+self.err[key])%360,2)%360
        res=dict(accepted=True,virtual_time_s=self.virtual_time,measure_result=result)
        if angle is not None:res['svd_deg']=angle
        return 200,res
    def clear(self,x,y,c):
        self.move(x,y);s=self.source(c);hit=s is not None and dist((x,y),(s['x'],s['y']))<=20
        if hit:s['cleared']=True
        self.virtual_time+=5 if hit else 3
        return 200,dict(accepted=True,virtual_time_s=self.virtual_time,clear_result='success' if hit else 'no_target_in_range')
