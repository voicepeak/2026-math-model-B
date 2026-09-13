"""Second Q4 study: smaller certified coverage and information-aware scheduling."""
from strategy import Strategy as Base
import math
from geometry import unit,mul,dist,enclosing_circle,bearing,diameter_info,dot,sub,local_to_global,clip_wedge
from coverage_certificate import certify
from ring_certificate import ring_nodes
from routing import route

def layout(kind):
    if kind=='ring25':return ring_nodes()
    if kind=='ring22':
        return [(0.,0.)]+[mul(unit(i*360/7),998.) for i in range(7)]+[mul(unit(i*360/14),1848.) for i in range(14)]
    raise ValueError(kind)

class Strategy(Base):
    def __init__(self,client,mode='q4',layout_kind='ring22',schedule='joint',sweep_kind='grid',**kwargs):
        super().__init__(client,mode,routing='multistart',localizer='optical',**kwargs)
        self.nodes=layout(layout_kind);self.all_nodes=list(self.nodes)
        self.layout_certificate=certify(self.nodes)
        if not self.layout_certificate['certified']:raise ValueError('Coverage not certified')
        self.schedule=schedule;self.sweep_kind=sweep_kind
    def next_job(self):
        if self.schedule=='joint':return super().next_job()
        jobs=[]
        for ch,tr in self.tracks.items():
            c,r=enclosing_circle(tr['poly'])
            if self.schedule!='defer' or not self.nodes or r<=60 or tr['obs']>=2:jobs.append(('target',ch,c))
        scanjobs=[('scan',i,p) for i,p in enumerate(self.nodes)]
        if self.schedule=='inner':
            inner=[j for j in scanjobs if dist((0,0),j[2])<1100]
            if inner:scanjobs=inner
        jobs.extend(scanjobs)
        if not jobs:return None
        if self.schedule=='near':return min(jobs,key=lambda j:dist(self.client.position,j[2]))
        self.route_calls+=1
        order=route(self.client.position,[j[2] for j in jobs],'multistart',seed=self.route_calls)
        return jobs[order[0]]

    def sweep(self,ch):
        if self.sweep_kind=='grid':return super().sweep(ch)
        tr=self.tracks[ch]
        if self.sweep_kind in ('probe','probe_greedy'):
            c,r=enclosing_circle(tr['poly'])
            if r>19.9:
                if self.clear_at(c,ch):return
                self.observe(c,ch)
                if ch in self.cleared:return
        self.fallback_count+=1
        poly=self.tracks[ch]['poly'];a,b=diameter_info(poly)['diameter_pair']
        theta=bearing(a,b);u=unit(theta);v=(-u[1],u[0])
        xy=[(dot(sub(p,a),u),dot(sub(p,a),v)) for p in poly]
        lo,hi=min(x for x,y in xy),max(x for x,y in xy)
        bot,top=min(y for x,y in xy),max(y for x,y in xy)
        # Every rectangle cell remains inside a radius-19.9 disk.
        options=[]
        for ny in range(max(1,math.ceil((top-bot)/28)),max(1,math.ceil((top-bot)/28))+4):
            dy=(top-bot)/ny;dx=math.sqrt(max(1e-10,39.8**2-dy**2))
            nx=max(1,math.ceil((hi-lo)/dx));options.append((nx*ny,nx,ny))
        _,nx,ny=min(options)
        pts=[local_to_global(a,theta,(lo+(i+.5)*(hi-lo)/nx,bot+(j+.5)*(top-bot)/ny)) for i in range(nx) for j in range(ny)]
        if self.sweep_kind in ('greedy','probe_greedy'):
            # Deterministic interior quadrature determines order only. Every
            # certified rectangle cell is still visited if needed, so sampling
            # can never turn an unsuccessful search into a completeness claim.
            samples=[]
            for i in range(1,len(poly)-1):
                p,q,r=poly[0],poly[i],poly[i+1]
                area=abs((q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0]))/2
                for j,k in ((1,1),(1,3),(3,1),(2,2)):
                    samples.append(((p[0]+(q[0]-p[0])*j/5+(r[0]-p[0])*k/5,p[1]+(q[1]-p[1])*j/5+(r[1]-p[1])*k/5),area/4))
            remaining=set(range(len(pts)))
            while remaining:
                def score(i):
                    mass=sum(w for p,w in samples if dist(p,pts[i])<=19.9)
                    return mass/(dist(self.client.position,pts[i])/5+3),-dist(self.client.position,pts[i]),-i
                i=max(remaining,key=score);remaining.remove(i)
                if self.clear_at(pts[i],ch):return
                samples=[(p,w) for p,w in samples if dist(p,pts[i])>20]
        else:
            for i in route(self.client.position,pts,'twoopt'):
                if self.clear_at(pts[i],ch):return
        raise RuntimeError('Complete certified rectangle sweep failed')
