"""配对对比 Astra(新版) vs fast(懒覆盖)。用法: python bench_fast.py --seeds 1:20"""
import argparse
import random
import time

from benchmark import Fixture, PublicClient
from strategy import Strategy as Astra
from strategy_fast import Strategy as Fast
from geometry import dist

ALGOS = {'astra': Astra, 'fast': Fast}


def run_one(seed, stress, name):
    count = 10 + random.Random(seed + 891).randrange(7)
    fx = Fixture(seed, count, stress)
    cl = PublicClient(fx)
    st = ALGOS[name](cl)
    t0 = time.perf_counter()
    r = st.run()
    r['cpu_s'] = time.perf_counter() - t0
    r['actual'] = sum(s['cleared'] for s in fx.sources)
    pos = (0.0, 0.0)
    length = 0.0
    for row in st.trace:
        q = (row['x'], row['y'])
        length += dist(pos, q)
        pos = q
    r['distance_m'] = length
    return r, count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', default='1:20')
    ap.add_argument('--stress', default='random')
    a = ap.parse_args()
    if ':' in a.seeds:
        s0, s1 = map(int, a.seeds.split(':'))
        seeds = list(range(s0, s1 + 1))
    else:
        seeds = list(map(int, a.seeds.split(',')))
    agg = {}
    for name in ALGOS:
        agg[name] = dict(cases=0, sources=0, cleared=0, time=0.0, dist=0.0, measures=0)
    for seed in seeds:
        res = {}
        for name in ('astra', 'fast'):
            r, count = run_one(seed, a.stress, name)
            res[name] = (r, count)
            g = agg[name]
            g['cases'] += 1; g['sources'] += count; g['cleared'] += r['cleared']
            g['time'] += r['virtual_time_s']; g['dist'] += r['distance_m']
            g['measures'] += r['measures']
        ra, ca = res['astra']; rf, cf = res['fast']
        print('seed %-3d  astra %6.1f s/源 (%2d/%2d) | fast %6.1f s/源 (%2d/%2d)'
              % (seed, ra['average_time_s'], ra['cleared'], ca,
                 rf['average_time_s'], rf['cleared'], cf))
    print('\n=== 汇总 (%d 局, %s) ===' % (len(seeds), a.stress))
    for name in ('astra', 'fast'):
        g = agg[name]
        print('%-6s 平均 %.1f s/源  总时间 %.0fs  里程 %.1f km  检测 %d  清除 %d/%d'
              % (name, g['time'] / g['sources'], g['time'], g['dist'] / 1000,
                 g['measures'], g['cleared'], g['sources']))
    print('\n相对 Astra 降低: %.1f%%'
          % (100 * (agg['astra']['time'] - agg['fast']['time']) / agg['astra']['time']))


if __name__ == '__main__':
    main()
