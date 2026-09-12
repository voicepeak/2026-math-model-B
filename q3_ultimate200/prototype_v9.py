"""Short forward localization baseline, shared observations and optical trial."""
from prototype_v5 import Strategy as V5
from geometry import dist,add,mul,unit,enclosing_circle

class Strategy(V5):
    def __init__(self,client,mode='q3',*,forward=150,lateral=40,radius=1150,attempt=50,**kwargs):
        super().__init__(client,mode,attempt=attempt,replace=False,**kwargs)
        self.forward=forward;self.lateral=lateral;self.radius=radius
        if not 1125<=radius<=1730:raise ValueError('invalid coverage radius')
        self.fixed_nodes=[mul(unit(a),radius) for a in range(0,360,60)]

    def viewpoint(self,tr):
        c,r=enclosing_circle(tr['poly'])
        if tr['observations']!=1 or (self.visibility and r<300):return super().viewpoint(tr)
        p=add(tr['last'],mul(unit(tr['theta']),self.forward));v=unit(tr['theta']+90)
        return min([add(p,mul(v,self.lateral)),add(p,mul(v,-self.lateral))],key=lambda q:dist(self.client.position,q))

    def summary(self,status):
        out=super().summary(status);out.update(algorithm='ultimate200_v9',first_forward=self.forward,first_lateral=self.lateral,hex_radius=self.radius);return out
