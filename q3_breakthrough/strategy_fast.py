"""Q3 加速版：把覆盖扫描折进清目标路线（懒覆盖），减少专门跑覆盖节点的移动。

相对 Astra(q3_breakthrough/strategy.py) 的变化：
  1. 每个频道的覆盖用 100 m 网格逐格记账；扫描一次的 1000 m 圆内格子标记为已排除。
  2. 只有在目标路线停靠点还“有新格可排除”时，才顺手扫该未发现频道（懒覆盖）。
  3. 目标清空后，仅对仍有未排除格的频道，按增益/代价选补扫点；全部覆盖即可判无源。
  4. 保留 19.9 m 认证清除、near 立即清除、条带回退。
"""
import math
from geometry import dist, add, sub, mul, unit, bearing, prior, clip_wedge, enclosing_circle
from robot_core import StrategyBase, BudgetStop, ALPHA, CLEAR_SAFE, localize_poly
from robot_client import RobotError

CELL = 100.0
HALFDIAG = (CELL / 2) * math.sqrt(2)
COVER_R = 1000.0 - 1e-6
GAIN_THRESH = 40


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
    def __init__(self, client, mode='q3'):
        if mode != 'q3':
            raise ValueError('fast coverage certificate is q3 only')
        super().__init__(client, mode)
        self.unknown = set(range(1, 21))
        self.tracks = {}
        self.cells = _cells()
        self.remaining = {ch: set(range(len(self.cells))) for ch in range(1, 21)}
        self._cache = {}
        self.shared_count = 0

    # ---------- coverage bookkeeping ----------
    def _hits(self, p):
        px, py = p
        return [i for i, (cx, cy) in enumerate(self.cells)
                if math.hypot(px - cx, py - cy) + HALFDIAG <= COVER_R]

    def _gain(self, ch, p):
        px, py = p
        rem = self.remaining.get(ch)
        if not rem:
            return 0
        return sum(1 for i in rem if math.hypot(px - self.cells[i][0], py - self.cells[i][1]) + HALFDIAG <= COVER_R)

    # ---------- actions ----------
    def observe(self, p, ch):
        key = (ch, round(p[0], 6), round(p[1], 6))
        if key in self._cache:
            return self._cache[key]
        res = self.action('measure', p, ch)
        self._cache[key] = res
        kind = res['measure_result']
        self.shared_count += 1
        if kind == 'near':
            hit = self.action('clear', p, ch)
            if hit['clear_result'] != 'success':
                raise RobotError('near clear failed')
            self.unknown.discard(ch)
            self.remaining.pop(ch, None)
            self.tracks.pop(ch, None)
        elif kind == 'direction':
            t = res['svd_deg']
            self.unknown.discard(ch)
            self.remaining.pop(ch, None)
            if ch not in self.tracks:
                self.tracks[ch] = dict(poly=prior(p, t, ALPHA), s0=p, t0=t, last=p, theta=t,
                                       observations=1, center=enclosing_circle(prior(p, t, ALPHA))[0])
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

    def scan_unknown(self, p):
        chs = [c for c in self.unknown if self._gain(c, p) >= GAIN_THRESH]
        chs.sort(key=lambda c: (c != self.client.channel, -self._gain(c, p), c))
        for ch in chs:
            if ch not in self.unknown:
                continue
            self.observe(p, ch)

    # ---------- localization / clearing ----------
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
                self.scan_unknown(tuple(self.client.position))
                return
            p = self.viewpoint(tr)
            self.observe(p, ch)
            self.scan_unknown(tuple(self.client.position))
        if ch not in self.cleared:
            tr = self.tracks.pop(ch, None)
            if tr is None:
                return
            localize_poly(self, ch, tr['poly'], tr['s0'], tr['t0'], tr['last'], tr['theta'])

    # ---------- coverage-only tail ----------
    def coverage_target(self):
        # candidate points: subsampled remaining cell centres + hex nodes
        cand = []
        for ch in self.unknown:
            rem = self.remaining.get(ch)
            if rem:
                cand.extend(self.cells[i] for i in list(rem)[::7])
        cand.extend(mul(unit(a), 1200) for a in range(0, 360, 60))
        if not cand:
            return None
        pos = tuple(self.client.position)
        best, bp = 0, None
        for p in cand:
            g = sum(self._gain(ch, p) for ch in self.unknown)
            if g <= 0:
                continue
            score = g / (dist(pos, p) + 400)
            if score > best:
                best, bp = score, p
        return bp

    def run(self):
        status = 'complete_coverage'
        try:
            self.scan_unknown((0.0, 0.0))
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
                    p = self.coverage_target()
                    if p is None:
                        break
                    need = [c for c in self.unknown if self._gain(c, p) > 0]
                    if not need:
                        break
                    anchor = max(need, key=lambda c: (c != self.client.channel, self._gain(c, p)))
                    self.observe(p, anchor)
                    self.scan_unknown(p)
                else:
                    break
        except BudgetStop as exc:
            status = str(exc)
        return self.summary(status)

    def summary(self, status):
        out = super().summary(status)
        absent = sum(1 for ch in range(1, 21)
                     if ch in self.unknown and not self.remaining.get(ch))
        out.update(algorithm='fast_lazy_coverage', shared_measures=self.shared_count,
                   absent_proven=absent, unknown_left=len(self.unknown))
        return out

