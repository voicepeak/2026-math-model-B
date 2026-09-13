# -*- coding: utf-8 -*-
"""Build optimized paper: insert Q4 chapter, new figures, Q4 tables, remap figure numbers."""
import os, re, copy, shutil
import glob as globmod
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

ROOT = r"C:\Users\张靖浩\Desktop\2026数学建模\2026-math-model-B"
FIG = os.path.join(ROOT, "figures_opt")
SRC = [x for x in globmod.glob(os.path.join(ROOT, "*.docx")) if "前两问备份" not in x and "优化版" not in x][0]
DST = os.path.join(ROOT, "完整论文_优化版.docx")

doc = Document(SRC)

# ---------------------------------------------------------------- helpers
def set_font(run, size_pt=12, east="宋体", bold=False):
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rFonts.set(qn("w:eastAsia"), east)


def set_center(p):
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER


def set_keepnext(p):
    pPr = p._p.get_or_add_pPr()
    if pPr.find(qn("w:keepNext")) is None:
        el = OxmlElement("w:keepNext")
        pPr.insert(0, el)


def set_spacing(p, line_pt=None, rule=None, before=0, after=0, first_indent_pt=None):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if line_pt is not None:
        pf.line_spacing = Pt(line_pt)
        pf.line_spacing_rule = rule if rule is not None else WD_LINE_SPACING.EXACTLY
    if first_indent_pt is not None:
        pf.first_line_indent = Pt(first_indent_pt)


def add_body(anchor, text):
    p = anchor.insert_paragraph_before()
    set_spacing(p, line_pt=18, first_indent_pt=24)
    r = p.add_run(text)
    set_font(r, 12, "宋体")
    return p


def add_caption(anchor, text, size=10, bold=False):
    p = anchor.insert_paragraph_before()
    set_spacing(p, line_pt=15, rule=WD_LINE_SPACING.AT_LEAST)
    set_center(p)
    set_keepnext(p)
    r = p.add_run(text)
    set_font(r, size, "宋体", bold=bold)
    return p


def add_image(anchor, img, width_cm):
    p = anchor.insert_paragraph_before()
    set_spacing(p, line_pt=15, rule=WD_LINE_SPACING.AT_LEAST)
    set_center(p)
    set_keepnext(p)
    r = p.add_run()
    r.add_picture(os.path.join(FIG, img), width=Cm(width_cm))
    return p


def add_note(anchor, text):
    return add_caption(anchor, text, size=10)


def replace_image(caption_par, img, width_cm):
    prev = caption_par._p.getprevious()
    if prev is None or prev.tag.split("}")[1] != "p":
        raise RuntimeError("no image paragraph before caption: " + caption_par.text)
    par = Paragraph(prev, caption_par._parent)
    for r in list(par.runs):
        r._r.getparent().remove(r._r)
    r = par.add_run()
    r.add_picture(os.path.join(FIG, img), width=Cm(width_cm))
    set_center(par)
    set_keepnext(par)


def del_par(p):
    p._p.getparent().remove(p._p)


def find_par(pred, paras=None):
    for p in (paras if paras is not None else doc.paragraphs):
        if pred(p):
            return p
    return None


def par_after(pred):
    paras = doc.paragraphs
    for i, p in enumerate(paras):
        if pred(p):
            return paras[i + 1]
    return None


def make_table(anchor, rows, widths=None, font_pt=10):
    tbl = doc.add_table(rows=len(rows), cols=len(rows[0]))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    proto = doc.tables[9]._tbl  # stress table 7x5 has same border design
    tbl._tbl.replace(tbl._tbl.tblPr, copy.deepcopy(proto.tblPr))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.paragraphs[0].text = ""
            p = cell.paragraphs[0]
            set_center(p)
            set_spacing(p, line_pt=14, rule=WD_LINE_SPACING.AT_LEAST)
            r = p.add_run(str(val))
            set_font(r, font_pt, "宋体", bold=(i == 0))
    anchor._p.addprevious(tbl._tbl)
    return tbl


