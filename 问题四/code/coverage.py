"""Continuous Q4 certificate: each intersecting cell's vertices surround its sources.
Every cell diameter is <1000 m. At least one vertex lies in every closed
directional half-plane through any point in the cell. No orientation sampling.
"""
import math
from geometry import dist, dot, sub, cross

def origin_distance(poly):
    signs=[cross(sub(b,a),(-a[0],-a[1])) for a,b in zip(poly,poly[1:]+poly[:1])]
    if all(v>=-1e-9 for v in signs) or all(v<=1e-9 for v in signs):return 0.
    result=math.inf
    for a,b in zip(poly,poly[1:]+poly[:1]):
        v=sub(b,a);t=max(0.,min(1.,-dot(a,v)/dot(v,v)))
        result=min(result,math.hypot(a[0]+t*v[0],a[1]+t*v[1]))
    return result

def mesh(kind='triangle',spacing=990.,phase=0.):
    if kind=='square':
        h=spacing/math.sqrt(2);n=math.ceil(1800/h)+2
        cells=[[(i*h,j*h),((i+1)*h,j*h),((i+1)*h,(j+1)*h),(i*h,(j+1)*h)]
               for i in range(-n,n) for j in range(-n,n)]
    else:
        h=spacing*math.sqrt(3)/2;n=math.ceil(1800/h)+3
        def p(i,j):return (spacing*(i+j*.5),h*j)
        cells=[]
        for i in range(-n,n):
            for j in range(-n,n):
                cells.extend([[p(i,j),p(i+1,j),p(i,j+1)], [p(i+1,j),p(i+1,j+1),p(i,j+1)]])
    cells=[c for c in cells if origin_distance(c)<=1800+1e-7]
    a=math.radians(phase);co,si=math.cos(a),math.sin(a)
    cells=[[(co*x-si*y,si*x+co*y) for x,y in c] for c in cells]
    nodes=sorted(set(v for c in cells for v in c))
    assert max(dist(a,b) for c in cells for a in c for b in c)<1000
    return nodes,cells
