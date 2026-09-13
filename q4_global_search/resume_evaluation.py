"""Resume only missing cases after an interrupted batch; preserve original failure."""
import json,shutil
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from evaluate_final import tasks_for,worker,write_rows
HERE=Path(__file__).resolve().parent
def main():
    path=HERE/'results/final_combined.json';backup=HERE/'results/final_combined_before_resume.json'
    if not backup.exists():shutil.copyfile(path,backup)
    rows=json.loads(path.read_text());keys={(r['dataset'],r['seed'],r['stress'],r['algorithm']) for r in rows}
    assert len(keys)==len(rows)
    tasks=[t for phase in ('development','holdout','stress') for t in tasks_for(phase) if t[:4] not in keys]
    print('Resuming missing cases',len(tasks),flush=True)
    with ProcessPoolExecutor(max_workers=4) as ex:
        for f in as_completed([ex.submit(worker,t) for t in tasks]):
            rows.append(f.result());write_rows(rows,path)
            if len(rows)%10==0:print('validated',len(rows),'/ 440',flush=True)
    assert len(rows)==440
    for phase in ('development','holdout','stress'):
        write_rows([r for r in rows if r['dataset']==phase],HERE/'results'/f'final_{phase}.json')
    print('All 440 final runs recorded; prior interruption retained separately.',flush=True)
if __name__=='__main__':main()
