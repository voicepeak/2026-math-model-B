"""Certified compressed Q4 layouts, with optional online certified replacement."""
import json
from pathlib import Path
from strategy import Strategy as Base
from coverage_certificate import certify
from geometry import dist,enclosing_circle
from routing import route,length
from robot_client import RobotError
HERE=Path(__file__).resolve().parent

class Strategy(Base):
    def __init__(self,client,mode='q4',*,layout='ring25',adaptive=False,**kwargs):
        super().__init__(client,mode,**kwargs)
        path=HERE/('layout_ring25.json' if layout=='ring25' else 'layout_optimized.json')
        data=json.loads(path.read_text(encoding='utf-8'));nodes=[tuple(p) for p in data['nodes']]
        self.layout_certificate=certify(nodes)
        if not self.layout_certificate['certified']:raise RobotError('Uncertified scan layout')
        self.nodes=nodes;self.all_nodes=list(nodes);self.adaptive=adaptive
        self.replacements=[];self.checked_clear_count=0;self.in_scan=False
    def scan(self,p):
        self.in_scan=True
        try:super().scan(p)
        finally:self.in_scan=False
    def share(self,p,exclude=None):
        super().share(p,exclude)
        if not self.adaptive or self.in_scan or len(self.cleared)>=16:return
        if len(self.cleared)==self.checked_clear_count:return
        self.checked_clear_count=len(self.cleared)
        if not self.unknown or not self.nodes:return
        near=sorted(range(len(self.nodes)),key=lambda i:dist(p,self.nodes[i]))[:2]
        for i in near:
            if dist(p,self.nodes[i])>450:continue
            remaining=self.nodes[:i]+self.nodes[i+1:]
            cert=certify(self.scans+[p]+remaining,max_depth=15,max_tiles=15000)
            if not cert['certified']:continue
            old=self.nodes[i];self.scan(p);self.nodes=remaining
            self.replacements.append(dict(old=old,new=p,certificate=cert));break
    def summary(self,status):
        out=super().summary(status)
        out.update(algorithm='q4_compressed',adaptive_replacements=len(self.replacements))
        return out
