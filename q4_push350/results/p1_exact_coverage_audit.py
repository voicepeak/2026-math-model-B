"""Independent QA artifact: strict rational tile containment, inflated outer domain."""
import sys, math, json
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from strategy_explore import layout
from geometry import dist,hull,unit,mul,add
def fp(p):return tuple(map(F,p))
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def exact_contains(poly,p):return len(poly)>=3 and all(cross(a,b,p)>=0 for a,b in zip(poly,poly[1:]+poly[:1]))
def audit():
    nodes=layout('ring22'); nf={p:fp(p) for p in nodes}
    radius=(1800+1e-6)/math.cos(math.pi/96)
    boundary=[mul(unit(i*360/96),radius) for i in range(96)]
    bf=list(map(fp,boundary))
    assert all(cross((F(0),F(0)),a,b)**2>=1800**2*((b[0]-a[0])**2+(b[1]-a[1])**2) for a,b in zip(bf,bf[1:]+bf[:1]))
    assert all(cross(a,b,c)>0 for a,b,c in zip(bf,bf[1:]+bf[:1],bf[2:]+bf[:2]))
    stack=[([(0.,0.),boundary[i],boundary[(i+1)%96]],0) for i in range(96)]
    checked=passed=depthmax=0
    while stack:
        tri,depth=stack.pop();checked+=1;depthmax=max(depth,depthmax)
        local=[p for p in nodes if all(dist(p,v)<=999.99 for v in tri)]
        poly=list(map(fp,hull(local)));tf=list(map(fp,tri))
        if all(exact_contains(poly,v) for v in tf):
            assert all((nf[p][0]-v[0])**2+(nf[p][1]-v[1])**2<=1000**2 for p in local for v in tf)
            passed+=1;continue
        assert depth<20 and checked<200000,(depth,checked)
        i,j=max(((0,1),(1,2),(2,0)),key=lambda ij:dist(tri[ij[0]],tri[ij[1]]))
        k=3-i-j;m=mul(add(tri[i],tri[j]),.5)
        # Binary float midpoint may not be exactly on the parent edge. Use
        # exact rational midpoint from here onward to preserve the tiling.
        m=tuple((F(tri[i][axis])+F(tri[j][axis]))/2 for axis in (0,1))
        stack.extend([([tri[i],m,tri[k]],depth+1),([m,tri[j],tri[k]],depth+1)])
    return dict(status='PASS',nodes=len(nodes),checked=checked,passed=passed,max_depth=depthmax,arithmetic='Fraction exact represented coordinates',outer_domain_radial_margin_m=1e-6,distance_limit_m=1000)
if __name__=='__main__':print(json.dumps(audit()))
