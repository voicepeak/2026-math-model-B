"""Frozen production Q4 entry. All online dependencies are Python standard library."""
import json,math
from pathlib import Path
from strategy import Strategy as Base
from ring_certificate import ring_nodes,verify_ring
from geometry import unit,mul,dot
HERE=Path(__file__).resolve().parent

class Strategy(Base):
    def __init__(self,client,mode='q4'):
        config=json.loads((HERE/'frozen_config.json').read_text(encoding='utf-8'))
        self.pilot=float(config['pilot_m']);self.initial_done=False
        super().__init__(client,mode,routing=config['routing'],localizer=config['localizer'],
                         trial_radius=config['trial_radius_m'],shared=True)
        self.nodes=ring_nodes();self.all_nodes=list(self.nodes);self.layout_certificate=verify_ring(self.nodes)
        self.selected_name=config['selected_development_candidate']
    def scan(self,p):
        super().scan(p)
        if self.initial_done:return
        self.initial_done=True
        if self.pilot and self.tracks and len(self.cleared)<16:
            dirs=[unit(t['theta']) for t in self.tracks.values()]
            a=max(range(0,360,15),key=lambda a:sum(1-dot(unit(a),u)**2 for u in dirs))
            q=mul(unit(a),self.pilot)
            for ch in sorted(list(self.tracks),key=lambda ch:(ch!=self.client.channel,ch)):
                if ch in self.cleared:continue
                self.observe(q,ch)
                if len(self.cleared)==16:return
    def summary(self,status):
        out=super().summary(status);out.update(algorithm='q4_final',selected_candidate=self.selected_name,
                                             coverage_certificate='32_triangles_exact_coordinate_checks')
        return out
