# B题支撑材料说明（精简版）

本包与修订论文对应，按“题目 → 结果数据 → 正式测试”分级组织，仅保留最终在线入口、可独立运行的完整源程序、正式测试必交文件与论文结果数据。实验过程记录、重复图表、开发中间产物与历史版本数据未随包提交（论文正文与附表已汇总）。

## 目录结构

- `问题一与问题二/`
  - `code/`：几何内核 `geometry.py`（可行域、直径、最小包围圆、条件接收判据）、问题一入口 `solve_q1.py`、问题二入口 `solve_q2.py` 与求解过程 `study.py`、回归测试 `test_core.py`、离线合成环境（`offline_sim.py`、`strategy.py`、`robot_client.py`、`config.json`）；
  - `results/`：论文表3—表7对应结果与离线合成运行记录。
- `问题三/`
  - `code/`：最终在线入口 `run_robot.py`（冻结策略 `strategy.py`，共享先导+弹性巡回 combo100）；完整继承链 `prototype_v1..v10.py`、`baseline_original.py`、`baseline_breakthrough.py`、`baseline_gemini.py`；认证清除内核 `robot_core.py`、连续覆盖证书 `coverage_exact.py`；回归测试 `test_strategy.py` 与离线环境。
- `问题四/`
  - `code/`：最终在线入口 `run_q4.py`（冻结策略 `strategy_selected.py`，延迟调度 defer22）；策略族 `strategy*.py`、22 点三角网 `coverage.py`、连续可见性证书 `coverage_certificate.py`、开放路径 `routing.py`、精确复核 `results/p1_exact_coverage_audit.py`、HTTP 自测 `http_selftest.py`。
- `正式测试/`
  - `加密日志/`：六份原名、原字节正式测试加密日志（必交）；
  - `客户端记录/`：六场正式测试的客户端日志与汇总（身份字段已匿名，实验数值与案例编码未改动）；
  - `official_results_to_fill.csv`、`formal_timing_evidence.json`：论文表13/表17对应的成绩与计时证据。
- 根目录：`README_复现说明.md`、`AI工具使用详情.pdf`（必交）、`verify_submission.py`、`requirements.txt`、`submission_manifest.json`（全包 SHA-256）。

> 每个问题目录自包含：公共几何与接口模块在各问题目录中保留运行所需的一份，单独取出该目录（或包内任意问题目录）即可运行；问题三/四的 `prototype_v*.py`、`baseline_*.py` 是冻结策略的继承链，按原文件名保留，最终入口以 `strategy.py`、`strategy_selected.py` 为准。

## 快速核验

Python 3.12 或以上，在解压根目录执行：

```powershell
python verify_submission.py
```

核验内容：包内文件 SHA-256、问题一楔形反例与最小包围圆、问题二两种网格最优值、问题三策略回归测试、问题四 22 点布局离线有理数精确覆盖审计（2831 片）与私有本地模拟的 HTTP 协议自测；全部通过时末行输出 PASS。核验在临时副本中进行，不修改本包。

## 与论文的对应

- 正文图、表均已嵌入论文；`问题一与问题二/results/` 保留表3—表7的关键结果文件，`正式测试/` 保留表13、表17的成绩与计时证据。
- 正式表中的程序运行时间由成功 `/enter` 与 `/exit` 响应服务器时间戳差估计（分辨率 1 ms，公开接口重建值），不是官方界面转录；客户端 `summary.json` 保留原墙钟。
- 在线算法只使用题面公开接口与 Python 标准库；辅助开发脚本与历史实验数据未打包。
- AI 使用详情见 `AI工具使用详情.pdf`；论文附录列出本包实际文件清单与核心源程序选读。
