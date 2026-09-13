"""HTTP protocol smoke using a private ephemeral local mock, never official port."""
import argparse,json,tempfile
from pathlib import Path
import mock_simulator as ms
from robot_client import RobotClient
from strategy_final import Strategy
HERE=Path(__file__).resolve().parent
def main():
    rows=[];folder=HERE/'results'/'http_smoke';folder.mkdir(exist_ok=True)
    for seed,count in ((17,10),(29,16)):
        args=argparse.Namespace(port=0,seed=seed,count=count,mode='q4',scenario=None,robot_id='SELFTEST',log_dir=str(folder),quiet=True)
        world=ms.build_world(args,robot_id='SELFTEST');server=ms.make_server(0,world)
        client=RobotClient('http://127.0.0.1:%d'%server.server_address[1],'SELFTEST',log_path=str(folder/f'client_{seed}.jsonl'))
        try:
            status,res=client.enter();assert status==200 and res['accepted']
            st=Strategy(client);summary=st.run();status,res=client.exit();assert status==200 and res['accepted']
            truth=world.scenario.truth();assert summary['cleared']==truth['total']==count
            assert summary['status'].startswith('complete')
            rows.append(dict(seed=seed,summary=summary,truth_total=truth['total']));print(seed,count,summary['virtual_time_s'],flush=True)
        finally:server.shutdown();server.server_close();client.close_log('selftest_end')
    (HERE/'results/http_selftest.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':main()
