"""Generic Q2 grid strategy; coordinates m, bearing degrees. No live simulator calls."""
import argparse,json
from pathlib import Path
from study import solve_q2,csv_write

def main():
    p=argparse.ArgumentParser();p.add_argument('--x',type=float,default=0);p.add_argument('--y',type=float,default=0);p.add_argument('--bearing',type=float,default=0);p.add_argument('--step',type=int,default=50);p.add_argument('--output',default='q2_custom');a=p.parse_args()
    if a.step<=0:raise ValueError('step must be positive')
    rows,best=solve_q2((a.x,a.y),a.bearing,a.step);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    csv_write(out/'candidates.csv',rows);(out/'best.json').write_text(json.dumps(best,ensure_ascii=False,indent=2),encoding='utf-8');print(best)
if __name__=='__main__':main()