# ---------------------------------------------------------------- 1. remap figure refs
MAP = {1: 2, 2: 4, 3: 5, 4: 6, 5: 8, 6: 9, 7: 12, 8: 13, 9: 15, 10: 16, 11: 17}
pat = re.compile(r"图\s?(\d{1,2})")

def remap_text(s):
    return pat.sub(lambda m: "图" + str(MAP[int(m.group(1))]) if int(m.group(1)) in MAP else m.group(0), s)

for p in doc.paragraphs:
    for r in p.runs:
        if "图" in r.text:
            r.text = remap_text(r.text)
for t in doc.tables:
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    if "图" in r.text:
                        r.text = remap_text(r.text)

# ---------------------------------------------------------------- 2. targeted text edits
# old 图8 note
p = find_par(lambda p: p.text.startswith("注：Breakthrough表示上一版"))
if p:
    p.runs[0].text = "注：上一版用橙色虚线表示，最终策略用蓝色实线表示；该图为开发种子1，不作为独立留出结果。"
# old 图10 note
p = find_par(lambda p: p.text.startswith("注：Travel、Measure、Switch、Clear"))
if p:
    p.runs[0].text = "注：依次统计移动、检测、切换与清除；失败试清耗时计入清除。"

# abstract: insert Q4 paragraph before results paragraph
p_res = find_par(lambda p: p.text.startswith("在100场未参与调参的新留出合成场景中"))
abs_q4 = ("针对问题四，定向源的可见性受±90°发射扇区限制，无信号响应不再可解释为距离或位置排除。"
          "本文保留正向示向度的楔形约束，将覆盖扫描加密为600 m网格四角共49个节点，并给出发现完整性引理："
          "任意源到其所在单元某角点的距离不超过848.53 m<1000 m，且该角点位于源的有效扇区内。"
          "清除仍采用认证包围圆与条带回退，最坏清除距离19.21 m<20 m。官方演练5场共67个源全部清除，"
          "平均1023.70—1436.56 s/源；定向源占比越高条带回退越频繁，是问题四时间的主要来源。")
add_body(p_res, abs_q4)
r = p_res.add_run("问题三、问题四的三次正式测试均尚未执行，表13与表16按题定结构如实记录“未执行”，不以演练或本地合成结果代填。")
set_font(r, 12, "宋体")

# ---------------------------------------------------------------- 3. insert new figures
# 图1 roadmap
anchor = find_par(lambda p: p.style.name == "Heading 1" and p.text.strip().startswith("2 模型假设"))
add_body(anchor, "本文四问共享同一集合定位内核：以位置可行集逐次求交保留观测信息，以最坏距离界保证发现与清除的完整性；"
                 "问题一、二建立几何基础，问题三、四把该内核嵌入在线搜索与清除策略。总体建模与验证路线见图1。")
add_image(anchor, "fig_roadmap.png", 15.2)
add_caption(anchor, "图1  本文四问的总体建模与验证路线")

# 图3 states
anchor = find_par(lambda p: p.style.name == "Heading 2" and "3.3 定位直径" in p.text)
add_body(anchor, "算法对区域状态的判别结果如图3所示：单次观测不足以约束二维位置时区域无界，合法的两次观测形成有界多边形，"
                 "而互相矛盾的观测给出空集并触发不一致报告。")
add_image(anchor, "fig_q1_states.png", 15.0)
add_caption(anchor, "图3  交会区域的三类状态：无界、有界与空集")
add_note(anchor, "注：观测为构造数据，仅用于状态判别演示；(b)中黑色星号为构造源。")

# 图7 reception region
anchor = find_par(lambda p: p.style.name == "Heading 2" and "4.4 以有限场景" in p.text)
add_body(anchor, "图7对比本文的条件保证接收区C与仅使用R≥1000 m的保守区域，并叠加50 m候选格点；"
                 "条件区明显更大，说明首次已接收到信号这一事实确实收紧了接收半径下界、放宽了可用候选位置。")
add_image(anchor, "fig_q2_region.png", 12.8)
add_caption(anchor, "图7  条件保证接收区与保守区域的对比")
add_note(anchor, "注：格点为20 m步长的数值检验；C的边界仍以第4.3节连续判据为准。")

