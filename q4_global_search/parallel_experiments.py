"""Independent synthetic fixtures in separate processes; never live robot actions."""
import argparse,importlib,json
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path

def one(task):
    module,seed,algorithm=task;importlib.import_module(module)
    import benchmark
    return benchmark.run_one(seed,'random',algorithm)
def main():
    p=argparse.ArgumentParser();p.add_argument('--module',required=True);p.add_argument('--seeds',required=True);p.add_argument('--algorithms',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    lo,hi=map(int,a.seeds.split(':'));tasks=[(a.module,s,n) for s in range(lo,hi+1) for n in a.algorithms.split(',')];rows=[]
    out=Path(__file__).resolve().parent/'results'/f'{a.out}.json'
    with ProcessPoolExecutor(max_workers=4) as ex:
        for f in as_completed([ex.submit(one,t) for t in tasks]):
            rows.append(f.result());out.write_text(json.dumps(sorted(rows,key=lambda r:(r['seed'],r['algorithm'])),indent=2))
            print(f'{len(rows)}/{len(tasks)} cases validated',flush=True)
if __name__=='__main__':main()
