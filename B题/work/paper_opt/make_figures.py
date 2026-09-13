# -*- coding: utf-8 -*-
"""Generate optimized paper figures (Chinese labels, unified style)."""
import os, sys, json, math, csv, traceback
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, FancyArrowPatch, Polygon, Wedge as MWedge, Rectangle

ROOT = r"C:\Users\张靖浩\Desktop\2026数学建模\2026-math-model-B"
sys.path.insert(0, os.path.join(ROOT, "B题", "code"))
OUT = os.path.join(ROOT, "figures_opt")
os.makedirs(OUT, exist_ok=True)

import geometry as G

PAL = {"primary": "#0072B2", "secondary": "#E69F00", "positive": "#009E73",
       "contrast": "#D55E00", "accent": "#CC79A7", "sky": "#56B4E9",
       "neutral": "#6B7280", "dark": "#222222"}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["SimSun", "Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "font.size": 9,
    "axes.titlesize": 9.5,
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.2,
    "axes.unicode_minus": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "svg.fonttype": "none",
    "savefig.dpi": 300,
    "figure.dpi": 110,
})


def save(fig, name):
    base = os.path.join(OUT, name)
    fig.savefig(base + ".png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(base + ".svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)


def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(p):
    with open(p, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- F01 roadmap
def fig_roadmap():
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    def box(x, y, w, h, text, fc, ec, fs=9, bold=False, radius=0.02):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6",
                                    fc=fc, ec=ec, lw=1.0, mutation_scale=1))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, color=PAL["dark"], linespacing=1.45,
                fontweight=("bold" if bold else "normal"))

    def arrow(x1, y1, x2, y2, style="-|>", color=PAL["neutral"], ls="-", rad=0.0):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                     mutation_scale=11, lw=1.0, color=color,
                                     linestyle=ls, shrinkA=1, shrinkB=1,
                                     connectionstyle="arc3,rad=%.2f" % rad))

    box(2, 88, 96, 9.5, "数据与假设：1800 m圆域｜示向误差±1°（有界）｜接收半径1000—1500 m｜光学定位20 m、近距5 m",
        "#F4F7FB", PAL["primary"], fs=8.0)
    arrow(50, 88, 50, 82)

    box(1.5, 63, 22.5, 16, "问题一\n集合定位\n楔形求交→凸包→衰退锥\n直径=最大顶点对\n覆盖判别用最小包围圆",
        "#EAF2FA", PAL["primary"], fs=8.0)
    box(26.5, 63, 22.5, 16, "问题二\n保证接收区\n首次接收收紧半径下界\n连续判据→有限检验\n有限场景最坏直径优选",
        "#EAF2FA", PAL["primary"], fs=8.0)
    box(51.5, 63, 22.5, 16, "问题三\n全向源搜索清除\n正负观测融合｜覆盖扫描\n100 m共享先导｜滚动路径\n认证清除+条带回退",
        "#E8F5EF", PAL["positive"], fs=8.0)
    box(76.5, 63, 22, 16, "问题四\n混合源扩展\n定向可见性建模\n覆盖加密为49节点\n同一认证清除内核",
        "#FDF3E3", PAL["secondary"], fs=8.0)
    arrow(24, 71, 26.5, 71)
    arrow(49, 71, 51.5, 71)
    arrow(74, 71, 76.5, 71)

    box(6, 40.5, 88, 13, "共用内核：位置可行集 P（圆域∩接收圆∩示向楔形→逐次求交，保留包含关系）\n"
                       "清除保证：最小包围圆 r≤19.9 m 认证清除；条带回退最坏距离 19.21 m < 20 m",
        "#F7F7F7", PAL["neutral"], fs=8.4)
    arrow(50, 63, 50, 53.8)

    box(6, 20, 41, 13.5, "验证一：几何与数值\n构造反例（直径28.96681 m，漏覆盖0.26549 m）\n"
                         "120个线性规划交叉核验（最大差7.1×10^-15 m）",
        "#FBEEF3", PAL["accent"], fs=8.0)
    box(53, 20, 41, 13.5, "验证二：任务表现\n190场配对试验（100%清除，改善5.77%）\n"
                          "官方演练：全向5场、混合5场均100%清除",
        "#FBEEF3", PAL["accent"], fs=8.0)
    arrow(26.5, 40.5, 26.5, 33.8)
    arrow(73.5, 40.5, 73.5, 33.8)

    box(6, 4, 88, 11, "结论边界：数值优选与时间结果限定于所测网格、场景与误差模型；\n"
                      "不宣称连续全局最优；正式测试未执行处明确标注为「未执行」",
        "#FFF8E1", PAL["secondary"], fs=8.4)
    arrow(50, 20, 50, 15.2)
    save(fig, "fig_roadmap")


