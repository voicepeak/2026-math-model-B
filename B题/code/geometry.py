"""Bounded-bearing geometry. Coordinates m; public angles degrees. Standard library only."""
import itertools
import math

TOL = 1e-7

def add(a,b): return (a[0]+b[0],a[1]+b[1])
def sub(a,b): return (a[0]-b[0],a[1]-b[1])
def mul(a,t): return (a[0]*t,a[1]*t)
def dot(a,b): return a[0]*b[0]+a[1]*b[1]
def cross(a,b): return a[0]*b[1]-a[1]*b[0]
def dist(a,b): return math.hypot(a[0]-b[0],a[1]-b[1])
def unit(deg):
    t=math.radians(deg); return (math.cos(t),math.sin(t))
def bearing(a,b): return math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))%360

def wedge(s,theta,alpha=1.0):
    if not 0<alpha<90: raise ValueError('Require 0 < alpha < 90 degrees')
    lo,hi=unit(theta-alpha),unit(theta+alpha)
    n1,n2=(lo[1],-lo[0]),(-hi[1],hi[0])
    return [(n1[0],n1[1],dot(n1,s)),(n2[0],n2[1],dot(n2,s))]

def inside(p,hps,tol=TOL): return all(a*p[0]+b*p[1]<=c+tol for a,b,c in hps)

def hull(points):
    pts=sorted(points); unique=[]
    for p in pts:
        if not unique or dist(p,unique[-1])>TOL: unique.append(p)
    if len(unique)<3: return unique
    def half(seq):
        h=[]
        for p in seq:
            while len(h)>1 and cross(sub(h[-1],h[-2]),sub(p,h[-1]))<=1e-10: h.pop()
            h.append(p)
        return h
    return half(unique)[:-1]+half(reversed(unique))[:-1]

def intersection(observations,alpha=1.0):
    """Pure wedges, no artificial clipping box; statuses empty/unbounded/bounded."""
    hs=[h for x,y,t in observations for h in wedge((x,y),t,alpha)]
    if not hs: return {'status':'unbounded','vertices':[],'diameter':None}
    pts=[]
    for (a,b,c),(d,e,f) in itertools.combinations(hs,2):
        det=a*e-b*d
        if abs(det)<1e-12: continue
        p=((c*e-b*f)/det,(a*f-c*d)/det)
        if inside(p,hs): pts.append(p)
    if not pts: return {'status':'empty','vertices':[],'diameter':None}
    vs=hull(pts)
    for a,b,_ in hs:
        for v in [(b,-a),(-b,a)]:
            if all(d*v[0]+e*v[1]<=1e-12 for d,e,_ in hs):
                return {'status':'unbounded','vertices':vs,'diameter':None}
    return dict(status='bounded',vertices=vs,**diameter_info(vs))

def diameter_info(vs):
    if not vs: raise ValueError('Empty polygon')
    a,b=max(itertools.product(vs,repeat=2),key=lambda pair:dist(*pair))
    d=dist(a,b); c=mul(add(a,b),0.5)
    excess=max(dist(v,c)-d/2 for v in vs)
    return {'diameter':d,'diameter_pair':[a,b],'diameter_center':c,
            'diameter_circle_covers':excess<=TOL,'circle_excess':excess}

def enclosing_circle(vs):
    if not vs: raise ValueError('Empty polygon')
    best=(None,math.inf)
    def consider(c,r):
        nonlocal best
        if r<best[1] and all(dist(v,c)<=r+TOL for v in vs): best=(c,r)
    for v in vs: consider(v,0)
    for a,b in itertools.combinations(vs,2):
        c=mul(add(a,b),0.5); consider(c,dist(a,b)/2)
    for a,b,c in itertools.combinations(vs,3):
        ab,ac=sub(b,a),sub(c,a); den=2*cross(ab,ac)
        if abs(den)<1e-12: continue
        bb,cc=dot(ab,ab),dot(ac,ac)
        o=add(a,((bb*ac[1]-cc*ab[1])/den,(ab[0]*cc-ac[0]*bb)/den))
        consider(o,dist(o,a))
    if best[0] is None: raise ArithmeticError('No enclosing circle')
    return best

def clip(poly,hp):
    if not poly:return []
    a,b,c=hp; out=[]
    for p,q in zip(poly,poly[1:]+poly[:1]):
        fp=a*p[0]+b*p[1]-c; fq=a*q[0]+b*q[1]-c
        ip,iq=fp<=TOL,fq<=TOL
        if ip: out.append(p)
        if ip!=iq:
            t=fp/(fp-fq); out.append(add(p,mul(sub(q,p),t)))
    return hull(out)

def clip_wedge(poly,s,theta,alpha=1.0):
    for h in wedge(s,theta,alpha): poly=clip(poly,h)
    return poly

def circle_hps(c,r,n=128):
    return [(u[0],u[1],dot(u,c)+r) for u in (unit(360*j/n) for j in range(n))]

def prior(s,theta,alpha=1.0,n=128):
    # Outer tangent polygon: every real point in both circles remains feasible.
    poly=[(-1800,-1800),(1800,-1800),(1800,1800),(-1800,1800)]
    for h in circle_hps((0,0),1800,n)+circle_hps(s,1500,n)+wedge(s,theta,alpha):
        poly=clip(poly,h)
    return poly

def local_to_global(s,theta,p):
    u=unit(theta);v=(-u[1],u[0]);return add(s,add(mul(u,p[0]),mul(v,p[1])))

def guaranteed(b,alpha=1.0):
    """Continuous guarantee over r in [5,1500], angle in [-alpha,alpha]."""
    ang=math.degrees(math.atan2(b[1],b[0]))
    opposite=(ang+360)%360-180
    ts=[-alpha,alpha]
    if -alpha<=opposite<=alpha: ts.append(opposite)
    minimum=min(dot(b,unit(t)) for t in ts)
    return all(dot(b,b)+r*r-2*r*minimum<=max(1000,r)**2+TOL for r in (5,1000,1500))

def sampled_score(s,theta,b,sources,errors,alpha=1.0,poly=None):
    if poly is None: poly=prior(s,theta,alpha)
    worst=0.0
    for g in sources:
        if dist(b,g)<=5: continue
        t=bearing(b,g)
        for e in errors:
            p=clip_wedge(poly,b,t+e,alpha)
            if not p: raise ArithmeticError('Sample excluded by its own wedge')
            worst=max(worst,diameter_info(p)['diameter'])
    return worst

def source_samples(s,theta,alpha=1.0,dense=False):
    rs=[6]+list(range(50 if dense else 100,1501,50 if dense else 100))
    ts=[-alpha,-alpha/2,0,alpha/2,alpha] if dense else [-alpha,0,alpha]
    return [g for r in rs for t in ts if dist((0,0),g:=local_to_global(s,theta,mul(unit(t),r)))<=1800+TOL]
