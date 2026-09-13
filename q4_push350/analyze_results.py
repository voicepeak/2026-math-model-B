"""Recompute tables and nine audited figures from frozen per-case outputs."""
import csv,json,math,hashlib,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[2]/'work'/'mplconfig'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from utils.plot_style import apply_publication_style,export_figure,PALETTE
from ring_certificate import verify_ring
HERE=Path(__file__).resolve().parent
BLUE=PALETTE['primary'];ORANGE=PALETTE['secondary']

def read(name):return json.loads((HERE/'results'/name).read_text(encoding='utf-8'))
def weighted(rr):return sum(r['virtual_time_s'] for r in rr)/sum(r['total'] for r in rr)
def paired(rows):
    by={}
    for r in rows:
        key=(r['dataset'],r['stress'],r['seed']);by.setdefault(key,{})
        if r['algorithm'] in by[key]:raise ValueError('Duplicate paired row')
        by[key][r['algorithm']]=r
        assert r['cleared']==r['actual_cleared']==r['total'] and r['status'].startswith('complete')
        assert math.isfinite(r['virtual_time_s'])
        expected=r['distance_m']/5+r['measures']*5+r['switches']+r['cleared']*5+r['failed_clears']*3
        assert abs(expected-r['virtual_time_s'])<1e-6
    assert all(set(v)=={'original','candidate'} and v['original']['total']==v['candidate']['total'] for v in by.values())
    return list(by.values())
def metric(rows):
    pairs=paired(rows);a=[p['original'] for p in pairs];b=[p['candidate'] for p in pairs]
    return dict(scenarios=len(pairs),sources=sum(r['total'] for r in b),baseline_s_per_source=weighted(a),
                candidate_s_per_source=weighted(b),reduction_percent=100*(1-weighted(b)/weighted(a)),
                wins=sum(y['virtual_time_s']<x['virtual_time_s'] for x,y in zip(a,b)),
                candidate_max_local_wall_s=max(r['local_pipeline_wall_s'] for r in b),
                baseline_failed_clears=sum(r['failed_clears'] for r in a),candidate_failed_clears=sum(r['failed_clears'] for r in b))
def save(fig,name):
    fig.canvas.draw();export_figure(fig,HERE/'figures'/name);plt.close(fig)
def axes(size=(6.4,4.0)):return plt.subplots(figsize=size,layout='constrained')
def arena(ax):
    t=np.linspace(0,2*np.pi,241);ax.plot(1800*np.cos(t),1800*np.sin(t),color='.55',ls='--',lw=.7)
    ax.set_aspect('equal');ax.set_xlabel('East (m)');ax.set_ylabel('North (m)')