# ---------------------------------------------------------------- F03 q1 states
def fig_q1_states():
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.9))

    def draw_wedge(ax, s, theta, alpha=1.0, length=60, color=PAL["primary"], ls="--"):
        for sign in (-1, 1):
            u = G.unit(theta + sign * alpha)
            ax.plot([s[0], s[0] + u[0] * length], [s[1], s[1] + u[1] * length],
                    ls=ls, color=color, lw=0.9)
        u0 = G.unit(theta)
        ax.plot([s[0], s[0] + u0[0] * length * 0.55], [s[1], s[1] + u0[1] * length * 0.55],
                ls=":", color=color, lw=0.8)
        ax.plot([s[0]], [s[1]], marker="s", ms=4.5, color=color)

    # (a) unbounded
    ax = axes[0]
    obs = [(-10, -8, 50)]
    r = G.intersection(obs)
    draw_wedge(ax, (-10, -8), 50, length=70)
    ax.text(0.5, 0.92, "(a) 单次观测：无界（区域＝闭楔形）", transform=ax.transAxes,
            ha="center", fontsize=8.6)
    ax.text(-2, 2, "直径 = ∞\n不做覆盖判别", fontsize=8.2, color=PAL["contrast"])
    ax.set_xlim(-30, 30); ax.set_ylim(-25, 30)

    # (b) bounded
    ax = axes[1]
    obs = [tuple(o) for o in [(359.5055815863, -115.3225120884, 162.7748154197),
                              (205.719778076, 700.2420960671, 253.516210017)]]
    r = G.intersection(obs)
    vs = r["vertices"]
    draw_wedge(ax, (obs[0][0], obs[0][1]), obs[0][2], length=130)
    draw_wedge(ax, (obs[1][0], obs[1][1]), obs[1][2], length=130, color=PAL["positive"])
    if vs:
        ax.add_patch(Polygon(vs, closed=True, fc=PAL["primary"], alpha=0.28, ec=PAL["primary"], lw=1.1))
    ax.plot([0], [0], marker="*", ms=9, color="black", zorder=5)
    ax.text(0.5, 0.92, "(b) 两次观测：有界多边形", transform=ax.transAxes, ha="center", fontsize=8.6)
    ax.text(0.5, 0.05, "直径 = 28.96681 m", transform=ax.transAxes, ha="center", fontsize=8.2,
            color=PAL["primary"])
    ax.set_xlim(-35, 35); ax.set_ylim(-35, 35)

    # (c) empty
    ax = axes[2]
    obs = [(0, 0, 0.0), (0, 30, 180.0)]
    r = G.intersection(obs)
    draw_wedge(ax, (0, 0), 0.0, length=42)
    draw_wedge(ax, (0, 30), 180.0, length=42, color=PAL["contrast"])
    ax.text(0.5, 0.92, "(c) 矛盾观测：空集", transform=ax.transAxes, ha="center", fontsize=8.6)
    ax.text(0.5, 0.05, "区域状态 = empty，报告不一致", transform=ax.transAxes, ha="center",
            fontsize=8.2, color=PAL["contrast"])
    ax.set_xlim(-25, 25); ax.set_ylim(-18, 42)

    for ax in axes:
        ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout()
    save(fig, "fig_q1_states")


# ---------------------------------------------------------------- F07 q2 region
def guaranteed_fixed1000(b, alpha=1.0):
    ang = math.degrees(math.atan2(b[1], b[0]))
    opposite = (ang + 360) % 360 - 180
    ts = [-alpha, alpha]
    if -alpha <= opposite <= alpha:
        ts.append(opposite)
    m = min(G.dot(b, G.unit(t)) for t in ts)
    return all(G.dot(b, b) + r * r - 2 * r * m <= 1000.0 ** 2 + 1e-7 for r in (5, 1000, 1500))


