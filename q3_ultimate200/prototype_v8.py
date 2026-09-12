"""Finite-scenario active view selection, certified execution unchanged."""
from prototype_v5 import Strategy as V5
from geometry import dist, add, mul, sub, unit, enclosing_circle, bearing, clip_wedge, diameter_info
from robot_core import ALPHA

class Strategy(V5):
    def __init__(self,client,mode='q3',*,weight=2,attempt=50,**kwargs):
        super().__init__(client,mode,attempt=attempt,replace=False,**kwargs)
        self.weight=weight

    def viewpoint(self,tr):
        poly=tr['poly'];c,r=enclosing_circle(poly);pos=tuple(self.client.position)
        usual=super().viewpoint(tr)
        if dist(pos,usual)<1e-5:return usual
        a,b=diameter_info(poly)['diameter_pair']
        samples=[add(a,mul(sub(b,a),f)) for f in (.1,.3,.5,.7,.9)]
        v=unit(tr['theta']+90);u=unit(tr['theta'])
        candidates=[usual,c]
        if tr['observations']==1:
            for fw in (100,200,350,500):
                for lat in (-75,-30,30,75):
                    candidates.append(add(tr['last'],add(mul(u,fw),mul(v,lat))))
        else:
            candidates.extend(add(c,mul(v,o)) for o in (-60,-25,25,60))
        best=None
        for q in candidates:
            loss=dist(pos,q)
            for g in samples:
                if dist(q,g)<5:continue
                pp=clip_wedge(poly,q,bearing(q,g),ALPHA)
                cc,rr=enclosing_circle(pp)
                loss+=(dist(q,cc)+self.weight*max(0,rr-19.9))/len(samples)
            if best is None or loss<best[0]:best=loss,q
        return best[1]

    def summary(self,status):
        out=super().summary(status);out.update(algorithm='ultimate200_v8',active_weight=self.weight);return out
