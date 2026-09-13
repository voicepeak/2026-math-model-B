import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
TIME={'runtime_s','pipeline_wall_s','local_pipeline_wall_s','strategy_wall_s_excluding_init'}
FILES=['final_development.json','final_holdout.json','final_stress.json','trace_original_random_40001.json','trace_candidate_random_40001.json']
def normalize(x):
    if isinstance(x,dict):return {k:normalize(v) for k,v in x.items() if k not in TIME}
    if isinstance(x,list):return [normalize(v) for v in x]
    return x
def fingerprint(p):return hashlib.sha256(json.dumps(normalize(json.loads(p.read_text(encoding='utf-8'))),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def check():
    expected=json.loads((HERE/'study_fingerprints.json').read_text(encoding='utf-8'))
    assert set(expected)==set(FILES)
    for f,sha in expected.items():assert fingerprint(HERE/'results'/f)==sha,f
    print('Scientific fingerprints verified:',len(FILES),flush=True)
if __name__=='__main__':check()