# 图10 comparison
anchor = find_par(lambda p: p.text.startswith("在粗网格优选点附近"))
add_body(anchor, "典型候选点的条件最坏定位直径对比如图10所示：沿示向前进虽保证接收，但径向不确定区很长；"
                 "纯横向点定位几何较好，却不具备接收保证；斜向点位于两者之间。")
add_image(anchor, "fig_q2_comparison.png", 13.8)
add_caption(anchor, "图10  典型第二检测点的条件最坏定位直径对照")
add_note(anchor, "注：(0, 100) m不满足连续保证接收，其数值为条件值。")

# 图11 coverage
anchor = find_par(lambda p: p.text.startswith("若所有扫描任务已执行"))
add_body(anchor, "外圈六个扫描点的整周覆盖与径向覆盖条件如图11所示。")
add_image(anchor, "fig_q3_coverage.png", 12.5)
add_caption(anchor, "图11  外圈六点的整周覆盖与径向覆盖条件")
add_note(anchor, "注：覆盖计算半径R_c=999.99 m；绿色弧段为各扫描点的覆盖范围。")

# 图14 progress
anchor = find_par(lambda p: p.text.startswith("如图15所示，逐场比较") or p.text.startswith("如图9所示，逐场比较"))
add_body(anchor, "图14进一步给出同一开发场景中两种策略的清除进度：最终策略在相同累计清除数下用时更短，"
                 "且两者均在任务末段保留了一段扫空时间。")
add_image(anchor, "fig_q3_progress.png", 12.5)
add_caption(anchor, "图14  同一开发场景的清除进度对比")
add_note(anchor, "注：数据为开发种子1，不作为独立留出结果。")

# ---------------------------------------------------------------- 4. replace Q3 figures (12,13,15,16,17)
REPL = [("图12  开发场景示例", "fig_q3_positions.png", 10.5),
        ("图13  同一开发场景的动作路线对比", "fig_q3_routes.png", 15.0),
        ("图15  新留出集100场的逐场配对耗时", "fig_q3_paired.png", 11.0),
        ("图16  新留出集的平均动作耗时分解", "fig_q3_cost.png", 13.5),
        ("图17  五类压力场景的逐场平均定位清除时间", "fig_q3_stress.png", 13.5)]
for cap_prefix, img, w in REPL:
    cp = find_par(lambda p: p.text.strip().startswith(cap_prefix))
    if cp is None:
        print("WARN caption not found:", cap_prefix)
        continue
    replace_image(cp, img, w)

# ---------------------------------------------------------------- 5. Q4 chapter
# --- 6.1 model
anchor = par_after(lambda p: p.style.name == "Heading 2" and p.text.strip().startswith("6.1"))
q4_61 = [
    "问题四的目标区域中同时存在全向源与定向源。定向源的发射方向δ未知，其有效覆盖角度为δ两侧各90°。"
    "设源位置为g、有效接收半径为R，则在测点p能够接收到该源信号的充要条件为：‖p−g‖≤R，且(p−g)·u(δ)≥0，"
    "其中u(δ)为发射方向的单位向量；全向源相当于第二个条件恒成立。",

    "定向方向与接收半径均未知，因此no_signal存在两类歧义：测点可能位于发射扇区之外，也可能超出有效接收半径；"
    "此外频道无源或已被清除同样返回no_signal。单一no_signal不能排除任何圆盘或半平面，"
    "这正是问题三第5.2节无信号排除规则在问题四失效的原因。问题四因此只利用正向观测："
    "direction给出以测点为中心、宽度2α_c的示向楔形，near给出距离不超过5 m的直接清除机会；"
    "位置可行集P_c仍按楔形逐次求交更新，首次观测后用目标圆域、1500 m接收圆与示向楔形构造先验外包络。",

    "负观测不可用意味着搜索完整性必须由扫描覆盖独立保证。将1800 m圆域按600 m间距划分网格，"
    "取全部位于圆域内的网格角点作为扫描节点，共49个。对任意源g，设其所在单元的四个角点为c1至c4："
    "g是四角的凸组合，且每个角点到g的距离不超过√(2×600²)=848.528 m<1000 m≤R；"
    "另一方面，若四个角点全部位于发射方向的背向半平面内，则它们的凸组合g也必在背向半平面内，与g按方向δ发射矛盾。"
    "因此至少存在一个角点同时满足接收距离与扇区可见性，机器狗扫描到该角点时必然收到信号。"
    "该引理保证49个节点的扫描不遗漏任何合法源，包括位于圆域边界与角落的源（图18(b)）。",

    "清除环节与问题三共用几何保证：最小包围圆半径r_c≤19.9 m时到圆心实施认证清除；"
    "局部交会未完成时进入条带回退。首次合法示向意味着源位于以首次测点为原点、沿示向0—1500 m、横向±w的条带内，"
    "其中w=1500·sin(α_c)=26.31 m。两条横向偏移±w/2的扫描线以28 m间隔共布置110个清除点；"
    "任意条带内点到最近清除点的距离不超过√(14²+(w/2)²)=19.21 m<20 m，"
    "故该方法不依赖后续射频信号即可完成清除。",

    "时间指标沿用式(25)、(26)的口径：移动按5 m/s计，每次检测含5 s稳定时间与1 s频道切换，"
    "清除成功5 s、失败3 s。优化目标仍是在全部清除的前提下最小化总时间。",
]
for t in q4_61:
    add_body(anchor, t)
