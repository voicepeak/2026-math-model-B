"""Windows/live entry point. Run only after official simulator interface is ready."""
import argparse,json,time,uuid
from pathlib import Path
from robot_client import RobotClient,RobotError
from strategy import Strategy

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['q3','q4'],required=True)
    p.add_argument('--robot-id',required=True)
    p.add_argument('--url',default='http://127.0.0.1:2026')
    p.add_argument('--out',default='windows_results')
    a=p.parse_args();folder=Path(a.out)/(time.strftime('%Y%m%d_%H%M%S')+'_'+a.mode+'_'+uuid.uuid4().hex[:6])
    folder.mkdir(parents=True,exist_ok=False)
    c=RobotClient(a.url,a.robot_id,log_path=str(folder/'client.jsonl'))
    st=Strategy(c,a.mode);started=time.monotonic()
    try:
        status,res=c.enter()
        if status!=200 or not res.get('accepted'):raise RobotError('enter rejected: '+str(res))
        summary=st.run()
        if c.time_left() is not None and c.time_left()>2:
            status,res=c.exit()
            if status!=200 or not res.get('accepted'):raise RobotError('exit rejected')
    except Exception as exc:
        summary=st.summary('error');summary['error']=repr(exc)
        # No new action after an uncertain network outcome.
    summary['program_runtime_s']=time.monotonic()-started
    summary['official_case_code']=None
    summary['official_total_sources']=None
    summary['official_encrypted_log']=None
    (folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    c.close_log(summary['status']);print(json.dumps(summary,ensure_ascii=False,indent=2));print(folder)
    return 0 if summary['status'].startswith('complete') else 2

if __name__=='__main__':raise SystemExit(main())
