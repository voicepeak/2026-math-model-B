"""Q3 public observations only: visibility constraints and joint coverage route."""
import math
from baseline_breakthrough import Strategy as Base
from geometry import dist, clip, hull, sub, dot, add, mul, unit, enclosing_circle
from coverage_exact import certificate, SAMPLES, mask

def exclude_disk(poly, p, radius=999.9999):
    # Convex hull of P outside disk. Extrema occur at polygon vertices or at
    # intersections of polygon edges with circle. Convexification is an outer
    # relaxation, so even disconnected feasible pieces are never discarded.
    pts=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if dist(a,p)>=radius: pts.append(a)
        v=sub(b,a); w=sub(a,p); aa=dot(v,v)
        if aa<1e-18: continue
        bb=2*dot(w,v); cc=dot(w,w)-radius*radius; disc=bb*bb-4*aa*cc
        if disc>=0:
            for t in ((-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa)):
                if 0<=t<=1: pts.append(add(a,mul(v,t)))
    return hull(pts)

def route_order(start,jobs):
    todo=list(jobs); out=[]; p=start
    while todo:
        k=min(range(len(todo)),key=lambda i:dist(p,todo[i][2])); j=todo.pop(k);out.append(j);p=j[2]
    for _ in range(80):
        improve=False
        for i in range(len(out)-1):
            a=start if i==0 else out[i-1][2]; b=out[i][2]
            for j in range(i+1,len(out)):
                c=out[j][2]; d=out[j+1][2] if j+1<len(out) else None
                if dist(a,c)+(dist(b,d) if d else 0)<dist(a,b)+(dist(c,d) if d else 0)-1e-6:
                    out[i:j+1]=reversed(out[i:j+1]);improve=True;break
            if improve:break
        if not improve:break
    return out

class Strategy(Base):
    def __init__(self,client,mode='q3',*,visibility=True,joint=True,shared=True,**kwargs):
        super().__init__(client,mode,shared=shared)
        self.visibility=visibility; self.joint=joint
        self.negative={c:[] for c in range(1,21)};self.positive={c:[] for c in range(1,21)}
        self.covered_mask=0; self.plan=[];self.coverage_proof=None
        self.candidates=[mul(unit(a),r) for r in (1200,1450) for a in range(0,360,10)]
        self.candidate_masks=[mask(p) for p in self.candidates]

    def observe(self,p,ch):
        cached=(ch,round(p[0],6),round(p[1],6)) in self._cache
        res=super().observe(p,ch)
        if cached or ch in self.cleared:return res
        if res['measure_result']=='no_signal':self.negative[ch].append(p)
        elif res['measure_result']=='direction':self.positive[ch].append(p)
        if self.visibility and ch in self.tracks:
            poly=self.tracks[ch]['poly']
            for n in self.negative[ch]:
                poly=exclude_disk(poly,n)
                for s in self.positive[ch]:
                    poly=clip(poly,(2*(n[0]-s[0]),2*(n[1]-s[1]),dot(n,n)-dot(s,s)+1e-6))
            if not poly:raise ArithmeticError('visibility constraints inconsistent')
            self.tracks[ch]['poly']=poly
        return res

    def scan(self,p):
        super().scan(p)
        self.covered_mask |= mask(p)

    def stop_tasks(self,exclude=None):
        self.share(tuple(self.client.position),exclude)
        if self.joint and self.unknown:
            p=tuple(self.client.position)
            gain=(mask(p)&~self.covered_mask).bit_count()
            if gain>=4:self.scan(p)

    def viewpoint(self,tr):
        # Once visibility has made a first bearing informative, do not impose
        # the generic short-baseline move intended for an unconstrained ray.
        c,r=enclosing_circle(tr['poly'])
        if self.visibility and tr['observations']==1 and r<300:
            tr=dict(tr,observations=2)
        return super().viewpoint(tr)

    def next_job(self):
        if not self.joint:return super().next_job()
        start=tuple(self.client.position)
        jobs=[('target',ch,enclosing_circle(tr['poly'])[0]) for ch,tr in self.tracks.items()]
        future=self.covered_mask
        for j in jobs:future |= mask(j[2])
        full=(1<<len(SAMPLES))-1
        route=route_order(start,jobs)
        while future != full:
            best=None
            for p,m in zip(self.candidates,self.candidate_masks):
                gain=(m&~future).bit_count()
                if not gain:continue
                for k in range(len(route)+1):
                    a=start if k==0 else route[k-1][2];b=route[k][2] if k<len(route) else None
                    cost=dist(a,p)+(dist(p,b)-dist(a,b) if b else 0)+60
                    score=cost/gain
                    if best is None or score<best[0]:best=(score,p,m,k)
            if best is None:raise ArithmeticError('coverage planning candidates insufficient')
            _,p,m,k=best;route.insert(k,('scan',None,p));future |= m
        route=route_order(start,route)
        if route:return route[0]
        ok,w,d=certificate(self.coverage.scans)
        self.coverage_proof=dict(complete=ok,worst_distance_m=d,witness=w,scans=list(self.coverage.scans))
        if ok:return None
        # Repair continuous gaps missed by planning samples, with an actual
        # scan centred on the witness. No sampled certificate can terminate.
        return ('scan',None,w)

    def run(self):
        if not self.joint:return super().run()
        from robot_core import BudgetStop
        status='complete_coverage'
        try:
            self.scan((0.,0.))
            for _ in range(200):
                if len(self.cleared)>=16:status='complete_upper_bound';break
                self.tracks={c:t for c,t in self.tracks.items() if c not in self.cleared}
                job=self.next_job()
                if job is None:break
                if job[0]=='target':self.engage(job[1])
                else:self.scan(job[2]);self.share(tuple(self.client.position))
            else:status='iteration_limit'
        except BudgetStop as exc:status=str(exc)
        return self.summary(status)

    def summary(self,status):
        out=super().summary(status)
        out.update(algorithm='ultimate200_prototype',visibility=self.visibility,joint=self.joint)
        if self.joint:
            out['coverage_certificate']='voronoi_outer_polygon' if self.coverage_proof and self.coverage_proof['complete'] else 'not_yet_complete'
            out['coverage_worst_m']=self.coverage_proof['worst_distance_m'] if self.coverage_proof else None
        return out
