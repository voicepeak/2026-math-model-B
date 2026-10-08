"""Meaningful regression tests for coverage, near and public action state."""
import math
import unittest
from benchmark import Fixture, PublicClient
from strategy import Strategy
from geometry import guaranteed, dist, inside, wedge

class StrategyTests(unittest.TestCase):
    def test_first_baseline_guaranteed(self):
        self.assertTrue(guaranteed((300,75),1.005))
        self.assertTrue(guaranteed((300,-75),1.005))

    def test_continuous_hexagon_bound(self):
        # Maximum over d in [1000,1800] occurs at an endpoint (convex quadratic).
        worst=max(math.sqrt(d*d+1200**2-2*d*1200*math.cos(math.pi/6)) for d in (1000,1800))
        self.assertLess(worst,1000)

    def test_near_and_extreme_boundaries(self):
        for seed,count,stress in [(23,10,'edge'),(41,16,'extreme'),(59,10,'bias')]:
            world=Fixture(seed,count,stress)
            world.sources[0].update(x=3.,y=0.)
            policy=Strategy(PublicClient(world))
            summary=policy.run()
            self.assertEqual(summary['cleared'],count)
            self.assertTrue(all(s['cleared'] for s in world.sources))
            self.assertTrue(any(row['response'].get('measure_result')=='near' for row in policy.trace))
            for cert in policy.certificates:
                source=next(s for s in world.sources if s['channel']==cert['channel'])
                self.assertLessEqual(dist(cert['center'],(source['x'],source['y'])),cert['radius']+1e-5)

    def test_cache_does_not_simulate_movement_or_channel_change(self):
        world=Fixture(1,10)
        policy=Strategy(PublicClient(world))
        ch=world.sources[0]['channel']
        policy.observe((0.,0.),ch)
        world.measure(50.,20.,20)
        state=(world.position,world.channel,world.virtual_time,len(policy.trace))
        policy.observe((0.,0.),ch)
        self.assertEqual(state,(world.position,world.channel,world.virtual_time,len(policy.trace)))

    def test_q4_rejected(self):
        with self.assertRaises(ValueError): Strategy(PublicClient(Fixture(1,10)),'q4')

if __name__=='__main__': unittest.main()
