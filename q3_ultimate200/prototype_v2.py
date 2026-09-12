"""Q3 v2: budgeted scan substitution along a jointly planned route."""
from prototype_v1 import Strategy as V1, route_order, exclude_disk
from geometry import dist, mul, unit, enclosing_circle
from coverage_exact import mask, SAMPLES, certificate
from robot_core import CLEAR_SAFE, localize_poly
from robot_client import RobotError

def length(start,route):
    return sum(dist(a,b) for a,b in zip([start]+[j[2] for j in route],[j[2] for j in route]))

class Strategy(V1):
    def __init__(self,client,mode='q3',*,visibility=True,joint=True,shared=True,
                 scan_gain=12,attempt=0,phases=1,**kwargs):
        super().__init__(client,mode,visibility=visibility,joint=joint,shared=shared)
        self.scan_gain=scan_gain;self.attempt=attempt;self.phases=phases
        self.optical_attempted=set();self.route_plan=[]

    def plan_route(self,extra=None):
        start=tuple(self.client.position)
        jobs=[('target',ch,enclosing_circle(tr['poly'])[0]) for ch,tr in self.tracks.items() if ch not in self.cleared]
        covered=self.covered_mask | (mask(extra) if extra is not None else 0)
        for j in jobs:covered |= mask(j[2])
        full=(1<<len(SAMPLES))-1
        best=None
        for phase in range(0,60,60//self.phases):
            scans=[('scan',None,mul(unit(a+phase),1200)) for a in range(0,360,60)]
            for _ in range(6):
                route=route_order(start,jobs+scans);options=[]
                for k,j in enumerate(route):
                    if j[0]!='scan':continue
                    cov=covered
                    for s in scans:
                        if s is not j:cov |= mask(s[2])
                    if cov!=full:continue
                    a=start if k==0 else route[k-1][2];b=route[k+1][2] if k+1<len(route) else None
                    saving=dist(a,j[2])+(dist(j[2],b)-dist(a,b) if b else 0)
                    options.append((saving,scans.index(j)))
                if not options:break
                scans.pop(max(options)[1])
            route=route_order(start,jobs+scans)
            cost=length(start,route)+len(scans)*6*len(self.unknown)*5
            if best is None or cost<best[0]:best=cost,route
        return best

    def next_job(self):
        if not self.joint:return super().next_job()
        _,route=self.plan_route();self.route_plan=route
        if route:return route[0]
        ok,w,d=certificate(self.coverage.scans)
        self.coverage_proof=dict(complete=ok,worst_distance_m=d,witness=w,scans=list(self.coverage.scans))
        if ok:return None
        return ('scan',None,w)

    def stop_tasks(self,exclude=None):
        self.share(tuple(self.client.position),exclude)
        if self.joint and self.unknown and exclude is None:
            p=tuple(self.client.position);gain=(mask(p)&~self.covered_mask).bit_count()
            if gain>=self.scan_gain:
                before,_=self.plan_route();after,_=self.plan_route(p)
                if before-after>len(self.unknown)*6*5:self.scan(p)

    def engage(self,ch):
        if not self.attempt:return super().engage(ch)
        for _ in range(8):
            if ch in self.cleared:return
            tr=self.tracks[ch];c,r=enclosing_circle(tr['poly']);certified=r<=CLEAR_SAFE
            if certified or (r<=self.attempt and ch not in self.optical_attempted):
                if certified:self.certificates.append(dict(channel=ch,center=c,radius=r,vertices=tr['poly'],time=self.client.virtual_time))
                else:self.optical_attempted.add(ch)
                res=self.action('clear',c,ch)
                if res['clear_result']=='success':
                    self.tracks.pop(ch,None);self.stop_tasks();return
                if certified:raise RobotError('certified clear failed')
            p=self.viewpoint(tr);res=self.observe(p,ch);self.stop_tasks(exclude=ch)
            if res['measure_result']=='no_signal':break
        if ch not in self.cleared:
            tr=self.tracks[ch];localize_poly(self,ch,tr['poly'],tr['s0'],tr['t0'],tr['last'],tr['theta'])
            self.tracks.pop(ch,None);self.stop_tasks()

    def summary(self,status):
        out=super().summary(status)
        out.update(algorithm='ultimate200_v2',scan_gain=self.scan_gain,optical_trial_radius=self.attempt,phases=self.phases)
        return out
