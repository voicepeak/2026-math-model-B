from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path.home()/'.codex/skills/math-modeling/tools/docx/scripts'))
import paper_format as pf
from docx.oxml.ns import qn
from docx.shared import Cm,Pt
D=pf.new_document('cumcm')
for s in D.sections:s.top_margin=s.bottom_margin=s.left_margin=s.right_margin=Cm(2.6)
pf.title(D,'AI工具使用详情')
def p(t):
 a=pf.body(D,t);a.paragraph_format.line_spacing=Pt(18)
def h(t):
 a=pf.heading2(D,t);a.paragraph_format.space_before=Pt(8);a.paragraph_format.keep_with_next=True
h('一、所用工具与说明范围')
p('使用工具为OpenAI Codex；本轮系统标识为GPT-6。记录日期为2026年9月11日。本说明记录当前可核验的使用过程；此前会话的具体模型版本尚未逐一确认，应由参赛队在最终提交前核对。当前论文完成问题一、二的草稿内容，问题三、四保留章节。')
h('二、使用目的与环节')
p('已有项目记录显示，AI用于建模分析辅助、代码实现与调试、构造场景计算、结果及图表核对。本轮主要用于依据已通过检查的问题一、二成果整理推导、撰写论文草稿、统一符号与数值、构建Word原生公式及表格，并检查导出后的版面。图表副本仅调整了轴向坐标色条标注和检测点形状标记。')
h('三、提示方式与处理过程')
p('本轮主要提示要求为：“开始写论文；问题三、四的算法在调整，先将问题一、二已通过的成果完整写入，并搭好全文框架，问题三、四留空。”处理时读取题目、建模报告、代码、真实结果表与图件，将每项数值结论与计算输出对应；首次成稿后检查公式、图表引用、参考文献及实际分页。')
p('采用的文字和数值包括半平面交会区域、顶点对直径证明、直径圆反例、最小包围圆判据，以及第二点保证接收区和有限场景比较。既有正式测试结果未被虚构或填入，问题三、四的算法内容未在本轮展开。')
h('四、采纳与核验情况')
p('机器辅助核对包括原始结果文件一致性检查、独立证据审查、文档结构和公式检查、实际渲染复核。关键数字包括问题一直径28.96681451 m、直径圆超出0.26548944 m；问题二基础格点(800,−600) m、目标112.14914075 m，局部加密点(850,−525) m、目标111.89311189 m。')
p('用户已明确问题一、二为通过版本；这不等同于对本轮新生成论文文字的逐项人工审查。本说明不将机器核验冒称为人工核验。参赛队仍需逐项核对、修改并确认新稿，补充此前会话的工具版本、实际采纳内容及人工修改记录；本轮尚无足够证据宣称这些工作全部完成。')
h('五、后续补充事项')
p('问题三、四确定后，应同步更新实际使用环节和结果核验情况；最终提交前由参赛队核实本说明与论文AI工具使用声明、实际使用过程一致，补齐人工审查记录。本文件为当前阶段的事实说明草稿，不含姓名、队号、学校或赛区信息。')
D.core_properties.author='';D.core_properties.last_modified_by=''
D.save(ROOT/'B题/work/paper/AI工具使用详情.docx')
print('AI details docx written')
