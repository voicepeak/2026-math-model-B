"""Stable scientific-result fingerprints; wall clock metadata is nondeterministic."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
TIME_FIELDS={'runtime_s','local_pipeline_wall_s','strategy_wall_s_excluding_init','program_wall_s_including_init'}
FILES=['final_development.json','final_holdout.json','final_stress.json','screening.json','screening_v2.json','screening_v3.json',
       'development_v2.json','development_v3.json','trace_original_random_30001.json','trace_candidate_random_30001.json',
       'offline_lower_bounds.json','fixed_scan_route_optimality.json','final_combined.failure.json','interrupted_case_replay.json']
def normalize(v):
    if isinstance(v,dict):return {k:normalize(x) for k,x in v.items() if k not in TIME_FIELDS}
    if isinstance(v,list):return [normalize(x) for x in v]
    return v
def fingerprint(path):
    value=normalize(json.loads(path.read_text(encoding='utf-8')))
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def check():
    expected=json.loads((HERE/'study_fingerprints.json').read_text(encoding='utf-8'))
    if set(expected)!=set(FILES):raise ValueError('Unexpected evidence manifest file set')
    for name,value in expected.items():
        if fingerprint(HERE/'results'/name)!=value:raise ValueError('Scientific evidence changed: '+name)
    print('Scientific evidence fingerprints verified:',len(expected),flush=True)
if __name__=='__main__':check()
