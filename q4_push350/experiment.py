"""Paired experiment entry; previous best remains an untouched comparator."""
import argparse,json,time
from pathlib import Path
import benchmark
from strategy_final import Strategy as Previous
from strategy_explore import Strategy as Explore
from strategy_ring21 import Strategy as Ring21
from strategy_particle import Strategy as Particle
from strategy_route import Strategy as Tour
from strategy_active import Strategy as Active
HERE=Path(__file__).resolve().parent
CONFIGS={'previous':None,'ring22':{},'defer22':dict(schedule='defer'),'defer25':dict(layout_kind='ring25',schedule='defer')}
CONFIGS.update({name+str(n):dict(layout_kind='ring'+str(n),**cfg) for n in (22,25) for name,cfg in {
    'inner':dict(schedule='inner'),'near':dict(schedule='near'),
    'greedy':dict(sweep_kind='greedy'),'probe':dict(sweep_kind='probe'),
    'probe_greedy':dict(sweep_kind='probe_greedy'),
    'defer_greedy':dict(schedule='defer',sweep_kind='greedy')}.items()})
CONFIGS.update({'ring21':{},'defer21':dict(schedule='defer'),'inner21':dict(schedule='inner'),
    'near21':dict(schedule='near'),'greedy21':dict(sweep_kind='greedy'),
    'particle21':{},'particle_defer21':dict(schedule='defer'),
    'particle22':dict(layout_kind='ring22'), 'particle25':dict(layout_kind='ring25'),
    'particle3':dict(particle_tries=3),'particle_plain':dict(negative_info=False),
    'tour150':dict(detour_limit=150.),'tour350':dict(detour_limit=350.),'tour700':dict(detour_limit=700.),
    'tour_eager':dict(wait_views=False),'tour25':dict(tour_layout='ring25')})
CONFIGS.update({
    'active_half':dict(fraction=.5),'active_default':{},'active_full':dict(fraction=1.),
    'active_narrow':dict(lateral=40.),'active_wide':dict(lateral=200.),
    'active_twice':dict(active_views=2),'active21':dict(active_layout='ring21'),
    'active_defer':dict(schedule='defer')})
def run(seed,stress,name,trace=False):
    benchmark.Strategy=Previous if name=='previous' else Active if name.startswith('active') else Particle if name.startswith('particle') else Tour if name.startswith('tour') else Ring21 if name.endswith('21') else Explore
    benchmark.CONFIGS={name:CONFIGS[name] or {}}
    start=time.perf_counter();r=benchmark.run_one(seed,stress,name,trace)
    r['pipeline_wall_s']=time.perf_counter()-start
    return r
def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',default='2,8');p.add_argument('--stress',default='random');p.add_argument('--configs',default='previous,ring22,defer22');p.add_argument('--out',default='minimal');a=p.parse_args()
    rows=[]
    for seed in map(int,a.seeds.split(',')):
        for stress in a.stress.split(','):
            for name in a.configs.split(','):
                r=run(seed,stress,name,True);rows.append(r)
                print(seed,stress,name,round(r['average_time_s'],3),r['cleared'],r['total'],flush=True)
                (HERE/'results'/f'{a.out}.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
if __name__=='__main__':main()
