import hashlib,json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmark import Fixture,PublicClient
from prototype_v7 import Strategy
from geometry import cross,sub,dist
from coverage_exact import certificate

def contained(p,poly):
    if len(poly)<3:return any(dist(p,q)<1e-5 for q in poly)
    return all(cross(sub(b,a),sub(p,a))>=-1e-4 for a,b in zip(poly,poly[1:]+poly[:1]))
paths=[ROOT/n for n in ('prototype_v1.py','prototype_v2.py','prototype_v4.py','prototype_v5.py','prototype_v7.py','strategy.py','coverage_exact.py','benchmark.py','baseline_breakthrough.py','robot_core.py','geometry.py','offline_sim.py','robot_client.py','run_robot.py')]
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
rows=[]
for seed,count,stress,name,kwargs in [(31,10,'minrange','pilot100_no_signal',dict(pilot=100))]:
    world=Fixture(seed,count,stress)
    if seed==17:world.sources[0].update(x=3.,y=0.)
    for i,src in enumerate(world.sources):
        src.update(x=999*math.cos(i*2*math.pi/count),y=999*math.sin(i*2*math.pi/count))
    truth={s['channel']:(s['x'],s['y']) for s in world.sources}
    checks={'truth_containment':0,'certified_clears':0,'timing_steps':0}
    class Audited(Strategy):
        def scan(self,p):
            old=self.pilot_done
            super().scan(p)
            if p==(0.,0.) and not old:
                pilot_rows=[t for t in self.trace if abs(math.hypot(t['x'],t['y'])-100)<1e-6]
                assert len(pilot_rows)>=2
                assert len(set((t['x'],t['y']) for t in pilot_rows))==1
                checks['pilot_measurements']=len(pilot_rows)
                checks['pilot_no_signal']=sum(t['response'].get('measure_result')=='no_signal' for t in pilot_rows)
                checks['pilot_position']=[pilot_rows[0]['x'],pilot_rows[0]['y']]
                checks['initial_scan_count']=len(self.coverage.scans)
                assert len(self.coverage.scans)==1, 'pilot wrongly counted as full scan'

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
    assert checks['pilot_no_signal']>0, 'pilot no-signal branch was not exercised'
    assert len({f['channel'] for f in failures})==len(failures), 'multiple failed optical trials per channel'
    row=dict(name=name,seed=seed,stress=stress,count=count,summary=r,checks=checks,reconstructed_virtual_time_s=total,distance_m=distance,switches=switches,failed_optical_attempts=failures,coverage=policy.coverage_proof)
    rows.append(row)
    (ROOT/'p1_review'/f'v7_trace_{name}_{seed}.json').write_text(json.dumps(policy.trace,indent=2),encoding='utf-8')
assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
report=dict(status='PASS',scope='P1 incremental v7; no network or official runs',hashes=hashes,rows=rows)
(ROOT/'p1_review'/'evidence_v7_no_signal.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(status='PASS',hashes=hashes,rows=[{k:v for k,v in r.items() if k!='coverage'} for r in rows]),indent=2))
