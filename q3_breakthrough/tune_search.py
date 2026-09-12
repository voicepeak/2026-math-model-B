"""Astra 参数随机搜索（在同一批配对场景上）。"""
import argparse
import random

from benchmark import Fixture, PublicClient
from strategy_tune import Strategy
from geometry import dist

BASE = dict(hex_r=1150.0, short_fwd=150.0, short_lat=50.0,
            vp_off_min=25.0, vp_off_max=160.0, vp_off_frac=0.15,
            share_dist=1150.0, share_base=60.0, share_ang=0.12, share_near=150.0,
            twopt_passes=8, reuse_dist=60.0, reuse_ang=0.15, shared=True)

SPACE = dict(
    hex_r=[1121.0, 1150.0, 1180.0, 1200.0],
    short_fwd=[60.0, 100.0, 150.0, 200.0, 260.0],
    short_lat=[35.0, 45.0, 55.0, 70.0],
    vp_off_frac=[0.10, 0.15, 0.20, 0.25],
    vp_off_max=[120.0, 160.0, 200.0],
    share_dist=[1000.0, 1150.0, 1300.0],
    share_ang=[0.08, 0.12, 0.16],
    reuse_dist=[40.0, 60.0, 90.0],
    reuse_ang=[0.10, 0.15, 0.22],
)


def evaluate(params, seeds):
    tt = ts = td = tm = tc = 0
    for seed in seeds:
        count = 10 + random.Random(seed + 891).randrange(7)
        fx = Fixture(seed, count, 'random')
        st = Strategy(PublicClient(fx), **params)
        r = st.run()
        pos = (0.0, 0.0); L = 0.0
        for row in st.trace:
            q = (row['x'], row['y']); L += dist(pos, q); pos = q
        tt += r['virtual_time_s']; ts += count; td += L; tm += r['measures']; tc += r['cleared']
    return tt / ts, td / 1000, tm, tc, ts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', default='1:16')
    ap.add_argument('--iters', type=int, default=40)
    ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()
    seeds = list(range(*[int(x) for x in a.seeds.split(':')]))
    rng = random.Random(a.seed)
    best = (evaluate(BASE, seeds), BASE)
    print('BASE  %.2f s/源  里程 %.1f km  检测 %d' % (best[0][0], best[0][1], best[0][2]))
    for it in range(a.iters):
        p = dict(BASE)
        for k, vals in SPACE.items():
            if rng.random() < 0.5:
                p[k] = rng.choice(vals)
        m = evaluate(p, seeds)
        if m[0] < best[0][0]:
            best = (m, p)
            print('it %-3d NEW BEST %.2f s/源  里程 %.1f km  检测 %d  %s'
                  % (it, m[0], m[1], m[2],
                     {k: p[k] for k in ('hex_r', 'short_fwd', 'short_lat', 'vp_off_frac',
                                        'share_dist', 'share_ang', 'reuse_dist', 'reuse_ang')}))
    m, p = best
    print('\nBEST %.2f s/源  里程 %.1f km  检测 %d  清除 %d/%d' % (m[0], m[1], m[2], m[3], m[4]))
    print('params:', {k: v for k, v in p.items()})


if __name__ == '__main__':
    main()