def fig_q2_region():
    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    step = 20
    pts_cond, pts_fix = [], []
    for ix in range(0, 1001, step):
        for iy in range(-800, 801, step):
            b = (ix, iy)
            if G.guaranteed(b):
                pts_cond.append(b)
            if guaranteed_fixed1000(b):
                pts_fix.append(b)
    pc = np.array(pts_cond); pf = np.array(pts_fix)
    ax.scatter(pc[:, 0] / 1000.0, pc[:, 1] / 1000.0, s=5, color=PAL["primary"],
               label="条件保证接收区 C（R≥max(1000,ρ)）", alpha=0.55)
    ax.scatter(pf[:, 0] / 1000.0, pf[:, 1] / 1000.0, s=3, color=PAL["secondary"],
               label="仅用R≥1000 m的保守区", alpha=0.95, marker="s", zorder=4)
    cand = load_csv(os.path.join(ROOT, "results", "q2_candidates.csv"))
    ax.scatter([float(r["local_x"]) / 1000 for r in cand], [float(r["local_y"]) / 1000 for r in cand],
               s=8, facecolors="none", edgecolors=PAL["neutral"], linewidths=0.4,
               label="50 m候选格点（483个）")
    ax.plot([0.8], [-0.6], marker="*", ms=13, color=PAL["contrast"], zorder=5,
            label="所选第二点 (800, -600) m")
    ax.plot([0.85], [-0.525], marker="D", ms=5, color=PAL["positive"], zorder=5,
            label="局部加密点 (850, -525) m")
    ax.set_xlabel("沿首次示向坐标 / km")
    ax.set_ylabel("横向坐标 / km")
    ax.set_xlim(-0.05, 1.05); ax.set_ylim(-0.85, 0.85)
    ax.legend(loc="upper left", frameon=False, fontsize=7.6)
    fig.tight_layout()
    save(fig, "fig_q2_region")


# ---------------------------------------------------------------- F10 comparison
def fig_q2_comparison():
    rows = load_csv(os.path.join(ROOT, "results", "q2_comparison.csv"))
    names = {"100,0": "沿示向前进 (100, 0)",
             "0,100": "纯横向 (0, 100)",
             "500,500": "斜向 (500, 500)",
             "750,300": "斜向 (750, 300)",
             "800,-600": "优选 (800, -600)"}
    labels, vals, ok = [], [], []
    for r in rows:
        key = "%s,%s" % (int(float(r["x"])), int(float(r["y"])))
        labels.append(names.get(key, key))
        vals.append(float(r["conditional_worst_m"]))
        ok.append(str(r["guaranteed_reception"]).lower() in ("true", "1", "yes"))
    order = np.argsort(vals)[::-1]
    labels = [labels[i] for i in order]; vals = [vals[i] for i in order]; ok = [ok[i] for i in order]
    colors = [PAL["primary"] if o else PAL["contrast"] for o in ok]
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    y = np.arange(len(vals))
    ax.barh(y, vals, color=colors, height=0.55)
    for i, (v, o) in enumerate(zip(vals, ok)):
        ax.text(v + 12, i, "%.2f m%s" % (v, "" if o else "（无接收保证，条件值）"),
                va="center", fontsize=8.2, color=PAL["dark"])
    ax.set_yticks(y, labels)
    ax.set_xlabel("有限场景最坏定位直径 / m")
    ax.set_xlim(0, 1560)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(fc=PAL["primary"], label="满足连续保证接收"),
                       Patch(fc=PAL["contrast"], label="不满足保证接收")],
              frameon=False, loc="upper right")
    fig.tight_layout()
    save(fig, "fig_q2_comparison")