def main():
    datasets={k:read('final_'+k+'.json') for k in ('development','holdout','stress')}
    from evaluate_final import tasks_for
    for phase,rows in datasets.items():
        expected={t[:4] for t in tasks_for(phase)}
        actual=[(r['dataset'],r['seed'],r['stress'],r['algorithm']) for r in rows]
        if len(actual)!=len(expected) or set(actual)!=expected:raise ValueError('Missing, duplicate or unexpected study cases: '+phase)
    metrics={k:metric(v) for k,v in datasets.items()};allrows=sum(datasets.values(),[]);metrics['all']=metric(allrows)
    pairs=paired(datasets['holdout']);rng=np.random.default_rng(20260912)
    a=np.array([p['original']['virtual_time_s'] for p in pairs]);b=np.array([p['candidate']['virtual_time_s'] for p in pairs])
    ix=rng.integers(0,len(a),size=(4000,len(a)));boot=100*(1-b[ix].sum(axis=1)/a[ix].sum(axis=1))
    metrics['holdout']['paired_bootstrap_95_percent']=np.quantile(boot,[.025,.975]).tolist()
    metrics['stress_groups']={k:metric([r for r in datasets['stress'] if r['stress']==k]) for k in sorted({r['stress'] for r in datasets['stress']})}
    metrics['worst_holdout_cases']=sorted([dict(seed=p['candidate']['seed'],baseline=p['original']['average_time_s'],candidate=p['candidate']['average_time_s'],delta=p['candidate']['average_time_s']-p['original']['average_time_s']) for p in pairs],key=lambda r:r['delta'],reverse=True)[:10]
    (HERE/'results/comparison_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    with (HERE/'results/analysis_data.csv').open('w',newline='',encoding='utf-8-sig') as f:
        keys=sorted(set().union(*(r.keys() for r in allrows))-{'channels'});w=csv.DictWriter(f,keys,extrasaction='ignore');w.writeheader();w.writerows(allrows)
    apply_publication_style(language='en',width='report')
    plt.rcParams.update({'font.size':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8})
    trace={n:read(f'trace_{n}_random_40001.json') for n in ('original','candidate')}
    sources=trace['candidate']['sources']
    fig,ax=axes();arena(ax)
    for kind,marker,color in ((False,'o',BLUE),(True,'^',ORANGE)):
        ss=[s for s in sources if (s['direction'] is not None)==kind]
        ax.scatter([s['x'] for s in ss],[s['y'] for s in ss],marker=marker,color=color,s=28,label='Directional' if kind else 'Omnidirectional')
        for s in ss:
            if kind:
                t=math.radians(s['direction']);ax.arrow(s['x'],s['y'],150*math.cos(t),150*math.sin(t),head_width=40,color=color,length_includes_head=True)
    ax.legend(loc='upper right');save(fig,'raw_q4_layout')
    cand=[p['candidate'] for p in pairs]
    fig,ax=axes();counts=[sum(r['total']==n for r in cand) for n in range(10,17)]
    ax.bar(range(10,17),counts,color=BLUE,width=.65);ax.set(xticks=range(10,17),xlabel='Sources per scenario',ylabel='Holdout scenarios',ylim=(0,max(counts)*1.2));save(fig,'raw_q4_source_counts')
    fig,ax=axes();jitter=np.random.default_rng(17).uniform(-.13,.13,(len(cand),2))
    ax.scatter(np.array([r['total'] for r in cand])+jitter[:,0],np.array([r['directional'] for r in cand])+jitter[:,1],s=22,alpha=.65,color=BLUE)
    ax.set(xlabel='Total sources',ylabel='Directional sources',xticks=range(10,17));save(fig,'raw_q4_direction_mix')
    fig,ax=axes();nodes=trace['candidate']['nodes'];ax.scatter(*zip(*nodes),s=20,color=ORANGE,label='New coverage sites')
    old=trace['original']['nodes'];ax.scatter(*zip(*old),s=35,facecolors='none',edgecolors=BLUE,marker='s',label='Previous sites');arena(ax);ax.legend(loc='upper right',fontsize=7)
    ax.set_xlim(-2050,2050);ax.set_ylim(-2050,2050);save(fig,'process_q4_scan_layout')
    fig,axs=plt.subplots(1,2,figsize=(7.2,3.6),layout='constrained')
    for ax,name,title,color in zip(axs,('original','candidate'),('Previous best','New candidate'),(BLUE,ORANGE)):
        tr=trace[name]['trace'];xy=[(0.,0.)]+[(r['x'],r['y']) for r in tr]
        ax.plot(*zip(*xy),color=color,lw=.65,alpha=.65);ax.scatter([s['x'] for s in sources],[s['y'] for s in sources],s=12,color='black',zorder=3)
        arena(ax);ax.set_title(title);ax.set_xlim(-2500,2500);ax.set_ylim(-2500,2500)
    save(fig,'process_q4_trajectories')
    fig,ax=axes();parts=[('Travel',lambda r:r['distance_m']/5),('Measure',lambda r:5*r['measures']),('Switch',lambda r:r['switches']),('Clear hit',lambda r:5*r['cleared']),('Clear miss',lambda r:3*r['failed_clears'])]
    colors=[BLUE,ORANGE,PALETTE['positive'],PALETTE['accent'],PALETTE['contrast']];left=np.zeros(2)
    for (label,fn),color in zip(parts,colors):
        vals=[sum(fn(r) for r in datasets['holdout'] if r['algorithm']==n)/sum(r['total'] for r in datasets['holdout'] if r['algorithm']==n) for n in ('original','candidate')]
        ax.barh([1,0],vals,left=left,color=color,height=.5,label=label);left+=vals
    ax.set(yticks=[0,1],yticklabels=['New candidate','Previous best'],xlabel='Virtual time per source (s)',xlim=(0,max(left)*1.06));ax.legend(loc='upper center',bbox_to_anchor=(.5,1.15),ncol=3);save(fig,'process_q4_time_parts')
    fig,ax=axes();x=np.array([p['original']['average_time_s'] for p in pairs]);y=np.array([p['candidate']['average_time_s'] for p in pairs]);limit=max(x.max(),y.max())*1.06
    ax.plot([0,limit],[0,limit],color='.5',ls='--',lw=.8,label='Equal time');ax.scatter(x,y,s=20,color=ORANGE,alpha=.7)
    ax.set(xlabel='Previous best time per source (s)',ylabel='New candidate time per source (s)',xlim=(0,limit),ylim=(0,limit));ax.legend();save(fig,'result_q4_paired')
    fig,ax=axes((7.2,4.2));groups=list(metrics['stress_groups']);rng=np.random.default_rng(11)
    for name,color,marker,off,label in [('original',BLUE,'o',-.15,'Previous best'),('candidate',ORANGE,'s',.15,'New candidate')]:
        for i,stress in enumerate(groups):
            rr=[r for r in datasets['stress'] if r['stress']==stress and r['algorithm']==name];yy=[r['average_time_s'] for r in rr]
            ax.scatter(i+off+rng.uniform(-.06,.06,len(yy)),yy,s=15,alpha=.5,color=color,marker=marker,label=label if i==0 else None)
            ax.plot([i+off-.09,i+off+.09],[weighted(rr)]*2,color=color,lw=2)
    ax.set(xticks=range(len(groups)),xticklabels=groups,ylabel='Time per source (s)');ax.legend();save(fig,'result_q4_stress')
    screening=sum([read(f'screening_round{s}.json')['rows'] for s in (2,3,4,5)],[])
    names=sorted({r['algorithm'] for r in screening},key=lambda n:(weighted([r for r in screening if r['algorithm']==n]),n))
    selected=json.loads((HERE/'selected_new.json').read_text(encoding='utf-8'))['selected']
    fig,ax=axes((6.4,10.4));rng=np.random.default_rng(15)
    for i,n in enumerate(names):
        rr=[r for r in screening if r['algorithm']==n];ax.scatter([r['average_time_s'] for r in rr],i+rng.uniform(-.15,.15,len(rr)),color='.7',s=9,alpha=.7)
        ax.scatter([weighted(rr)],[i],color=ORANGE if n==selected else BLUE,s=24,marker='D')
    ax.set(yticks=range(len(names)),yticklabels=names,xlabel='Time per source (s)');ax.invert_yaxis();save(fig,'result_q4_algorithms')
    print(json.dumps(metrics,indent=2),flush=True)
if __name__=='__main__':main()