add_image(anchor, "fig_q4_visibility.png", 15.0)
add_caption(anchor, "图18  定向源可见性与600 m网格四角覆盖")
add_note(anchor, "注：no_signal存在扇区外与超出半径两类歧义。")
del_par(anchor)

# --- 6.2 strategy
anchor = par_after(lambda p: p.style.name == "Heading 2" and p.text.strip().startswith("6.2"))
q4_62 = [
    "问题四在问题三的在线状态机上作三处修改。第一，频道仍划分为未发现U、已发现未清除H与已清除E三个集合，"
    "但H中频道只保存正向观测得到的可行多边形P_c与最近测点，no_signal不再参与可行集更新，只跳过该频道。",

    "第二，定位流程为至多4轮迭代：计算P_c的最小包围圆(c,r)；若r≤19.9 m，直接到c实施认证清除；"
    "否则沿与最近示向垂直的方向移动到c±offset处补测，其中offset=max(40,min(300,0.2d))，d为P_c直径，"
    "并在两个候选点中优先选择满足问题二保证接收判据、距离较近且字典序较小者；"
    "若补测返回direction，则以新楔形与P_c求交；若返回no_signal，立即转入条带回退。"
    "条带回退按6.1节所述110点蛇形顺序逐点尝试清除，直到成功或预算耗尽；"
    "若两条扫描线全部失败，程序报告模型或接口不一致，不静默放弃目标。",

    "第三，覆盖扫描在49个网格角点上依次执行：对每个节点遍历全部未清除频道，当前频道优先，检测到信号即就地定位；"
    "成功清除16个不同频道时按题定上界提前结束。与问题三最终策略相比，问题四不启用共享先导与弹性覆盖调整，"
    "因为这两项机制依赖正负观测融合与固定的全向可见性，其前提在定向源下不成立；"
    "作为补偿，扫描节点由17个增至49个，把发现的完整性直接建立在几何覆盖引理上。策略参数汇总于表14。",
]
for t in q4_62:
    add_body(anchor, t)
add_caption(anchor, "表14  问题四最终策略的主要参数")
make_table(anchor, [
    ["参数", "采用值", "作用"],
    ["扫描网格间距", "600 m", "网格角点覆盖引理"],
    ["扫描节点数", "49（7×7全域角点）", "保证每单元至少一个可见角点"],
    ["最坏扫描距离", "848.53 m", "小于最小接收半径1000 m"],
    ["定位迭代上限", "4轮", "每轮补测一次示向"],
    ["横向补测偏移", "max(40, min(300, 0.2d)) m", "依可行域直径自适应"],
    ["认证清除半径", "19.9 m", "在最小包围圆圆心处清除"],
    ["条带扫描", "110点，28 m间隔", "不依赖射频信号的确定性回退"],
    ["最坏条带距离", "19.21 m", "小于20 m光学清除半径"],
    ["建模半界α_c", "1.005°", "覆盖题定误差与舍入裕量"],
], font_pt=10)
del_par(anchor)

