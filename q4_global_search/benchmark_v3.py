import benchmark
from strategy_v3 import Strategy
benchmark.Strategy=Strategy
benchmark.CONFIGS={
 'original':None,
 'pilot100':dict(pilot=100.),
 'pilot200':dict(pilot=200.),
 'pilot300':dict(pilot=300.),
 'pilot100_multi':dict(pilot=100.,routing='multistart'),
 'pilot200_optical':dict(pilot=200.,localizer='optical'),
 'rotated':dict(rotate=True),
 'rotate_pilot':dict(rotate=True,pilot=100.),
}
if __name__=='__main__':benchmark.main()
