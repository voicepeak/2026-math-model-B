"""从官方演练 client.jsonl 反推清除点坐标，估源位置，算半径分布与 TSP 下限。"""
import glob
import json
import math
import os

BASE = r"C:\Users\张靖浩\Desktop\2026数学建模\2026-math-model-B\q3_五次演练汇总"


def path_len(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def nn2opt(start, pts):
    rem = list(pts)
    route = [start]
    while rem:
        k = min(range(len(rem)), key=lambda i: math.hypot(route[-1][0] - rem[i][0], route[-1][1] - rem[i][1]))
        route.append(rem.pop(k))
    improved = True
    while improved:
        improved = False
        for i in range(1, len(route) - 1):
            for j in range(i + 1, len(route)):
                a, b = route[i - 1], route[i]
                d = route[j + 1] if j + 1 < len(route) else None
                c = route[j]
                old = math.hypot(a[0]-b[0], a[1]-b[1]) + (math.hypot(c[0]-d[0], c[1]-d[1]) if d else 0)
                new = math.hypot(a[0]-c[0], a[1]-c[1]) + (math.hypot(b[0]-d[0], b[1]-d[1]) if d else 0)
                if new < old - 1e-9:
                    route[i:j+1] = reversed(route[i:j+1]); improved = True
    return route


tot_n = 0
tot_tsp = 0.0
all_r = []
print('%-28s %5s %5s  %s' % ('case', 'n', '清点', '半径 min/mean/max (m)    TSP m/源 (移动s/源)'))
for d in sorted(os.listdir(BASE)):
    full = os.path.join(BASE, d)
    if not os.path.isdir(full):
        continue
    sub = [x for x in os.listdir(full) if os.path.isdir(os.path.join(full, x))]
    if not sub:
        continue
    cj = os.path.join(full, sub[0], 'client.jsonl')
    res = [x for x in os.listdir(full) if x.endswith('.result.json')]
    jam = None
    if res:
        jam = json.load(open(os.path.join(full, res[0]), encoding='utf-8')).get('jammer_count')
    pts = []
    seen = set()
    for line in open(cj, encoding='utf-8'):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get('event') != 'http' or e.get('path') != '/clear':
            continue
        rsp = e.get('response') or {}
        if rsp.get('clear_result') != 'success':
            continue
        req = e.get('request') or {}
        pos = req.get('position') or {}
        ch = req.get('channel')
        x, y = pos.get('x'), pos.get('y')
        if x is None:
            continue
        key = (ch, round(x, 3), round(y, 3))
        if key in seen:
            continue
        seen.add(key)
        pts.append((x, y))
        all_r.append(math.hypot(x, y))
    if not pts:
        continue
    route = nn2opt((0.0, 0.0), pts)
    L = path_len(route)
    n = len(pts)
    rr = [math.hypot(x, y) for x, y in pts]
    tot_n += n
    tot_tsp += L
    print('%-28s %5s %5d  %6.0f/%.0f/%.0f   %6.0f (%.1f)'
          % (d[:28], jam, n, min(rr), sum(rr) / n, max(rr), L / n, L / n / 5))
print('\n合计 %d 个源' % tot_n)
print('官方反推半径: mean %.0f m (均匀分布理论 mean=1200 m), 范围 %.0f~%.0f'
      % (sum(all_r) / len(all_r), min(all_r), max(all_r)))
print('官方 TSP 移动下限: %.1f m/源 = %.1f s/源' % (tot_tsp / tot_n, tot_tsp / tot_n / 5))
print('再加每源 检测~40s + 清除5s + 切频~8s  => 下限约 %.0f s/源'
      % (tot_tsp / tot_n / 5 + 40 + 5 + 8))
