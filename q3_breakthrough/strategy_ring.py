"""在 Astra 基础上只改路线：把『目标 + 6 个覆盖点』按极角环形排序，
并与原 NN+2opt 路线取更短者，减少对穿折返。覆盖与定位机制完全不变。
"""
import math

from geometry import dist, enclosing_circle
from strategy import Strategy as Astra


def _path_len(pts):
    return sum(dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


class Strategy(Astra):
    def _two_opt(self, jobs, route, start):
        route = list(route)
        for _ in range(30):
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
                        route[i:j + 1] = reversed(route[i:j + 1])
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                break
        return route

    def _nn_route(self, jobs, start):
        remaining = list(range(len(jobs)))
        route = []
        pos = start
        while remaining:
            k = min(remaining, key=lambda i: dist(pos, jobs[i][2]))
            remaining.remove(k)
            route.append(k)
            pos = jobs[k][2]
        return route

    def _angular_route(self, jobs, start):
        sa = math.atan2(start[1], start[0])
        angles = [math.atan2(j[2][1], j[2][0]) for j in jobs]
        ids = list(range(len(jobs)))
        cw = sorted(ids, key=lambda i: (angles[i] - sa) % (2 * math.pi))
        ccw = sorted(ids, key=lambda i: (sa - angles[i]) % (2 * math.pi))
        return cw if _path_len([start] + [jobs[i][2] for i in cw]) <= \
            _path_len([start] + [jobs[i][2] for i in ccw]) else ccw

    def next_job(self):
        jobs = [('target', ch, enclosing_circle(tr['poly'])[0]) for ch, tr in self.tracks.items()]
        jobs += [('scan', i, p) for i, p in enumerate(self.fixed_nodes)]
        if not jobs:
            return None
        start = tuple(self.client.position)
        cands = [self._angular_route(jobs, start), self._nn_route(jobs, start)]
        best = min(cands, key=lambda rt: _path_len([start] + [jobs[i][2] for i in rt]))
        best = self._two_opt(jobs, best, start)
        return jobs[best[0]]