# ---------------------------------------------------------------- F11 q3 coverage
def fig_q3_coverage():
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    R_arena, r_scan, R_c = 1800.0, 1200.0, 999.99
    ax.add_patch(Circle((0, 0), R_arena, fill=False, ec=PAL["neutral"], lw=1.0))
    angs = np.arange(0, 360, 60)
    for a in angs:
        p = (r_scan * math.cos(math.radians(a)), r_scan * math.sin(math.radians(a)))
        ax.add_patch(Circle(p, R_c, fill=False, ec=PAL["primary"], lw=0.7, alpha=0.55))
        ax.plot([p[0]], [p[1]], marker="^", ms=6, color=PAL["primary"], zorder=5)
    cosw = (r_scan ** 2 + R_arena ** 2 - R_c ** 2) / (2 * R_arena * r_scan)
    w = math.degrees(math.acos(max(-1, min(1, cosw))))
    th = np.linspace(0, 2 * math.pi, 721)
    ax.plot(R_arena * np.cos(th), R_arena * np.sin(th), color=PAL["secondary"], lw=2.6, alpha=0.85,
            solid_capstyle="butt")
    for a in angs:
        t = np.linspace(math.radians(a - w), math.radians(a + w), 60)
        ax.plot(R_arena * np.cos(t), R_arena * np.sin(t), color=PAL["positive"], lw=3.2,
                solid_capstyle="butt")
    ax.annotate("", xy=(0, 0), xytext=(r_scan * math.cos(math.radians(30)),
                                       r_scan * math.sin(math.radians(30))),
                arrowprops=dict(arrowstyle="<->", color=PAL["dark"], lw=0.9))
    ax.text(r_scan * 0.52 * math.cos(math.radians(30)) - 130,
            r_scan * 0.52 * math.sin(math.radians(30)) + 40, "r=1200 m（外圈半径）", fontsize=8.2)
    ax.text(760 * math.cos(math.radians(-58)), 760 * math.sin(math.radians(-58)) + 60,
            "覆盖半宽 ω\n相邻圆弧交叠", fontsize=8.2, color=PAL["positive"])
    ax.set_aspect("equal")
    ax.set_xlabel("东向坐标 / m"); ax.set_ylabel("北向坐标 / m")
    ax.set_xlim(-2050, 2050); ax.set_ylim(-2050, 2150)
    ax.set_xticks([-1800, -900, 0, 900, 1800]); ax.set_yticks([-1800, -900, 0, 900, 1800])
    ax.text(0, 1960, "6个外圈扫描点（▽）与1000 m接收圆；圆周弧段（绿）整周交叠覆盖",
            ha="center", fontsize=8.4, color=PAL["dark"])
    fig.tight_layout()
    save(fig, "fig_q3_coverage")


# ---------------------------------------------------------------- Q3 regenerated
def fig_q3_positions():
    tr = load_json(os.path.join(ROOT, "q3_ultimate200", "results", "trace_ultimate_random_1.json"))
    src = tr["sources"]
    fig, ax = plt.subplots(figsize=(5.6, 4.5))
    ax.add_patch(Circle((0, 0), 1800, fill=False, ec=PAL["neutral"], lw=0.9))
    ax.scatter([s["x"] for s in src], [s["y"] for s in src], s=34, color=PAL["primary"],
               label="合成干扰源（真值仅供离线绘图）")
    ax.plot([0], [0], marker="+", ms=11, mew=2, color=PAL["dark"], label="起点 (0, 0)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=2, frameon=False)
    ax.set_aspect("equal")
    ax.set_xlabel("东向坐标 / m"); ax.set_ylabel("北向坐标 / m")
    ax.set_xticks([-1500, 0, 1500]); ax.set_yticks([-1500, 0, 1500])
    fig.tight_layout()
    save(fig, "fig_q3_positions")


def fig_q3_routes():
    traces = {
        "上一版": (load_json(os.path.join(ROOT, "q3_ultimate200", "results", "trace_breakthrough_random_1.json")),
                   PAL["contrast"], "--"),
        "最终策略": (load_json(os.path.join(ROOT, "q3_ultimate200", "results", "trace_ultimate_random_1.json")),
                     PAL["primary"], "-"),
    }
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 4.3))
    src = None
    for ax, (name, (tr, col, ls)) in zip(axes, traces.items()):
        src = tr["sources"]
        ax.add_patch(Circle((0, 0), 1800, fill=False, ec=PAL["neutral"], lw=0.9))
        pts = [(0, 0)] + [(r["x"], r["y"]) for r in tr["trace"]]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=1.0, ls=ls)
        ax.scatter([s["x"] for s in src], [s["y"] for s in src], s=22, marker="x", color="black")
        ax.set_title("%s：%.2f km" % (name, tr["summary"]["distance_m"] / 1000.0), fontsize=9.5)
        ax.set_aspect("equal")
        ax.set_xlabel("东向坐标 / m")
        ax.set_xticks([-1500, 0, 1500]); ax.set_yticks([-1500, 0, 1500])
    axes[0].set_ylabel("北向坐标 / m")
    axes[1].set_yticklabels([])
    fig.tight_layout()
    save(fig, "fig_q3_routes")


