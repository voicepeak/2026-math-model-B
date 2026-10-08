"""Paired Q4 synthetic experiments. Truth is confined to fixture and audit."""
import argparse,csv,hashlib,json,math,random,time,traceback
from pathlib import Path
from geometry import dist,unit
from offline_sim import OfflineClient
from strategy import Strategy
from baseline_original import Strategy as Original
HERE=Path(__file__).resolve().parent
CONFIGS={
 'original':None,
 'nearest':dict(routing='nearest'),
 'twoopt':dict(routing='twoopt'),
 'multistart':dict(routing='multistart'),
 'anneal':dict(routing='anneal'),
 'exact':dict(routing='exact'),
 'square':dict(mesh_kind='square'),
 'optical':dict(localizer='optical'),
 'strip':dict(localizer='strip'),
 'no_shared':dict(shared=False),
 'phase30':dict(phase=30.),
 'dense':dict(spacing=900.),
 'trial100':dict(trial_radius=100.),
 'no_trial':dict(trial_radius=0.),
}
class Fixture(OfflineClient):
    def __init__(self,seed,count,stress='random'):
        super().__init__('q4',seed,count);self.seed=seed;self.stress=stress
        for i,s in enumerate(self.sources):
            if stress in ('directed','edge','tangent','cluster','extreme','bias','minrange'):
                s['direction']=(seed*31.73+i*137.508)%360
            if stress=='omni':s['direction']=None
            if stress in ('edge','tangent'):
                a=(seed*7.123+i*360/count)%360;u=unit(a)
                s.update(x=1799.999*u[0],y=1799.999*u[1],radius=1000.,direction=a+(89.999 if stress=='tangent' else 0))
            elif stress=='cluster':
                a=seed*21.371+i*.2;u=unit(a);r=1300+10*(i%5)
                s.update(x=r*u[0],y=r*u[1],radius=1000.)
            elif stress=='minrange':s['radius']=1000.
        self.initial=[dict(s) for s in self.sources]
    def measure(self,x,y,c):
        key=(c,round(x,6),round(y,6));h=hashlib.sha256(f'{self.seed}:{key}'.encode()).digest()
        e=int.from_bytes(h[:8],'big')/(2**64-1)*2-1
        if self.stress=='extreme':e=1. if h[0]%2 else -1.
        elif self.stress=='bias':e=1. if c%2 else -1.
        self.err[key]=e
        return super().measure(x,y,c)
class PublicClient:
    __slots__=('__inner',)
    def __init__(self,inner):self.__inner=inner
    @property
    def position(self):return self.__inner.position
    @property
    def channel(self):return self.__inner.channel
    @property
    def virtual_time(self):return self.__inner.virtual_time
    def time_left(self):return self.__inner.time_left()
    def measure(self,x,y,ch):return self.__inner.measure(x,y,ch)
    def clear(self,x,y,ch):return self.__inner.clear(x,y,ch)

def run_one(seed,stress,name,save_trace=False):
    count=10+random.Random(seed+891).randrange(7);fixture=Fixture(seed,count,stress)
    st=Original(PublicClient(fixture),'q4') if name=='original' else Strategy(PublicClient(fixture),'q4',**CONFIGS[name])
    t0=time.perf_counter();result=st.run()
    result.update(seed=seed,stress=stress,algorithm=name,total=count,runtime_s=time.perf_counter()-t0,
                  actual_cleared=sum(s['cleared'] for s in fixture.sources),directional=sum(s['direction'] is not None for s in fixture.initial))
    pos=(0.,0.);channel=1;length=0.;switches=0;measures=0;success=0;failed=0
    for row in st.trace:
        p=(row['x'],row['y']);length+=dist(pos,p);pos=p
        if row['kind']=='measure':
            switches+=row['channel']!=channel;channel=row['channel'];measures+=1
        else:
            success+=row['response']['clear_result']=='success';failed+=row['response']['clear_result']!='success'
        expected=length/5+measures*5+switches+success*5+failed*3
        assert abs(expected-row['virtual_time_s'])<1e-6,(expected,row)
    result.update(distance_m=length,switches=switches,failed_clears=failed)
    assert result['actual_cleared']==count==result['cleared'],result
    assert result['status'].startswith('complete'),result
    for cert in getattr(st,'certificates',[]):
        source=next(s for s in fixture.initial if s['channel']==cert['channel'])
        assert dist(cert['center'],(source['x'],source['y']))<=20
        assert max(dist(cert['center'],v) for v in cert['vertices'])<=19.9+1e-6
    if save_trace:
        (HERE/'results').mkdir(exist_ok=True)
        (HERE/'results'/f'trace_{name}_{stress}_{seed}.json').write_text(json.dumps(dict(summary=result,
            sources=fixture.initial,trace=st.trace,scans=getattr(st,'scans',[]),nodes=getattr(st,'all_nodes',[]),
            certificates=getattr(st,'certificates',[])),indent=2),encoding='utf-8')
    return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seeds',default='1:2');ap.add_argument('--stress',default='random')
    ap.add_argument('--algorithms',default='original,twoopt');ap.add_argument('--out',default='minimal');ap.add_argument('--trace',action='store_true');a=ap.parse_args()
    if ':' in a.seeds:
        lo,hi=map(int,a.seeds.split(':'));seeds=range(lo,hi+1)
    else:seeds=list(map(int,a.seeds.split(',')))
    rows=[];folder=HERE/'results';folder.mkdir(exist_ok=True)
    for stress in a.stress.split(','):
        for seed in seeds:
            for name in a.algorithms.split(','):
                try:r=run_one(seed,stress,name,a.trace and seed==seeds[0]);rows.append(r)
                except Exception:
                    (folder/f'{a.out}_failure.txt').write_text(f'{stress} {seed} {name}\n'+traceback.format_exc(),encoding='utf-8');raise
                print(f'{stress} {seed} {name}: {r["actual_cleared"]}/{r["total"]} {r["average_time_s"]:.3f} s/source, {r["runtime_s"]:.2f}s strategy wall time (initialization excluded)',flush=True)
                (folder/f'{a.out}.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    keys=sorted(set().union(*(r.keys() for r in rows))-{'channels'})
    with (folder/f'{a.out}.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,keys,extrasaction='ignore');w.writeheader();w.writerows(rows)
    for name in a.algorithms.split(','):
        rr=[r for r in rows if r['algorithm']==name]
        print(name,sum(r['virtual_time_s'] for r in rr)/sum(r['total'] for r in rr),flush=True)
if __name__=='__main__':main()
