"""Alternative annulus: 8 interior sites and only 12 exterior sites."""
from strategy_explore import Strategy as Explore
from geometry import mul,unit
from coverage_certificate import certify

def nodes21():
    return [(0.,0.)]+[mul(unit(i*45),998.) for i in range(8)]+[mul(unit(i*30),1866.) for i in range(12)]

class Strategy(Explore):
    def __init__(self,client,mode='q4',**kwargs):
        super().__init__(client,mode,**kwargs)
        self.nodes=nodes21();self.all_nodes=list(self.nodes)
        self.layout_certificate=certify(self.nodes)
        if not self.layout_certificate['certified']:raise ValueError('Uncertified ring21')