def fig_q3_progress():
    traces = {
        "上一版": (load_json(os.path.join(ROOT, "q3_ultimate200", "results", "trace_breakthrough_random_1.json")),
                   PAL["contrast"], "--"),
        "最终策略": (load_json(os.path.join(ROOT, "q3_ultimate200", "results", "trace_ultimate_random_1.json")),
                     PAL["primary"], "-"),
    }
    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    ns = 0
    for name, (tr, col, ls) in traces.items():
        tt, nn = [0.0], [0]
        for r in tr["trace"]:
            if r["kind"] == "clear" and r["response"]["clear_result"] == "success":
                tt.append(r["virtual_time_s"]); nn.append(nn[-1] + 1)
        tt.append(tr["summary"]["virtual_time_s"]); nn.append(nn[-1])
        ns = max(ns, nn[-1])
        ax.step(np.array(tt) / 60.0, nn, where="post", color=col, ls=ls, label=name)
    ax.set_xlabel("虚拟时间 / min"); ax.set_ylabel("累计清除源数")
    ax.set_ylim(0, ns + 1); ax.set_xlim(0, None)
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    save(fig, "fig_q3_progress")


def fig_q3_paired():
    rows = load_json(os.path.join(ROOT, "q3_ultimate200", "results", "final_holdout.json"))
    a = [r for r in rows if r["algorithm"] == "breakthrough"]
    b = [r for r in rows if r["algorithm"] == "ultimate"]
    fig, ax = plt.subplots(figsize=(5.8, 4.4))
    ax.scatter([r["average_time_s"] for r in a], [r["average_time_s"] for r in b],
               s=16, alpha=0.65, color=PAL["primary"], edgecolors="none")
    lim = 350
    ax.plot([0, lim], [0, lim], ls="--", lw=0.9, color=PAL["neutral"])
    ax.text(0.72, 0.10, "对角线下方：最终策略更快", transform=ax.transAxes, fontsize=8.2,
            color=PAL["dark"])
    ax.set_xlabel("上一版 平均时间 / (s/源)"); ax.set_ylabel("最终策略 平均时间 / (s/源)")
    ax.set_xlim(150, lim); ax.set_ylim(150, lim)
    fig.tight_layout()
    save(fig, "fig_q3_paired")


def fig_q3_cost():
    rows = load_json(os.path.join(ROOT, "q3_ultimate200", "results", "final_holdout.json"))
    parts = [("移动", PAL["primary"]), ("检测", PAL["secondary"]),
             ("切换", PAL["neutral"]), ("清除", PAL["positive"])]
    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    left = np.zeros(2)
    names = ["上一版", "最终策略"]
    algos = ["breakthrough", "ultimate"]
    for pname, col in parts:
        vals = []
        for n in algos:
            rr = [r for r in rows if r["algorithm"] == n]
            total = sum(r["total"] for r in rr)
            if pname == "移动":
                v = sum(r["distance_m"] / 5.0 for r in rr) / total
            elif pname == "检测":
                v = sum(5.0 * r["measures"] for r in rr) / total
            elif pname == "切换":
                v = sum(r["switches"] for r in rr) / total
            else:
                v = sum(5.0 * r["cleared"] + 3.0 * (r["clear_attempts"] - r["cleared"]) for r in rr) / total
            vals.append(v)
        ax.barh([0, 1], vals, left=left, color=col, height=0.5, label=pname)
        left += vals
    for i, n in enumerate(algos):
        rr = [r for r in rows if r["algorithm"] == n]
        total = sum(r["total"] for r in rr)
        tot = sum(r["virtual_time_s"] for r in rr) / total
        ax.text(tot + 2, i, "合计 %.1f s/源" % tot, va="center", fontsize=8.2)
    ax.set_yticks([0, 1], names)
    ax.set_xlabel("平均时间 / (s/源)"); ax.set_xlim(0, 275)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=4, frameon=False)
    fig.tight_layout()
    save(fig, "fig_q3_cost")


