"""算理论下限：从原点出发访问所有真实源的最短开放路径 (NN + 2-opt)。"""
import random
from benchmark import Fixture
from geometry import dist


def path_len(pts):
    return sum(dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def two_opt(pts):
    best = list(pts)
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                a, b = best[i - 1], best[i]
                c, d = best[j], best[(j + 1)] if j + 1 < len(best) else None
                old = dist(a, b) + (dist(c, d) if d else 0)
                new = dist(a, c) + (dist(b, d) if d else 0)
                if new < old - 1e-9:
                    best[i:j + 1] = reversed(best[i:j + 1])
                    improved = True
    return best


def nn(start, pts):
    rem = list(pts)
    route = [start]
    while rem:
        k = min(range(len(rem)), key=lambda i: dist(route[-1], rem[i]))
        route.append(rem.pop(k))
    return route


tot_src = 0
tot_tsp = 0.0
all_n = 0
for seed in range(1, 21):
    count = 10 + random.Random(seed + 891).randrange(7)
    fx = Fixture(seed, count, 'random')
    pts = [(s['x'], s['y']) for s in fx.sources]
    route = two_opt(nn((0.0, 0.0), pts))
    L = path_len(route)
    tot_src += count
    tot_tsp += L
    all_n += 1
    print('seed %-3d n=%2d  最短路径 %7.0f m  = %6.1f m/源 = %6.1f s/源(仅移动)'
          % (seed, count, L, L / count, L / count / 5))
print('\n20 局合计: %d 源, 平均 %.1f m/源 = %.1f s/源(纯移动下限)'
      % (tot_src, tot_tsp / tot_src, tot_tsp / tot_src / 5))
print('再 + 每源约 2 次定位检测(10s) + 1 次清除(5s) + 少量切频 ≈ %.1f s/源 理论下限'
      % (tot_tsp / tot_src / 5 + 10 + 5 + 4))
