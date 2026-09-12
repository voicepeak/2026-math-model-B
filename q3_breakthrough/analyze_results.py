"""Build auditable comparison metrics, report and nine evidence figures."""
import csv, json, math, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from benchmark import Fixture
from utils.plot_style import apply_publication_style, export_figure

HERE = Path(__file__).resolve().parent
OUT = HERE/'results'
FIG = HERE/'figures'
COLORS = {'gemini': '#D55E00', 'breakthrough': '#0072B2'}
LABELS = {'gemini': 'Gemini', 'breakthrough': 'New strategy'}

def load(name):
    return json.loads((OUT/(name+'.json')).read_text(encoding='utf-8'))

def stats(rows):
    by = {}
    for name in ('gemini', 'breakthrough'):
        rr = [r for r in rows if r['algorithm'] == name]
        by[name] = dict(cases=len(rr), sources=sum(r['total'] for r in rr),
                        cleared=sum(r['cleared'] for r in rr),
                        total_time=sum(r['virtual_time_s'] for r in rr),
                        avg=sum(r['virtual_time_s'] for r in rr)/sum(r['total'] for r in rr),
                        distance=sum(r['distance_m'] for r in rr),
                        measures=sum(r['measures'] for r in rr),
                        worst=max(r['average_time_s'] for r in rr),
                        fallback=sum(r['fallback_count'] for r in rr),
                        max_runtime=max(r['runtime_s'] for r in rr))
    old = {(r['stress'],r['seed']):r for r in rows if r['algorithm']=='gemini'}
    new = {(r['stress'],r['seed']):r for r in rows if r['algorithm']=='breakthrough'}
    assert old.keys() == new.keys()
    keys = sorted(old)
    assert all(old[k]['total']==new[k]['total']==new[k]['cleared']==old[k]['cleared'] for k in keys)
    by['reduction'] = 1-by['breakthrough']['total_time']/by['gemini']['total_time']
    by['wins'] = sum(new[k]['virtual_time_s']<old[k]['virtual_time_s'] for k in keys)
    by['worst_pair_reduction'] = min(1-new[k]['virtual_time_s']/old[k]['virtual_time_s'] for k in keys)
    rng = np.random.default_rng(20260911)
    indices = rng.integers(0,len(keys),size=(4000,len(keys)))
    a = np.array([old[k]['virtual_time_s'] for k in keys])
    b = np.array([new[k]['virtual_time_s'] for k in keys])
    boot = 1-b[indices].sum(axis=1)/a[indices].sum(axis=1)
    by['paired_bootstrap_95pct'] = np.quantile(boot,[.025,.975]).tolist()
    return by

def newfig(w=6.2,h=4.2):
    fig,ax=plt.subplots(figsize=(w,h))
    fig.subplots_adjust(left=.14,right=.96,bottom=.16,top=.91)
    return fig,ax

def save(fig,name):
    export_figure(fig,FIG/name,dpi=300)
    plt.close(fig)

def arena(ax):
    ax.add_patch(Circle((0,0),1800,fill=False,edgecolor='.5',linewidth=.7))
    ax.set(xlim=(-1950,1950),ylim=(-1950,1950),xlabel='East (m)',ylabel='North (m)')
    ax.set_aspect('equal')
    ax.set_xticks([-1500,0,1500]); ax.set_yticks([-1500,0,1500])

