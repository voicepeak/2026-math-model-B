"""32-triangle certificate for the 25-point Q4 layout, with exact arithmetic QA."""
from fractions import Fraction as F
from geometry import unit,mul,dist,cross,sub

def ring_nodes():
    return [(0.,0.)]+[mul(unit(i*45),998.) for i in range(8)]+[mul(unit(i*22.5),1838.) for i in range(16)]

def verify_ring(nodes=None):
    if nodes is None:nodes=ring_nodes()
    if len(nodes)!=25:raise ValueError('Expected 25 nodes')
    expected=ring_nodes()
    if any(tuple(p)!=tuple(q) for p,q in zip(nodes,expected)):raise ValueError('Unexpected ring coordinates')
    I=nodes[1:9];O=nodes[9:];triangles=[]
    for i in range(8):
        a,b=I[i],I[(i+1)%8];c,d,e=O[2*i],O[(2*i+1)%16],O[(2*i+2)%16]
        triangles.extend([(nodes[0],a,b),(a,c,d),(a,d,b),(b,d,e)])
    def fc(a,b):return F(a[0])*F(b[1])-F(a[1])*F(b[0])
    def fs(a,b):return (F(a[0])-F(b[0]),F(a[1])-F(b[1]))
    limit=F('999.99')**2
    for tri in triangles:
        if fc(fs(tri[1],tri[0]),fs(tri[2],tri[0]))<=0:raise ValueError('Nonpositive tile')
        for a in tri:
            for b in tri:
                d=fs(a,b)
                if d[0]**2+d[1]**2>limit:raise ValueError('Tile diameter too large')
    # Exact boundary edge distance >1800; ordered convex polygon contains origin.
    boundary_area=F(0)
    for a,b in zip(O,O[1:]+O[:1]):
        e=fs(b,a);k=fc(a,b)
        if k<=0 or k*k<=F(1800)**2*(e[0]**2+e[1]**2):raise ValueError('Domain outside boundary')
        boundary_area+=k
    tile_area=sum(fc(fs(t[1],t[0]),fs(t[2],t[0])) for t in triangles)
    if tile_area!=boundary_area:raise ValueError('Exact tile area mismatch')
    return dict(certified=True,nodes=25,triangles=32,max_edge_m=max(dist(a,b) for t in triangles for a in t for b in t),
                boundary_inradius_m=1838.*__import__('math').cos(__import__('math').pi/16),
                arithmetic='Exact rational comparisons on stored binary floating-point coordinates',
                triangles_vertices=triangles)
if __name__=='__main__':
    import json
    r=verify_ring();print(json.dumps({k:v for k,v in r.items() if k!='triangles_vertices'}))
