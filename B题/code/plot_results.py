"""Draw computed synthetic/geometry evidence using the supplied publication tools."""
import os,sys,json,csv,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'B题/work/mpl'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from matplotlib.patches import Circle,Polygon
sys.path.insert(0,str(ROOT/'utils'))
import plot_style as ps
from export_figure import export_figure
from geometry import unit,mul,add

available_fonts={f.name for f in font_manager.fontManager.ttflist}
cjk_font=next((f for f in ['SimSun','Songti SC','STSong','Noto Serif CJK SC','Microsoft YaHei'] if f in available_fonts),None)
if cjk_font is None:
    raise RuntimeError('No supported CJK font installed; install SimSun or Noto Serif CJK SC before exporting.')
plt.rcParams.update({'font.family':['Times New Roman',cjk_font],
                     'font.size':9,'axes.unicode_minus':False,'axes.spines.top':False,
                     'axes.spines.right':False,'svg.fonttype':'none','axes.linewidth':0.7})
BLUE='#0072B2';ORANGE='#D55E00';GREEN='#009E73';GRAY='#777777'
SIZE=(14.5/2.54,9.1/2.54)

def read(name):
    with (ROOT/'results'/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def xy(rows):return np.array([[float(r['x']),float(r['y'])] for r in rows])
def base(equal=False):
    f,a=plt.subplots(figsize=SIZE,layout='constrained')
    if equal:a.set_aspect('equal',adjustable='datalim')
    a.set_xlabel('东向坐标 x / m');a.set_ylabel('北向坐标 y / m')
    return f,a

def save(fig,name):
    issues=ps.audit_layout(fig)+ps.audit_design(fig)
    if issues:raise ValueError(name+': '+'; '.join(issues))
    stem=ROOT/'figures'/name
    export_figure(fig,str(stem),formats=['png','svg'],dpi=300,size_inches=SIZE,tight=False)
    ps._save_grayscale_preview(stem.with_suffix('.png'),300)
    plt.close(fig)

def main():
    summary=json.loads((ROOT/'results/study_summary.json').read_text());q1=summary['q1']
    obs=np.array(q1['observations']);f,a=base(True)
    for i,(x,y,t) in enumerate(obs):
        for dt in [-1,1]:
            u=unit(t+dt);a.plot([x,x+1000*u[0]],[y,y+1000*u[1]],color=BLUE if i==0 else ORANGE,lw=.8,ls='--')
        a.scatter([x],[y],c=BLUE if i==0 else ORANGE,marker='s',s=28,label='检测点 '+str(i+1))
    a.scatter([0],[0],marker='*',s=65,c='black',label='构造源');a.legend(loc='upper left',fontsize=8,frameon=False)
    save(f,'raw_q1_observations')
    f,a=base();seq=read('q1_constraint_sequence.csv');a.plot([int(r['observations']) for r in seq],[float(r['diameter_m']) for r in seq],marker='o',color=BLUE)
    a.set_xlabel('检测点数量');a.set_ylabel('定位区域直径 / m');a.set_xticks(range(2,7));save(f,'process_q1_constraints')
    f,a=base(True);vs=np.array(q1['vertices']);a.add_patch(Polygon(vs,fc=BLUE,alpha=.15,ec=BLUE));a.plot(*np.vstack([vs,vs[0]]).T,c=BLUE,lw=1)
    a.add_patch(Circle(q1['diameter_center'],q1['diameter']/2,fill=False,ec=ORANGE,ls='--',lw=1.3,label='直径圆'))
    a.add_patch(Circle(q1['mec_center'],q1['mec_radius'],fill=False,ec=GREEN,lw=1.2,label='最小包围圆'))
    pair=np.array(q1['diameter_pair']);a.plot(*pair.T,c=GRAY,ls=':',lw=1);a.scatter(*vs.T,c=BLUE,s=18);a.set_xlim(-23,19);a.set_ylim(-22,17)
    a.legend(loc='upper right',fontsize=8,frameon=False)
    cc=np.array(q1['diameter_center']);v=vs[np.argmax(np.linalg.norm(vs-cc,axis=1))]
    inset=a.inset_axes([.03,.65,.27,.29]);inset.set_aspect('equal')
    inset.add_patch(Circle(q1['diameter_center'],q1['diameter']/2,fill=False,ec=ORANGE,ls='--',lw=1.2))
    inset.add_patch(Circle(q1['mec_center'],q1['mec_radius'],fill=False,ec=GREEN,lw=1.2))
    inset.plot(*np.vstack([vs,vs[0]]).T,c=BLUE,lw=.8);inset.scatter([v[0]],[v[1]],c='black',s=8)
    inset.set_xlim(v[0]-.65,v[0]+.65);inset.set_ylim(v[1]-.55,v[1]+.55);inset.set_xticks([]);inset.set_yticks([])
    inset.set_title('超出 0.265 m',fontsize=8);save(f,'result_q1_counter')
    src=xy(read('q2_source_scenarios.csv'));f,a=base();dots=a.scatter(*src.T,c=src[:,0],s=12,cmap='cividis');bar=f.colorbar(dots,ax=a,label='源距 / m');bar.solids.set_rasterized(False);a.set_ylabel('横向坐标 / m');a.set_xlabel('沿首次示向坐标 / m');save(f,'raw_q2_prior')
    rows=read('q2_candidates.csv');x=np.array([float(r['local_x']) for r in rows]);y=np.array([float(r['local_y']) for r in rows]);z=np.array([float(r['worst_diameter_m']) for r in rows]);best=summary['q2']['best']
    f,a=base(True);sc=a.scatter(x,y,c=z,cmap='viridis',s=16,marker='s');bar=f.colorbar(sc,ax=a,label='有限场景最坏直径 / m');bar.solids.set_rasterized(False);a.set_xlabel('沿首次示向坐标 / m');a.set_ylabel('横向坐标 / m');save(f,'process_q2_score')
    f,a=base(True);sel=np.array([r['candidate_10pct']=='True' for r in rows]);a.scatter(x,y,s=7,c='#cccccc',label='保证接收格点');a.scatter(x[sel],y[sel],s=24,marker='s',c=BLUE,label='10% 优选格点');a.scatter([best['local_x']],[best['local_y']],c=ORANGE,s=65,marker='*',label='选择点');a.legend(frameon=False,loc='upper right',fontsize=8);a.set_xlabel('沿首次示向坐标 / m');a.set_ylabel('横向坐标 / m');save(f,'result_q2_candidates')
    for mode in ['q3','q4']:
        ss=read(mode+'_synthetic_sources.csv');pos=xy(ss);f,a=base(True);a.add_patch(Circle((0,0),1800,fill=False,ec=GRAY,lw=.8))
        for r in ss:
            px,py=float(r['x']),float(r['y']);direction=r['direction']
            if direction:
                u=unit(float(direction));a.scatter(px,py,c=ORANGE,marker='^',s=26);a.arrow(px,py,180*u[0],180*u[1],color=ORANGE,width=7,head_width=65,length_includes_head=True)
            else:a.scatter(px,py,c=BLUE,marker='o',s=23)
        a.set_xlim(-2100,2100);a.set_ylim(-2100,2100);save(f,'raw_'+mode+'_sources')
    f,a=base(True);trace=json.loads((ROOT/'results/q3_trace.json').read_text());route=np.array([[0,0]]+[[r['x'],r['y']] for r in trace]);a.plot(*route.T,color=BLUE,lw=.7,alpha=.8);a.add_patch(Circle((0,0),1800,fill=False,ec=GRAY,ls='--'))
    a.scatter([0],[0],c=ORANGE,marker='*',s=55);save(f,'process_q3_route')
    f,a=base();hits=[r for r in trace if r['kind']=='clear' and r['response']['clear_result']=='success'];times=[0]+[r['virtual_time_s'] for r in hits]+[trace[-1]['virtual_time_s']];counts=[0]+list(range(1,len(hits)+1))+[len(hits)]
    a.step(np.array(times)/60,counts,where='post',c=BLUE,lw=1.5);a.set_xlabel('虚拟时间 / min');a.set_ylabel('累计清除数 / 个');a.set_ylim(0,13);save(f,'result_q3_clearing')
    f,a=base(True);nodes=xy(read('q4_scan_nodes.csv'));a.scatter(*nodes.T,c=BLUE,s=12);a.add_patch(Circle((0,0),1800,fill=False,ec=GRAY,lw=1));a.add_patch(Polygon([(0,0),(600,0),(600,600),(0,600)],fc=GREEN,alpha=.2,ec=GREEN));a.scatter([275],[320],marker='*',c=ORANGE,s=55)
    a.set_xlim(-2300,2300);a.set_ylim(-2300,2300);save(f,'process_q4_coverage')
    f,a=base();runs=read('synthetic_runs.csv')
    for j,mode in enumerate(['q3','q4']):
        rr=[r for r in runs if r['mode']==mode];ys=[float(r['average_time_s']) for r in rr];a.scatter([j-.07,j,j+.07],ys,c=BLUE if j==0 else ORANGE,marker='o' if j==0 else '^',s=35)
    a.set_xticks([0,1],['全向场景 q3','混合场景 q4']);a.set_xlim(-.4,1.4);a.set_xlabel('构造场景类别（每类 3 个种子）');a.set_ylabel('平均定位清除时间 / s');a.set_ylim(bottom=0);save(f,'result_q4_times')
    print('12 logical figures exported')
if __name__=='__main__':main()
