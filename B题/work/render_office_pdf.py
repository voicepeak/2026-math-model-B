"""Windows adapter: use the packaged render_docx rasterizer on an actual Office PDF.

LibreOffice is absent from this Windows runtime. The PDF must have been exported
from the same DOCX through word_export.ps1; its identity is saved in a sidecar.
No document layout is re-created here.
"""
import argparse,hashlib,importlib.util,json,os,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('docx');p.add_argument('pdf');p.add_argument('output');p.add_argument('--dpi',type=int,default=120)
a=p.parse_args();docx=Path(a.docx).resolve();pdf=Path(a.pdf).resolve();out=Path(a.output).resolve()
runtime=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'
os.environ['PATH']=str(runtime/'native/poppler/Library/bin')+os.pathsep+os.environ['PATH']
script=Path.home()/'.codex/plugins/cache/openai-primary-runtime/documents/26.909.12148/skills/documents/render_docx.py'
spec=importlib.util.spec_from_file_location('render_docx',script);renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
def office_pdf(input_path,user_profile,convert_tmp_dir,stem,verbose=False):
    target=Path(convert_tmp_dir)/(stem+'.pdf');shutil.copy2(pdf,target)
    return str(target),'Actual Windows Office COM export; LibreOffice not installed.'
renderer.convert_to_pdf=office_pdf
pages=renderer.rasterize(str(docx),str(out),a.dpi,verbose=True,emit_pdf=False)
from pypdf import PdfReader
report={'engine':str(PdfReader(pdf).metadata.get('/Creator','Office COM')),'docx_sha256':hashlib.sha256(docx.read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':len(pages),'dpi':a.dpi,'renderer':str(script.name)}
out.mkdir(parents=True,exist_ok=True);(out/'render.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report)
