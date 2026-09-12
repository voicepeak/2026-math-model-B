"""Hybrid: 目标停靠点顺手扫覆盖 + 缺口才回覆盖节点。

相对 Astra：
  - 每个频道用 100m 网格记账“已被 1000m 扫描圆排除的格子”。
  - 目标路线上每次停靠，若某未发现频道在此能新排除足够多格子，就顺手测一次（免费覆盖）。
  - 目标清完后，只对仍有未排除格的频道，去“还没扫过的六边形节点”补扫；全部覆盖即判无源。
  - 若某频道剩余格无法被任何未扫节点覆盖，则安全兜底：把该频道在全部 6 节点各扫一次。
保留 19.9m 认证清除、near 立即清除、条带回退。
"""
import math

from geometry import dist, add, sub, mul, unit, bearing, prior, clip_wedge, enclosing_circle
from robot_core import StrategyBase, BudgetStop, ALPHA, CLEAR_SAFE, localize_poly
from robot_client import RobotError

CELL = 100.0
HALFDIAG = (CELL / 2) * math.sqrt(2)
COVER_R = 1000.0 - 1e-6
FIXED_NODES = [mul(unit(a), 1200.0) for a in range(0, 360, 60)]


def _cells():
    out = []
    n = int(1800 // CELL) + 2
    for i in range(-n, n):
        for j in range(-n, n):
            x, y = (i + .5) * CELL, (j + .5) * CELL
            if math.hypot(max(0, abs(x) - CELL / 2), max(0, abs(y) - CELL / 2)) <= 1800:
                out.append((x, y))
    return out


class Strategy(StrategyBase):
    def __init__(self, client, mode='q3', gain_thresh=60):
        if mode != 'q3':
            raise ValueError('hybrid is q3 only')
        super().__init__(client, mode)
        self.unknown = set(range(1, 21))
        self.tracks = {}
        self.cells = _cells()
        self.remaining = {ch: set(range(len(self.cells))) for ch in range(1, 21)}
        self.scanned_node = {ch: set() for ch in range(1, 21)}
        self._cache = {}
        self.gain_thresh = gain_thresh
        self.shared_count = 0

    # ---------- coverage ----------
    def _hits(self, p):
        px, py = p
        return [i for i, (cx, cy) in enumerate(self.cells)
                if math.hypot(px - cx, py - cy) + HALFDIAG <= COVER_R]

    def _gain(self, ch, p):
        rem = self.remaining.get(ch)
        if not rem:
            return 0
        px, py = p
        return sum(1 for i in rem
                   if math.hypot(px - self.cells[i][0], py - self.cells[i][1]) + HALFDIAG <= COVER_R)

    # ---------- action ----------
    def observe(self, p, ch):
        key = (ch, round(p[0], 6), round(p[1], 6))
        if key in self._cache:
            return self._cache[key]
        res = self.action('measure', p, ch)
        self._cache[key] = res
        kind = res['measure_result']
        if kind == 'near':
            hit = self.action('clear', p, ch)
            if hit['clear_result'] != 'success':
                raise RobotError('near clear failed')
            self.unknown.discard(ch); self.remaining.pop(ch, None); self.tracks.pop(ch, None)
        elif kind == 'direction':
            t = res['svd_deg']
            self.unknown.discard(ch); self.remaining.pop(ch, None)
            if ch not in self.tracks:
                poly = prior(p, t, ALPHA)
                self.tracks[ch] = dict(poly=poly, s0=p, t0=t, last=p, theta=t,
                                       observations=1, center=enclosing_circle(poly)[0])
            else:
                tr = self.tracks[ch]
                tr['poly'] = clip_wedge(tr['poly'], p, t, ALPHA)
                tr.update(last=p, theta=t, observations=tr['observations'] + 1)
                tr['center'] = enclosing_circle(tr['poly'])[0]
        else:
            rem = self.remaining.get(ch)
            if rem:
                rem.difference_update(self._hits(p))
        return res

    def scan_opportunistic(self, p):
        chs = [c for c in self.unknown if self._gain(c, p) >= self.gain_thresh]
        chs.sort(key=lambda c: (c != self.client.channel, -self._gain(c, p), c))
        for ch in chs:
            if ch in self.unknown:
                self.observe(p, ch)

    # ---------- localization ----------
    def viewpoint(self, tr):
        c, r = enclosing_circle(tr['poly'])
        v = unit(tr['theta'] + 90)
        offset = max(25, min(160, .25 * r))
        candidates = [add(c, mul(v, offset)), add(c, mul(v, -offset))]
        pos = tuple(self.client.position)
        if dist(pos, tr['last']) > 60:
            a = abs(math.sin(math.radians(bearing(pos, c) - bearing(tr['last'], c))))
            if a > .15 and dist(pos, c) < 1000:
                return pos
        if tr['observations'] == 1:
            forward = add(tr['last'], mul(unit(tr['theta']), 300))
            candidates = [add(forward, mul(v, 75)), add(forward, mul(v, -75))]
        return min(candidates, key=lambda q: dist(pos, q))

    def engage(self, ch):
        for _ in range(8):
            if ch in self.cleared:
                return
            tr = self.tracks[ch]
            c, r = enclosing_circle(tr['poly'])
            if r <= CLEAR_SAFE:
                if self.action('clear', c, ch)['clear_result'] != 'success':
                    raise RobotError('Certified clear failed')
                self.tracks.pop(ch, None)
                self.scan_opportunistic(tuple(self.client.position))
                return
            p = self.viewpoint(tr)
            self.observe(p, ch)
            self.scan_opportunistic(tuple(self.client.position))
        if ch not in self.cleared:
            tr = self.tracks.pop(ch, None)
            if tr is None:
                return
            localize_poly(self, ch, tr['poly'], tr['s0'], tr['t0'], tr['last'], tr['theta'])

    # ---------- coverage tail ----------
    def _needed_nodes(self):
        plan = {}
        for ch in self.unknown:
            rem = self.remaining.get(ch)
            if not rem:
                continue
            for idx, node in enumerate(FIXED_NODES):
                if idx in self.scanned_node.get(ch, ()):
                    continue
                if self._gain(ch, node) > 0:
                    plan.setdefault(idx, set()).add(ch)
        return plan

    def _force_nodes(self):
        todo = {ch: [i for i in range(len(FIXED_NODES)) if i not in self.scanned_node[ch]]
                for ch in self.unknown if self.remaining.get(ch)}
        return {ch: v for ch, v in todo.items() if v}

    def tail(self):
        while True:
            plan = self._needed_nodes()
            if not plan:
                todo = self._force_nodes()
                if not todo:
                    return
                pos = tuple(self.client.position)
                idx = min({i for v in todo.values() for i in v},
                          key=lambda i: dist(pos, FIXED_NODES[i]))
                node = FIXED_NODES[idx]
                chs = [ch for ch, v in todo.items() if idx in v]
            else:
                pos = tuple(self.client.position)
                idx = min(plan, key=lambda i: dist(pos, FIXED_NODES[i]))
                node = FIXED_NODES[idx]
                chs = sorted(plan[idx], key=lambda c: (c != self.client.channel, c))
            for ch in chs:
                self.observe(node, ch)
                self.scanned_node[ch].add(idx)

    def run(self):
        status = 'complete_coverage'
        try:
            self.scan_opportunistic((0.0, 0.0))
            while True:
                if len(self.cleared) >= 16:
                    status = 'complete_upper_bound'
                    break
                for ch in list(self.tracks):
                    if ch in self.cleared:
                        self.tracks.pop(ch)
                if self.tracks:
                    pos = tuple(self.client.position)
                    ch = min(self.tracks, key=lambda c: dist(pos, self.tracks[c]['center']))
                    self.engage(ch)
                elif self.unknown:
                    before = sum(len(self.remaining.get(c, ())) for c in self.unknown)
                    self.tail()
                    after = sum(len(self.remaining.get(c, ())) for c in self.unknown)
                    if after == before:
                        break
                else:
                    break
        except BudgetStop as exc:
            status = str(exc)
        return self.summary(status)

    def summary(self, status):
        out = super().summary(status)
        out.update(algorithm='hybrid', shared_measures=self.shared_count,
                   unknown_left=len(self.unknown),
                   absent=sum(1 for ch in self.unknown if not self.remaining.get(ch)))
        return out
