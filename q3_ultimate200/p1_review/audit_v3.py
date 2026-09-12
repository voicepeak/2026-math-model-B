import hashlib,json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmark import Fixture,PublicClient
from prototype_v3 import Strategy
from geometry import dist,cross,sub
paths=[ROOT/n for n in ('prototype_v1.py','prototype_v2.py','prototype_v3.py','coverage_exact.py','benchmark.py','baseline_breakthrough.py','robot_core.py','geometry.py','offline_sim.py','robot_client.py','run_robot.py')]
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
# At angular difference <=30 degrees, distance squared is bounded by f(d,r).
# f is convex separately in d and r, so the four rectangle corners bound
# all d in [1000,1800] and all ring radii r in [1125,1730].
corners=[dict(source_radius=d,ring_radius=r,distance=math.sqrt(d*d+r*r-2*d*r*math.cos(math.pi/6))) for d in (1000,1800) for r in (1125,1730)]
assert max(x['distance'] for x in corners)<1000
rows=[]
for radius in (1125,1450,1730):
    world=Fixture(17,10,'minrange');world.sources[0].update(x=3.,y=0.)
    truth={s['channel']:(s['x'],s['y']) for s in world.sources}
    policy=Strategy(PublicClient(world),radius=radius)
    start=time.perf_counter();r=policy.run();r['runtime_s']=time.perf_counter()-start
    assert r['cleared']==10 and all(s['cleared'] for s in world.sources)
    assert r['status']=='complete_coverage' and r['pending_tracks']==0 and r['fixed_nodes_visited']==6
    assert r['coverage_certificate']=='hexagon_analytic'
    scans=policy.coverage.scans;assert scans[0]==(0.,0.) and len(scans)==7
    assert all(abs(math.hypot(*p)-radius)<1e-5 for p in scans[1:])
    angles=sorted(math.atan2(y,x)%(2*math.pi) for x,y in scans[1:])
    assert all(abs(((angles[(i+1)%6]-angles[i])%(2*math.pi))-math.pi/3)<1e-7 for i in range(6))
    pos=(0.,0.);ch=1;total=0.;failures=[]
    for i,t in enumerate(policy.trace):
        p=(t['x'],t['y']);total+=dist(pos,p)/5;pos=p
        if t['kind']=='measure':total+=5+(t['channel']!=ch);ch=t['channel']
        else:
            ok=t['response']['clear_result']=='success';total+=5 if ok else 3
            assert ok==(dist(p,truth[t['channel']])<=20)
            if not ok:
                assert any(u['kind']=='clear' and u['channel']==t['channel'] and u['response']['clear_result']=='success' for u in policy.trace[i+1:])
                failures.append(dict(index=i,channel=t['channel']))
        assert abs(total-t['virtual_time_s'])<1e-7
    for c in policy.certificates:assert dist(c['center'],truth[c['channel']])<=c['radius']+1e-5 and c['radius']<=19.9
    rows.append(dict(radius=radius,summary=r,reconstructed_virtual_time_s=total,failed_optical_attempts=failures,scans=scans))
    (ROOT/'p1_review'/f'v3_trace_{radius}.json').write_text(json.dumps(policy.trace,indent=2),encoding='utf-8')
for bad in (1124.99,1730.01):
    try:Strategy(PublicClient(Fixture(1,10)),radius=bad)
    except ValueError:pass
    else:raise AssertionError('bad radius accepted')
assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
report=dict(status='PASS',scope='P1 incremental v3; offline only',hashes=hashes,continuous_coverage_bound=corners,rows=rows)
(ROOT/'p1_review'/'evidence_v3.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(status='PASS',hashes=hashes,corners=corners,rows=[{k:v for k,v in r.items() if k!='scans'} for r in rows]),indent=2))