# --- 6.3 practice
anchor = par_after(lambda p: p.style.name == "Heading 2" and p.text.strip().startswith("6.3"))
q4_63a = [
    "问题四的演练分为本地合成场景与官方模拟器两部分。本地合成场景沿用问题三的配对生成器，"
    "每场12个源、定向源占比约40%，三个种子的场景均全部清除：虚拟总时间分别为14469.15、15558.53、15735.82 s，"
    "折合平均1205.76、1296.54、1311.32 s/源，条带回退分别触发2、3、3次。"
    "官方模拟器演练5场，全部完成覆盖并清除全部源，逐场结果列于表15。",
]
for t in q4_63a:
    add_body(anchor, t)
add_caption(anchor, "表15  问题四官方模拟器演练结果（5场，非正式测试）")
make_table(anchor, [
    ["案例编码", "源数（全向/定向）", "清除数", "清除比例", "平均时间 / (s/源)", "程序运行 / s", "条带回退"],
    ["6V97-T58V-6288-FVFS", "15（12/3）", "15", "15/15", "1023.70", "7.18", "1"],
    ["83FD-8B4K-3MBB-954J", "12（4/8）", "12", "12/12", "1436.56", "12.97", "6"],
    ["HNA8-GUGP-7XWK-26RT", "14（0/14）", "14", "14/14", "1313.94", "12.71", "9"],
    ["RJU6-83MV-8X9J-HGKX", "12（3/9）", "12", "12/12", "1419.00", "12.22", "7"],
    ["4M5T-2KS6-NAF9-XZD7", "14（5/9）", "14", "14/14", "1124.42", "10.37", "6"],
], font_pt=8.5)

q4_63b = [
    "5场演练共清除67/67个源，清除比例100%；平均定位清除时间最低1023.70 s/源（6V97，12个全向源、3个定向源），"
    "最高1436.56 s/源（83FD，4个全向源、8个定向源）；程序运行时间7.18—12.97 s，远低于20 min上限。"
    "图19给出逐场清除结果与定向源个数—耗时关系：定向源个数与平均时间呈中等正相关（Pearson相关系数0.53）；"
    "14个源全为定向源的HNA8场平均1313.94 s/源，比以全向源为主的6V97场高290.24 s/源，条带回退次数由1次增至9次。",
]
for t in q4_63b:
    add_body(anchor, t)
add_image(anchor, "fig_q4_practice.png", 15.0)
add_caption(anchor, "图19  问题四5场官方演练的清除结果与定向源—耗时关系")
add_note(anchor, "注：官方演练结果，非正式测试成绩；右图点大小表示条带回退次数。")

q4_63c = [
    "图20左图给出HNA8场的实际动作轨迹：定向源在多数停点不可见或超出半径，机器狗多次进入条带回退，"
    "逐点试清形成大量失败动作（该场374次清除尝试中360次失败，橙色叉号为失败位置）。"
    "右图按动作拆分时间：移动占77.4%—85.5%，检测占11.5%—15.9%，清除仅占1.2%—6.3%，"
    "分解残差为0 s。失败试清使清除代价显著放大（HNA8场清除耗时1150 s，其中失败代价1080 s），"
    "但时间主体仍是行走。与问题三最终策略在新留出集上的233.72 s/源相比，问题四演练平均高约4—6倍，"
    "说明定向可见性造成的信息缺失不能由问题三的加速机制自动弥补。",

    "以上均为演练结果。演练数据说明策略在混合源场景中能够全部清除并在20 min程序预算内完成，"
    "但不构成正式成绩；正式测试的案例编码、清除数与加密日志尚不可核验。",
]
for t in q4_63c:
    add_body(anchor, t)
add_image(anchor, "fig_q4_route_cost.png", 15.0)
add_caption(anchor, "图20  问题四演练案例HNA8的动作轨迹与逐场时间分解")
add_note(anchor, "注：源自官方演练日志；时间分解残差为0 s。")
del_par(anchor)

