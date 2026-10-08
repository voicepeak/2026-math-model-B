"""方案二（gemini）：正六边形 7 点极小覆盖 + 多信道全息批感知 + 正交基线快速交会。

7 点：原点 + 半径 1200 m 正六边形外圈（覆盖证明给出的最大盲区 968.9 m < 1000 m）。
原点处一次性批扫全部存活信道，按极角排序后依次用“前出 700 m + 侧移 450 m”
的正交第二测点交会清除；随后沿外圈 6 点环形推进。始终保留 19.9 m 认证清除。
"""
import math
from geometry import dist, add, sub, mul, bearing, prior, clip_wedge, enclosing_circle, unit
from robot_client import RobotError
from robot_core import StrategyBase, BudgetStop, ALPHA, CLEAR_SAFE, localize_poly

MAX_TARGETS = 16
R_HEX = 1200.0


def hex_scan_nodes():
    nodes = [(0.0, 0.0)]
    for k in range(6):
        a = math.pi * k / 3.0
        nodes.append((round(R_HEX * math.cos(a), 3), round(R_HEX * math.sin(a), 3)))
    return nodes


class Strategy(StrategyBase):
    def __init__(self, client, mode='q3'):
        super().__init__(client, mode)
        self.base_nodes = hex_scan_nodes()
        self.active = set(range(1, 21))

    def _batch_sense(self, pos):
        found = {}
        chs = sorted(self.active, key=lambda c: (c != self.client.channel, c))
        for ch in chs:
            res = self.action('measure', pos, ch)
            if res['measure_result'] == 'near':
                hit = self.action('clear', pos, ch)
                if hit['clear_result'] != 'success':
                    raise RobotError('near clear failed')
                self.active.discard(ch)
            elif res['measure_result'] == 'direction':
                found[ch] = res['svd_deg']
        return found

    def _orthogonal(self, s1, theta1):
        u = unit(theta1)
        v = (-u[1], u[0])
        b = add(s1, mul(u, 700.0))
        c1 = add(b, mul(v, 450.0))
        c2 = add(b, mul(v, -450.0))
        if dist(c1, (0, 0)) <= 1750:
            return c1
        if dist(c2, (0, 0)) <= 1750:
            return c2
        return c1 if dist(c1, (0, 0)) <= dist(c2, (0, 0)) else c2

    def _engagement(self, ch, s1, theta1):
        poly = prior(s1, theta1, ALPHA)
        pos2 = self._orthogonal(s1, theta1)
        res = self.action('measure', pos2, ch)
        last_s, last_t = pos2, theta1
        if res['measure_result'] == 'near':
            hit = self.action('clear', pos2, ch)
            if hit['clear_result'] != 'success':
                raise RobotError('near clear failed')
            return
        if res['measure_result'] == 'direction':
            poly = clip_wedge(poly, pos2, res['svd_deg'], ALPHA)
            last_t = res['svd_deg']
            if enclosing_circle(poly)[1] <= CLEAR_SAFE:
                c, _ = enclosing_circle(poly)
                out = self.action('clear', c, ch)
                if out['clear_result'] != 'success':
                    raise RobotError('Certified clear failed')
                return
        localize_poly(self, ch, poly, s1, theta1, last_s, last_t)

    def run(self):
        status = 'complete_coverage'
        try:
            visible = self._batch_sense((0.0, 0.0))
            for ch in sorted(visible, key=lambda c: visible[c]):
                if ch in self.cleared:
                    continue
                self._engagement(ch, (0.0, 0.0), visible[ch])
                if len(self.cleared) >= MAX_TARGETS:
                    status = 'complete_upper_bound'
                    return self.summary(status)
            for node in self.base_nodes[1:]:
                if len(self.cleared) >= MAX_TARGETS:
                    break
                vis = self._batch_sense(node)
                for ch in sorted(vis, key=lambda c: vis[c]):
                    if ch in self.cleared:
                        continue
                    self._engagement(ch, node, vis[ch])
                    if len(self.cleared) >= MAX_TARGETS:
                        status = 'complete_upper_bound'
                        return self.summary(status)
        except BudgetStop as exc:
            status = str(exc)
        return self.summary(status)
