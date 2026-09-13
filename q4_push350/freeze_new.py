"""Freeze the development winner before any new holdout scenes are generated."""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from experiment import CONFIGS
HERE=Path(__file__).resolve().parent
def main():
    output=HERE/'selected_new.json'
    if output.exists():raise RuntimeError('Selection already frozen')
    files=sorted((HERE/'results').glob('screening_round*.json'))+[HERE/'results/development_extension.json']
    extra=HERE/'results/development_active.json'
    if extra.exists():files.append(extra)
    rows=sum([json.loads(p.read_text(encoding='utf-8'))['rows'] for p in files],[])
    scores={}
    for name in sorted({r['algorithm'] for r in rows}):
        rr=[r for r in rows if r['algorithm']==name]
        if len(rr)==40 and {r['seed'] for r in rr}==set(range(1,41)):
            scores[name]=sum(r['virtual_time_s'] for r in rr)/sum(r['total'] for r in rr)
    selected=min(scores,key=lambda n:(scores[n],n))
    out=dict(selected=selected,kwargs=CONFIGS[selected],development_scores=scores,criterion='Total virtual seconds / total sources across seeds 1..40',
        frozen_at_utc=datetime.now(timezone.utc).isoformat(),target_s_per_source=350,holdout_seeds=[40001,40100],stress_seeds=[201,210],
        selection_input_sha256={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    output.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
