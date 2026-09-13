"""Offline scan-site exploration: sampled screening followed by rigorous certificate."""
import json,math,itertools,time
from pathlib import Path
import numpy as np
from coverage import mesh
from coverage_certificate import certify
from routing import route,length
from geometry import dist,mul,unit
HERE=Path(__file__).resolve().parent

def samples():
    pts=[(0.,0.)]
    for r in range(100,1801,100):
        for a in np.linspace(0,2*np.pi,max(32,int(2*np.pi*r/80)),endpoint=False):pts.append((r*np.cos(a),r*np.sin(a)))
    return np.array(pts)
SAMPLES=samples()
def screen(nodes):
    v=np.asarray(nodes)[None,:,:]-SAMPLES[:,None,:]
    d=np.linalg.norm(v,axis=2);angles=np.arctan2(v[:,:,1],v[:,:,0]);angles[d>999.]=10.
    aa=np.sort(angles,axis=1);count=(d<=999.).sum(axis=1)
    if np.any(count<3):return False
    gaps=np.diff(aa,axis=1);mask=np.arange(aa.shape[1]-1)[None,:]<count[:,None]-1
    gaps=np.where(mask,gaps,0.)
    wrap=2*np.pi+aa[:,0]-aa[np.arange(len(aa)),count-1]
    return bool(np.all(np.maximum(gaps.max(axis=1),wrap)<np.pi-1e-5))
def score(nodes):
    pts=[p for p in nodes if dist(p,(0,0))>1e-7]
    order=route((0.,0.),pts,'multistart');return length((0.,0.),pts,order)+300*len(pts)
def main():
    rows=[];candidates=[];base,_=mesh()
    # Different radial deformations of the certified triangular starting lattice.
    for cap in (1900,1950,2000,2050,2100,2150,2200,2250,2300,2400,2500,2650):
        for scale in (.90,.95,1.):
            nodes=[mul(p,min(scale,cap/max(dist(p,(0,0)),1))) for p in base]
            if screen(nodes):candidates.append((score(nodes),f'cap{cap}_scale{scale}',nodes))
    for n1,n2 in ((6,12),(6,15),(6,18),(8,16),(8,20),(10,20),(12,18)):
        for r1,r2,phase in itertools.product((700,800,900,1000,1100),(1850,1900,1950,2000,2100),(0,.5)):
            nodes=[(0.,0.)]+[mul(unit(i*360/n1),r1) for i in range(n1)]+[mul(unit((i+phase)*360/n2),r2) for i in range(n2)]
            if screen(nodes):candidates.append((score(nodes),f'rings{n1}_{n2}_{r1}_{r2}_{phase}',nodes))
    candidates.sort();print('screened candidates',len(candidates),flush=True)
    best=None
    for value,name,nodes in candidates[:15]:
        cert=certify(nodes);rows.append(dict(name=name,score=value,node_count=len(nodes),certificate=cert))
        print(name,value,len(nodes),cert['certified'],cert['checked'],flush=True)
        if cert['certified'] and (best is None or value<best['score']):best=dict(name=name,score=value,nodes=nodes,certificate=cert)
    if best:
        # Greedy certified node removal, retaining the origin for initial batch.
        changed=True
        while changed:
            changed=False;nodes=best['nodes'];opts=[]
            for i in range(len(nodes)):
                if dist(nodes[i],(0,0))<1:continue
                ns=nodes[:i]+nodes[i+1:]
                if screen(ns):opts.append((score(ns),i,ns))
            for value,i,ns in sorted(opts):
                cert=certify(ns)
                if cert['certified']:
                    best.update(score=value,nodes=ns,certificate=cert);changed=True;print('pruned',len(ns),value,flush=True);break
        (HERE/'layout_optimized.json').write_text(json.dumps(best,indent=2),encoding='utf-8')
    (HERE/'results/layout_search.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    if best:print('best',best['name'],len(best['nodes']),best['score'],flush=True)
if __name__=='__main__':main()
