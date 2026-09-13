"""Unique offline reproduction entry for the second Q4 study."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    deps=HERE.parents[1]/'work/pydeps'
    if deps.exists():sys.path.insert(0,str(deps));os.environ['PYTHONPATH']=str(deps)+os.pathsep+os.environ.get('PYTHONPATH','')
    os.environ['PYTHONIOENCODING']='utf-8';os.environ.setdefault('MPLCONFIGDIR',str(HERE.parents[1]/'work/mplconfig'))
    lock=json.loads((HERE/'frozen_hashes.json').read_text(encoding='utf-8'))
    for f,sha in lock.items():assert hashlib.sha256((HERE/f).read_bytes()).hexdigest()==sha,f
    from evidence_integrity import check
    check();log=[]
    commands=[['utils/check_env.py','--features','data','visualization','optimization'],['results/p1_exact_coverage_audit.py']]
    commands.extend([['evaluate_final.py','--phase',s] for s in (['minimal'] if a.verify_only else ['development','holdout','stress'])])
    commands.extend([['http_selftest.py'],['analyze_results.py'],['build_report.py'],
        ['utils/check_figure.py',str(HERE/'figures/*.svg'),str(HERE/'figures/*.png'),str(HERE/'figures/_qa/*.png'),'--strict'],
        ['utils/figure_audit.py',str(HERE/'figures'),'--questions','q4','--strict']])
    for cmd in commands:
        print('RUN',' '.join(cmd),flush=True)
        r=subprocess.run([sys.executable]+cmd,cwd=HERE,capture_output=True,text=True,encoding='utf-8',errors='replace')
        log.append(dict(command=[sys.executable]+cmd,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
        (HERE/'results/reproduction_log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
        if r.returncode:print(r.stdout,r.stderr);raise SystemExit(r.returncode)
        print(r.stdout[-600:],flush=True)
    check()
    from utils.repro_manifest import build_manifest
    cfg=json.loads((HERE/'selected_new.json').read_text(encoding='utf-8'))
    out=build_manifest([str(HERE/f) for f in lock],20260912,dict(selected=cfg,mode='verify-only' if a.verify_only else 'full'),
                       'python reproduce.py',['numpy','scipy','matplotlib','pandas','Pillow'])
    (HERE/'results/复现清单.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('All reproduction checks passed.',flush=True)
if __name__=='__main__':main()
