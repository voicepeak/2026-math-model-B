"""Recompute statistics and nine evidence figures from actual paired records."""
import csv,json,math,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from benchmark import Fixture
from utils.plot_style import apply_publication_style,audit_layout,audit_design,_save_grayscale_preview
from utils.export_figure import export_figure
from utils.profile_data import profile_data,render_report

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'results'; FIG=ROOT/'figures'
COLORS={'breakthrough':'#D55E00','ultimate':'#0072B2'}
LABELS={'breakthrough':'Breakthrough','ultimate':'Ultimate candidate'}
def load(name):return json.loads((OUT/(name+'.json')).read_text(encoding='utf-8'))
def dump(name,x):(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def aggregate(rr):
    n=sum(r['total'] for r in rr);tt=sum(r['virtual_time_s'] for r in rr)
    return dict(cases=len(rr),sources=n,cleared=sum(r['cleared'] for r in rr),seconds=tt,
                seconds_per_source=tt/n,under200=sum(r['average_time_s']<=200 for r in rr),
                distance_m=sum(r['distance_m'] for r in rr),measures=sum(r['measures'] for r in rr),
                failed_clears=sum(r['clear_attempts']-r['cleared'] for r in rr),
                fallback=sum(r['fallback_count'] for r in rr),worst=max(r['average_time_s'] for r in rr),
                max_runtime_s=max(r['runtime_s'] for r in rr))
def stats(rows):
    by={n:aggregate([r for r in rows if r['algorithm']==n]) for n in COLORS}
    old={(r['stress'],r['seed']):r for r in rows if r['algorithm']=='breakthrough'}
    new={(r['stress'],r['seed']):r for r in rows if r['algorithm']=='ultimate'}
    assert old.keys()==new.keys()
    kk=sorted(old)
    assert all(old[k]['cleared']==new[k]['cleared']==new[k]['total']==old[k]['total'] for k in kk)
    a=np.array([old[k]['virtual_time_s'] for k in kk]);b=np.array([new[k]['virtual_time_s'] for k in kk])
    rng=np.random.default_rng(20260912);idx=rng.integers(0,len(kk),(4000,len(kk)))
    by['improvement']=1-b.sum()/a.sum()
    by['bootstrap_95pct']=np.quantile(1-b[idx].sum(axis=1)/a[idx].sum(axis=1),[.025,.975]).tolist()
    by['wins']=int((b<a).sum());by['ties']=int((abs(b-a)<1e-7).sum())
    by['worst_regressions']=[dict(stress=k[0],seed=k[1],baseline=old[k]['average_time_s'],candidate=new[k]['average_time_s'],
                                  increase_s_per_source=new[k]['average_time_s']-old[k]['average_time_s'])
                              for k in sorted(kk,key=lambda k:new[k]['average_time_s']-old[k]['average_time_s'],reverse=True)[:10]]
    return by
def figure(w=6.4,h=4.3):
    fig,ax=plt.subplots(figsize=(w,h));fig.subplots_adjust(left=.14,right=.96,bottom=.17,top=.89);return fig,ax
def save(fig,name):
    issues=audit_layout(fig)+audit_design(fig)
    if issues:raise ValueError(name+': '+';'.join(issues))
    export_figure(fig,str(FIG/name),formats=['svg','png'],dpi=300,tight=False,grayscale_preview=False)
    _save_grayscale_preview(FIG/(name+'.png'),300);plt.close(fig)
def arena(ax):
    ax.add_patch(Circle((0,0),1800,fill=False,edgecolor='.6',lw=.7))
    ax.set(xlim=(-1950,1950),ylim=(-1950,1950),xlabel='East (m)',ylabel='North (m)')
    ax.set_aspect('equal');ax.set_xticks([-1500,0,1500]);ax.set_yticks([-1500,0,1500])
def lower_bound(sources):
    pts=[(0,0)]+[(s['x'],s['y']) for s in sources];remaining=set(range(1,len(pts)));best={i:math.dist(pts[0],pts[i]) for i in remaining};mst=0.
    while remaining:
        j=min(remaining,key=lambda i:best[i]);mst+=best[j];remaining.remove(j)
        for i in remaining:best[i]=min(best[i],math.dist(pts[j],pts[i]))
    n=len(sources);return max(0,mst-40*n)/(5*n)+5

def main():
    sets={n:load('final_'+n) for n in ('development','stress','holdout')}
    rows=[r for rr in sets.values() for r in rr];metrics={n:stats(rr) for n,rr in sets.items()}
    metrics['all']=stats(rows)
    metrics['stress_groups']={s:stats([r for r in sets['stress'] if r['stress']==s]) for s in sorted({r['stress'] for r in sets['stress']})}
    metrics['holdout_by_count']={str(n):stats([r for r in sets['holdout'] if r['total']==n]) for n in sorted({r['total'] for r in sets['holdout']})}
    experiments=[]
    for f in ('prototype_v1','screening','screening2','screening3','screening4','development_more','combo_development'):
        if (OUT/(f+'.json')).exists():
            rr=load(f)
            experiments.extend(dict(batch=f,algorithm='prototype_v1' if f=='prototype_v1' and n=='ultimate' else n,
                                    **aggregate([r for r in rr if r['algorithm']==n])) for n in sorted({r['algorithm'] for r in rr}))
    metrics['research_batches']=experiments
    dump('comparison_metrics.json',metrics)
    fields=['algorithm','stress','seed','total','cleared','virtual_time_s','average_time_s','distance_m','measures','switches','clear_attempts','fallback_count','runtime_s']
    with (OUT/'analysis_data.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    info=profile_data(str(OUT/'analysis_data.csv'),group_cols=['algorithm','stress'])
    (OUT/'数据剖析.md').write_text(render_report(info),encoding='utf-8')
    apply_publication_style(language='en',width='report')
    plt.rcParams.update({'font.size':9,'axes.labelsize':10,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,
                         'svg.fonttype':'none','figure.constrained_layout.use':False,'figure.autolayout':False})
    traces={n:load('trace_'+n+'_random_1') for n in COLORS};sources=traces['ultimate']['sources']
    fig,ax=figure();arena(ax)
    ax.scatter([s['x'] for s in sources],[s['y'] for s in sources],s=30,color=COLORS['ultimate'],label='Synthetic sources')
    ax.scatter([0],[0],s=55,marker='+',color='black',label='Start');ax.legend(frameon=False,loc='upper center',bbox_to_anchor=(.5,1.16),ncol=2)
    save(fig,'raw_q3_positions')
    all_sources=[]
    for r in sets['holdout']:
        if r['algorithm']=='ultimate':all_sources.extend(Fixture(r['seed'],r['total']).initial)
    fig,ax=figure();ax.hist([s['radius'] for s in all_sources],bins=np.linspace(1000,1500,11),color=COLORS['ultimate'],edgecolor='white')
    ax.set(xlabel='Reception radius (m)',ylabel='Synthetic source count',xlim=(990,1510));save(fig,'raw_q3_ranges')
    fig,ax=figure()
    for stress,seed,marker,col in [('random',1,'o','#0072B2'),('edge',101,'s','#D55E00'),('cluster',101,'^','#009E73')]:
        tr=load(f'trace_ultimate_{stress}_{seed}');pts=[(s['x'],s['y']) for s in tr['sources']]
        ax.scatter([math.hypot(*p) for p in pts],[min(math.dist(p,q) for q in pts if q!=p) for p in pts],marker=marker,color=col,label=stress,s=27)
    ax.set(xlabel='Source distance from origin (m)',ylabel='Nearest-source distance (m)',ylim=(0,None));ax.legend(frameon=False);save(fig,'raw_q3_spacing')
    fig,axes=plt.subplots(1,2,figsize=(8,4.4));fig.subplots_adjust(left=.08,right=.98,bottom=.17,top=.88,wspace=.32)
    for ax,(n,tr) in zip(axes,traces.items()):
        arena(ax);pts=[(0,0)]+[(r['x'],r['y']) for r in tr['trace']]
        ax.plot(*zip(*pts),color=COLORS[n],lw=.9,ls='--' if n=='breakthrough' else '-')
        ax.scatter([s['x'] for s in sources],[s['y'] for s in sources],s=20,marker='x',color='black')
        ax.set_title(f'{LABELS[n]}: {tr["summary"]["distance_m"]/1000:.2f} km',fontsize=10)
    save(fig,'process_q3_routes')
    fig,ax=figure()
    for n,tr in traces.items():
        tt=[0.];nn=[0]
        for r in tr['trace']:
            if r['kind']=='clear' and r['response']['clear_result']=='success':tt.append(r['virtual_time_s']);nn.append(nn[-1]+1)
        tt.append(tr['summary']['virtual_time_s']);nn.append(nn[-1])
        ax.step(tt,nn,where='post',label=LABELS[n],color=COLORS[n],ls='--' if n=='breakthrough' else '-')
    ax.set(xlabel='Virtual time (s)',ylabel='Cleared sources',ylim=(0,len(sources)+1),xlim=(0,None));ax.legend(frameon=False,loc='lower right');save(fig,'process_q3_progress')
    fig,ax=figure();tr=load('trace_ultimate_minrange_101');truth={s['channel']:(s['x'],s['y']) for s in tr['sources']}
    for success,marker,col,label in [(True,'o','#0072B2','Successful clear'),(False,'x','#D55E00','Optical trial missed')]:
        rr=[(i,r) for i,r in enumerate(tr['trace']) if r['kind']=='clear' and (r['response']['clear_result']=='success')==success]
        ax.scatter([i for i,r in rr],[math.dist((r['x'],r['y']),truth[r['channel']]) for i,r in rr],marker=marker,color=col,s=32,label=label)
    ax.axhline(20,color='.4',ls='--',lw=.8,label='20 m clearing limit')
    ax.set(xlabel='Action index (minrange, seed 101)',ylabel='Clear point to true source (m)',ylim=(0,None));ax.legend(frameon=False,loc='upper center',bbox_to_anchor=(.5,1.10),ncol=3);save(fig,'process_q3_clearance')
    fig,ax=figure();rr=sets['holdout'];a=[r for r in rr if r['algorithm']=='breakthrough'];b=[r for r in rr if r['algorithm']=='ultimate']
    ax.scatter([r['average_time_s'] for r in a],[r['average_time_s'] for r in b],s=20,alpha=.7,color=COLORS['ultimate'])
    lim=math.ceil(max(r['average_time_s'] for r in rr)/50)*50
    ax.plot([0,lim],[0,lim],ls='--',lw=.8,color='.4');ax.set(xlabel='Breakthrough time per source (s)',ylabel='Candidate time per source (s)',xlim=(0,lim),ylim=(0,lim));save(fig,'result_q3_paired')
    fig,ax=figure();fig.subplots_adjust(left=.25);left=np.zeros(2)
    for part,col in [('Travel','#0072B2'),('Measure','#E69F00'),('Switch','#777777'),('Clear','#009E73')]:
        vals=[]
        for n in COLORS:
            rr=[r for r in sets['holdout'] if r['algorithm']==n];total=sum(r['total'] for r in rr)
            vals.append(sum(r['distance_m']/5 if part=='Travel' else 5*r['measures'] if part=='Measure' else r['switches'] if part=='Switch' else 5*r['cleared']+3*(r['clear_attempts']-r['cleared']) for r in rr)/total)
        ax.barh([0,1],vals,left=left,label=part,color=col,height=.5);left+=vals
    ax.set_yticks([0,1],list(LABELS.values()));ax.set(xlabel='Time per source (s)',xlim=(0,None));ax.legend(frameon=False,loc='upper center',bbox_to_anchor=(.5,1.08),ncol=4);save(fig,'result_q3_cost')
    fig,ax=figure(7.4,4.5);groups=list(metrics['stress_groups'])
    for j,n in enumerate(COLORS):
        for i,g in enumerate(groups):
            vals=[r['average_time_s'] for r in sets['stress'] if r['stress']==g and r['algorithm']==n]
            ax.scatter([i+(j-.5)*.24]*len(vals),vals,marker='s' if j==0 else 'o',color=COLORS[n],s=18,alpha=.65,label=LABELS[n] if i==0 else None)
    ax.set_xticks(range(len(groups)),groups);ax.set(xlabel='Synthetic stress family (10 paired cases each)',ylabel='Time per source (s)',ylim=(0,None));ax.legend(frameon=False,loc='upper left');save(fig,'result_q3_stress')
    bounds=[]
    for r in rows:
        if r['algorithm']=='ultimate':
            ss=Fixture(r['seed'],r['total'],r['stress']).initial
            bounds.append(dict(seed=r['seed'],stress=r['stress'],sources=r['total'],mst_lower_s=lower_bound(ss),actual_s=r['average_time_s']))
    dump('offline_lower_bounds.json',bounds)
    lines=['# 第三问200秒探索：实测结果','', '所有数值来自本地合成场景；官方测试未执行。200秒/源为探索目标，未作为停止或漏扫条件。','', '|集合|场景|目标|基准秒/源|候选秒/源|改善|胜出|','|---|---:|---:|---:|---:|---:|---:|']
    for n in ('development','stress','holdout','all'):
        m=metrics[n];a=m['breakthrough'];b=m['ultimate'];lines.append(f'|{n}|{b["cases"]}|{b["sources"]}|{a["seconds_per_source"]:.3f}|{b["seconds_per_source"]:.3f}|{100*m["improvement"]:.2f}%|{m["wins"]}/{b["cases"]}|')
    m=metrics['holdout'];lines+=['',f'新留出集为20001..20100：全清{m["ultimate"]["cleared"]}/{m["ultimate"]["sources"]}；不超过200秒/源的场景{m["ultimate"]["under200"]}/100。配对场景bootstrap改善95%区间{[round(100*x,2) for x in m["bootstrap_95pct"]]}%。区间只描述合成分布中的抽样不确定性。','', '## 留出集最差退化案例','', '|seed|基准|候选|增加秒/源|','|---|---:|---:|---:|']
    for r in m['worst_regressions']:lines.append(f'|{r["seed"]}|{r["baseline"]:.3f}|{r["candidate"]:.3f}|{r["increase_s_per_source"]:.3f}|')
    lines+=['','## 按源数量分层（全部留出组）','','|每局源数|场景数|基准秒/源|候选秒/源|','|---|---:|---:|---:|']
    for n,x in metrics['holdout_by_count'].items():
        lines.append(f'|{n}|{x["ultimate"]["cases"]}|{x["breakthrough"]["seconds_per_source"]:.3f}|{x["ultimate"]["seconds_per_source"]:.3f}|')
    lines+=['','## 压力分组（不删除退化类别）','','|类型|源数|基准秒/源|候选秒/源|','|---|---:|---:|---:|']
    for n,x in metrics['stress_groups'].items():
        lines.append(f'|{n}|{x["ultimate"]["sources"]}|{x["breakthrough"]["seconds_per_source"]:.3f}|{x["ultimate"]["seconds_per_source"]:.3f}|')
    lines+=['',f'冻结版新留出平均为{m["ultimate"]["seconds_per_source"]:.3f}秒/源，'+('达到' if m['ultimate']['seconds_per_source']<=200 else '尚未达到')+'整体200秒/源目标；分层均值或单个优秀案例不能替代整体结果。']
    lines+=['','## 未达到目标的边界','', '不能把中心访问路线的启发式解称为理论下界。这里单独以原点和真实源中心的MST构造保守下界：每源允许20m清除半径，L≥max(0,MST−40N)，T/N≥L/(5N)+5。真值只用于离线诊断，算法不读取。详见results/offline_lower_bounds.json。','', '## 研究批次（全部保留）','', '|批次|算法|场景|秒/源|','|---|---|---:|---:|']
    for r in experiments:lines.append(f'|{r["batch"]}|{r["algorithm"]}|{r["cases"]}|{r["seconds_per_source"]:.3f}|')
    lines+=['', '详见研究记录.md、图表契约.md、results/复现清单.json与P1/P2独立回执。线上算法只需Python标准库；完整图表复现需numpy、pandas、matplotlib与Pillow。正式测试次数未消耗。']
    (ROOT/'探索结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':main()
