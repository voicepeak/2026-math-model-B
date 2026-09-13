"""Sufficient continuous certificate for arbitrary Q4 scan sites.
Adaptive triangles tile an outer regular 96-gon containing the true disk.
For each tile C, use only sites within 999.99m of every vertex of C.
If C is inside their convex hull, every source in C sees at least one site
for every closed directional half-plane. Subdivision reduces conservatism.
Failure means unproved, never a permission to stop scanning.
"""
import math
from geometry import dist,hull,cross,sub,unit,mul,add

def contains(poly,p,tol=1e-7):
    return len(poly)>=3 and all(cross(sub(b,a),sub(p,a))>=-tol for a,b in zip(poly,poly[1:]+poly[:1]))

def certify(nodes,max_depth=18,max_tiles=100000):
    radius=1800/math.cos(math.pi/96)
    boundary=[mul(unit(i*360/96),radius) for i in range(96)]
    stack=[([(0.,0.),boundary[i],boundary[(i+1)%96]],0) for i in range(96)]
    passed=0;checked=0;depth_seen=0
    while stack:
        tri,depth=stack.pop();checked+=1;depth_seen=max(depth_seen,depth)
        local=[p for p in nodes if all(dist(p,v)<=999.99 for v in tri)]
        poly=hull(local)
        if all(contains(poly,v) for v in tri):passed+=1;continue
        if depth>=max_depth or checked>=max_tiles:
            return dict(certified=False,checked=checked,passed=passed,max_depth=depth_seen,unproved_triangle=tri)
        i,j=max(((0,1),(1,2),(2,0)),key=lambda ij:dist(tri[ij[0]],tri[ij[1]]))
        k=3-i-j;m=mul(add(tri[i],tri[j]),.5)
        stack.extend([([tri[i],m,tri[k]],depth+1),([m,tri[j],tri[k]],depth+1)])
    return dict(certified=True,checked=checked,passed=passed,max_depth=depth_seen,domain_outer_sides=96,distance_limit_m=999.99)

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('layout');a=p.parse_args()
    data=json.loads(Path(a.layout).read_text());r=certify(data['nodes']);print(json.dumps(r))
    raise SystemExit(0 if r['certified'] else 1)
