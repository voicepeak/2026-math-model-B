"""Portable offline verification; never calls the official simulator.

Standard library only. Checks package hashes, the Q1 counterexample, Q2 grid
optima, Q3 regression tests, the Q4 exact 22-point coverage audit and a private
local HTTP smoke test. Runs inside a temporary copy and never modifies the pack.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cwd, *args):
    print('RUN', Path(cwd).name, *args[:2], flush=True)
    r = subprocess.run([sys.executable, *args], cwd=cwd, check=True,
                       capture_output=True, text=True, encoding='utf8', errors='replace')
    print(r.stdout[-1800:], flush=True)
    return r


def read_json_line(t):
    return json.loads(t.strip().splitlines()[-1])


def main():
    manifest = read(ROOT / 'submission_manifest.json')
    for item in manifest['files']:
        p = ROOT / item['path']
        assert p.is_file(), item['path']
        assert sha(p) == item['sha256'], item['path']
    with tempfile.TemporaryDirectory(prefix='b_submission_verify_') as tmp:
        base = Path(tmp) / 'package'
        shutil.copytree(ROOT, base)
        q12 = base / '问题一与问题二/code'
        a3 = base / '问题三/code'
        a4 = base / '问题四/code'
        run(q12, 'test_core.py')
        run(q12, 'solve_q1.py', 'q1_example.json', '--output', 'q1_verified.json')
        q1 = read(q12 / 'q1_verified.json')
        assert q1['status'] == 'bounded'
        assert abs(q1['diameter'] - 28.966814507054192) < 1e-8
        assert q1['circle_excess'] > 0.26
        run(q12, '-c', "from geometry import *; s=source_samples((0,0),0); p=prior((0,0),0); "
                       "a=sampled_score((0,0),0,(800,-600),s,[-1,0,1],poly=p); "
                       "b=sampled_score((0,0),0,(850,-525),source_samples((0,0),0,dense=True),[-1,-.5,0,.5,1],poly=p); "
                       "assert abs(a-112.14914074531447)<1e-8 and abs(b-111.89311189189851)<1e-8; "
                       "print({'base_score':a,'refined_score':b})")
        run(a3, 'test_strategy.py')
        exact = run(a4, 'results/p1_exact_coverage_audit.py')
        assert read_json_line(exact.stdout)['passed'] == 2831
        run(a4, 'http_selftest.py')
    print('PASS: package hashes, Q1 counterexample, Q2 grid optima, Q3 regression tests, '
          'Q4 exact 22-point coverage audit (2831 tiles) and private HTTP smoke.')


if __name__ == '__main__':
    main()
