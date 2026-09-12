import hashlib,json,math,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmark import Fixture, PublicClient
from strategy import Strategy, exclude_disk
from coverage_exact import certificate
from geometry import cross,sub,dist,hull,unit,mul

def contained(p,poly):
    if len(poly)<3: return any(dist(p,q)<1e-5 for q in poly)
    return all(cross(sub(b,a),sub(p,a))>=-1e-4 for a,b in zip(poly,poly[1:]+poly[:1]))

paths=[ROOT/n for n in ('strategy.py','coverage_exact.py','benchmark.py','baseline_breakthrough.py','robot_core.py','geometry.py','offline_sim.py','robot_client.py','run_robot.py')]
paths += [ROOT.parent/n for n in ('题目分析报告.md','术语表格.md')]
paths += [ROOT.parents[1]/n for n in ('_B题_pdf.txt','_附件1.txt','_附件2.txt')]
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
world=Fixture(17,10,'minrange')
world.sources[0].update(x=3.,y=0.)
truth={s['channel']:(s['x'],s['y']) for s in world.sources}
checks={'track_truth_checks':0,'clear_certificate_checks':0,'timing_steps':0}
class Audited(Strategy):
    def observe(self,p,ch):
        res=super().observe(p,ch)
        for channel,tr in self.tracks.items():
            if channel not in self.cleared:
                assert contained(truth[channel],tr['poly']), ('truth_excluded',channel,truth[channel],tr['poly'])
                checks['track_truth_checks']+=1
        return res

public=PublicClient(world)
assert not any(hasattr(public,n) for n in ('sources','initial','seed','rng','err'))
policy=Audited(public)
started=time.perf_counter(); result=policy.run(); result['runtime_s']=time.perf_counter()-started
assert result['cleared']==10 and all(s['cleared'] for s in world.sources), result
assert result['status']=='complete_coverage' and result['pending_tracks']==0, result
assert policy.coverage_proof['complete']
assert any(r['response'].get('measure_result')=='near' for r in policy.trace)
pos=(0.,0.); ch=1; total=0.; distance=0.; switches=0
for r in policy.trace:
    p=(r['x'],r['y']); step=dist(pos,p); distance+=step;total+=step/5;pos=p
    assert all(math.isfinite(x) and abs(x)<=2e6 for x in p)
    assert 1<=r['channel']<=20
    if r['kind']=='measure':
        sw=(r['channel']!=ch); total+=5+sw;switches+=sw;ch=r['channel']
    else:total+=5 if r['response']['clear_result']=='success' else 3
    assert abs(total-r['virtual_time_s'])<1e-7
    checks['timing_steps']+=1
for c in policy.certificates:
    assert contained(truth[c['channel']],c['vertices'])
    assert dist(c['center'],truth[c['channel']])<=c['radius']+1e-5
    assert c['radius']<=19.9
    checks['clear_certificate_checks']+=1
assert not certificate([(0.,0.)])[0]
hex_sites=[(0.,0.)]+[mul(unit(a),1200) for a in range(0,360,60)]
hex_certificate=certificate(hex_sites)
assert hex_certificate[0]
# Independent sampled diagnostic supplements the continuous Voronoi proof.
max_sample=0.
for a in range(720):
    for rad in (0,600,1000,1400,1800):
        p=mul(unit(a/2),rad)
        max_sample=max(max_sample,min(dist(p,s) for s in policy.coverage.scans))
assert max_sample<=policy.coverage_proof['worst_distance_m']+1e-5
rng=random.Random(123); kept=0
for k in range(100):
    poly=hull([(rng.uniform(-1500,1500),rng.uniform(-1500,1500)) for _ in range(12)])
    center=(rng.uniform(-700,700),rng.uniform(-700,700)); out=exclude_disk(poly,center)
    for j in range(300):
        weights=[rng.random() for _ in poly]; total_w=sum(weights)
        p=tuple(sum(w*v[d] for w,v in zip(weights,poly))/total_w for d in (0,1))
        if dist(p,center)>=1000:
            assert contained(p,out), ('exclude_disk_nonconservative',poly,center,p,out)
            kept+=1
checks.update(exclude_disk_feasible_samples=kept,independent_coverage_samples=3600)
after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
assert before==after, 'inputs changed during audit'
report=dict(status='PASS',scope='P1 local minimum slice; no HTTP or official tests',hashes=before,summary=result,checks=checks,distance_m=distance,switches=switches,reconstructed_virtual_time_s=total,coverage=policy.coverage_proof,independent_sample_worst_m=max_sample,hexagon_certificate=hex_certificate)
out=ROOT/'p1_review'/'evidence.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
