"""Monotone cover replacement: never discard a remaining scan without a proof."""
from prototype_v2 import Strategy as V2, length
from prototype_v1 import route_order
from geometry import dist, enclosing_circle
from coverage_exact import certificate, mask, SAMPLES

class Strategy(V2):
    def __init__(self,client,mode='q3',*,attempt=50,visibility=True,replace=True,**kwargs):
        super().__init__(client,mode,joint=False,attempt=attempt,visibility=visibility,**kwargs)
        self.replace=replace;self.replaced=0;self.coverage_proof=None

    def stop_tasks(self,exclude=None):
        self.share(tuple(self.client.position),exclude)
        if not self.replace or exclude is not None or not self.unknown or not self.fixed_nodes:return
        p=tuple(self.client.position);full=(1<<len(SAMPLES))-1
        best=None
        for i,q in enumerate(self.fixed_nodes):
            remaining=self.fixed_nodes[:i]+self.fixed_nodes[i+1:]
            sites=self.coverage.scans+[p]+remaining
            cov=0
            for s in sites:cov |= mask(s)
            if cov!=full:continue
            jobs=[('target',ch,enclosing_circle(t['poly'])[0]) for ch,t in self.tracks.items()]
            before=length(p,route_order(p,jobs+[('scan',None,s) for s in self.fixed_nodes]))
            after=length(p,route_order(p,jobs+[('scan',None,s) for s in remaining]))
            if before-after>30*len(self.unknown) and certificate(sites)[0]:
                if best is None or before-after>best[0]:best=before-after,i
        if best:
            self.scan(p);self.fixed_nodes.pop(best[1]);self.replaced+=1

    def run(self):
        result=super().run()
        if result['status']=='complete_coverage':
            ok,w,d=certificate(self.coverage.scans)
            if not ok:raise ArithmeticError('monotone cover invariant violated')
            self.coverage_proof=dict(complete=ok,worst_distance_m=d,witness=w,scans=self.coverage.scans)
            result=self.summary(result['status'])
        return result

    def summary(self,status):
        out=super().summary(status)
        out.update(algorithm='ultimate200_v4',replaced_nodes=self.replaced)
        if self.coverage_proof:
            out.update(coverage_certificate='voronoi_outer_polygon',coverage_worst_m=self.coverage_proof['worst_distance_m'])
        return out
