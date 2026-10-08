"""Optical-first terminal localization with same-location measurement on miss."""
from prototype_v4 import Strategy as V4
from geometry import enclosing_circle
from robot_core import CLEAR_SAFE, localize_poly
from robot_client import RobotError

class Strategy(V4):
    def __init__(self,client,mode='q3',*,attempt=150,**kwargs):
        super().__init__(client,mode,attempt=attempt,**kwargs)

    def engage(self,ch):
        for _ in range(8):
            if ch in self.cleared:return
            tr=self.tracks[ch];c,r=enclosing_circle(tr['poly']);certified=r<=CLEAR_SAFE
            optical=certified or (r<=self.attempt and ch not in self.optical_attempted)
            if optical:
                if certified:self.certificates.append(dict(channel=ch,center=c,radius=r,vertices=tr['poly'],time=self.client.virtual_time))
                else:self.optical_attempted.add(ch)
                res=self.action('clear',c,ch)
                if res['clear_result']=='success':
                    self.tracks.pop(ch,None);self.stop_tasks();return
                if certified:raise RobotError('certified clear failed')
                p=c
            else:p=self.viewpoint(tr)
            res=self.observe(p,ch);self.stop_tasks(exclude=ch)
            if res['measure_result']=='no_signal':break
        if ch not in self.cleared:
            tr=self.tracks[ch];localize_poly(self,ch,tr['poly'],tr['s0'],tr['t0'],tr['last'],tr['theta'])
            self.tracks.pop(ch,None);self.stop_tasks()

    def summary(self,status):
        out=super().summary(status);out['algorithm']='ultimate200_v5';return out
