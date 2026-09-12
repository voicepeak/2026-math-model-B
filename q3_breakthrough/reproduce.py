"""Unique deterministic reproduction entry. Never contacts official simulator."""
import subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def run(script,*args):
    subprocess.run([sys.executable,str(HERE/script),*args],cwd=HERE,check=True)

def main():
    run('test_strategy.py')
    run('benchmark.py','--seeds','1:40','--out','paired_random','--trace')
    run('benchmark.py','--seeds','101:110','--stress','edge,cluster,minrange,bias,extreme','--out','stress','--trace')
    run('benchmark.py','--seeds','1001:1100','--out','holdout','--trace')
    run('benchmark.py','--seeds','1:20','--algorithms','no_shared,fixed_cover','--out','ablation')
    run('benchmark.py','--seeds','1:10','--algorithms','original','--out','original')
    run('selftest.py','--seeds','11,12,13,14,15')
    run('analyze_results.py')

if __name__=='__main__': main()
