"""Frozen new candidate; previous deliverable remains independent."""
import json
from pathlib import Path
from strategy_explore import Strategy as Explore
from strategy_ring21 import Strategy as Ring21
from strategy_particle import Strategy as Particle
from strategy_active import Strategy as Active
from strategy_final import Strategy as Previous
CFG=json.loads((Path(__file__).resolve().parent/'selected_new.json').read_text(encoding='utf-8'))
NAME=CFG['selected']
BASE=Previous if NAME=='previous' else Active if NAME.startswith('active') else Particle if NAME.startswith('particle') else Ring21 if NAME.endswith('21') else Explore
class Strategy(BASE):
    def __init__(self,client,mode='q4'):
        super().__init__(client,mode,**CFG['kwargs'])
