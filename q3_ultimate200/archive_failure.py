"""Reconstruct the exact v6 revision rejected by independent P1."""
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parent
s=(root/'prototype_v6.py').read_text(encoding='utf-8')
s=s.replace('from baseline_breakthrough import Strategy as Base\n','')
s=s.replace("        out['coverage_certificate']='circular_arc_radial' if boundary_cover(self.coverage.scans) else 'not_yet_complete'\n",'')
s=s[:s.index('\n    def run(self):')]
expected='bd30fbd409941c4338ba163a2736ff53f164db7f86f111fb6ce388938e54e0e6'
for suffix in ('','\n','\n\n'):
    data=(s+suffix).encode()
    if hashlib.sha256(data).hexdigest()==expected:break
else:raise AssertionError('Cannot reconstruct original failure revision')
out=root/'archived';out.mkdir(exist_ok=True)
(out/'prototype_v6_failed.py').write_bytes(data)
print('Preserved failed revision',expected)
