"""Fixed complete cover with data-dependent orientation, local optical trials."""
from prototype_v2 import Strategy as V2, length
from prototype_v1 import route_order
from geometry import mul, unit, enclosing_circle

class Strategy(V2):
    def __init__(self,client,mode='q3',*,radius=1450,rotate=True,attempt=50,visibility=True,**kwargs):
        super().__init__(client,mode,joint=False,attempt=attempt,visibility=visibility,**kwargs)
        if not 1125<=radius<=1730:raise ValueError('radius outside analytic coverage range')
        self.radius=radius;self.rotate=rotate;self.oriented=False
        self.fixed_nodes=[mul(unit(a),radius) for a in range(0,360,60)]

    def next_job(self):
        start=tuple(self.client.position)
        jobs=[('target',ch,enclosing_circle(tr['poly'])[0]) for ch,tr in self.tracks.items()]
        if not self.oriented:
            self.oriented=True
            if self.rotate:
                best=None
                for a in range(0,60,5):
                    pts=[mul(unit(t+a),self.radius) for t in range(0,360,60)]
                    rt=route_order(start,jobs+[('scan',i,p) for i,p in enumerate(pts)])
                    cost=length(start,rt)
                    if best is None or cost<best[0]:best=cost,pts
                self.fixed_nodes=best[1]
        return route_order(start,jobs+[('scan',i,p) for i,p in enumerate(self.fixed_nodes)])[0]

    def summary(self,status):
        out=super().summary(status)
        out.update(algorithm='ultimate200_v3',hex_radius=self.radius,rotate=self.rotate)
        return out
