from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'B题/code'))
import plot_results as pr
OUT=ROOT/'B题/work/paper/figures';OUT.mkdir(exist_ok=True)
# Same coordinates and color values as accepted plots; only correct labeling and marker redundancy.
def save(f,n):
 issues=pr.ps.audit_layout(f)+pr.ps.audit_design(f)
 if issues:raise RuntimeError(issues)
 pr.export_figure(f,str(OUT/n),formats=['png','svg'],dpi=300,size_inches=pr.SIZE,tight=False,grayscale_preview=True)
 pr.plt.close(f)
src=pr.xy(pr.read('q2_source_scenarios.csv'))
f,a=pr.base();dots=a.scatter(*src.T,c=src[:,0],s=12,cmap='cividis')
bar=f.colorbar(dots,ax=a,label='沿首次示向坐标 / m');bar.solids.set_rasterized(False)
a.set_ylabel('横向坐标 / m');a.set_xlabel('沿首次示向坐标 / m');save(f,'raw_q2_prior')
q1=json.loads((ROOT/'results/study_summary.json').read_text())['q1']
f,a=pr.base(True)
for i,(x,y,t) in enumerate(q1['observations']):
 for dt in [-1,1]:
  u=pr.unit(t+dt);a.plot([x,x+1000*u[0]],[y,y+1000*u[1]],color=pr.BLUE if i==0 else pr.ORANGE,lw=.8,ls='--')
 a.scatter([x],[y],c=pr.BLUE if i==0 else pr.ORANGE,marker='s' if i==0 else '^',s=28,label='检测点 '+str(i+1))
a.scatter([0],[0],marker='*',s=65,c='black',label='构造源');a.legend(loc='upper left',fontsize=8,frameon=False)
save(f,'raw_q1_observations')
