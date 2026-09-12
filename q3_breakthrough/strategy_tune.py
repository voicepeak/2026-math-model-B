"""Astra 参数化版本，用于微调。算法逻辑与 strategy.py 完全一致，只把常量提成属性。
覆盖半径 hex_r 必须满足覆盖证书：1121 <= hex_r <= 1997 时圆域最大盲区 <= 1000m。
"""
import math

from geometry import dist, add, mul, unit, bearing, prior, clip_wedge, enclosing_circle
from robot_core import StrategyBase, BudgetStop, ALPHA, CLEAR_SAFE, localize_poly
from robot_client import RobotError

CELL = 100.0


class Coverage:
    def __init__(self):
        self.cells = []
        for i in range(-18, 18):
            for j in range(-18, 18):
                x, y = (i + .5) * CELL, (j + .5) * CELL
                if math.hypot(max(0, abs(x) - CELL / 2), max(0, abs(y) - CELL / 2)) <= 1800:
                    self.cells.append((x, y))
        self.initial = len(self.cells)
        self.scans = []

    @staticmethod
    def covers(p, c):
        return (abs(p[0] - c[0]) + CELL / 2) ** 2 + (abs(p[1] - c[1]) + CELL / 2) ** 2 <= (1000 - 1e-5) ** 2

    def gain(self, p):
        return sum(self.covers(p, c) for c in self.cells)

    def update(self, p):
        self.cells = [c for c in self.cells if not self.covers(p, c)]
        self.scans.append(p)

    def next_point(self, pos):
        candidates = list(self.cells[::4])
        candidates += [mul(unit(a), r) for r in (1150, 1350) for a in range(0, 360, 30)]
        return max(candidates, key=lambda p: self.gain(p) / (dist(pos, p) + 400)) if candidates else None


