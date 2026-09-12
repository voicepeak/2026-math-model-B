"""对 Astra 做单因素参数扫描，同一批配对场景比较平均 s/源。
用法: python sweep.py --seeds 1:16
"""
import argparse
import random
import time

from benchmark import Fixture, PublicClient
from strategy_tune import Strategy
from geometry import dist

BASE = dict(hex_r=1200.0, short_fwd=300.0, short_lat=75.0,
            vp_off_min=25.0, vp_off_max=160.0, vp_off_frac=0.25,
            share_dist=1150.0, share_base=60.0, share_ang=0.12, share_near=150.0,
            twopt_passes=8, reuse_dist=60.0, reuse_ang=0.15, shared=True)

GRID = [
    ('hex_r', [1121.0, 1150.0, 1200.0, 1260.0, 1350.0]),
    ('short_fwd', [0.0, 150.0, 220.0, 300.0, 400.0, 550.0]),
    ('short_lat', [30.0, 50.0, 75.0, 120.0, 200.0]),
    ('vp_off_frac', [0.15, 0.25, 0.35, 0.5]),
    ('vp_off_max', [100.0, 160.0, 220.0, 320.0]),
    ('share_dist', [800.0, 1150.0, 1400.0]),
    ('share_ang', [0.05, 0.12, 0.2, 0.3]),
    ('twopt_passes', [2, 8, 25]),
    ('shared', [True, False]),
]


def evaluate(params, seeds):
    total_t = total_src = total_d = total_m = total_c = 0
    for seed in seeds:
        count = 10 + random.Random(seed + 891).randrange(7)
        fx = Fixture(seed, count, 'random')
        cl = PublicClient(fx)
        st = Strategy(cl, **params)
        r = st.run()
        pos = (0.0, 0.0); L = 0.0
        for row in st.trace:
            q = (row['x'], row['y']); L += dist(pos, q); pos = q
        total_t += r['virtual_time_s']; total_src += count
        total_d += L; total_m += r['measures']; total_c += r['cleared']
    return dict(avg=total_t / total_src, time=total_t, src=total_src,
                dist=total_d / 1000, measures=total_m, cleared=total_c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', default='1:16')
    a = ap.parse_args()
    seeds = list(range(*[int(x) for x in a.seeds.split(':')])) if ':' in a.seeds \
        else list(map(int, a.seeds.split(',')))
    base = evaluate(BASE, seeds)
    print('BASE  %.2f s/源 (里程 %.1f km, 检测 %d, 清除 %d/%d)\n'
          % (base['avg'], base['dist'], base['measures'], base['cleared'], base['src']))
    best = dict(avg=base['avg'], params={})
    for key, vals in GRID:
        print('--- %s ---' % key)
        for v in vals:
            p = dict(BASE); p[key] = v
            m = evaluate(p, seeds)
            mark = ''
            if m['avg'] < base['avg']:
                mark = '  <'
            print('  %-12s %8.2f s/源  里程 %6.1f km  检测 %5d  clear %d/%d%s'
                  % (v, m['avg'], m['dist'], m['measures'], m['cleared'], m['src'], mark))
        print()


if __name__ == '__main__':
    main()
