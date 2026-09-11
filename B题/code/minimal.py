import json
from geometry import *
from test_core import COUNTER
from offline_sim import OfflineClient
from strategy import Strategy

def main():
    counter=intersection(COUNTER)
    print('q1',json.dumps(counter))
    sources=source_samples((0,0),0)
    score=sampled_score((0,0),0,(750,300),sources,[-1,0,1])
    print('q2',dict(guaranteed=guaranteed((750,300)),diameter=score,scenarios=len(sources)*3))
    for mode in ['q3','q4']:
        c=OfflineClient(mode,20260910,count=10);st=Strategy(c,mode);result=st.run()
        assert all(s['cleared'] for s in c.sources),result
        assert result['cleared']==10
        print('synthetic_only',json.dumps(result))
if __name__=='__main__':main()