def fig_q3_stress():
    rows = load_json(os.path.join(ROOT, "q3_ultimate200", "results", "final_stress.json"))
    order = ["bias", "cluster", "edge", "extreme", "minrange"]
    zh = {"bias": "固定偏差", "cluster": "外环聚簇", "edge": "圆周边缘",
          "extreme": "端点误差", "minrange": "最小半径"}
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    for j, (algo, marker, col, name) in enumerate([("breakthrough", "s", PAL["contrast"], "上一版"),
                                                   ("ultimate", "o", PAL["primary"], "最终策略")]):
        for i, g in enumerate(order):
            vals = [r["average_time_s"] for r in rows if r["stress"] == g and r["algorithm"] == algo]
            ax.scatter([i + (j - 0.5) * 0.24] * len(vals), vals, marker=marker, color=col,
                       s=20, alpha=0.7, label=name if i == 0 else None)
    ax.set_xticks(range(len(order)), [zh[g] for g in order])
    ax.set_xlabel("压力场景类型（每类10个配对场景）")
    ax.set_ylabel("平均时间 / (s/源)")
    ax.set_ylim(0, None)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    save(fig, "fig_q3_stress")


# ---------------------------------------------------------------- F18 q4 visibility
def fig_q4_visibility():
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6))

    ax = axes[0]
    g = np.array([600.0, 250.0]); delta = math.radians(60.0); R = 1200.0
    d = np.array([math.cos(delta), math.sin(delta)])
    n = np.array([-d[1], d[0]])
    quad = [g - d * 700 - n * 700, g + d * 1500 - n * 1500,
            g + d * 1500 + n * 1500, g - d * 700 + n * 700]
    ax.add_patch(Polygon(quad, closed=True, fc=PAL["primary"], alpha=0.10, ec="none"))
    ax.add_patch(Circle(g, R, fill=False, ec=PAL["neutral"], lw=0.9, ls="--"))
    ax.annotate("", xy=g + d * 650, xytext=g,
                arrowprops=dict(arrowstyle="-|>", color=PAL["dark"], lw=1.2))
    ax.text(*(g + d * 620 + n * 55), "定向方向 δ", fontsize=8.2)
    pts = [(np.array(g) + 500 * np.array(G.unit((math.degrees(delta) + 25))), PAL["positive"], "direction", (35, 20)),
           (np.array(g) + 520 * np.array(G.unit((math.degrees(delta) + 120))), PAL["contrast"], "no_signal\n(扇区外)", (-150, 30)),
           (np.array(g) + 1400 * np.array(G.unit((math.degrees(delta) - 30))), PAL["contrast"], "no_signal\n(超出半径)", (30, 35)),
           (np.array(g) + 3.0 * np.array(G.unit((math.degrees(delta) + 5))), PAL["secondary"], "near", (-110, -70))]
    for p, c, lab, off in pts:
        ax.plot([p[0]], [p[1]], marker="o", ms=5, color=c, zorder=5)
        ax.text(p[0] + off[0], p[1] + off[1], lab, fontsize=8.0, color=c)
    ax.add_patch(Circle(g, 5, fc=PAL["secondary"], ec="none", alpha=0.9))
    ax.plot([g[0]], [g[1]], marker="*", ms=12, color="black", zorder=6)
    ax.set_title("(a) 定向源可见性：距离≤R 且位于±90°扇区内", fontsize=8.6, loc="left")
    ax.set_xlim(-250, 2150); ax.set_ylim(-1250, 1750)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])

    ax = axes[1]
    ax.add_patch(Circle((0, 0), 1800, fill=False, ec=PAL["neutral"], lw=0.9))
    nodes = [(x, y) for x in range(-1800, 1801, 600) for y in range(-1800, 1801, 600)
             if math.hypot(max(-600, min(0, x)), max(-600, min(0, y))) <= 1800]
    ax.scatter([p[0] for p in nodes], [p[1] for p in nodes], s=10, color=PAL["primary"], zorder=4)
    x0, y0 = 600, 600
    ax.add_patch(Rectangle((x0, y0), 600, 600, fc=PAL["secondary"], alpha=0.22, ec=PAL["secondary"], lw=1.0))
    src = np.array([1030.0, 980.0]); dd = math.radians(250.0)
    ax.plot([src[0]], [src[1]], marker="*", ms=11, color="black", zorder=6)
    for c in [(x0, y0), (x0 + 600, y0), (x0 + 600, y0 + 600), (x0, y0 + 600)]:
        ax.plot([c[0]], [c[1]], marker="o", ms=4.5, color=PAL["dark"], zorder=5)
    vis = [(1200, 1200)]
    ax.plot([src[0], vis[0][0]], [src[1], vis[0][1]], ls="--", color=PAL["dark"], lw=0.9)
    ax.text(980, 1015, "≤848.53 m", fontsize=8.0, rotation=36)
    ax.set_title("(b) 600 m网格四角：每单元格至少有1个可见角点", fontsize=8.6, loc="left")
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])

    fig.tight_layout()
    save(fig, "fig_q4_visibility")


