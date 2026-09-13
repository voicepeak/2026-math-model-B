"""Exact MILP + subtour cuts for the fixed 25-site OPEN scan route.
This optimization excludes unknown targets, localization and online decisions.
"""
import json,time
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
from geometry import dist
from routing import route,length
HERE=Path(__file__).resolve().parent

def main():
    data=json.loads((HERE/'layout_ring25.json').read_text());points=[(0.,0.)]+[tuple(p) for p in data['nodes'] if dist(p,(0,0))>1e-7]
    n=len(points)-1;sink=n+1
    arcs=[(i,j) for i in range(n+1) for j in range(1,n+2) if i!=j and not(i==0 and j==sink)]
    costs=np.array([0. if j==sink else dist(points[i],points[j]) for i,j in arcs])
    constraints=[]
    for i in range(n+1):constraints.append(([k for k,(a,b) in enumerate(arcs) if a==i],1.,1.))
    for j in range(1,n+2):constraints.append(([k for k,(a,b) in enumerate(arcs) if b==j],1.,1.))
    cuts=set();history=[];t0=time.perf_counter();solution=None;best_bound=0.
    heuristic=route((0.,0.),points[1:],'multistart');upper=length((0.,0.),points[1:],heuristic)
    while time.perf_counter()-t0<180:
        A=lil_matrix((len(constraints),len(arcs)))
        for r,(indices,lo,hi) in enumerate(constraints):A[r,indices]=1.
        result=milp(costs,integrality=np.ones(len(arcs)),bounds=Bounds(0,1),
            constraints=LinearConstraint(A.tocsr(),[r[1] for r in constraints],[r[2] for r in constraints]),
            options=dict(time_limit=min(40,180-(time.perf_counter()-t0)),mip_rel_gap=0.0))
        if getattr(result,'mip_dual_bound',None) is not None:best_bound=max(best_bound,float(result.mip_dual_bound))
        if result.x is None:break
        successor={i:j for k,(i,j) in enumerate(arcs) if result.x[k]>.5}
        visited={0};path=[];j=successor[0]
        while j!=sink and j not in visited:
            visited.add(j);path.append(j);j=successor[j]
        remain=set(range(1,n+1))-set(path);subtours=[]
        while remain:
            first=min(remain);cyc=[];j=first
            while j not in cyc:cyc.append(j);remain.discard(j);j=successor[j]
            subtours.append(frozenset(cyc))
        history.append(dict(iteration=len(history)+1,objective_m=float(result.fun),dual_bound_m=best_bound,subtours=len(subtours),status=int(result.status)))
        print(history[-1],flush=True)
        if not subtours:
            solution=path;upper=float(result.fun);break
        for S in subtours:
            if S not in cuts:
                cuts.add(S);constraints.append(([k for k,(i,j) in enumerate(arcs) if i in S and j in S],-np.inf,len(S)-1))
    if solution is None:solution=[i+1 for i in heuristic]
    actual=sum(dist(points[0] if k==0 else points[solution[k-1]],points[j]) for k,j in enumerate(solution))
    assert len(set(solution))==n and abs(actual-upper)<1e-5
    out=dict(scope='Fixed 25 scan sites, origin start, free endpoint; NOT global optimum of Q4 online task.',
             optimal=upper-best_bound<=1e-5,upper_bound_m=upper,lower_bound_m=best_bound,
             relative_gap=(upper-best_bound)/upper,route=[points[0]]+[points[i] for i in solution],
             runtime_s=time.perf_counter()-t0,history=history)
    (HERE/'results/fixed_scan_route_optimality.json').write_text(json.dumps(out,indent=2));print(out['optimal'],upper,best_bound,flush=True)
if __name__=='__main__':main()
