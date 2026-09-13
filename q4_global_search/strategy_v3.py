"""Shared initial baselines and public-observation rotation of a certified layout."""
import math
from strategy_v2 import Strategy as Base
from geometry import dist,unit,mul,dot,bearing

class Strategy(Base):
    def __init__(self,client,mode='q4',*,pilot=0.,rotate=False,**kwargs):
        self.pilot=pilot;self.rotate_layout=rotate;self.initial_done=False
        super().__init__(client,mode,**kwargs)
    def scan(self,p):
        super().scan(p)
        if self.initial_done:return
        self.initial_done=True
        if self.rotate_layout and self.tracks:
            # Rigid rotation preserves the true disk coverage theorem.
            tr=min(self.tracks.values(),key=lambda t:dist(t['last'],p))
            angle=tr['theta'];co,si=math.cos(math.radians(angle)),math.sin(math.radians(angle))
            def transform(v):return (co*v[0]-si*v[1],si*v[0]+co*v[1])
            self.nodes=[transform(v) for v in self.nodes];self.all_nodes=list(self.nodes)
        if self.pilot and self.tracks and len(self.cleared)<16:
            dirs=[unit(t['theta']) for t in self.tracks.values()]
            a=max(range(0,360,15),key=lambda a:sum(1-dot(unit(a),u)**2 for u in dirs))
            q=mul(unit(a),self.pilot)
            for ch in sorted(list(self.tracks),key=lambda ch:(ch!=self.client.channel,ch)):
                if ch in self.cleared:continue
                self.observe(q,ch)
                if len(self.cleared)==16:return
