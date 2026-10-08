"""Public-observation particle search with a certified geometric fallback.

Particles affect only the order of optical attempts. They never certify that a
source is absent, never terminate coverage, and never replace the full sweep.
"""
import math
from strategy_explore import Strategy as Explore
from strategy_ring21 import nodes21
from geometry import dist,enclosing_circle,bearing
from coverage_certificate import certify

def radical(n,base):
    x=0.;scale=1.
    while n:n,d=divmod(n,base);scale/=base;x+=d*scale
    return x

def particles(poly,n=144):
    if len(poly)<3:return list(poly)
    triangles=[];total=0.
    for i in range(1,len(poly)-1):
        a,b,c=poly[0],poly[i],poly[i+1]
        area=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
        total+=area;triangles.append((total,a,b,c))
    if total<1e-12:return list(poly)
    out=[]
    for i in range(n):
        z=(i+.5)/n*total
        _,a,b,c=next(t for t in triangles if t[0]>=z)
        u=math.sqrt(radical(i+1,2));v=radical(i+1,3)
        out.append(((1-u)*a[0]+u*(1-v)*b[0]+u*v*c[0],(1-u)*a[1]+u*(1-v)*b[1]+u*v*c[1]))
    return out

def possible(g,positive,negative):
    """Existence screening for latent range and directional orientation.
    Used for heuristic weights only; conservative tolerances are intentional.
    """
    radius=max([1000.]+[dist(g,p) for p in positive])
    if radius>1500.01:return False
    relevant=[p for p in negative if dist(g,p)<radius-1e-5]
    if not relevant:return True
    pa=[bearing(g,p) for p in positive];na=[bearing(g,p) for p in relevant]
    edges=sorted({(t+sgn*90)%360 for t in pa+na for sgn in (-1,1)})
    mids=[(a+((b-a)%360)/2)%360 for a,b in zip(edges,edges[1:]+edges[:1])]
    for phi in edges+mids:
        if all(math.cos(math.radians(t-phi))>=-1e-9 for t in pa) and all(math.cos(math.radians(t-phi))<=1e-9 for t in na):return True
    return False

class Strategy(Explore):
    def __init__(self,client,mode='q4',layout_kind='ring21',particle_tries=6,negative_info=True,**kwargs):
        selected=layout_kind
        super().__init__(client,mode,layout_kind='ring22' if selected=='ring21' else selected,**kwargs)
        if selected=='ring21':
            self.nodes=nodes21();self.all_nodes=list(self.nodes);self.layout_certificate=certify(self.nodes)
            if not self.layout_certificate['certified']:raise ValueError('Uncertified particle scan layout')
        self.particle_tries=particle_tries;self.negative_info=negative_info
    def sweep(self,ch):
        history=[r for r in self.trace if r['channel']==ch]
        positive=[(r['x'],r['y']) for r in history if r['kind']=='measure' and r['response']['measure_result'] in ('direction','near')]
        negative=[(r['x'],r['y']) for r in history if r['kind']=='measure' and r['response']['measure_result']=='no_signal']
        failed=[(r['x'],r['y']) for r in history if r['kind']=='clear' and r['response']['clear_result']!='success']
        pts=particles(self.tracks[ch]['poly'])
        if self.negative_info:pts=[p for p in pts if possible(p,positive,negative)]
        pts=[p for p in pts if all(dist(p,q)>20 for q in failed)]
        for _ in range(self.particle_tries):
            if not pts:break
            def value(p):
                mass=sum(dist(p,q)<=19.8 for q in pts)
                return mass/(dist(self.client.position,p)/5+3)**.65
            p=max(pts,key=value)
            if self.clear_at(p,ch):return
            pts=[q for q in pts if dist(p,q)>20]
        # No particle-based success or absence claim: use the previously
        # audited rectangle coverage whenever heuristic attempts did not clear.
        return super().sweep(ch)
