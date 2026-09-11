"""Reproducible offline study: synthetic examples, never official test results."""
import argparse,csv,json,math,time
from pathlib import Path
from geometry import *
from test_core import COUNTER
from offline_sim import OfflineClient
from strategy import Strategy,scan_nodes,fallback_points,ALPHA
ROOT=Path(__file__).resolve().parents[2]

def csv_write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def solve_q2(s=(0,0),theta=0,step=50):
    sources=source_samples(s,theta);poly=prior(s,theta);rows=[]
    if not sources:raise ValueError('First observation has no sampled source within arena')
    for x in range(0,1001,step):
        for y in range(-800,801,step):
            if not guaranteed((x,y)):continue
            b=local_to_global(s,theta,(x,y))
            score=sampled_score(s,theta,b,sources,[-1,0,1],poly=poly)
            rows.append(dict(local_x=x,local_y=y,x=b[0],y=b[1],worst_diameter_m=score,move_m=math.hypot(x,y)))
    # 1e-8 m tie resolution avoids floating-point asymmetry of reflected cases.
    best=min(rows,key=lambda r:(round(r['worst_diameter_m'],8),r['move_m'],r['local_x'],r['local_y']))
    for r in rows:r['candidate_10pct']=r['worst_diameter_m']<=1.1*best['worst_diameter_m']
    return rows,best

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(ROOT/'results'));a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();q1=intersection(COUNTER);c,r=enclosing_circle(q1['vertices']);q1.update(mec_center=c,mec_radius=r,observations=COUNTER)
    csv_write(out/'q1_observations.csv',[dict(x=x,y=y,bearing_deg=t,alpha_deg=1) for x,y,t in COUNTER])
    csv_write(out/'q1_vertices.csv',[dict(vertex=i+1,x=x,y=y) for i,(x,y) in enumerate(q1['vertices'])])
    seq=[];obs=list(COUNTER)
    for i in range(2,7):
        if i>2:
            s=mul(unit(30*i),500);obs.append([*s,bearing(s,(0,0))+0.2])
        rr=intersection(obs);seq.append(dict(observations=i,diameter_m=rr['diameter']))
    csv_write(out/'q1_constraint_sequence.csv',seq)
    rows,best=solve_q2();csv_write(out/'q2_candidates.csv',rows)
    csv_write(out/'q2_eta_sensitivity.csv',[dict(eta=eta,candidates=sum(r['worst_diameter_m']<=(1+eta)*best['worst_diameter_m'] for r in rows)) for eta in [0.05,0.10,0.20]])
    src=source_samples((0,0),0);csv_write(out/'q2_source_scenarios.csv',[dict(x=x,y=y) for x,y in src])
    print('Q2 base',best,flush=True)
    dense_src=source_samples((0,0),0,dense=True);poly=prior((0,0),0);sens=[]
    # Local grid refinement; explicitly not a full global 25 m grid.
    for x in range(max(0,best['local_x']-100),min(1000,best['local_x']+100)+1,25):
        for y in range(max(-800,best['local_y']-100),min(800,best['local_y']+100)+1,25):
            if guaranteed((x,y)):
                score=sampled_score((0,0),0,(x,y),dense_src,[-1,-0.5,0,0.5,1],poly=poly)
                sens.append(dict(local_x=x,local_y=y,worst_diameter_m=score))
    refined=min(sens,key=lambda r:r['worst_diameter_m']);csv_write(out/'q2_local_refinement.csv',sens)
    comparisons=[]
    for b in [(100,0),(0,100),(500,500),(750,300),(best['local_x'],best['local_y'])]:
        comparisons.append(dict(x=b[0],y=b[1],guaranteed_reception=guaranteed(b),
                                 conditional_worst_m=sampled_score((0,0),0,b,src,[-1,0,1],poly=poly)))
    csv_write(out/'q2_comparison.csv',comparisons)
    runs=[]
    for mode in ['q3','q4']:
        for seed in [20260910,20260911,20260912]:
            client=OfflineClient(mode,seed,count=12);st=Strategy(client,mode);rs=st.run()
            rs.update(seed=seed,total=12,cleared_ratio=sum(s['cleared'] for s in client.sources)/12)
            assert rs['cleared_ratio']==1,rs
            runs.append(rs)
            if seed==20260910:
                (out/(mode+'_trace.json')).write_text(json.dumps(st.trace,ensure_ascii=False,indent=2))
                csv_write(out/(mode+'_synthetic_sources.csv'),client.sources)
            print('SYNTHETIC',mode,seed,rs['virtual_time_s'],flush=True)
    csv_write(out/'synthetic_runs.csv',runs)
    nodes={mode:scan_nodes(mode) for mode in ['q3','q4']}
    for mode,points in nodes.items():csv_write(out/(mode+'_scan_nodes.csv'),[dict(order=i,x=x,y=y) for i,(x,y) in enumerate(points)])
    summary=dict(q1=q1,q2=dict(best=best,refined=refined,candidate_count=len(rows),source_scenarios=len(src),second_error_count=3,
                              local_refinement_count=len(sens),dense_source_count=len(dense_src),dense_error_count=5),
                 synthetic_runs=runs,coverage=dict(q3_nodes=len(nodes['q3']),q4_nodes=len(nodes['q4']),
                 worst_scan_distance_m=600*math.sqrt(2),strip_points=len(fallback_points((0,0),0)),
                 worst_optical_distance_m=math.hypot(14,750*math.sin(math.radians(ALPHA)))),
                 official_windows_results='NOT_RUN',runtime_s=time.monotonic()-started)
    (out/'study_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    csv_write(out/'official_results_to_fill.csv',[dict(question=q,run=i,case_code='未执行',cleared='未执行',average_time_s='未执行',program_runtime_s='未执行',encrypted_log='未导出') for q in ['q3','q4'] for i in range(1,4)])
    print('Saved',out,flush=True)
if __name__=='__main__':main()
