"""Reproduce frozen paired study, metrics, figures and verifications (offline only).
Usage: python reproduce.py
       python reproduce.py --verify-only  # saved-study integrity + smaller replay
"""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
# Local task dependency directory; a portable installation may instead use pip.
LOCAL_DEPS=HERE.parents[1]/'work'/'pydeps'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,log):
    command=[sys.executable]+args;print('RUN',' '.join(args),flush=True)
    result=subprocess.run(command,cwd=HERE,env=os.environ.copy(),capture_output=True,text=True,encoding='utf-8',errors='replace')
    log.append(dict(command=command,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
    (HERE/'results/reproduction_log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
    if result.returncode:
        print(result.stdout);print(result.stderr);raise RuntimeError(f'Command failed: {args}')
    print(result.stdout[-1800:],flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    if LOCAL_DEPS.exists():
        os.environ['PYTHONPATH']=str(LOCAL_DEPS)+os.pathsep+os.environ.get('PYTHONPATH','')
        sys.path.insert(0,str(LOCAL_DEPS))
    os.environ['PYTHONIOENCODING']='utf-8'
    os.environ.setdefault('MPLCONFIGDIR',str(LOCAL_DEPS.parent/'mplconfig'))
    lock=json.loads((HERE/'frozen_hashes.json').read_text(encoding='utf-8'))
    for name,value in lock.items():
        if sha(HERE/name)!=value:raise RuntimeError('Frozen file changed: '+name)
    from evidence_integrity import check as check_evidence
    check_evidence()
    log=[];run(['ring_certificate.py'],log)
    run(['utils/check_env.py','--features','data','visualization','optimization'],log)
    if a.verify_only:run(['evaluate_final.py','--phase','minimal','--workers',str(a.workers),'--out','verification_replay'],log)
    else:
        for phase in ('development','holdout','stress'):run(['evaluate_final.py','--phase',phase,'--workers',str(a.workers)],log)
    run(['http_selftest.py'],log)
    check_evidence()
    run(['analyze_results.py'],log)
    run(['build_report.py'],log)
    run(['utils/check_figure.py',str(HERE/'figures'/'*.svg'),str(HERE/'figures'/'*.png'),str(HERE/'figures'/'_qa'/'*.png'),'--strict'],log)
    run(['utils/figure_audit.py',str(HERE/'figures'),'--questions','q4','--strict'],log)
    # Supplied skill manifest builder, no substitute for its schema.
    from utils.repro_manifest import build_manifest
    manifest=build_manifest([str(HERE/name) for name in lock],20260912,
        dict(config=json.loads((HERE/'frozen_config.json').read_text(encoding='utf-8')),scope='q4',workers=a.workers,
             mode='verify-only' if a.verify_only else 'full',study='40 development + 100 holdout + 80 stress'),
        'python reproduce.py',['numpy','scipy','matplotlib','pandas','Pillow'])
    manifest['input_files']=[{**r,'path':str(Path(r['path']).relative_to(HERE))} for r in manifest['input_files']]
    (HERE/'results/复现清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('All requested reproduction checks passed.',flush=True)
if __name__=='__main__':main()
