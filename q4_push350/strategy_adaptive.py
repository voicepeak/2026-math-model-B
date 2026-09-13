"""Reuse clearing stops as coverage sites; remove only freshly certified sites."""
from strategy_ring21 import Strategy as Ring21
from strategy_explore import layout
from geometry import dist
from coverage_certificate import certify

class Strategy(Ring21):
    def __init__(self,client,mode='q4',adaptive_layout='ring21',check_radius=850.,**kwargs):
        super().__init__(client,mode,**kwargs)
        if adaptive_layout!='ring21':
            self.nodes=layout(adaptive_layout);self.all_nodes=list(self.nodes)
        self.check_radius=check_radius;self.in_scan=False;self.checked_clears=0;self.replacements=[]
    def scan(self,p):
        self.in_scan=True
        try:super().scan(p)
        finally:self.in_scan=False
    def share(self,p,exclude=None):
        super().share(p,exclude)
        if self.in_scan or len(self.cleared)==self.checked_clears:return
        self.checked_clears=len(self.cleared)
        if len(self.cleared)>=16 or not self.nodes:return
        if not self.unknown:
            self.nodes=[]
            return
        removed=[]
        for q in sorted(self.nodes,key=lambda q:dist(p,q)):
            if dist(p,q)>self.check_radius:continue
            others=[v for v in self.nodes if v!=q]
            cert=certify(self.scans+[p]+others,max_depth=16,max_tiles=10000)
            if cert['certified']:
                self.nodes=others;removed.append(dict(node=q,certificate=cert))
        if removed:
            self.scan(p);self.replacements.append(dict(new=p,removed=removed))
    def summary(self,status):
        out=super().summary(status);out.update(adaptive_removed=sum(len(r['removed']) for r in self.replacements),adaptive_stops=len(self.replacements))
        return out
