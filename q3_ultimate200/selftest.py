"""本地自测：用内置 mock 模拟器跑若干局，检查是否 100% 清除。
用法：python selftest.py [--seeds 1,2,3,4,5] [--count 12]
不会连接官方模拟器，不消耗正式机会。
"""
import argparse
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_simulator as ms
from robot_client import RobotClient
from strategy import Strategy

HERE = os.path.dirname(os.path.abspath(__file__))


def run_one(seed, count):
    args = argparse.Namespace(port=0, seed=seed, count=count, mode='q3', scenario=None,
                              robot_id='SELFTEST', log_dir=os.path.join(HERE, 'logs'), quiet=True)
    world = ms.build_world(args, robot_id='SELFTEST')
    server = ms.make_server(0, world)
    port = server.server_address[1]
    client = RobotClient('http://127.0.0.1:%d' % port, 'SELFTEST',
                         log_path=os.path.join(HERE, 'logs', 'selftest_%d.jsonl' % seed))
    try:
        status, res = client.enter()
        if status != 200 or not res.get('accepted'):
            raise RuntimeError('mock enter failed')
        st = Strategy(client, 'q3')
        summary = st.run()
        status, res = client.exit()
        if status != 200 or not res.get('accepted'):
            raise RuntimeError('mock exit failed')
    finally:
        server.shutdown()
        server.server_close()
    return summary, world.scenario.truth()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', default='1,2,3,4,5')
    ap.add_argument('--count', type=int, default=0,
                    help='0 = 按第三题随机 10~16 个源；>0 = 固定源数')
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(',') if x.strip()]
    count = a.count if a.count else None
    total = cleared = errors = 0
    rows=[]
    worst = 0.0
    for s in seeds:
        try:
            summary, truth = run_one(s, count)
        except Exception as exc:
            print('seed %-4d ERROR  %r' % (s, exc))
            errors += 1
            rows.append(dict(seed=s,error=repr(exc)))
            continue
        total += truth['total']
        rows.append(dict(seed=s,truth_total=truth['total'],summary=summary))
        cleared += summary['cleared']
        worst = max(worst, summary['virtual_time_s'])
        flag = 'OK ' if summary['cleared'] == truth['total'] else 'MISS'
        print('seed %-4d %s cleared=%2d/%2d  time=%8.1fs  status=%s' % (
            s, flag, summary['cleared'], truth['total'],
            summary['virtual_time_s'], summary['status']))
    print('TOTAL %d/%d  worst_time=%.1fs' % (cleared, total, worst))
    folder=Path(HERE)/'results';folder.mkdir(exist_ok=True)
    (folder/'http_selftest.json').write_text(json.dumps(dict(total=total,cleared=cleared,errors=errors,rows=rows),ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if not errors and total and cleared == total else 1


if __name__ == '__main__':
    raise SystemExit(main())
