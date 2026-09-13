"""Frozen Q4 paired benchmark, independent offline processes only; no HTTP calls."""
import argparse,csv,json,time,os
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
HERE=Path(__file__).resolve().parent

def worker(task):
    phase,seed,stress,name,save_trace=task
    import benchmark
    from strategy_final import Strategy
    benchmark.Strategy=Strategy;benchmark.CONFIGS={'original':None,'candidate':{}}
    t0=time.perf_counter();r=benchmark.run_one(seed,stress,name,save_trace)
    r['local_pipeline_wall_s']=time.perf_counter()-t0
    r['strategy_wall_s_excluding_init']=r.pop('runtime_s')
    r['dataset']=phase
    return r

def tasks_for(phase):
    if phase=='development':seeds=range(1,41);stresses=['random']
    elif phase=='holdout':seeds=range(30001,30101);stresses=['random']
    elif phase=='stress':seeds=range(101,111);stresses=['directed','edge','tangent','cluster','minrange','bias','extreme','omni']
    elif phase=='minimal':seeds=[2,8];stresses=['random','tangent','extreme']
    else:raise ValueError(phase)
    return [(phase,s,stress,n,s==seeds[0]) for stress in stresses for s in seeds for n in ('original','candidate')]

def write_rows(rows,path):
    rows=sorted(rows,key=lambda r:(r['dataset'],r['stress'],r['seed'],r['algorithm']))
    path.write_text(json.dumps(rows,indent=2),encoding='utf-8')
    keys=sorted(set().union(*(r.keys() for r in rows))-{'channels'})
    with path.with_suffix('.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,keys,extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['minimal','development','holdout','stress','all'],default='minimal')
    ap.add_argument('--workers',type=int,default=4);ap.add_argument('--out');a=ap.parse_args()
    phases=['development','holdout','stress'] if a.phase=='all' else [a.phase]
    tasks=[t for phase in phases for t in tasks_for(phase)];rows=[]
    path=HERE/'results'/((a.out or 'final_'+a.phase)+'.json')
    with ProcessPoolExecutor(max_workers=a.workers) as executor:
        futures={executor.submit(worker,t):t for t in tasks}
        for future in as_completed(futures):
            try:r=future.result()
            except Exception as exc:
                path.with_suffix('.failure.json').write_text(json.dumps(dict(task=futures[future],error=repr(exc)),indent=2));raise
            rows.append(r)
            if len(rows)%10==0 or len(rows)==len(tasks):
                write_rows(rows,path);print(f'validated {len(rows)}/{len(tasks)} offline runs',flush=True)
    write_rows(rows,path)
    for name in ('original','candidate'):
        rr=[r for r in rows if r['algorithm']==name];print(name,sum(r['virtual_time_s'] for r in rr)/sum(r['total'] for r in rr),flush=True)
if __name__=='__main__':main()
