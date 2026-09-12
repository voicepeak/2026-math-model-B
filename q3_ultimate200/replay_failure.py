"""Replay the archived certificate-contract bug; expected failure is explicit."""
import importlib.util,json
from pathlib import Path
from benchmark import Fixture,PublicClient
root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('archived_v6',root/'archived'/'prototype_v6_failed.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
world=Fixture(17,10,'minrange');world.sources[0].update(x=3.,y=0.)
policy=mod.Strategy(PublicClient(world))
try:policy.run()
except ArithmeticError as e:
    assert str(e)=='monotone cover invariant violated'
    assert len(policy.cleared)==10 and mod.boundary_cover(policy.coverage.scans)
    report=dict(expected_failure_reproduced=True,error=str(e),cleared=10,time_s=world.virtual_time,
                explanation='True circular domain covered; larger outer polygon certificate rejected the legacy run.')
else:raise AssertionError('Expected archived failure did not occur')
(root/'results'/'archived_failure_replay.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
