"""Offline lower bounds; source truth is never provided to an online strategy."""
import argparse,json,math
from pathlib import Path
from geometry import dist
from routing import route,length
HERE=Path(__file__).resolve().parent

def mst(points):
    used={0};remain=set(range(1,len(points)));best={j:dist(points[0],points[j]) for j in remain};total=0.
    while remain:
        j=min(remain,key=lambda k:best[k]);total+=best[j];used.add(j);remain.remove(j)
        for k in remain:best[k]=min(best[k],dist(points[j],points[k]))
    return total

def center_path_exact(points):
    """Held–Karp on all target centres with prescribed origin and free endpoint.
    Python array stores O(n2^n) doubles, with no high-overhead recursion cache.
    """
    from array import array
    n=len(points);size=1<<n;table=array('d',[math.inf])*(size*n)
    ds=[[dist(a,b) for b in points] for a in points]
    for j in range(n):table[(1<<j)*n+j]=dist((0.,0.),points[j])
    for mask in range(1,size):
        remaining=(size-1)^mask;bits=mask
        while bits:
            bit=bits&-bits;j=bit.bit_length()-1;bits^=bit;value=table[mask*n+j]
            rem=remaining
            while rem:
                b=rem&-rem;k=b.bit_length()-1;rem^=b;idx=(mask|b)*n+k;v=value+ds[j][k]
                if v<table[idx]:table[idx]=v
    return min(table[(size-1)*n:])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seeds',default='1,2,3');a=ap.parse_args()
    from benchmark import Fixture
    import random
    rows=[]
    for seed in map(int,a.seeds.split(',')):
        n=10+random.Random(seed+891).randrange(7);f=Fixture(seed,n);pts=[(s['x'],s['y']) for s in f.initial]
        m=mst([(0.,0.)]+pts);exact=center_path_exact(pts)
        # Any route reaching N 20m disks can detour through their centres for
        # <=40N added metres; exact centre optimum <= actual route +40N.
        bound=max(0.,exact-40*n)/5+5*n
        r=dict(seed=seed,total=n,center_open_path_optimal_m=exact,mst_m=m,
               oracle_lower_bound_s=bound,oracle_lower_bound_s_per_source=bound/n)
        rows.append(r);print(r,flush=True)
    (HERE/'results/offline_lower_bounds.json').write_text(json.dumps(dict(
        scope='Synthetic, full-information relaxation; not an attainable online policy.',
        proof='L_online >= max(0, L_exact_center_path - 40*N); T >= L_online/5 + 5*N.',rows=rows),indent=2))
if __name__=='__main__':main()
