"""ultimate200 自动参数搜索（本地合成配对，仅用开发种子；留出集只用于最终验证、不回调参）。

用法:
  python iterate_search.py --configs 4 --seeds 1:4          # 快速自检
  python iterate_search.py --configs 120 --seeds 1:24 --budget 3000 --validate
结果增量写入 results/iterate_search.jsonl，最佳配置写入 results/iterate_best.json。
"""
import argparse
import json
import os
import random
import time

from benchmark import Fixture, PublicClient
from prototype_v10 import Strategy as V10
from geometry import dist, mul, unit

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, 'results')
LOG = os.path.join(RES, 'iterate_search.jsonl')
BEST = os.path.join(RES, 'iterate_best.json')

SPACE = dict(
    pilot=[40, 70, 100, 130, 160, 200, 250],
    attempt=[25, 35, 50, 70, 100],
    passes=[1, 2, 3, 4],
    elastic=[True, False],
    visibility=[True, False],
    radius=[1150, 1200, 1250],
)


def build(cfg, client):
    st = V10(client, 'q3', pilot=cfg['pilot'], attempt=cfg['attempt'],
             passes=cfg['passes'], elastic=cfg['elastic'], visibility=cfg['visibility'])
    st.fixed_nodes = [mul(unit(a), cfg['radius']) for a in range(0, 360, 60)]
    return st


def evaluate(cfg, seeds, stress='random'):
    total_t = 0.0
    total_src = 0
    total_d = 0.0
    for seed in seeds:
        count = 10 + random.Random(seed + 891).randrange(7)
        fx = Fixture(seed, count, stress)
        st = build(cfg, PublicClient(fx))
        try:
            r = st.run()
        except Exception as exc:
            return dict(ok=False, error=repr(exc), src=total_src)
        if r['cleared'] != count or not r['status'].startswith('complete'):
            return dict(ok=False, error='not all cleared: %s' % r['status'], src=total_src)
        pos = (0.0, 0.0)
        L = 0.0
        for row in st.trace:
            q = (row['x'], row['y'])
            L += dist(pos, q)
            pos = q
        total_t += r['virtual_time_s']
        total_src += count
        total_d += L
    return dict(ok=True, avg=total_t / total_src, total_t=total_t, src=total_src, dist=total_d)


def key_of(cfg):
    return json.dumps(cfg, sort_keys=True)


def load_done():
    done = {}
    if os.path.exists(LOG):
        for line in open(LOG, encoding='utf-8'):
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get('ok'):
                done[key_of(o['cfg'])] = o
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--configs', type=int, default=60)
    ap.add_argument('--seeds', default='1:24')
    ap.add_argument('--budget', type=float, default=700.0, help='seconds for this invocation')
    ap.add_argument('--validate', action='store_true')
    ap.add_argument('--rng', type=int, default=20260912)
    a = ap.parse_args()
    s0, s1 = map(int, a.seeds.split(':'))
    seeds = list(range(s0, s1 + 1))
    rng = random.Random(a.rng)
    done = load_done()
    print('已评估配置数: %d' % len(done), flush=True)
    t_start = time.time()
    tried = 0
    best = None
    if done:
        best = min(done.values(), key=lambda o: o['avg'])
        print('历史最佳: %.2f s/源 %s' % (best['avg'], best['cfg']), flush=True)
    while tried < a.configs and (time.time() - t_start) < a.budget:
        cfg = {k: rng.choice(v) for k, v in SPACE.items()}
        key = key_of(cfg)
        if key in done:
            continue
        tried += 1
        res = evaluate(cfg, seeds)
        rec = dict(cfg=cfg, seeds=[s0, s1], stress='random', **res)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec) + '\n')
        if res.get('ok'):
            if best is None or res['avg'] < best['avg']:
                best = rec
                print('NEW BEST %.2f s/源  里程 %.1f km  %s' % (
                    res['avg'], res['dist'] / 1000, cfg), flush=True)
                json.dump(best, open(BEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            else:
                print('  %.2f s/源  %s' % (res['avg'], cfg), flush=True)
        else:
            print('  INVALID (%s)  %s' % (res.get('error'), cfg), flush=True)
    if best:
        print('\n本次最佳: %.2f s/源  %s' % (best['avg'], best['cfg']), flush=True)
    if a.validate and best:
        cfg = best['cfg']
        dev = evaluate(cfg, list(range(1, 41)))
        hold = evaluate(cfg, list(range(20001, 20101)))
        out = dict(cfg=cfg, dev=dev, holdout=hold)
        json.dump(out, open(os.path.join(RES, 'iterate_validate.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
        print('验证 dev=%s holdout=%s' % (dev.get('avg'), hold.get('avg')), flush=True)


if __name__ == '__main__':
    main()
