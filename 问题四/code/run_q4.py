"""Run only when the official Q4 simulator interface is ready; never starts a case."""
import argparse,json,time,uuid
from pathlib import Path
from robot_client import RobotClient,RobotError
from strategy_selected import Strategy

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--robot-id',required=True)
    p.add_argument('--url',default='http://127.0.0.1:2026');p.add_argument('--out',default='windows_results_q4')
    a=p.parse_args();folder=Path(a.out)/(time.strftime('%Y%m%d_%H%M%S')+'_q4_'+uuid.uuid4().hex[:6]);folder.mkdir(parents=True)
    c=RobotClient(a.url,a.robot_id,log_path=str(folder/'client.jsonl'));st=None;t0=time.perf_counter()
    try:
        status,res=c.enter()
        if status!=200 or res.get('accepted') is not True:raise RobotError('enter rejected: '+str(res))
        st=Strategy(c,'q4');summary=st.run()
        if c.time_left() is not None and c.time_left()>2:
            status,res=c.exit()
            if status!=200 or res.get('accepted') is not True:raise RobotError('exit rejected')
    except Exception as exc:
        summary=st.summary('error') if st is not None else dict(mode='q4',status='error',cleared=0)
        summary['error']=repr(exc)
    summary['program_wall_s_including_init']=time.perf_counter()-t0
    summary.update(official_case_code=None,official_total_sources=None,official_encrypted_log=None)
    (folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    if st is not None:
        (folder/'trace.json').write_text(json.dumps(st.trace,indent=2),encoding='utf-8')
        (folder/'certificates.json').write_text(json.dumps(st.certificates,indent=2),encoding='utf-8')
    c.close_log(summary['status']);print(json.dumps(summary,ensure_ascii=False,indent=2));print(folder.resolve())
    return 0 if summary['status'].startswith('complete') else 2
if __name__=='__main__':raise SystemExit(main())
