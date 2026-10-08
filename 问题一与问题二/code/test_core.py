"""Independent properties for model geometry and strategy. python B题/code/test_core.py"""
import json,math,random,unittest
from geometry import *
from strategy import fallback_points,scan_nodes,ALPHA,Strategy

COUNTER=[[359.5055815863,-115.3225120884,162.7748154197],
         [205.7197780760,700.2420960671,253.5162100170]]

class CoreTests(unittest.TestCase):
    def test_counter(self):
        r=intersection(COUNTER);self.assertEqual(r['status'],'bounded')
        self.assertFalse(r['diameter_circle_covers']);self.assertGreater(r['circle_excess'],0.26)
        c,radius=enclosing_circle(r['vertices'])
        self.assertTrue(all(dist(c,v)<=radius+1e-7 for v in r['vertices']))
    def test_empty_unbounded(self):
        self.assertEqual(intersection([[0,0,0]])['status'],'unbounded')
        self.assertEqual(intersection([[0,0,0],[-10,0,180]])['status'],'empty')
        self.assertEqual(intersection([[0,0,0],[10,0,180]])['status'],'bounded')
    def test_random_containment(self):
        rng=random.Random(20260910)
        for _ in range(100):
            g=(rng.uniform(-500,500),rng.uniform(-500,500));obs=[]
            for j in range(3):
                s=mul(unit(j*120+rng.uniform(-10,10)),800)
                obs.append([*s,bearing(s,g)+rng.uniform(-1,1)])
            r=intersection(obs);self.assertEqual(r['status'],'bounded')
            self.assertTrue(inside(g,[h for x,y,t in obs for h in wedge((x,y),t)]))
            c,rad=enclosing_circle(r['vertices']);self.assertLessEqual(dist(g,c),rad+1e-6)
    def test_circle_triangle(self):
        vs=[(0,0),(2,0),(1,math.sqrt(3))];self.assertFalse(diameter_info(vs)['diameter_circle_covers'])
        self.assertAlmostEqual(enclosing_circle(vs)[1],2/math.sqrt(3))
    def test_reception(self):
        self.assertTrue(guaranteed((750,300)));self.assertFalse(guaranteed((-10,0)))
        for b in [(750,300),(500,500),(100,100)]:
            self.assertTrue(guaranteed(b))
            for r in range(5,1501,13):
                for t in [-1,-0.5,0,0.5,1]: self.assertLessEqual(dist(b,mul(unit(t),r)),max(1000,r)+1e-7)
    def test_optical_cover(self):
        pts=fallback_points((0,0),0);self.assertEqual(len(pts),110)
        self.assertLess(math.hypot(14,750*math.sin(math.radians(ALPHA))),20)
        for r in range(0,1501,13):
            for t in [-ALPHA,0,ALPHA]:self.assertLess(min(dist(mul(unit(t),r),p) for p in pts),20)
    def test_directional_cover(self):
        ps=scan_nodes('q4')
        for radius in (0,300,1799,1800):
            for t in range(0,360,15):
                g=mul(unit(t),radius)
                for d in range(0,360,15):
                    self.assertTrue(any(dist(g,p)<=1000 and dot(sub(p,g),unit(d))>=-1e-9 for p in ps))
    def test_near_at_current_point(self):
        class Client:
            position=(1000.,0.);virtual_time=0;channel=1
            def time_left(self):return 100
            def clear(self,x,y,ch):
                assert (x,y)==(1000.,0.)
                self.virtual_time+=5
                return 200,dict(accepted=True,clear_result='success')
        st=Strategy(Client());st.locate((1000.,0.),1,{'measure_result':'near'})
        self.assertEqual(st.cleared,{1})
    def test_invalid_response_stops(self):
        from robot_client import RobotError
        class Client:
            position=(0.,0.);virtual_time=0;channel=1
            def time_left(self):return 100
            def measure(self,x,y,ch):return 200,dict(accepted=True,measure_result='malformed')
        with self.assertRaises(RobotError):Strategy(Client()).run()

if __name__=='__main__': unittest.main(verbosity=2)
