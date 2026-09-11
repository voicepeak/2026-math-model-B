import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path.home()/'.codex/skills/math-modeling/tools/docx/scripts'))
import paper_format as pf
doc=pf.new_document('cumcm',ROOT/'B题/work/官方格式2026.docx')
pf.title(doc,'无线电干扰源交会定位导出验证')
pf.abstract_title(doc)
pf.body(doc,'构造交会区域的直径为28.9668米，但对应直径圆不能覆盖整个区域。此文档只用于验证原生公式与图片的导出链路。')
pf.keywords(doc,'交会定位；凸几何')
pf.equation(doc,r'\|w-c\|^2-\frac{\|a-b\|^2}{4}=(w-a)\cdot(w-b)')
pf.image(doc,ROOT/'figures/result_q1_counter.png',12)
pf.figure_caption(doc,'图1 交会定位区域与覆盖圆')
pf.body(doc,'如图1所示，直径圆外仍存在可行位置，题目测角误差取值来自赛题[1]。')
pf.heading1(doc,'AI工具使用声明')
pf.body(doc,'本参赛队在竞赛过程中使用了 AI 工具，主要用于模型分析、代码调试和论文草稿撰写，详细使用情况见支撑材料。')
pf.heading1(doc,'参考文献')
pf.body(doc,'[1] 全国大学生数学建模竞赛组委会. 2026年高教社杯全国大学生数学建模竞赛B题 无线电干扰源的快速自动定位与清除. 2026.')
pf.save_document(doc,ROOT,'B题/work/导出链路验证.docx',overwrite=True)
print('smoke docx created')
