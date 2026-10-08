"""Deterministic coverage and bearing localization. No simulator truth access."""
import math
from geometry import (dist,unit,add,sub,mul,dot,bearing,prior,clip_wedge,
                      diameter_info,enclosing_circle,local_to_global,guaranteed)
from robot_client import RobotError

ALPHA=1.005

def cells(h):
    n=math.ceil(1800/h)
    for i in range(-n,n):
        for j in range(-n,n):
            x,y=i*h,j*h
            nearest=(max(x,min(0,x+h)),max(y,min(0,y+h)))
            if dist(nearest,(0,0))<=1800:
                yield [(x,y),(x+h,y),(x+h,y+h),(x,y+h)]

def scan_nodes(mode):
    h=1200 if mode=='q3' else 600
    pts={(0.,0.)}
    for cell in cells(h):
        if mode=='q3':pts.add(mul(add(cell[0],cell[2]),0.5))
        else:pts.update(cell)
    remaining=pts-{(0.,0.)};ordered=[(0.,0.)]
    while remaining:
        p=min(remaining,key=lambda v:(dist(ordered[-1],v),v))
        ordered.append(p);remaining.remove(p)
    return ordered

def fallback_points(s,theta):
    w=1500*math.sin(math.radians(ALPHA))
    xs=list(range(0,1500,28))+[1500]
    return [local_to_global(s,theta,(x,y)) for y,xx in [(-w/2,xs),(w/2,list(reversed(xs)))] for x in xx]

class BudgetStop(Exception): pass

class Strategy:
    def __init__(self,client,mode='q3'):
        if mode not in ('q3','q4'): raise ValueError('mode must be q3/q4')
        self.client=client;self.mode=mode;self.cleared=set();self.measure_count=0
        self.clear_count=0;self.trace=[];self.fallback_count=0
    def action(self,kind,p,ch):
        left=self.client.time_left()
        if left is not None and left<30: raise BudgetStop('real_time_budget')
        if self.client.virtual_time+dist(self.client.position,p)/5+6>359000:
            raise BudgetStop('virtual_time_budget')
        status,res=getattr(self.client,kind)(p[0],p[1],ch)
        if status!=200 or not isinstance(res,dict) or res.get('accepted') is not True:
            raise RobotError('Rejected action: %s %s'%(status,res))
        key='measure_result' if kind=='measure' else 'clear_result'
        allowed=('direction','near','no_signal') if kind=='measure' else ('success','no_target_in_range')
        if res.get(key) not in allowed:
            raise RobotError('Invalid result code: '+repr(res))
        if kind=='measure' and res[key]=='direction':
            angle=res.get('svd_deg')
            if isinstance(angle,bool) or not isinstance(angle,(int,float)) or not math.isfinite(angle) or not 0<=angle<360:
                raise RobotError('Invalid bearing: '+repr(res))
        self.trace.append(dict(kind=kind,x=p[0],y=p[1],channel=ch,response=res,
                               virtual_time_s=self.client.virtual_time))
        if kind=='measure': self.measure_count+=1
        else:
            self.clear_count+=1
            if res.get('clear_result')=='success':self.cleared.add(ch)
        return res
    def locate(self,s,ch,res):
        if res['measure_result']=='near':
            r=self.action('clear',s,ch)
            if r['clear_result']!='success':raise RobotError('near then clear failed')
            return
        theta=res['svd_deg'];poly=prior(s,theta,ALPHA);last=s;last_theta=theta
        for _ in range(4):
            if not poly: raise RobotError('Inconsistent bearing polygon')
            c,r=enclosing_circle(poly)
            if r<=19.9:
                out=self.action('clear',c,ch)
                if out['clear_result']!='success':raise RobotError('Certified clear failed')
                return
            d=diameter_info(poly)['diameter'];u=unit(last_theta);v=(-u[1],u[0])
            offset=max(40,min(300,0.2*d))
            candidates=[add(c,mul(v,offset)),add(c,mul(v,-offset))]
            u0=unit(theta);v0=(-u0[1],u0[0])
            candidates.sort(key=lambda p:(not guaranteed((dot(sub(p,s),u0),dot(sub(p,s),v0)),ALPHA),dist(last,p),p))
            p=candidates[0];out=self.action('measure',p,ch)
            if out['measure_result']=='near':
                hit=self.action('clear',p,ch)
                if hit['clear_result']!='success':raise RobotError('near clear failed')
                return
            if out['measure_result']=='no_signal':break
            poly=clip_wedge(poly,p,out['svd_deg'],ALPHA);last=p;last_theta=out['svd_deg']
        self.fallback_count+=1
        for p in fallback_points(s,theta):
            if self.action('clear',p,ch)['clear_result']=='success':return
        raise RobotError('Complete strip sweep failed: model/interface inconsistent')
    def run(self):
        status='complete_coverage'
        try:
            for p in scan_nodes(self.mode):
                chs=[c for c in range(1,21) if c not in self.cleared]
                chs.sort(key=lambda c:(c!=self.client.channel,c))
                for ch in chs:
                    res=self.action('measure',p,ch)
                    if res['measure_result'] in ('direction','near'):self.locate(p,ch,res)
                    if len(self.cleared)==16:
                        status='complete_upper_bound';return self.summary(status)
        except BudgetStop as exc: status=str(exc)
        return self.summary(status)
    def summary(self,status):
        n=len(self.cleared)
        return dict(mode=self.mode,status=status,cleared=n,channels=sorted(self.cleared),
                    virtual_time_s=self.client.virtual_time,
                    average_time_s=self.client.virtual_time/n if n else None,
                    measures=self.measure_count,clear_attempts=self.clear_count,
                    fallback_count=self.fallback_count,official_validated=False)
