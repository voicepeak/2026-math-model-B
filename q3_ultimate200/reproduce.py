"""Unique local reproduction command; never contacts the official simulator."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run(script,*args):
    print('RUN',script,*args,flush=True)
    subprocess.run([sys.executable,str(ROOT/script),*args],cwd=ROOT,check=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis-only',action='store_true');p.add_argument('--research',action='store_true');a=p.parse_args()
    start=time.perf_counter()
    if not a.analysis_only:
        run('utils/check_env.py','--features','data','visualization')
        run('test_strategy.py')
        run('replay_failure.py')
        if a.research:
            batches=[('prototype_v1','1:10','breakthrough,visibility,prototype_v1'),
                     ('screening','1:10','v2,combined,r1200,r1450,r1650,v4,optical_fixed,v4_no_optical,trial50,trial150,trial300'),
                     ('screening2','1:10','elastic,elastic50,elastic0,pilot100,pilot200,pilot300'),
                     ('screening3','1:10','active1,active2'),('screening4','1:10','short100,short150,short200,short_radius1200'),
                     ('development_more','11:40','breakthrough,optical_fixed,elastic50,pilot200,active2'),
                     ('combo_development','1:40','combo100,combo200')]
            for name,seeds,alg in batches:run('benchmark.py','--seeds',seeds,'--algorithms',alg,'--out',name)
        run('benchmark.py','--seeds','1:40','--algorithms','breakthrough,ultimate','--out','final_development','--trace')
        run('benchmark.py','--seeds','101:110','--stress','edge,cluster,minrange,bias,extreme','--algorithms','breakthrough,ultimate','--out','final_stress','--trace')
        run('benchmark.py','--seeds','20001:20100','--algorithms','breakthrough,ultimate','--out','final_holdout','--trace')
        run('selftest.py','--seeds','211,212,213,214,215')
    run('analyze_results.py')
    run('utils/check_figure.py','figures/*.png','figures/*.svg','--strict')
    run('utils/figure_audit.py','figures','--questions','q3','--strict')
    from utils.repro_manifest import build_manifest
    files=list(ROOT.glob('*.py'))+list((ROOT/'utils').glob('*.py'))+list((ROOT/'archived').glob('*.py'))+[ROOT/'frozen_config.json']+list((ROOT/'inputs').glob('*.txt'))
    files += [ROOT/'results'/(n+'.json') for n in ('prototype_v1','screening','screening2','screening3','screening4','development_more','combo_development') if (ROOT/'results'/(n+'.json')).exists()]
    manifest=build_manifest(files,20260912,dict(configuration=json.loads((ROOT/'frozen_config.json').read_text(encoding='utf-8')),
        development='1:40',stress='101:110 five families',holdout='20001:20100',http='211,212,213,214,215',
        error_model='fixed channel-position SHA256; same seed for paired policies',alpha_deg=1.005,speed_m_s=5,clear_radius_m=20),
        'python reproduce.py', ['numpy','pandas','matplotlib','Pillow'])
    manifest['elapsed_s']=time.perf_counter()-start
    manifest['artifacts']=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                           for p in sorted((ROOT/'results').glob('final_*.csv'))]
    (ROOT/'results'/'复现清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('REPRODUCTION COMPLETE',manifest['elapsed_s'],flush=True)

if __name__=='__main__':main()