# ---------------------------------------------------------------- F19 q4 practice
def collect_q4():
    base = os.path.join(ROOT, "q4_五次演练汇总")
    runs = []
    for d in sorted(os.listdir(base)):
        fp = os.path.join(base, d)
        if not os.path.isdir(fp):
            continue
        s = load_json(os.path.join(fp, "summary.json"))
        off = None
        for f in os.listdir(fp):
            if f.endswith(".result.json"):
                off = load_json(os.path.join(fp, f))
        s["dir_frac"] = (off["directional_jammer_count"] / off["jammer_count"]) if off else None
        s["total_sources"] = off["jammer_count"] if off else None
        s["omni"] = off["omnidirectional_jammer_count"] if off else None
        s["dir"] = off["directional_jammer_count"] if off else None
        s["folder"] = d
        s["case_short"] = d.split("_", 1)[1].split("-")[0] if "_" in d else d
        runs.append(s)
    return runs


def fig_q4_practice():
    runs = collect_q4()
    codes = [r["case_short"] for r in runs]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.6))
    ax = axes[0]
    x = np.arange(len(runs)); wd = 0.38
    ax.bar(x - wd / 2, [r["total_sources"] for r in runs], width=wd, color="#D9D9D9",
           edgecolor=PAL["neutral"], label="官方总源数")
    ax.bar(x + wd / 2, [r["cleared"] for r in runs], width=wd, color=PAL["positive"],
           label="成功清除数")
    for i, r in enumerate(runs):
        ax.text(i, r["total_sources"] + 0.25, "%d/%d" % (r["cleared"], r["total_sources"]),
                ha="center", fontsize=7.8)
    ax.set_xticks(x, codes)
    ax.set_xlabel("演练案例编码（前缀）")
    ax.set_ylabel("干扰源个数")
    ax.set_ylim(0, 18)
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.15))

    ax = axes[1]
    xs = [r["dir"] for r in runs]
    ys = [r["average_time_s"] for r in runs]
    fs = [r["fallback_count"] for r in runs]
    sc = ax.scatter(xs, ys, s=[25 + 10 * f for f in fs], color=PAL["primary"], alpha=0.75,
                    edgecolors=PAL["dark"], zorder=4)
    for xx, yy, ff in zip(xs, ys, fs):
        ax.text(xx + 0.25, yy + 8, "回退%d次" % ff, fontsize=7.8)
    ax.set_xlabel("定向源个数（每场总源数12—15）")
    ax.set_ylabel("平均定位清除时间 / (s/源)")
    ax.set_xlim(0, 16)
    ax.set_ylim(950, 1520)
    fig.tight_layout()
    save(fig, "fig_q4_practice")


