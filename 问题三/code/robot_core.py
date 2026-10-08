"""Shared low-level action layer and certified wedge-localization core.

All four experimental strategies keep the proven "wedge intersection + minimum
enclosing circle <= 19.9 m certified clear" kernel from the original solver.
Only the outer search / scheduling logic differs between the variants.
"""
import math
from geometry import (dist, unit, add, sub, mul, dot, bearing, prior, clip_wedge,
                      diameter_info, enclosing_circle, local_to_global, guaranteed)
from robot_client import RobotError

ALPHA = 1.005
CLEAR_SAFE = 19.9
VIRTUAL_BUDGET = 359000.0
REAL_MIN = 30.0


class BudgetStop(Exception):
    pass


def fallback_points(s, theta):
    w = 1500 * math.sin(math.radians(ALPHA))
    xs = list(range(0, 1500, 28)) + [1500]
    return [local_to_global(s, theta, (x, y))
            for y, xx in [(-w / 2, xs), (w / 2, list(reversed(xs)))] for x in xx]


def _thin(poly, cap=10):
    if len(poly) <= cap:
        return list(poly)
    step = max(1, len(poly) // cap)
    return list(poly[::step])


def default_viewpoint(poly, s0, theta0, last, last_theta):
    """Original heuristic: lateral offset off the MEC centre."""
    c, r = enclosing_circle(poly)
    d = diameter_info(poly)['diameter']
    u = unit(last_theta)
    v = (-u[1], u[0])
    offset = max(40, min(300, 0.2 * d))
    candidates = [add(c, mul(v, offset)), add(c, mul(v, -offset))]
    u0 = unit(theta0)
    v0 = (-u0[1], u0[0])
    candidates.sort(key=lambda p: (not guaranteed((dot(sub(p, s0), u0), dot(sub(p, s0), v0)), ALPHA),
                                  dist(last, p), p))
    return candidates[0]


def localize_poly(strategy, ch, poly, s0, theta0, last, last_theta, viewpoint=None):
    """Iteratively shrink `poly` with further bearings, then certified-clear.

    viewpoint(poly, s0, theta0, last, last_theta) -> next measurement point.
    """
    for _ in range(4):
        if not poly:
            raise RobotError('Inconsistent bearing polygon')
        c, r = enclosing_circle(poly)
        if r <= CLEAR_SAFE:
            out = strategy.action('clear', c, ch)
            if out['clear_result'] != 'success':
                raise RobotError('Certified clear failed')
            return
        if viewpoint is None:
            p = default_viewpoint(poly, s0, theta0, last, last_theta)
        else:
            p = viewpoint(poly, s0, theta0, last, last_theta)
        res = strategy.action('measure', p, ch)
        if res['measure_result'] == 'near':
            hit = strategy.action('clear', p, ch)
            if hit['clear_result'] != 'success':
                raise RobotError('near clear failed')
            return
        if res['measure_result'] == 'no_signal':
            break
        poly = clip_wedge(poly, p, res['svd_deg'], ALPHA)
        last, last_theta = p, res['svd_deg']
    strategy.fallback_count += 1
    for p in fallback_points(s0, theta0):
        if strategy.action('clear', p, ch)['clear_result'] == 'success':
            return
    raise RobotError('Complete strip sweep failed: model/interface inconsistent')


def localize(strategy, ch, s, res, viewpoint=None):
    """Entry point used by a single fresh observation."""
    if res['measure_result'] == 'near':
        out = strategy.action('clear', s, ch)
        if out['clear_result'] != 'success':
            raise RobotError('near then clear failed')
        return
    theta = res['svd_deg']
    poly = prior(s, theta, ALPHA)
    localize_poly(strategy, ch, poly, s, theta, s, theta, viewpoint=viewpoint)


class StrategyBase:
    """Action wrapper + certified bearer of counters/logging (mirrors the original)."""

    def __init__(self, client, mode='q3'):
        if mode not in ('q3', 'q4'):
            raise ValueError('mode must be q3/q4')
        self.client = client
        self.mode = mode
        self.cleared = set()
        self.measure_count = 0
        self.clear_count = 0
        self.trace = []
        self.fallback_count = 0

    def action(self, kind, p, ch):
        left = self.client.time_left()
        if left is not None and left < REAL_MIN:
            raise BudgetStop('real_time_budget')
        if self.client.virtual_time + dist(self.client.position, p) / 5 + 6 > VIRTUAL_BUDGET:
            raise BudgetStop('virtual_time_budget')
        status, res = getattr(self.client, kind)(p[0], p[1], ch)
        if status != 200 or not isinstance(res, dict) or res.get('accepted') is not True:
            raise RobotError('Rejected action: %s %s' % (status, res))
        key = 'measure_result' if kind == 'measure' else 'clear_result'
        allowed = ('direction', 'near', 'no_signal') if kind == 'measure' else ('success', 'no_target_in_range')
        if res.get(key) not in allowed:
            raise RobotError('Invalid result code: ' + repr(res))
        if kind == 'measure' and res[key] == 'direction':
            angle = res.get('svd_deg')
            if isinstance(angle, bool) or not isinstance(angle, (int, float)) \
                    or not math.isfinite(angle) or not 0 <= angle < 360:
                raise RobotError('Invalid bearing: ' + repr(res))
        self.trace.append(dict(kind=kind, x=p[0], y=p[1], channel=ch, response=res,
                               virtual_time_s=self.client.virtual_time))
        if kind == 'measure':
            self.measure_count += 1
        else:
            self.clear_count += 1
            if res.get('clear_result') == 'success':
                self.cleared.add(ch)
        return res

    def summary(self, status):
        n = len(self.cleared)
        return dict(mode=self.mode, status=status, cleared=n, channels=sorted(self.cleared),
                    virtual_time_s=self.client.virtual_time,
                    average_time_s=self.client.virtual_time / n if n else None,
                    measures=self.measure_count, clear_attempts=self.clear_count,
                    fallback_count=self.fallback_count, official_validated=False)
