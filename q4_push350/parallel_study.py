"""Run independent offline fixtures in parallel; retain failures as evidence."""
import argparse,json,csv
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from experiment import CONFIGS,run
HERE=Path(__file__).resolve().parent
def worker(task):
    seed,stress,name=task
    try:return run(seed,stress,name),None
    except Exception as exc:return None,dict(seed=seed,stress=stress,algorithm=name,error=repr(exc))
def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',default='1:10');p.add_argument('--stress',default='random');p.add_argument('--configs',default=','.join(CONFIGS));p.add_argument('--workers',type=int,default=4);p.add_argument('--out',default='screening');a=p.parse_args()
    lo,hi=map(int,a.seeds.split(':'));tasks=[(s,t,n) for s in range(lo,hi+1) for t in a.stress.split(',') for n in a.configs.split(',')];rows=[];failures=[]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for future in as_completed([pool.submit(worker,t) for t in tasks]):
            r,e=future.result()
            if e:failures.append(e)
            else:rows.append(r)
            rows.sort(key=lambda r:(r['seed'],r['stress'],r['algorithm']))
            (HERE/'results'/f'{a.out}.json').write_text(json.dumps(dict(tasks=tasks,rows=rows,failures=failures),indent=2),encoding='utf-8')
            if (len(rows)+len(failures))%10==0:print('completed',len(rows)+len(failures),'/',len(tasks),'failures',len(failures),flush=True)
    for n in a.configs.split(','):
        rr=[r for r in rows if r['algorithm']==n]
        print(n,len(rr),sum(r['virtual_time_s'] for r in rr)/sum(r['total'] for r in rr) if rr else None,flush=True)
    if failures:raise SystemExit(2)
if __name__=='__main__':main()
