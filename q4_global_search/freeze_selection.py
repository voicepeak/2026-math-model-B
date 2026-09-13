"""Select using development data only, before any holdout evaluations."""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    files=['screening_v2.json','development_v2.json','screening_v3.json','development_v3.json']
    candidates=['ring_multi','ring_optical','ring_multi_optical','pilot200_optical']
    rows=sum([json.loads((HERE/'results'/f).read_text()) for f in files],[]);scores={}
    for n in candidates:
        rr=[r for r in rows if r['algorithm']==n]
        assert len(rr)==40 and {r['seed'] for r in rr}==set(range(1,41))
        assert all(r['actual_cleared']==r['total'] for r in rr)
        scores[n]=sum(r['virtual_time_s'] for r in rr)/sum(r['total'] for r in rr)
    chosen=min(scores,key=scores.get)
    cfg=dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),selected_development_candidate=chosen,
             routing='multistart' if chosen in ('ring_multi','ring_multi_optical') else 'twoopt',
             localizer='recover' if chosen=='ring_multi' else 'optical',pilot_m=200. if chosen=='pilot200_optical' else 0.,
             trial_radius_m=60.,scores_40_development_s_per_source=scores,
             development_seeds=[1,40],holdout_seeds=[30001,30100],stress_seeds=[101,110],
             rule='Minimum source-weighted completion time among four development finalists, all-cleared required; no holdout tuning.',
             input_hashes={f:hashlib.sha256((HERE/'results'/f).read_bytes()).hexdigest() for f in files})
    path=HERE/'frozen_config.json'
    if path.exists():raise RuntimeError('Already frozen; do not overwrite after observing holdout')
    path.write_text(json.dumps(cfg,indent=2),encoding='utf-8');print(json.dumps(cfg,indent=2),flush=True)
if __name__=='__main__':main()
