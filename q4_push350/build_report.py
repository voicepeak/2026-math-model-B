"""Create a candid second-study report from measured outcomes."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    m=json.loads((HERE/'results/comparison_metrics.json').read_text(encoding='utf-8'))
    cfg=json.loads((HERE/'selected_new.json').read_text(encoding='utf-8'))
    rows=['|集合|场景|目标/策略|上一轮秒/源|新方案秒/源|降低|更快场景|','|---|---:|---:|---:|---:|---:|---:|']
    for key,label in [('development','开发'),('holdout','新留出'),('stress','新压力')]:
        r=m[key];rows.append(f"|{label}|{r['scenarios']}|{r['sources']}|{r['baseline_s_per_source']:.3f}|{r['candidate_s_per_source']:.3f}|{r['reduction_percent']:.2f}%|{r['wins']}/{r['scenarios']}|")
    h=m['holdout'];ci=h['paired_bootstrap_95_percent']
    mean_claim='均值改善' if h['reduction_percent']>0 else '均值退化'
    evidence_claim='本地新留出支持平均改善' if ci[0]>0 else '本地新留出支持平均退化' if ci[1]<0 else '区间跨零，尚无充分证据支持稳定的平均改善'
    target_gap=f"距离350目标还高{h['candidate_s_per_source']-350:.2f}秒/源" if h['candidate_s_per_source']>350 else f"本批均值低于350目标{350-h['candidate_s_per_source']:.2f}秒/源"
    groups=['|压力类型|旧秒/源|新秒/源|降低（负数为退化）|更快场景|','|---|---:|---:|---:|---:|']
    for name,r in m['stress_groups'].items():groups.append(f"|{name}|{r['baseline_s_per_source']:.2f}|{r['candidate_s_per_source']:.2f}|{r['reduction_percent']:.2f}%|{r['wins']}/{r['scenarios']}|")
    worst=['|seed|旧秒/源|新秒/源|差值（正数为退化）|','|---|---:|---:|---:|']
    for r in m['worst_holdout_cases']:worst.append(f"|{r['seed']}|{r['baseline']:.2f}|{r['candidate']:.2f}|{r['delta']:+.2f}|")
    verdict='尚未达到' if h['candidate_s_per_source']>350 else '本批合成留出均值达到'
    text=f'''# 第四题：继续尝试350秒/源的第二轮实验

最终冻结候选 **{cfg['selected']}**；{verdict}350秒/源。所有数值是离线合成实验，不是官方模拟器成绩，不是整个在线问题的全局最优证明。

{chr(10).join(rows)}

本轮的“上一轮”是已经优化过的ring_multi_optical，不能将这里的相对改善与最初基础算法混用。新留出使用40001–40100，压力使用201–210，各种子均未参与本轮调参。两策略使用同一场景和固定误差场。全部记录经逐动作计时和真实清除状态审计；任何单局退化均保留。

新留出相对降低95%配对bootstrap区间：**[{ci[0]:.2f}%, {ci[1]:.2f}%]**（4000次，以场景为单位；负值表示可能变慢）。结论为**{mean_claim}；{evidence_claim}**。{target_gap}。该结果不支持把最好单局或开发集平均数说成稳定350。

## 换了什么算法

1. 减少覆盖点：原25点改为原点、998米内环7点、1848米外环14点，共22点。独立有理数验证证明膨胀外域仍满足定向半平面覆盖。另实现并验证了21点布局，但开发集略逊。
2. 延迟不确定目标：目标只有一次方位、可行域包围半径大于60米且尚有扫描点时，先继续覆盖扫描，借其他停靠点共享交叉测向；已获得两次方位或半径不超过60米时再纳入联合清除路线。扫描完后必须处理所有未清目标。
3. 仍保留有界误差楔形交会、可靠清除证书和完整矩形光学回退；不把第四题no_signal误当成位置圆排除。

本轮共40个配置各跑12个开发场景：22/21点布局、延迟调度、内圈优先、最近任务、矩形格点贪心、中心失败后补测、粒子搜索、固定完整扫描路线加目标插入、面积质心主动测向，以及上一轮比较器。粒子根据公开正负观测安排尝试，失败必回完整几何搜索；tour绕路阈值仅约束目标中心插入，不限制整个定位过程。6个配置（含比较器）扩展到40场景后，按总虚拟时间除总源数冻结选优。40场景总数不是6个互不相交的数据集。

试过的新机制并不都更快，所有筛选结果保留在`results/screening_round2..5.json`，开发扩展保存在`development_extension.json`和`development_active.json`。未认证或未进入完整验收的探索（例如strategy_adaptive.py）不作为推荐入口。旧版本和旧交付包保持原样。

## 退化检查

{chr(10).join(groups)}

{chr(10).join(worst)}

候选在新留出100局中{h['wins']}局更快；不要理解为逐局保证改善。是否适合官方场景还需要官方演练，不能仅凭本地平均结果替换所有既有实测选择。

## 本机运行

在官方模拟器中选择第四题演练、接口就绪后，从本目录执行：

```powershell
python run_q4.py --robot-id 你的参赛队号
```

在线仅需Python标准库，默认连接127.0.0.1:2026。程序不启动案例，不选择正式测试。结果写入windows_results_q4中的时间戳目录。退出0表示策略完整完成；错误或预算耗尽退出2。`official_total_sources`留空，须对照官方界面核验；本程序不生成官方加密日志。

## 完整复现与门禁

研究绘图需requirements-research.txt中的依赖；在本目录运行：

```powershell
python reproduce.py
```

唯一完整入口核验冻结输入与科学结果指纹，重跑40开发、100新留出、80新压力两策略共440次，执行私有随机端口HTTP自测、统计、9图导出、两项严格图审和复现清单。`--verify-only`仅缩小重放与保存研究检查。

关键证据：`selected_new.json`、`frozen_hashes.json`、`results/comparison_metrics.json`、`results/final_*.csv/json`、`results/reproduction_log.json`、`results/复现清单.json`、`results/p1_*review.json`及最终独立P2回执。以实际回执状态为准，不以本报告模板生成视为验收通过。

使用了math-modeling、编程手、科研可视化工具及其提供的环境/剖析/绘图/图审/清单脚本，并执行独立P1/P2门禁；详细读图口径见图表契约。此次不生成论文，也不执行官方测试。
'''
    (HERE/'README.md').write_text(text,encoding='utf-8');print('Report generated from measured paired results.')
if __name__=='__main__':main()
