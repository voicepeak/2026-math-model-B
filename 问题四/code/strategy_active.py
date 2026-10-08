"""Active second-bearing acquisition near the posterior area centroid."""
from strategy_explore import Strategy as Explore
from strategy_ring21 import nodes21
from geometry import dist,enclosing_circle,add,mul,unit,sub,dot
from coverage_certificate import certify

def centroid(poly):
    area=x=y=0.
    for a,b in zip(poly,poly[1:]+poly[:1]):
        z=a[0]*b[1]-a[1]*b[0];area+=z;x+=(a[0]+b[0])*z;y+=(a[1]+b[1])*z
    if abs(area)<1e-10:return enclosing_circle(poly)[0]
    return x/(3*area),y/(3*area)

class Strategy(Explore):
    def __init__(self,client,mode='q4',active_layout='ring22',fraction=.8,lateral=100.,active_views=1,**kwargs):
        super().__init__(client,mode,layout_kind='ring22' if active_layout=='ring21' else active_layout,**kwargs)
        if active_layout=='ring21':
            self.nodes=nodes21();self.all_nodes=list(self.nodes)
            self.layout_certificate=certify(self.nodes)
            if not self.layout_certificate['certified']:raise ValueError('Uncertified active layout')
        self.fraction=fraction;self.lateral=lateral;self.active_views=active_views
    def engage(self,ch):
        for _ in range(self.active_views):
            if ch not in self.tracks:return
            tr=self.tracks[ch];c,r=enclosing_circle(tr['poly'])
            if r<=60 or tr['obs']>2:break
            mean=centroid(tr['poly']);center=add(tr['last'],mul(sub(mean,tr['last']),self.fraction))
            side=unit(tr['theta']+90)
            choices=[add(center,mul(side,s*self.lateral)) for s in (-1,1)]
            choices=[p for p in choices if (ch,round(p[0],6),round(p[1],6)) not in self.cache]
            if not choices:break
            p=min(choices,key=lambda q:dist(self.client.position,q))
            self.observe(p,ch);self.share(self.client.position,exclude=ch)
        return super().engage(ch)