# --- 6.4 formal
anchor = par_after(lambda p: p.style.name == "Heading 2" and p.text.strip().startswith("6.4"))
q4_64 = [
    "题面要求问题四进行三次正式测试，并在论文中按题面表1的格式报告案例编码、清除源个数、平均定位清除时间与程序运行时间，"
    "同时导出加密日志放入支撑材料。截至本稿完成，问题四正式测试尚未执行。"
    "为保持题定结构与证据状态一致，表16按正式测试表保留三行记录位并如实标注“未执行”。",

    "未执行不等于数值0，也不代表测试失败；表15的演练结果与本地合成结果均不能代替正式测试数据填入表16。"
    "若后续完成正式测试，应逐场回填案例编码、清除数、平均时间与程序运行时间，并将原名导出的加密日志随支撑材料提交。",
]
for t in q4_64:
    add_body(anchor, t)
add_caption(anchor, "表16  问题四正式测试结果记录状态")
make_table(anchor, [
    ["测试", "案例编码", "清除干扰源个数", "平均定位清除时间", "程序运行时间"],
    ["测试1", "未执行", "未执行", "未执行", "未执行"],
    ["测试2", "未执行", "未执行", "未执行", "未执行"],
    ["测试3", "未执行", "未执行", "未执行", "未执行"],
], font_pt=10)
del_par(anchor)

# ---------------------------------------------------------------- 6. 7.4 and 8.3
anchor = par_after(lambda p: p.style.name == "Heading 2" and p.text.strip().startswith("7.4"))
q4_74 = [
    "问题四沿用了集合定位与认证清除内核，几何保证在定向可见性下仍然成立："
    "600 m网格四角覆盖引理把发现的完整性化为可验证的距离条件，条带回退把清除的完整性化为不依赖射频信号的有限扫描，"
    "二者分别给出明确的最坏距离界848.53 m与19.21 m。正负观测的严格区分避免把问题三的no_signal排除规则错误移植到定向源上。",

    "局限同样明显。定向方向未知使负观测信息完全不可用，可行集只能靠正向观测逐步收缩，定位过程明显变长；"
    "演练中条带回退触发频繁，成为时间的主要增量。问题三最终策略中的共享测点与弹性覆盖等加速机制未在问题四生效，"
    "两问的策略尚未统一。此外演练场数有限，平均时间的差异同时受场景构成影响，不能据此给出不同定向比例下的时间函数。",

    "后续改进可将定向方向与位置联合估计纳入可行集，例如用同一频道多次direction的扇区一致性反推方向区间；"
    "或利用no_signal的扇区外与超距两类事件构造析取约束，以减少条带回退；"
    "也可把49节点扫描与共享测向结合，缩减重复检测。",
]
for t in q4_74:
    add_body(anchor, t)
del_par(anchor)

anchor = par_after(lambda p: p.style.name == "Heading 2" and p.text.strip().startswith("8.3"))
q4_83 = [
    "针对混合干扰源，本文在问题三框架上建立了定向可见性模型与覆盖加密策略："
    "以600 m网格四角共49个节点保证任意源在至少一个扫描点同时满足接收距离与扇区条件，"
    "用最小包围圆认证清除与110点条带回退保证清除完整性。",

    "本地合成3场（每场12源、约40%定向）与官方演练5场（共67个源，其中全向24个、定向43个）均全部清除；"
    "官方演练平均定位清除时间1023.70—1436.56 s/源，程序运行7.18—12.97 s。"
    "定向源个数与耗时呈中等正相关（r=0.53），条带回退由1次增至9次，说明定向源的信息缺失是主要耗时来源。",

    "问题四正式测试尚未执行，表16保持“未执行”状态；本文不报告任何未经官方核验的正式成绩。",
]
for t in q4_83:
    add_body(anchor, t)
del_par(anchor)

