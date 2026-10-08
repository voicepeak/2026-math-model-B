"""Frozen combo100 policy. Public protocol only; standard-library runtime."""
from prototype_v10 import Strategy as Combo

class Strategy(Combo):
    def __init__(self,client,mode='q3',*,shared=True):
        super().__init__(client,mode,pilot=100,attempt=50,shared=shared)

    def summary(self,status):
        out=super().summary(status)
        out['algorithm']='ultimate200_frozen_combo100'
        return out
