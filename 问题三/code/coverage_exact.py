"""Conservative continuous coverage certificate via clipped Voronoi cells.
Outer regular polygon contains the entire radius-1800 disk. A convex squared
distance reaches its maximum at a vertex of each clipped Voronoi cell.
Sampling is used for planning only, never for completion certification.
"""
import math
from geometry import unit, mul, clip, dist, dot

OUTER = [mul(unit((i+.5)*5), 1800/math.cos(math.radians(2.5))) for i in range(72)]
SAMPLES = [mul(unit(a), r) for r, step in [(600,30),(1100,15),(1500,10),(1800,5)] for a in range(0,360,step)] + [(0.,0.)]

def certificate(sites):
    if not sites: return False, (1800.,0.), float('inf')
    worst = -1.; witness = None
    for i,s in enumerate(sites):
        poly = list(OUTER)
        for j,t in enumerate(sites):
            if i == j or dist(s,t)<1e-8: continue
            poly = clip(poly, (2*(t[0]-s[0]), 2*(t[1]-s[1]), dot(t,t)-dot(s,s)))
            if not poly: break
        for v in poly:
            d = dist(v,s)
            if d>worst: worst,witness=d,v
    return worst < 1000-1e-4, witness, worst

def mask(p):
    return sum(1<<i for i,q in enumerate(SAMPLES) if dist(p,q)<990)

