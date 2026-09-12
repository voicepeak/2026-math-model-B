import hashlib,json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmark import Fixture,PublicClient
from prototype_v8 import Strategy
from geometry import cross,sub,dist
from coverage_exact import certificate

def contained(p,poly):
    if len(poly)<3:return any(dist(p,q)<1e-5 for q in poly)
    return all(cross(sub(b,a),sub(p,a))>=-1e-4 for a,b in zip(poly,poly[1:]+poly[:1]))
paths=[ROOT/n for n in ('prototype_v1.py','prototype_v2.py','prototype_v4.py','prototype_v5.py','prototype_v8.py','strategy.py','coverage_exact.py','benchmark.py','baseline_breakthrough.py','robot_core.py','geometry.py','offline_sim.py','robot_client.py','run_robot.py')]
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
rows=[]
for seed,count,stress,name,kwargs in [(17,10,'minrange','active1',dict(weight=1)),(17,10,'minrange','active2',dict(weight=2))]:
    world=Fixture(seed,count,stress)
    if seed==17:world.sources[0].update(x=3.,y=0.)
    truth={s['channel']:(s['x'],s['y']) for s in world.sources}
    checks={'truth_containment':0,'certified_clears':0,'timing_steps':0}
    class Audited(Strategy):
        def viewpoint(self,tr):
            import copy
            before=copy.deepcopy(tr)
            q=super().viewpoint(tr)
            assert tr==before, 'planning mutated observation feasible set'
            assert all(math.isfinite(x) and abs(x)<=2e6 for x in q)
            checks['viewpoint_calls']=checks.get('viewpoint_calls',0)+1
            return q
        def observe(self,p,ch):
            res=super().observe(p,ch)
            for channel,tr in self.tracks.items():
                if channel not in self.cleared:
                    assert contained(truth[channel],tr['poly']), ('truth_excluded',channel)
                    checks['truth_containment']+=1
            return res
    policy=Audited(PublicClient(world),**kwargs)
    start=time.perf_counter();r=policy.run();r['runtime_s']=time.perf_counter()-start
    assert all(s['cleared'] for s in world.sources) and r['cleared']==count,r
    assert r['status']=='complete_coverage' and r['pending_tracks']==0,r
    assert policy.coverage_proof['complete'] and certificate(policy.coverage.scans)[0]
    if seed==17:assert any(t['response'].get('measure_result')=='near' for t in policy.trace)
    pos=(0.,0.);ch=1;total=0.;distance=0.;switches=0;failures=[]
    for i,t in enumerate(policy.trace):
        p=(t['x'],t['y']);d=dist(pos,p);distance+=d;total+=d/5;pos=p
        assert all(math.isfinite(x) and abs(x)<=2e6 for x in p)
        if t['kind']=='measure':
            total+=5+(t['channel']!=ch);switches+=(t['channel']!=ch);ch=t['channel']
        else:
            ok=t['response']['clear_result']=='success';total+=5 if ok else 3
            assert ok == (dist(p,truth[t['channel']])<=20)
            if not ok:
                later=[(j,u) for j,u in enumerate(policy.trace[i+1:],i+1) if u['channel']==t['channel']]
                assert any(u['kind']=='clear' and u['response']['clear_result']=='success' for j,u in later)
                assert any(u['kind']=='measure' for j,u in later)
                assert later[0][1]['kind']=='measure' and (later[0][1]['x'],later[0][1]['y'])==p, 'miss not followed by same-position bearing'
                failures.append(dict(index=i,channel=t['channel'],distance_to_source_m=dist(p,truth[t['channel']]),subsequent_same_channel=[dict(index=j,kind=u['kind'],result=u['response'].get('measure_result',u['response'].get('clear_result'))) for j,u in later]))
        assert abs(total-t['virtual_time_s'])<1e-7
        checks['timing_steps']+=1
    for c in policy.certificates:
        assert contained(truth[c['channel']],c['vertices'])
        assert dist(c['center'],truth[c['channel']])<=c['radius']+1e-5 and c['radius']<=19.9
        checks['certified_clears']+=1
    if name=='combined_failure_reproduction':assert failures, 'Failure branch was not exercised'
    assert len({f['channel'] for f in failures})==len(failures), 'multiple failed optical trials per channel'
    row=dict(name=name,seed=seed,stress=stress,count=count,summary=r,checks=checks,reconstructed_virtual_time_s=total,distance_m=distance,switches=switches,failed_optical_attempts=failures,coverage=policy.coverage_proof)
    rows.append(row)
    (ROOT/'p1_review'/f'v8_trace_{name}_{seed}.json').write_text(json.dumps(policy.trace,indent=2),encoding='utf-8')
assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
report=dict(status='PASS',scope='P1 incremental v8; no network or official runs',hashes=hashes,rows=rows)
(ROOT/'p1_review'/'evidence_v8.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(status='PASS',hashes=hashes,rows=[{k:v for k,v in r.items() if k!='coverage'} for r in rows]),indent=2))