def main():
    sets = {name:load(name) for name in ('paired_random','stress','holdout')}
    rows = [r for rr in sets.values() for r in rr]
    metrics = {name:stats(rr) for name,rr in sets.items()}
    metrics['all'] = stats(rows)
    metrics['stress_groups'] = {s:stats([r for r in sets['stress'] if r['stress']==s])
                                for s in sorted({r['stress'] for r in sets['stress']})}
    ar=load('ablation')+[r for r in sets['paired_random'] if r['seed']<=20 and r['algorithm']=='breakthrough']
    metrics['ablation']={name:sum(r['virtual_time_s'] for r in ar if r['algorithm']==name)/sum(r['total'] for r in ar if r['algorithm']==name)
                         for name in ('no_shared','fixed_cover','breakthrough')}
    originals=load('original')+[r for r in sets['paired_random'] if r['seed']<=10]
    metrics['three_generations']={name:sum(r['virtual_time_s'] for r in originals if r['algorithm']==name)/sum(r['total'] for r in originals if r['algorithm']==name)
                                 for name in ('original','gemini','breakthrough')}
    (OUT/'comparison_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    columns=['seed','stress','algorithm','total','cleared','virtual_time_s','average_time_s','distance_m','measures','switches','clear_attempts','fallback_count']
    with (OUT/'analysis_data.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,columns,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    apply_publication_style(language='en',width='report')
    plt.rcParams.update({'font.size':9,'axes.labelsize':10,'xtick.labelsize':8,'ytick.labelsize':8,
                         'legend.fontsize':8,'svg.fonttype':'none',
                         'figure.constrained_layout.use':False,'figure.autolayout':False})
    traces={n:load(f'trace_{n}_random_1') for n in COLORS}
    sources=traces['breakthrough']['sources']
    fig,ax=newfig(); arena(ax)
    ax.scatter([s['x'] for s in sources],[s['y'] for s in sources],s=32,color=COLORS['breakthrough'],label='Synthetic sources')
    ax.scatter([0],[0],marker='+',s=65,color='black',label='Start')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,1.13),ncol=2,frameon=False)
    save(fig,'raw_q3_positions')

    all_sources=[]
    for r in sets['paired_random']:
        if r['algorithm']=='breakthrough': all_sources += Fixture(r['seed'],r['total']).initial
    fig,ax=newfig()
    ax.hist([s['radius'] for s in all_sources],bins=np.linspace(1000,1500,11),color=COLORS['breakthrough'],edgecolor='white')
    ax.set(xlabel='Reception radius (m)',ylabel='Number of synthetic sources',xlim=(990,1510))
    save(fig,'raw_q3_ranges')

    fig,ax=newfig()
    for stress,marker,color in [('random','o','#0072B2'),('edge','s','#D55E00'),('cluster','^','#009E73')]:
        tr=load('trace_breakthrough_'+stress+'_'+('1' if stress=='random' else '101'))
        pts=[(s['x'],s['y']) for s in tr['sources']]
        ax.scatter([math.hypot(*p) for p in pts],[min(math.dist(p,q) for q in pts if q!=p) for p in pts],
                   s=30,marker=marker,color=color,label=stress.capitalize())
    ax.set(xlabel='Distance to origin (m)',ylabel='Nearest-source distance (m)',ylim=(0,None))
    ax.legend(frameon=False); save(fig,'raw_q3_spacing')

    fig,axes=plt.subplots(1,2,figsize=(8,4.4)); fig.subplots_adjust(left=.08,right=.98,bottom=.16,top=.88,wspace=.32)
    for ax,(name,tr) in zip(axes,traces.items()):
        arena(ax); pts=[(0,0)]+[(r['x'],r['y']) for r in tr['trace']]
        ax.plot(*zip(*pts),color=COLORS[name],lw=.9,ls='--' if name=='gemini' else '-')
        ax.scatter([s['x'] for s in sources],[s['y'] for s in sources],color='black',marker='x',s=20)
        ax.set_title(f'{LABELS[name]}: {tr["summary"]["distance_m"]/1000:.2f} km',fontsize=10)
    save(fig,'process_q3_routes')

    fig,ax=newfig()
    for name,tr in traces.items():
        tt=[0.]; nn=[0]
        for row in tr['trace']:
            if row['kind']=='clear' and row['response']['clear_result']=='success':
                tt.append(row['virtual_time_s']); nn.append(nn[-1]+1)
        tt.append(tr['summary']['virtual_time_s']); nn.append(nn[-1])
        ax.step(tt,nn,where='post',lw=1.5,color=COLORS[name],ls='--' if name=='gemini' else '-',label=LABELS[name])
        ax.scatter([tt[-1]],[nn[-1]],marker='s' if name=='gemini' else 'o',color=COLORS[name],s=28)
    ax.set(xlabel='Virtual time (s)',ylabel='Cleared sources',ylim=(0,len(sources)+1),xlim=(0,None))
    ax.legend(frameon=False,loc='lower right'); save(fig,'process_q3_progress')

    cert=traces['breakthrough']['certificates']
    fig,ax=newfig()
    ax.scatter(range(1,len(cert)+1),[c['radius'] for c in cert],color=COLORS['breakthrough'],s=32)
    ax.axhline(19.9,color='.35',ls='--',lw=1,label='Certified limit: 19.9 m')
    ax.set(xlabel='Certified clearance index',ylabel='Enclosing radius (m)',ylim=(0,23))
    ax.legend(frameon=False,loc='lower right'); save(fig,'process_q3_certification')

    old={(r['stress'],r['seed']):r for r in rows if r['algorithm']=='gemini'}
    new={(r['stress'],r['seed']):r for r in rows if r['algorithm']=='breakthrough'}
    fig,ax=newfig()
    for group,marker,color in [('random','o','#0072B2'),('stress','^','#D55E00')]:
        kk=[k for k in old if (k[0]=='random')==(group=='random')]
        ax.scatter([old[k]['average_time_s'] for k in kk],[new[k]['average_time_s'] for k in kk],
                   marker=marker,s=18,alpha=.75,color=color,label=group.capitalize())
    limit=math.ceil(max(r['average_time_s'] for r in rows)/100)*100
    ax.plot([0,limit],[0,limit],ls='--',color='.4',lw=.9)
    ax.set(xlabel='Gemini time per source (s)',ylabel='New time per source (s)',xlim=(0,limit),ylim=(0,limit))
    ax.legend(frameon=False,loc='upper left'); save(fig,'result_q3_paired')

    fig,ax=newfig()
    parts=[('Travel','#0072B2'),('Measure','#E69F00'),('Switch','#777777'),('Clear','#009E73')]
    left=np.zeros(2)
    for part,color in parts:
        vals=[]
        for name in COLORS:
            rr=[r for r in sets['holdout'] if r['algorithm']==name]; total=sum(r['total'] for r in rr)
            val=sum(r['distance_m']/5 if part=='Travel' else 5*r['measures'] if part=='Measure' else r['switches'] if part=='Switch' else 5*r['cleared']+3*(r['clear_attempts']-r['cleared']) for r in rr)/total
            vals.append(val)
        ax.barh([0,1],vals,left=left,label=part,color=color,height=.5)
        left+=vals
    ax.set(yticks=[0,1],yticklabels=['Gemini','New strategy'],xlabel='Weighted time per source (s)',xlim=(0,max(left)*1.08))
    ax.legend(frameon=False,ncol=4,loc='upper center',bbox_to_anchor=(.5,1.13))
    save(fig,'result_q3_cost')

    fig,ax=newfig(); groups=['random','edge','cluster','minrange','bias','extreme']
    for i,g in enumerate(groups):
        kk=[k for k in old if k[0]==g]
        yy=[100*(1-new[k]['virtual_time_s']/old[k]['virtual_time_s']) for k in kk]
        jitter=np.linspace(-.18,.18,len(yy))
        ax.scatter(i+jitter,yy,s=15,color=COLORS['breakthrough'],alpha=.7)
    ax.axhline(0,color='.4',ls='--',lw=.8)
    ax.set(xticks=range(len(groups)),xticklabels=['Random','Edge','Cluster','R=1000','Fixed bias','Extreme'],ylabel='Time reduction per paired case (%)')
    save(fig,'result_q3_stress')

    lines=['# 第三问算法突破：实测结果','',
           '所有下列成绩来自本地合成配对测试；尚未进行新版官方演练或正式测试。', '',
           '| 数据集 | 场景数 | 目标总数/每策略 | Gemini 秒/源 | 新版 秒/源 | 总时间降低 | 新版胜出局数 |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for name,label in [('paired_random','改进阶段随机集'),('stress','压力集'),('holdout','独立留出随机集'),('all','合计')]:
        m=metrics[name]; b=m['breakthrough']; o=m['gemini']
        lines.append(f'| {label} | {b["cases"]} | {b["sources"]} | {o["avg"]:.2f} | {b["avg"]:.2f} | {m["reduction"]:.2%} | {m["wins"]}/{b["cases"]} |')
    h=metrics['holdout']; ci=h['paired_bootstrap_95pct']
    lines += ['', '消融（相同seeds1—20）：']
    for name,val in metrics['ablation'].items():
        lines.append(f'- {name}：{val:.2f}秒/源。')
    lines += ['', '三代算法（相同seeds1—10）：']
    for name,val in metrics['three_generations'].items():
        lines.append(f'- {name}：{val:.2f}秒/源。')
    lines += ['',f'留出集按场景配对 bootstrap 4000次，种子20260911，总时间相对降低的95%百分位区间：{ci[0]:.2%}—{ci[1]:.2%}。该区间只描述本合成生成器，不外推为官方成绩保证。',
              '', '| 压力类型 | Gemini 秒/源 | 新版 秒/源 | 降低 | 最差配对降低 |', '|---|---:|---:|---:|---:|']
    for name,m in metrics['stress_groups'].items():
        lines.append(f'| {name} | {m["gemini"]["avg"]:.2f} | {m["breakthrough"]["avg"]:.2f} | {m["reduction"]:.2%} | {m["worst_pair_reduction"]:.2%} |')
    lines += ['', '压力定义：edge为1799.9米圆周、接收半径1000米；cluster为外环紧簇；minrange为全部接收半径1000米；bias为每频道固定±1°误差；extreme为各位置误差取±1°端点。其余采用面积均匀位置、1000—1500米接收半径、固定空间散列误差场。源数按预定种子生成10—16个。',
              '', '算法变化：持久化全部已知目标的楔形交会区域；测点停靠时共享有用方位；将清除目标与未访问的六边形扫描点统一作开放路径最近邻和2-opt滚动规划；首次单方位采用(前进300米、侧移±75米)短基线，减少近源过冲；保留19.9米包围圆认证、near直接清除、条带完整回退。',
              '', '没有目标总数或源坐标泄漏。无信号不能等价于该频道不存在；尚未发现的频道在所有覆盖节点扫描。10—15个目标须完整覆盖且清空已知轨迹，16个可按题定上界提前结束。六边形1200米半径给出最大检测距离968.901572米，覆盖圆域内全部可能目标。',
              '', '旧Gemini文件夹保持原样。原官方五次日志仅是历史参考，不能与不同场景的本地新版成绩作严格配对。官方演练总源数需要从结束界面/官方结果中核对，summary中的official_total_sources为空不能当作100%官方清除证明。',
              '', '主要限制：路线是在线启发式，未证明时间全局最优；未发现位置分布在官方模拟器中可能不同。新版仅支持q3，不能用于有定向源的q4。完整合成验证、HTTP模拟器通过也不能替代官方演练。',
              '', '逐局明细、时间分解和证书见 results/*.csv、comparison_metrics.json、trace_*.json；九张图的范围和统计口径见图表契约.md。']
    (HERE/'突破结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(metrics['all'],indent=2))

if __name__=='__main__': main()
