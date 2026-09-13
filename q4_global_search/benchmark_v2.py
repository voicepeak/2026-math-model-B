"""Additional candidates; baseline benchmark remains immutable during its run."""
import benchmark
from strategy_v2 import Strategy
benchmark.Strategy=Strategy
benchmark.CONFIGS={
 'original':None,
 'ring_twoopt':{},
 'ring_nearest':dict(routing='nearest'),
 'ring_multi':dict(routing='multistart'),
 'ring_anneal':dict(routing='anneal'),
 'ring_exact':dict(routing='exact'),
 'ring_optical':dict(localizer='optical'),
 'ring_multi_optical':dict(routing='multistart',localizer='optical'),
 'ring_adaptive':dict(adaptive=True),
 'cap_twoopt':dict(layout='cap'),
 'cap_adaptive':dict(layout='cap',adaptive=True),
}
if __name__=='__main__':benchmark.main()
