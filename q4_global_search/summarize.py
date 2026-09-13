import json,sys
from pathlib import Path
for fn in sys.argv[1:]:
    rows=json.loads(Path(fn).read_text(encoding='utf-8'));print(fn,len(rows))
    for name in sorted({r['algorithm'] for r in rows}):
        rr=[r for r in rows if r['algorithm']==name]
        print(name,len(rr),round(sum(r['virtual_time_s'] for r in rr)/sum(r['total'] for r in rr),3),
              'fallback',sum(r['fallback_count'] for r in rr),'replacements',sum(r.get('adaptive_replacements',0) for r in rr))
