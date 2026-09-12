"""对比 Astra vs 环形路由版。用法 python bench_cmp.py --seeds 1:20"""
import argparse
import random
import time

from benchmark import Fixture, PublicClient
from strategy import Strategy as Astra
from strategy_ring import Strategy as Ring
from strategy_hybrid import Strategy as Hybrid
from geometry import dist

ALGOS = (('astra', Astra), ('ring', Ring), ('hybrid', Hybrid))


def run_one(seed, stress, cls):
    count = 10 + random.Random(seed + 891).randrange(7)
    fx = Fixture(seed, count, stress)
    cl = PublicClient(fx)
    st = cls(cl)
    r = st.run()
    pos = (0.0, 0.0)
    L = 0.0
    for row in st.trace:
        q = (row['x'], row['y']); L += dist(pos, q); pos = q
    r['distance_m'] = L
    return r, count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', default='1:20')
    ap.add_argument('--stress', default='random')
    a = ap.parse_args()
    seeds = list(range(*[int(x) for x in a.seeds.split(':')])) if ':' in a.seeds \
        else list(map(int, a.seeds.split(',')))
    agg = {n: dict(src=0, cleared=0, t=0.0, d=0.0, m=0) for n, _ in ALGOS}
    for seed in seeds:
        line = 'seed %-3d ' % seed
        for name, cls in ALGOS:
            r, count = run_one(seed, a.stress, cls)
            g = agg[name]
            g['src'] += count; g['cleared'] += r['cleared']; g['t'] += r['virtual_time_s']
            g['d'] += r['distance_m']; g['m'] += r['measures']
            line += '| %-5s %6.1f (%2d/%2d) ' % (name, r['average_time_s'], r['cleared'], count)
        print(line)
    print('\n=== 汇总 %d 局 ===' % len(seeds))
    for name, _ in ALGOS:
        g = agg[name]
        print('%-6s 平均 %.1f s/源  总时间 %.0fs  里程 %.1f km  检测 %d  清除 %d/%d'
              % (name, g['t'] / g['src'], g['t'], g['d'] / 1000, g['m'], g['cleared'], g['src']))
    ta, tr = agg['astra']['t'], agg['ring']['t']
    print('ring 相对 astra 降低 %.1f%%' % (100 * (ta - tr) / ta))


if __name__ == '__main__':
    main()