# ---------------------------------------------------------------- 7. appendix manifest
p_appb = find_par(lambda p: p.text.strip().startswith("附录B") and p.style.name == "Heading 2")
# empty paragraph after appendix B heading
p_after = None
started = False
for p in doc.paragraphs:
    if p._p is p_appb._p:
        started = True
        continue
    if started:
        p_after = p
        break
manifest = [
    "受篇幅限制，题定“完整源程序”随支撑材料提交，核心文件清单如下（完整SHA-256见results/复现清单.json）：",
    "几何内核与问题一：B题/code/geometry.py、solve_q1.py、study.py、test_core.py；"
    "问题二：solve_q2.py、study.py；问题三策略：q3_ultimate200/strategy.py及其依赖"
    "（prototype_v1.py—prototype_v10.py、baseline_breakthrough.py、robot_core.py、coverage_exact.py）；"
    "问题四策略：B题/code/strategy.py；运行入口run_robot.py；通信客户端robot_client.py；"
    "本地模拟器mock_simulator.py、offline_sim.py。",
    "图表复现：q3_ultimate200/analyze_results.py、utils/plot_style.py、utils/export_figure.py、"
    "B题/work/paper_opt/make_figures.py；问题一、二的数值核验记录见B题/work/q1_lp_check.json与results/目录。",
]
for t in manifest:
    p = p_after.insert_paragraph_before()
    set_spacing(p, line_pt=18, first_indent_pt=24)
    r = p.add_run(t)
    set_font(r, 12, "宋体")
if p_after is not None and not p_after.text.strip():
    del_par(p_after)
# rename appendix B heading to match manifest content
head_b = find_par(lambda p: p.style.name == "Heading 2" and p.text.strip().startswith("附录B"))
if head_b and head_b.runs:
    head_b.runs[0].text = "附录B 完整源程序清单"

# appendix D note
head_d = find_par(lambda p: p.style.name == "Heading 2" and p.text.strip().startswith("附录D"))
p_d = par_after(lambda p: p._p is head_d._p) if head_d is not None else None
if p_d is not None:
    r = p_d.add_run("全题源程序、官方演练日志、结果表格与图表复现脚本均随电子支撑材料提交；"
                    "问题一至问题四的输入数据、关键数值与复现命令见results/复现清单.json。"
                    "问题三、问题四的正式测试加密日志尚待测试执行后补充。")
    set_font(r, 12, "宋体")

# appendix A final sentence
p = find_par(lambda p: p.text.startswith("问题一的构造观测、顶点与约束递增试验"))
if p:
    p.runs[0].text = ("问题一的构造观测、顶点与约束递增试验分别保存于q1_observations.csv、q1_vertices.csv与"
                      "q1_constraint_sequence.csv；问题二的格点评分、典型点对照、局部加密结果与容忍度分析分别保存于"
                      "q2_candidates.csv、q2_comparison.csv、q2_local_refinement.csv与q2_eta_sensitivity.csv。"
                      "对应图件为正文图2至图10。")

# appendix C append Q4
p = find_par(lambda p: p.text.startswith("第三题最终入口位于"))
if p:
    r = p.add_run("问题四入口为B题/code/run_robot.py（--mode q4），策略为B题/code/strategy.py；"
                  "官方演练日志（practice-p4-*.jlog/.psum/.result.json）与我方client.jsonl、summary.json"
                  "按场归档于q4_五次演练汇总/。问题三对应图件为正文图11至图17，问题四对应图18至图20。")
    set_font(r, 12, "宋体")

# table 13 cells: align with abstract wording (未执行)
cap13 = find_par(lambda p: p.text.strip().startswith("表13"))
if cap13 is not None:
    el = cap13._p.getnext()
    while el is not None and el.tag.split("}")[1] != "tbl":
        el = el.getnext()
    if el is not None:
        from docx.table import Table
        t13 = Table(el, cap13._parent)
        for i in range(1, len(t13.rows)):
            for j in range(1, len(t13.columns)):
                cell = t13.cell(i, j)
                for r in list(cell.paragraphs[0].runs):
                    r._r.getparent().remove(r._r)
                rr = cell.paragraphs[0].add_run("未执行")
                set_font(rr, 10, "宋体")

doc.save(DST)
print("saved", DST)