# ---------------------------------------------------------------- F20 q4 route/cost
def parse_client_positions(fp):
    events = []
    with open(fp, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("event") != "http":
                continue
            path = e.get("path")
            if path not in ("/measure", "/clear"):
                continue
            req = e.get("request", {})
            resp = e.get("response", {})
            events.append(dict(path=path, x=req.get("position", {}).get("x"),
                               y=req.get("position", {}).get("y"), channel=req.get("channel"),
                               result=resp.get("measure_result") or resp.get("clear_result"),
                               vt=resp.get("virtual_time_s")))
    return events


def fig_q4_route_cost():
    runs = collect_q4()
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 4.2))
    ax = axes[0]
    r3 = [r for r in runs if r["folder"].startswith("03_")][0]
    fp = os.path.join(ROOT, "q4_五次演练汇总", r3["folder"], "client.jsonl")
    ev = parse_client_positions(fp)
    xs = [e["x"] for e in ev]; ys = [e["y"] for e in ev]
    ax.add_patch(Circle((0, 0), 1800, fill=False, ec=PAL["neutral"], lw=0.9))
    ax.plot(xs, ys, color=PAL["primary"], lw=0.6, alpha=0.75)
    okp = [(e["x"], e["y"]) for e in ev if e["path"] == "/clear" and e["result"] == "success"]
    badp = [(e["x"], e["y"]) for e in ev if e["path"] == "/clear" and e["result"] != "success"]
    ax.scatter([p[0] for p in okp], [p[1] for p in okp], s=12, color=PAL["positive"],
               label="成功清除", zorder=5)
    ax.scatter([p[0] for p in badp], [p[1] for p in badp], s=8, marker="x",
               color=PAL["contrast"], alpha=0.7, label="失败试清（3 s/次）", zorder=5)
    ax.set_title("案例 HNA8（14个源全为定向源，条带回退9次）", fontsize=8.6)
    ax.legend(loc="lower left", frameon=False, fontsize=8, framealpha=0.9)
    ax.set_aspect("equal")
    ax.set_xlabel("东向坐标 / m"); ax.set_ylabel("北向坐标 / m")
    ax.set_xticks([-1500, 0, 1500]); ax.set_yticks([-1500, 0, 1500])

    ax = axes[1]
    names = {"移动": PAL["primary"], "检测": PAL["secondary"], "切换": PAL["neutral"], "清除": PAL["positive"]}
    table = []
    for r in runs:
        fp = os.path.join(ROOT, "q4_五次演练汇总", r["folder"], "client.jsonl")
        ev = parse_client_positions(fp)
        travel = 0.0
        prev = None
        switches = 0
        last_ch = None
        for e in ev:
            if prev is not None:
                travel += math.hypot(e["x"] - prev[0], e["y"] - prev[1])
            prev = (e["x"], e["y"])
            if e["path"] == "/measure":
                if last_ch is not None and e["channel"] != last_ch:
                    switches += 1
                last_ch = e["channel"]
        t_travel = travel / 5.0
        t_meas = 5.0 * r["measures"]
        t_clear = 5.0 * r["cleared"] + 3.0 * (r["clear_attempts"] - r["cleared"])
        t_switch = switches * 1.0
        t_total = r["virtual_time_s"]
        resid = t_total - (t_travel + t_meas + t_clear + t_switch)
        table.append((r["case_short"], t_travel, t_meas, t_switch, t_clear, resid))
    y = np.arange(len(table))
    left = np.zeros(len(table))
    vals = {"移动": [t[1] for t in table], "检测": [t[2] for t in table],
            "切换": [t[3] for t in table], "清除": [t[4] for t in table]}
    for k, v in vals.items():
        ax.barh(y, v, left=left, color=names[k], height=0.55, label=k)
        left += np.array(v)
    ax.set_yticks(y, [t[0] for t in table])
    ax.invert_yaxis()
    ax.set_xlabel("虚拟时间 / s")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), frameon=False, ncol=4, fontsize=8.5)
    fig.tight_layout()
    save(fig, "fig_q4_route_cost")


if __name__ == "__main__":
    tasks = [fig_roadmap, fig_q1_states, fig_q2_region, fig_q2_comparison, fig_q3_coverage,
             fig_q3_positions, fig_q3_routes, fig_q3_progress, fig_q3_paired, fig_q3_cost,
             fig_q3_stress, fig_q4_visibility, fig_q4_practice, fig_q4_route_cost]
    for t in tasks:
        try:
            t()
        except Exception:
            print("FAILED:", t.__name__)
            traceback.print_exc()
