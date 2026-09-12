"""Elastic six-scan tour with exact angular cover preserved at every update.
For centres at radius <=1660, coverage of the 1800m boundary plus an origin
scan implies coverage of the whole disk (convex radial squared-distance).
"""
import math
from prototype_v5 import Strategy as V5
from prototype_v1 import route_order
from geometry import dist, mul, unit, enclosing_circle, add, sub, dot

def boundary_cover(sites):
    arcs=[]
    for p in sites:
        r=math.hypot(*p)
        if r<800.1 or r>1660.0001:continue
        h=math.acos(max(-1,min(1,(1800**2+r*r-999.99**2)/(3600*r))))
        a=math.atan2(p[1],p[0])%(2*math.pi)
        lo,hi=a-h,a+h
        if lo<0:arcs.extend([(0,hi),(lo+2*math.pi,2*math.pi)])
        elif hi>2*math.pi:arcs.extend([(lo,2*math.pi),(0,hi-2*math.pi)])
        else:arcs.append((lo,hi))
    end=0.
    for lo,hi in sorted(arcs):
        if lo>end+1e-12:return False
        end=max(end,hi)
    return end>=2*math.pi-1e-12

class Strategy(V5):
    def __init__(self,client,mode='q3',*,elastic=True,passes=3,attempt=150,**kwargs):
        super().__init__(client,mode,replace=False,attempt=attempt,**kwargs)
        self.elastic=elastic;self.passes=passes;self.node_moves=0

    def next_job(self):
        start=tuple(self.client.position)
        jobs=[('target',ch,enclosing_circle(tr['poly'])[0]) for ch,tr in self.tracks.items()]
        route=route_order(start,jobs+[('scan',i,p) for i,p in enumerate(self.fixed_nodes)])
        if self.elastic:
            for _ in range(self.passes):
                changed=False
                for k,j in enumerate(route):
                    if j[0]!='scan':continue
                    i=j[1];p=self.fixed_nodes[i]
                    a=start if k==0 else route[k-1][2];b=route[k+1][2] if k+1<len(route) else None
                    if b is None:target=a
                    else:
                        v=sub(b,a);t=max(0,min(1,dot(sub(p,a),v)/max(1e-10,dot(v,v))))
                        target=add(a,mul(v,t))
                    candidates=[add(p,mul(sub(target,p),f)) for f in (1,.75,.5,.25,.125)]
                    candidates += [add(p,mul(unit(ang),step)) for step in (100,30) for ang in range(0,360,45)]
                    old=dist(a,p)+(dist(p,b) if b else 0);best=old,p
                    for q in candidates:
                        r=math.hypot(*q)
                        if not 801<=r<=1660:continue
                        cost=dist(a,q)+(dist(q,b) if b else 0)
                        if cost>=best[0]-1e-5:continue
                        sites=self.coverage.scans+self.fixed_nodes[:i]+[q]+self.fixed_nodes[i+1:]
                        if boundary_cover(sites):best=cost,q
                    if best[0]<old-1e-5:
                        self.fixed_nodes[i]=best[1];route[k]=('scan',i,best[1]);changed=True;self.node_moves+=1
                if not changed:break
                route=route_order(start,jobs+[('scan',i,p) for i,p in enumerate(self.fixed_nodes)])
        return route[0]

    def summary(self,status):
        out=super().summary(status);out.update(algorithm='ultimate200_v6',elastic_node_updates=self.node_moves,elastic=self.elastic)
        return out
