"""Fresh held-out experiment after parameter freeze; only two selected policies."""
import argparse,csv,json,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
from experiment import run
HERE=Path(__file__).resolve().parent
def tasks_for(phase):
    if phase=='development':seeds=range(1,41);stresses=['random']
    elif phase=='holdout':seeds=range(40001,40101);stresses=['random']
    elif phase=='stress':seeds=range(201,211);stresses=['directed','edge','tangent','cluster','minrange','bias','extreme','omni']
    elif phase=='minimal':seeds=[2,8];stresses=['random','edge','extreme']
    else:raise ValueError(phase)
    return [(phase,s,t,a,s==seeds[0]) for s in seeds for t in stresses for a in ('original','candidate')]
def worker(task):
    phase,seed,stress,alg,trace=task
    cfg=json.loads((HERE/'selected_new.json').read_text(encoding='utf-8'))
    name='previous' if alg=='original' else cfg['selected']
    r=run(seed,stress,name,trace)
    r.update(dataset=phase,algorithm=alg,study_config=name,local_pipeline_wall_s=r.pop('pipeline_wall_s'))
    r['strategy_wall_s_excluding_init']=r.pop('runtime_s')
    if trace:
        source=HERE/'results'/f'trace_{name}_{stress}_{seed}.json'
        (HERE/'results'/f'trace_{alg}_{stress}_{seed}.json').write_bytes(source.read_bytes())
    return r
def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','holdout','stress','minimal'],required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    rows=[];tasks=tasks_for(a.phase);path=HERE/'results'/f'final_{a.phase}.json'
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures={pool.submit(worker,t):t for t in tasks}
        for f in as_completed(futures):
            try:rows.append(f.result())
            except Exception as exc:
                path.with_suffix('.failure.json').write_text(json.dumps(dict(task=futures[f],error=repr(exc)),indent=2),encoding='utf-8');raise
            rows.sort(key=lambda r:(r['dataset'],r['stress'],r['seed'],r['algorithm']))
            path.write_text(json.dumps(rows,indent=2),encoding='utf-8')
            if len(rows)%20==0:print(a.phase,len(rows),'/',len(tasks),flush=True)
    keys=sorted(set().union(*(r.keys() for r in rows))-{'channels'})
    with path.with_suffix('.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,keys,extrasaction='ignore');w.writeheader();w.writerows(rows)
    for n in ('original','candidate'):
        rr=[r for r in rows if r['algorithm']==n];print(n,sum(r['virtual_time_s'] for r in rr)/sum(r['total'] for r in rr),flush=True)
if __name__=='__main__':main()
