"""Commit to a coverage tour, insert localized sources by marginal detour."""
from strategy_ring21 import Strategy as Ring21
from strategy_explore import layout
from geometry import dist,enclosing_circle
from routing import route
from coverage_certificate import certify

class Strategy(Ring21):
    def __init__(self,client,mode='q4',detour_limit=350.,wait_views=True,tour_layout='ring21',**kwargs):
        super().__init__(client,mode,**kwargs)
        if tour_layout!='ring21':
            self.nodes=layout(tour_layout);self.all_nodes=list(self.nodes)
            self.layout_certificate=certify(self.nodes)
            if not self.layout_certificate['certified']:raise ValueError('Uncertified tour')
        order=route((0.,0.),[p for p in self.nodes if dist(p,(0,0))>1e-7],'multistart')
        pts=[p for p in self.nodes if dist(p,(0,0))>1e-7]
        self.tour=[pts[i] for i in order]
        self.detour_limit=detour_limit;self.wait_views=wait_views
    def next_job(self):
        if not self.nodes:return super().next_job()
        available=set(self.nodes);p=next(p for p in self.tour if p in available)
        candidates=[]
        for ch,tr in self.tracks.items():
            c,r=enclosing_circle(tr['poly'])
            if self.wait_views and r>60 and tr['obs']<2:continue
            extra=dist(self.client.position,c)+dist(c,p)-dist(self.client.position,p)
            if extra<=self.detour_limit:candidates.append((extra,ch,c))
        if candidates:
            _,ch,c=min(candidates);return ('target',ch,c)
        return ('scan',self.nodes.index(p),p)
