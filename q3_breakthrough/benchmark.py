"""Paired synthetic comparison, fixed spatial errors independent of action order.
No official case reconstruction; no live simulator calls.
"""
import argparse, csv, hashlib, json, math, random, time
from pathlib import Path
from offline_sim import OfflineClient
from geometry import dist
from strategy import Strategy
from baseline_gemini import Strategy as Gemini
from baseline_original import Strategy as Original
HERE = Path(__file__).resolve().parent

class Fixture(OfflineClient):
    def __init__(self, seed, count, stress='random'):
        super().__init__('q3', seed, count)
        self.seed = seed
        self.stress = stress
        if stress == 'edge':
            for i, s in enumerate(self.sources):
                t = 2*math.pi*(i+.5)/count + seed*.173
                s.update(x=1799.9*math.cos(t), y=1799.9*math.sin(t), radius=1000.)
        elif stress == 'cluster':
            for i, s in enumerate(self.sources):
                t = seed*.371 + i*.013; r = 1300 + 25*(i%5)
                s.update(x=r*math.cos(t), y=r*math.sin(t), radius=1000.)
        elif stress == 'minrange':
            for s in self.sources: s['radius'] = 1000.
        self.initial = [dict(s) for s in self.sources]

    def measure(self, x, y, c):
        key = (c, round(x, 6), round(y, 6))
        h = hashlib.sha256(f'{self.seed}:{key}'.encode()).digest()
        error = int.from_bytes(h[:8], 'big')/(2**64-1)*2-1
        if self.stress == 'bias': error = 1. if c%2 else -1.
        if self.stress == 'extreme': error = 1. if h[0]%2 else -1.
        self.err[key] = error
        return super().measure(x, y, c)

class PublicClient:
    """Public protocol/state facade, without fixture truth attributes."""
    def __init__(self, inner): self.__inner = inner
    @property
    def position(self): return self.__inner.position
    @property
    def channel(self): return self.__inner.channel
    @property
    def virtual_time(self): return self.__inner.virtual_time
    def time_left(self): return self.__inner.time_left()
    def measure(self, x, y, ch): return self.__inner.measure(x, y, ch)
    def clear(self, x, y, ch): return self.__inner.clear(x, y, ch)

def run_one(seed, stress, name, save_trace=False):
    count = 10+random.Random(seed+891).randrange(7)
    fixture = Fixture(seed, count, stress); client = PublicClient(fixture)
    if name == 'gemini': st = Gemini(client)
    elif name == 'original': st = Original(client)
    elif name == 'no_shared': st = Strategy(client, shared=False)
    elif name == 'fixed_cover': st = Strategy(client, adaptive=False, routing=False)
    elif name == 'adaptive': st = Strategy(client, adaptive=True)
    else: st = Strategy(client)
    t0 = time.perf_counter(); result = st.run()
    result.update(seed=seed, stress=stress, algorithm=name, total=count,
                  runtime_s=time.perf_counter()-t0, actual_cleared=sum(s['cleared'] for s in fixture.sources))
    pos = (0., 0.); channel = 1; length = 0.; switches = 0
    for row in st.trace:
        p = (row['x'], row['y']); length += dist(pos, p); pos = p
        if row['kind'] == 'measure':
            switches += row['channel'] != channel; channel = row['channel']
    result.update(distance_m=length, switches=switches)
    reconstructed = length/5+5*result['measures']+switches+5*result['cleared']+3*(result['clear_attempts']-result['cleared'])
    assert abs(reconstructed-result['virtual_time_s']) < 1e-6
    assert result['actual_cleared'] == count == result['cleared'], result
    assert result['status'].startswith('complete'), result
    if save_trace:
        (HERE/'results').mkdir(exist_ok=True)
        (HERE/'results'/f'trace_{name}_{stress}_{seed}.json').write_text(json.dumps(dict(
            summary=result, sources=fixture.initial, trace=st.trace,
            scans=getattr(getattr(st, 'coverage', None), 'scans', []),
            certificates=getattr(st, 'certificates', [])), indent=2), encoding='utf-8')
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', default='1:3'); ap.add_argument('--stress', default='random')
    ap.add_argument('--algorithms', default='gemini,breakthrough'); ap.add_argument('--out', default='benchmark')
    ap.add_argument('--trace', action='store_true'); a = ap.parse_args()
    if ':' in a.seeds:
        start, end = map(int, a.seeds.split(':')); seeds = list(range(start, end+1))
    else: seeds = list(map(int, a.seeds.split(',')))
    rows = []
    for stress in a.stress.split(','):
        for seed in seeds:
            for name in a.algorithms.split(','):
                r = run_one(seed, stress, name, a.trace and seed == seeds[0]); rows.append(r)
                print(f'{stress} {seed} {name}: {r["actual_cleared"]}/{r["total"]}, {r["average_time_s"]:.2f} s/source, {r["runtime_s"]:.2f}s CPU', flush=True)
    folder = HERE/'results'; folder.mkdir(exist_ok=True)
    (folder/f'{a.out}.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    keys = sorted(set().union(*(r.keys() for r in rows)) - {'channels'})
    with (folder/f'{a.out}.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    for name in a.algorithms.split(','):
        rr = [r for r in rows if r['algorithm'] == name]
        print(name, 'weighted seconds/source', sum(r['virtual_time_s'] for r in rr)/sum(r['total'] for r in rr))
if __name__ == '__main__': main()
