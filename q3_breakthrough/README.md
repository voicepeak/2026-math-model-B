# 第三问新版：共享交会 + 搜索清除联合路线 + 短基线逼近

推荐入口为本目录 `run_robot.py`，核心是 `strategy.py`。仅支持第三问（全向源）。原 `q3_gemini算法` 未被覆盖，随时可回用。

## 官方演练运行

在官方模拟器选择「问题3演练测试」，确认接口就绪。在本目录打开 PowerShell：

```powershell
python run_robot.py --robot-id 你的实际参赛队号
```

也可从项目根目录运行：

```powershell
python q3_breakthrough/run_robot.py --mode q3 --robot-id 你的实际参赛队号
```

端口不同追加 `--url http://127.0.0.1:端口`。默认结果目录为启动命令所在目录下的 `windows_results/时间_q3_随机串`。每局输出 `summary.json`、完整请求响应 `client.jsonl`、动作 `trace.json`、清除几何证书 `certificates.json`。

目前新版官方测试尚未执行。请在演练结束后把官方给出的源总数与 `summary.cleared` 核对；程序接口不返回真实总数，所以 `official_total_sources` 保留 null，不能自动将其写成100%官方清除率。正式测试日志须从官方模拟器导出并保留原名，程序日志不代替官方加密日志。

## 已验证的变化

1. 每频道持久保存多次方位形成的凸可行域，跨停点、跨目标复用，不重新从第一条射线开始。
2. 在已经停下的位置补测有价值的其他目标，多个目标共用移动基线。
3. 将已知目标和六个未访问的覆盖节点统一成开放路径，用最近邻初始化和2-opt滚动重排。无需回原点，探索与清除可交错。
4. 单方位目标首次取前进300米、侧移75米的短基线；中远目标在接近过程中继续交会，避免近源被大基线带来长距离过冲。
5. 保留半径≤19.9米的最小包围圆清除认证、near立即清除和完整条带回退。只清到10个不能退出；完整覆盖后清空全部已知目标，或清到题定上限16个，才结束。

覆盖使用原点+半径1200米的六边形解析保证：最坏目标距最近测点968.901572米<1000米。访问顺序不影响该证明。`uncovered_cells` 是保守整方格的辅助诊断，可能非零；默认算法应看 `coverage_certificate=hexagon_analytic` 或 `status=complete_upper_bound`。自适应网格分支只保留作研究对照，默认关闭。

## 本地验证与复现

快速完整HTTP测试（不会连接官方模拟器）：

```powershell
python selftest.py --seeds 11,12,13,14,15
```

单场景三代算法配对：

```powershell
python benchmark.py --seeds 1 --algorithms original,gemini,breakthrough --out quick
```

完整复现（190个配对场景、消融、原算法对照、HTTP自测、九张证据图）：

```powershell
python reproduce.py
```

从项目根目录的唯一复现命令为 `python q3_breakthrough/reproduce.py`。在线算法只使用Python标准库；完整作图另需要numpy、matplotlib，验证环境见 `results/复现清单.json`。`突破结果.md` 提供全部实测统计；`results/analysis_data.csv` 为逐局结果；`figures/` 为SVG、300DPI PNG及灰度预览。

所有配对场景共用相同目标、接收半径和确定的空间误差场。策略只能读取公开动作和位置/频道/计时状态；真值用于独立测试器计分、时间重构及作图。合成分布不声称等于官方随机分布，改善比例不是官方成绩保证。

竞赛时间已核验：[官方主页](https://en.mcm.edu.cn/)为北京时间2026-09-13 20:00结束；本地题目另规定模拟器9月13日17:30停止启动新测试、建议15:30前完成正式测试。本轮不修改既有论文或官方日志。