class Strategy(StrategyBase):
    def __init__(self, client, mode='q3', *, shared=True, adaptive=False, routing=True,
                 hex_r=1200.0, short_fwd=300.0, short_lat=75.0,
                 vp_off_min=25.0, vp_off_max=160.0, vp_off_frac=0.25,
                 share_dist=1150.0, share_base=60.0, share_ang=0.12, share_near=150.0,
                 twopt_passes=8, reuse_dist=60.0, reuse_ang=0.15):
        if mode != 'q3':
            raise ValueError('This coverage certificate is valid only for q3')
        super().__init__(client, mode)
        self.unknown = set(range(1, 21))
        self.tracks = {}
        self.coverage = Coverage()
        self.shared = shared
        self.adaptive = adaptive
        self.routing = routing
        self.shared_count = 0
        self.certificates = []
        self._cache = {}
        self.fixed_nodes = [mul(unit(a), hex_r) for a in range(0, 360, 60)]
        self.visited_fixed = 0
        self.short_fwd = short_fwd
        self.short_lat = short_lat
        self.vp_off_min = vp_off_min
        self.vp_off_max = vp_off_max
        self.vp_off_frac = vp_off_frac
        self.share_dist = share_dist
        self.share_base = share_base
        self.share_ang = share_ang
        self.share_near = share_near
        self.twopt_passes = twopt_passes
        self.reuse_dist = reuse_dist
        self.reuse_ang = reuse_ang

    def next_job(self):
        jobs = [('target', ch, enclosing_circle(tr['poly'])[0]) for ch, tr in self.tracks.items()]
        jobs += [('scan', i, p) for i, p in enumerate(self.fixed_nodes)]
        if not jobs:
            return None
        start = tuple(self.client.position)
        remaining = list(range(len(jobs)))
        route = []
        pos = start
        while remaining:
            k = min(remaining, key=lambda i: dist(pos, jobs[i][2]))
            remaining.remove(k); route.append(k); pos = jobs[k][2]
        for _ in range(self.twopt_passes):
            improved = False
            for i in range(len(route) - 1):
                before = start if i == 0 else jobs[route[i - 1]][2]
                a = jobs[route[i]][2]
                for j in range(i + 1, len(route)):
                    b = jobs[route[j]][2]
                    after = jobs[route[j + 1]][2] if j + 1 < len(route) else None
                    old = dist(before, a) + (dist(b, after) if after else 0)
                    new = dist(before, b) + (dist(a, after) if after else 0)
                    if new < old - 1e-6:
                        route[i:j + 1] = reversed(route[i:j + 1]); improved = True
                        break
                if improved:
                    break
            if not improved:
                break
        return jobs[route[0]]

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
            self.unknown.discard(ch)
            self.tracks.pop(ch, None)
        elif kind == 'direction':
            t = res['svd_deg']
            self.unknown.discard(ch)
            if ch not in self.tracks:
                self.tracks[ch] = dict(poly=prior(p, t, ALPHA), s0=p, t0=t,
                                       last=p, theta=t, observations=1)
            else:
                tr = self.tracks[ch]
                tr['poly'] = clip_wedge(tr['poly'], p, t, ALPHA)
                tr.update(last=p, theta=t, observations=tr['observations'] + 1)
            if not self.tracks[ch]['poly']:
                raise RobotError('Inconsistent bearing polygon')
        return res

    def scan(self, p):
        for ch in sorted(self.unknown, key=lambda c: (c != self.client.channel, c)):
            self.observe(p, ch)
        self.coverage.update(p)

    def share(self, p, exclude=None):
        if not self.shared:
            return
        for ch in sorted(list(self.tracks), key=lambda c: (c != self.client.channel, c)):
            if ch == exclude or ch in self.cleared:
                continue
            tr = self.tracks[ch]
            c, r = enclosing_circle(tr['poly'])
            baseline = dist(p, tr['last'])
            angle = abs(math.sin(math.radians(bearing(p, c) - bearing(tr['last'], c))))
            if r > CLEAR_SAFE and dist(p, c) <= self.share_dist and baseline >= self.share_base \
                    and (angle > self.share_ang or dist(p, c) < self.share_near):
                self.observe(p, ch)
                self.shared_count += 1

    def stop_tasks(self, exclude=None):
        p = tuple(self.client.position)
        self.share(p, exclude)
        if self.adaptive and self.unknown and self.coverage.gain(p) >= 60:
            self.scan(p)

    def viewpoint(self, tr):
        c, r = enclosing_circle(tr['poly'])
        v = unit(tr['theta'] + 90)
        offset = max(self.vp_off_min, min(self.vp_off_max, self.vp_off_frac * r))
        candidates = [add(c, mul(v, offset)), add(c, mul(v, -offset))]
        pos = tuple(self.client.position)
        if dist(pos, tr['last']) > self.reuse_dist:
            a = abs(math.sin(math.radians(bearing(pos, c) - bearing(tr['last'], c))))
            if a > self.reuse_ang and dist(pos, c) < 1000:
                return pos
        if tr['observations'] == 1:
            forward = add(tr['last'], mul(unit(tr['theta']), self.short_fwd))
            candidates = [add(forward, mul(v, self.short_lat)), add(forward, mul(v, -self.short_lat))]
        return min(candidates, key=lambda p: dist(pos, p))

    def engage(self, ch):
        for _ in range(8):
            if ch in self.cleared:
                return
            tr = self.tracks[ch]
            c, r = enclosing_circle(tr['poly'])
            if r <= CLEAR_SAFE:
                self.certificates.append(dict(channel=ch, center=c, radius=r,
                                              vertices=tr['poly'], time=self.client.virtual_time))
                if self.action('clear', c, ch)['clear_result'] != 'success':
                    raise RobotError('Certified clear failed')
                self.tracks.pop(ch, None)
                self.stop_tasks()
                return
            p = self.viewpoint(tr)
            result = self.observe(p, ch)
            self.stop_tasks(exclude=ch)
            if result['measure_result'] == 'no_signal':
                break
        if ch not in self.cleared:
            tr = self.tracks[ch]
            localize_poly(self, ch, tr['poly'], tr['s0'], tr['t0'], tr['last'], tr['theta'])
            self.tracks.pop(ch, None)
            self.stop_tasks()

    def run(self):
        status = 'complete_coverage'
        try:
            self.scan((0., 0.))
            while True:
                if len(self.cleared) >= 16:
                    status = 'complete_upper_bound'
                    break
                self.tracks = {ch: tr for ch, tr in self.tracks.items() if ch not in self.cleared}
                if self.routing and not self.adaptive and (self.tracks or self.fixed_nodes):
                    kind, index, p = self.next_job()
                    if kind == 'target':
                        self.engage(index)
                    else:
                        self.scan(self.fixed_nodes.pop(index))
                        self.visited_fixed += 1
                        self.share(tuple(self.client.position))
                elif self.tracks:
                    p = tuple(self.client.position)
                    ch = min(self.tracks, key=lambda c: dist(p, enclosing_circle(self.tracks[c]['poly'])[0]))
                    self.engage(ch)
                elif self.adaptive and self.coverage.cells and self.unknown:
                    self.scan(self.coverage.next_point(self.client.position))
                    self.share(tuple(self.client.position))
                elif not self.adaptive and self.fixed_nodes:
                    self.scan(self.fixed_nodes.pop(0))
                    self.visited_fixed += 1
                    self.share(tuple(self.client.position))
                else:
                    break
        except BudgetStop as exc:
            status = str(exc)
        return self.summary(status)

    def summary(self, status):
        out = super().summary(status)
        out.update(algorithm='astra_tuned', shared_measures=self.shared_count,
                   full_scan_count=len(self.coverage.scans),
                   uncovered_cells=len(self.coverage.cells), pending_tracks=len(self.tracks),
                   coverage_cell_m=CELL, fixed_nodes_visited=self.visited_fixed,
                   coverage_certificate='hexagon_analytic' if self.visited_fixed == 6 else 'not_yet_complete')
        return out
