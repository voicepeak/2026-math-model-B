"""Open Euclidean route portfolio; exact DP only certifies the current point set."""
import math, random
from functools import lru_cache
from geometry import dist

def length(start, points, order):
    return sum(dist(start if k == 0 else points[order[k-1]], points[i]) for k,i in enumerate(order))

def improve(start, points, route):
    route=list(route)
    for _ in range(60):
        best=0.; move=None
        for i in range(len(route)-1):
            prev=start if i==0 else points[route[i-1]]; a=points[route[i]]
            for j in range(i+1,len(route)):
                b=points[route[j]]; nxt=points[route[j+1]] if j+1<len(route) else None
                gain=dist(prev,a)-dist(prev,b)
                if nxt is not None:gain+=dist(b,nxt)-dist(a,nxt)
                if gain>best+1e-7:best=gain;move=(i,j)
        if move is None:break
        i,j=move;route[i:j+1]=reversed(route[i:j+1])
    return route

def route(start,points,method='twoopt',seed=0):
    n=len(points)
    if not n:return []
    ds=[[dist(a,b) for b in points] for a in points]
    if method=='exact' and n<=13:
        @lru_cache(None)
        def dp(last,mask):
            if not mask:return (0.,-1)
            choices=[(ds[last][j]+dp(j,mask^(1<<j))[0],j) for j in range(n) if mask>>j&1]
            return min(choices)
        mask=(1<<n)-1
        _,first=min((dist(start,points[j])+dp(j,mask^(1<<j))[0],j) for j in range(n))
        out=[first];mask^=1<<first
        while mask:
            first=dp(first,mask)[1];out.append(first);mask^=1<<first
        return out
    remaining=set(range(n));order=[];pos=start
    while remaining:
        j=min(remaining,key=lambda k:(dist(pos,points[k]),k));order.append(j);remaining.remove(j);pos=points[j]
    if method=='nearest':return order
    best=improve(start,points,order)
    if method in ('multistart','anneal','exact'):
        rng=random.Random(seed)
        for trial in range(6):
            order=list(best)
            if trial<3:
                order=order[trial+1:]+order[:trial+1]
            else:rng.shuffle(order)
            order=improve(start,points,order)
            if length(start,points,order)<length(start,points,best):best=order
        if method=='anneal':
            cur=list(best);val=length(start,points,cur);bv=length(start,points,best)
            for k in range(240):
                i,j=sorted(rng.sample(range(n),2)) if n>1 else (0,0)
                nxt=cur[:i]+list(reversed(cur[i:j+1]))+cur[j+1:]
                nv=length(start,points,nxt);temp=150*(1-k/240)+.1
                if nv<val or rng.random()<math.exp(min(0,(val-nv)/temp)):cur,val=nxt,nv
                if val<bv:best,bv=list(cur),val
            best=improve(start,points,best)
    return best
