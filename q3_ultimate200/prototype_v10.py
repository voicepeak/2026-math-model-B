"""Combine shared initial bearings with a continuously certified elastic tour."""
from prototype_v6 import Strategy as V6
from prototype_v7 import Strategy as V7

class Strategy(V6):
    def __init__(self,client,mode='q3',*,pilot=200,attempt=50,**kwargs):
        super().__init__(client,mode,attempt=attempt,**kwargs)
        self.pilot=pilot;self.pilot_done=False

    def scan(self,p):
        # V7.scan's super() needs V7 in the MRO, so share the small operation
        # through a helper proxy over exactly this public policy state.
        super().scan(p)
        if self.pilot_done or p!=(0.,0.):return
        self.pilot_done=True
        if len(self.tracks)<2 or not self.pilot:return
        import math
        from geometry import dist,unit,mul,enclosing_circle,bearing
        estimates=[enclosing_circle(t['poly']) for t in self.tracks.values()]
        best=None
        for a in range(0,360,15):
            q=mul(unit(a),self.pilot);loss=0.
            for c,r in estimates:
                s=abs(math.sin(math.radians(bearing(q,c)-bearing(p,c))))
                loss+=min(r,.035*dist(q,c)/max(s,.015))
            if best is None or loss<best[0]:best=loss,q
        for ch in sorted(list(self.tracks),key=lambda c:(c!=self.client.channel,c)):
            self.observe(best[1],ch)

    def share(self,p,exclude=None):
        if len(self.cleared)<16:super().share(p,exclude)

    def summary(self,status):
        out=super().summary(status);out.update(algorithm='ultimate200_v10',pilot_m=self.pilot);return out
