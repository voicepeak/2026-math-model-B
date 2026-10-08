"""Q4 public-observation-only persistent localization and certified coverage."""
import math
from geometry import (dist,add,sub,mul,unit,bearing,prior,clip_wedge,enclosing_circle,
                      diameter_info,dot,local_to_global)
from robot_core import StrategyBase,BudgetStop,ALPHA,CLEAR_SAFE,fallback_points
from robot_client import RobotError
from coverage import mesh
from routing import route

class Strategy(StrategyBase):
    def __init__(self,client,mode='q4',*,routing='twoopt',mesh_kind='triangle',spacing=990.,
                 phase=0.,localizer='recover',shared=True,trial_radius=60.,batch=True):
        if mode!='q4':raise ValueError('Q4 only')
        super().__init__(client,mode)
        self.unknown=set(range(1,21));self.tracks={};self.cache={}
        self.nodes,self.cells=mesh(mesh_kind,spacing,phase);self.all_nodes=list(self.nodes)
        self.scans=[];self.certificates=[];self.routing=routing;self.localizer=localizer
        self.shared=shared;self.trial_radius=trial_radius;self.batch=batch
        self.shared_count=0;self.recoveries=0;self.route_calls=0
    def observe(self,p,ch):
        key=(ch,round(p[0],6),round(p[1],6))
        if key in self.cache:return self.cache[key]
        res=self.action('measure',p,ch);self.cache[key]=res;k=res['measure_result']
        if k=='near':
            if self.action('clear',p,ch)['clear_result']!='success':raise RobotError('near failed')
            self.unknown.discard(ch);self.tracks.pop(ch,None)
        elif k=='direction':
            self.unknown.discard(ch)
            if ch not in self.tracks:
                self.tracks[ch]=dict(poly=prior(p,res['svd_deg'],ALPHA),s0=p,t0=res['svd_deg'],
                    last=p,theta=res['svd_deg'],obs=1,tried=[],optical=False)
            else:
                tr=self.tracks[ch];tr['poly']=clip_wedge(tr['poly'],p,res['svd_deg'],ALPHA)
                tr.update(last=p,theta=res['svd_deg'],obs=tr['obs']+1)
            if not self.tracks[ch]['poly']:raise RobotError('Empty feasible region')
        return res
    def scan(self,p):
        # Batch measures before any localization; near clears occur at p itself.
        for ch in sorted(list(self.unknown),key=lambda c:(c!=self.client.channel,c)):
            self.observe(p,ch)
            if len(self.cleared)==16:return
        self.scans.append(p)
        self.share(p)
    def share(self,p,exclude=None):
        if not self.shared or len(self.cleared)==16:return
        for ch in sorted(list(self.tracks),key=lambda c:(c!=self.client.channel,c)):
            if ch==exclude or ch in self.cleared:continue
            tr=self.tracks[ch];c,r=enclosing_circle(tr['poly'])
            angle=abs(math.sin(math.radians(bearing(p,c)-bearing(tr['last'],c))))
            if r>CLEAR_SAFE and dist(p,c)<1200 and dist(p,tr['last'])>60 and (angle>.12 or dist(p,c)<150):
                self.observe(p,ch);self.shared_count+=1
                if len(self.cleared)==16:return
    def clear_at(self,p,ch,certificate=None):
        ok=self.action('clear',p,ch)['clear_result']=='success'
        if certificate is not None:
            if not ok:raise RobotError('Certified clear failed')
            self.certificates.append(certificate)
        if ok:self.tracks.pop(ch,None)
        return ok
    def sweep(self,ch):
        """Tight rectangle covering the *remaining* polygon, optical distance only.
        Local grid <=28 x28 m gives radius <=sqrt(14²+14²)<20 m.
        Then nearest-neighbour/2opt visits every point unless success occurs.
        """
        self.fallback_count+=1;tr=self.tracks[ch];poly=tr['poly']
        info=diameter_info(poly);a,b=info['diameter_pair'];t=bearing(a,b);u=unit(t);v=(-u[1],u[0])
        coords=[(dot(sub(p,a),u),dot(sub(p,a),v)) for p in poly]
        xs=[p[0] for p in coords];ys=[p[1] for p in coords]
        lo,hi=min(xs),max(xs);bot,top=min(ys),max(ys)
        nx=max(1,math.ceil((hi-lo)/28));ny=max(1,math.ceil((top-bot)/28))
        pts=[local_to_global(a,t,(lo+(i+.5)*(hi-lo)/nx,bot+(j+.5)*(top-bot)/ny)) for i in range(nx) for j in range(ny)]
        order=route(self.client.position,pts,'twoopt')
        for i in order:
            if self.clear_at(pts[i],ch):return
        raise RobotError('Complete feasible rectangle sweep failed')
    def engage(self,ch):
        if ch not in self.tracks:return
        tr=self.tracks[ch]
        for attempt in range(8):
            if ch in self.cleared:return
            tr=self.tracks[ch];c,r=enclosing_circle(tr['poly'])
            if r<=CLEAR_SAFE:
                self.clear_at(c,ch,dict(channel=ch,center=c,radius=r,vertices=tr['poly']))
                self.share(self.client.position);return
            if r<=self.trial_radius and not tr['optical']:
                tr['optical']=True
                if self.clear_at(c,ch):self.share(self.client.position);return
            if self.localizer=='optical' and (tr['obs']>=2 or attempt>=2):break
            v=unit(tr['theta']+90);offset=max(25,min(160,.25*r))
            if tr['obs']==1:
                center=add(tr['last'],mul(unit(tr['theta']),300))
                candidates=[add(center,mul(v,75)),add(center,mul(v,-75))]
                # Remaining candidates reduce forward overshoot or gather broad parallax.
                candidates += [add(tr['last'],mul(v,sgn*80)) for sgn in (1,-1)]
            else:
                candidates=[add(c,mul(v,offset)),add(c,mul(v,-offset)),
                            mul(add(c,tr['last']),.5)]
            candidates += [add(tr['s0'],mul(sub(c,tr['s0']),f)) for f in (.25,.5,.75)]
            candidates=[p for p in candidates if all(dist(p,q)>1 for q in tr['tried'])
                        and (ch,round(p[0],6),round(p[1],6)) not in self.cache]
            if not candidates:break
            p=min(candidates,key=lambda p:dist(self.client.position,p)) if attempt else candidates[0]
            tr['tried'].append(p);res=self.observe(p,ch);self.share(self.client.position,exclude=ch)
            if res['measure_result']=='no_signal':
                if self.localizer=='strip':break
                self.recoveries+=1
        if ch not in self.cleared:self.sweep(ch);self.share(self.client.position)
    def next_job(self):
        jobs=[('target',ch,enclosing_circle(tr['poly'])[0]) for ch,tr in self.tracks.items()]
        jobs += [('scan',i,p) for i,p in enumerate(self.nodes)]
        if not jobs:return None
        self.route_calls+=1
        order=route(tuple(self.client.position),[j[2] for j in jobs],self.routing,seed=self.route_calls)
        return jobs[order[0]]
    def run(self):
        status='complete_coverage'
        try:
            self.scan((0.,0.));self.nodes=[p for p in self.nodes if dist(p,(0,0))>1e-7]
            while len(self.cleared)<16:
                job=self.next_job()
                if job is None:break
                kind,i,p=job
                if kind=='scan':self.nodes.pop(i);self.scan(p)
                else:self.engage(i)
            if len(self.cleared)==16:status='complete_upper_bound'
            elif self.nodes or self.tracks:raise RobotError('Incomplete coverage')
        except BudgetStop as exc:status=str(exc)
        return self.summary(status)
    def summary(self,status):
        out=super().summary(status)
        out.update(algorithm='q4_persistent',full_scan_count=len(self.scans),pending_nodes=len(self.nodes),
                   pending_tracks=len(self.tracks),shared_measures=self.shared_count,recoveries=self.recoveries,
                   mesh_nodes=len(self.all_nodes),route_calls=self.route_calls)
        return out
