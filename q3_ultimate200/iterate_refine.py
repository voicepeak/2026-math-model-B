"""围绕当前最佳配置的细化随机搜索，写入 results/iterate_refine.jsonl。"""
import argparse
import json
import os
import random
import time

from iterate_search import build, evaluate, key_of, RES

LOG = os.path.join(RES, 'iterate_refine.jsonl')

SPACE = dict(
    pilot=[150, 175, 200, 225, 250, 300],
    attempt=[45, 55, 60, 65, 70, 80, 90, 110],
    passes=[2, 3, 4, 5, 6],
    elastic=[True],
    visibility=[True, False],
    radius=[1121, 1135, 1150, 1165, 1180, 1200],
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--configs', type=int, default=60)
    ap.add_argument('--seeds', default='1:24')
    ap.add_argument('--budget', type=float, default=100000.0)
    ap.add_argument('--rng', type=int, default=999)
    a = ap.parse_args()
    s0, s1 = map(int, a.seeds.split(':'))
    seeds = list(range(s0, s1 + 1))
    rng = random.Random(a.rng)
    done = set()
    if os.path.exists(LOG):
        for line in open(LOG, encoding='utf-8'):
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get('ok'):
                done.add(key_of(o['cfg']))
    t0 = time.time()
    tried = 0
    best = None
    while tried < a.configs and (time.time() - t0) < a.budget:
        cfg = {k: rng.choice(v) for k, v in SPACE.items()}
        if key_of(cfg) in done:
            continue
        tried += 1
        res = evaluate(cfg, seeds)
        rec = dict(cfg=cfg, seeds=[s0, s1], **res)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec) + '\n')
        if res.get('ok'):
            tag = ''
            if best is None or res['avg'] < best[0]:
                best = (res['avg'], cfg)
                tag = '  <== best'
            print('%.2f s/源  %s%s' % (res['avg'], cfg, tag), flush=True)
        else:
            print('INVALID %s  %s' % (res.get('error'), cfg), flush=True)
    if best:
        print('REFINE BEST %.2f  %s' % best, flush=True)


if __name__ == '__main__':
    main()
