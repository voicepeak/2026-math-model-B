"""Generic Q1 command: python B题/code/solve_q1.py input.json --output answer.json"""
import argparse,json,math
from pathlib import Path
from geometry import intersection,enclosing_circle

def main():
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--output',default='q1_answer.json');a=p.parse_args()
    data=json.loads(Path(a.input).read_text(encoding='utf-8-sig'));obs=data['observations'];alpha=float(data.get('alpha_deg',1))
    if any(len(row)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in row) for row in obs):raise ValueError('Each observation must be finite [x,y,bearing_deg]')
    result=intersection(obs,alpha)
    if result['status']=='bounded':result['mec_center'],result['mec_radius']=enclosing_circle(result['vertices'])
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
