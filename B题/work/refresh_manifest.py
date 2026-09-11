"""Use the skill manifest builder, then make input paths portable and anonymous."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SKILL=Path.home()/'.codex/skills/math-modeling'
sys.path.insert(0,str(SKILL/'references/roles/编程手/scripts'))
from repro_manifest import build_manifest
old=json.loads((ROOT/'results/复现清单.json').read_text(encoding='utf-8'))
inputs=[ROOT/x['path'] for x in old['input_files']]
for name in ['题目分析报告.md','术语表格.md']:
    if ROOT/name not in inputs: inputs.append(ROOT/name)
manifest=build_manifest(inputs,20260910,old['key_parameters'],'python B题/code/reproduce.py',['numpy','matplotlib','pillow','scipy'])
for item in manifest['input_files']:
    item['path']=Path(item['path']).relative_to(ROOT).as_posix()
(ROOT/'results/复现清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Manifest refreshed:',len(inputs),'inputs; runtime',manifest['runtime'])
