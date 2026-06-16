# C3.2 Explicit Local Execution Design

Date: 2026-06-16

## 背景

项目已经完成 C3.2 open model cross-dataset evaluation contract scaffold。当前默认入口 `experiment c-stage-c32` 可以在离线安全边界下生成 contract report，状态为 `contract_ready_local_execution_blocked`。C3.1 已通过 NASA C-MAPSS classic 12 个 raw text 文件的 explicit local raw mapping review，并记录 `schema_validated_ready_for_c32` / `full_classic_cmapss_validated`。

下一阶段不应继续停留在 C3.1 授权或 schema paper trail，也不应直接进入完整公开 benchmark、开源模型 leaderboard 或自研训练。更合适的推进是：在显式本机 opt-in 下，把 C3.2 的 contract 变成一个最小可执行评估切片，用真实 C-MAPSS raw 文件计算 RUL baseline 指标，同时用 FU13-like simulated canonical observations 计算 forecasting baseline reference。两类指标分开解释，只作为下一步模型路线判断的证据，不合成排名。

## 目标

- 为 C3.2 增加 explicit local execution 配置样例，默认配置仍保持安全 contract-only。
- 在显式本机配置下读取 ignored 本机 C-MAPSS raw txt，执行第一轮 RUL baseline evaluation。
- 复用 FU13-like simulation 与现有 forecasting baseline，执行第一轮 forecasting reference。
- 报告中并列展示 RUL 指标和 forecasting 指标，但明确二者不可直接排名、不可生成 leaderboard。
- 更新 README 和 `details.md`，把当前阶段推进到 C3.2 explicit local execution。
- 保持默认项目状态可安装、可测试、可运行，不提交 raw、zip、parquet、cache 或生成报告。

## 非目标

- 不下载公开数据。
- 不提交 C-MAPSS raw、zip、parquet、FU13 真实数据、模型 cache 或报告产物。
- 不运行 TTM、Chronos、TimesFM、Moirai、MOMENT、UniTS 等 open model adapter。
- 不训练或微调任何模型。
- 不把 C-MAPSS RUL 与 FU13-like forecasting 合成为单一分数。
- 不宣称生产 RUL、故障概率、维修建议、生产告警或自研模型优越性。

## 关键假设

- C3.1 的 license/source 结论仍有效，C-MAPSS raw 文件只能通过本机 ignored 目录显式提供。
- 第一轮 RUL baseline 需要足够简单且可解释：使用 train 轨迹上基于 cycle progress 的中位数 RUL profile，预测 test 轨迹末端 RUL；计算 MAE、RMSE 和 NASA score。
- 第一轮 FU13-like forecasting reference 不需要读取 FU13 真实数据；使用现有模拟数据生成器生成 canonical observations，再用已有 robust / seasonal baseline 计算 MAE、RMSE 和 residual ranking。
- C3.2 local execution 的目的不是证明模型领先，而是证明本项目能在一个公开 RUL benchmark 与一个设备 forecasting reference 上产生分离、可复核、低夸大的证据。

## 方案比较

### 方案 A：只写 local execution 设计，不写执行入口

优点是风险最低，但项目已经具备 C3.2 contract scaffold、C3.1 raw parser 和 forecasting baseline。继续停留在文档会让 C3.2 无法形成可检验证据。

### 方案 B：显式本机 opt-in 的 baseline-only local execution

新增 local execution 配置样例和 runner。默认 C3.2 仍 contract-only；只有 local config 明确允许 `allow_local_raw_data: true` 与 `allow_local_execution: true` 时，才读取 C-MAPSS raw。RUL 只跑 baseline，不跑 open models；FU13-like forecasting 使用模拟数据和现有 baseline。报告保持指标分离。

这是推荐方案。它比纯文档更有推进力，又避免过早进入 open model 竞赛或自研训练。

### 方案 C：直接运行多开源模型跨数据 benchmark

短期看更激进，但会混合 raw 数据可用性、模型依赖、权重 cache、任务不兼容和指标解释问题。它容易生成误导性的 leaderboard，也会破坏当前项目“先证据、后路线”的节奏。

## 设计

### 配置

新增 `configs/local/c_stage_c32_explicit_local_execution.example.yaml`。它是本机 opt-in 样例，必须保持在 `configs/local/` 下，指向 ignored 的本机 raw 目录和 ignored 的临时输出路径。

配置分为：

- `stage`: 仍为 `C3_2_open_model_cross_dataset_evaluation`。
- `safety_policy`: 保留 `allow_network: false`、`allow_download: false`、`allow_model_cache: false`、`allow_training: false`、`allow_write_processed: false`；新增或使用 `allow_local_execution: true` 和 `allow_local_raw_data: true` 表达显式本机执行。
- `local_execution`: 控制 `enabled`、C-MAPSS raw dir、subsets、FU13-like simulation days/seed、forecasting window 参数和 `max_windows`。
- `metric_contract`: 继续禁止 leaderboard；RUL 与 forecasting 指标分开。

默认 `configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml` 不读取本机数据，也不执行 scoring。

启用条件必须是确定的：

- `local_execution.enabled: false` 或缺失时，只执行现有 contract-only 路径。
- `local_execution.enabled: true` 时，必须同时满足 `safety_policy.allow_local_execution: true` 和 `safety_policy.allow_local_raw_data: true`。
- `local_execution.enabled: true` 但任一 required safety flag 不满足时，loader 直接报 config error，不降级为 contract-only。
- 即使 local execution 开启，`allow_network`、`allow_download`、`allow_model_cache`、`allow_training`、`allow_write_processed` 仍必须为 false。
- 选定 C-MAPSS subset 的任一 required raw file 缺失时，整次 local execution 返回 blocked 状态，不输出部分分数。
- `local_execution.cmapss.subsets` 默认和 example config 均为 `[FD001, FD002, FD003, FD004]`，允许范围只包括经典四个 subset。测试可以用临时配置覆盖为 `[FD001]` 做 smoke fixture，但真实 example 应覆盖 full classic。

### C-MAPSS RUL Baseline

第一轮只做 baseline，不做训练框架。输入为 C-MAPSS classic raw txt：

- 对每个 subset 读取 `train_FDxxx.txt`、`test_FDxxx.txt`、`RUL_FDxxx.txt`。
- train 轨迹的真实 RUL 为 `last_cycle - current_cycle`。
- test 轨迹只在末端预测 final RUL，与 `RUL_FDxxx.txt` 对齐。
- baseline 使用 normalized cycle progress 的 train 中位数 RUL profile：`progress = cycle_index / max_cycle_by_unit`，按 bucket 聚合 train RUL 中位数；test final progress 使用每个 test unit 的末端 cycle / train max-cycle median 进行裁剪。
- 指标为 RUL MAE、RUL RMSE、NASA score、evaluated_units、subset_count。

这个 baseline 简单、可复核、不会引入模型训练，也不会把 sensor 特征误用于 target leakage。它足够作为第一轮公开 RUL baseline bar，但不代表最佳 C-MAPSS 方法。

确定性默认值：

- `progress_bucket_count: 20`。
- bucket 边界为 `[0.0, 0.05), [0.05, 0.10), ... [0.95, 1.0]`，通过 `min(int(progress * bucket_count), bucket_count - 1)` 计算 bucket index。
- 每个 subset 独立建立 train profile，不跨 subset 聚合。
- 每个 subset 的 `train_max_cycle_reference` 使用该 subset train units 的 max cycle median。
- 空 bucket 使用最近非空 bucket 的 median RUL；若两侧距离相同，使用较低 bucket；若整个 profile 为空则 config error。
- test final prediction 只在每个 test unit 末端生成一次，`test_progress = min(final_test_cycle / train_max_cycle_reference, 1.0)`。
- `cycle_index` 使用 C-MAPSS raw 文件中的原始 1-based cycle 值，不做 0-based 转换。
- NASA score 使用常见 PHM08 方向：`error = prediction - truth`；`error < 0` 时 `exp(-error / 13) - 1`，`error >= 0` 时 `exp(error / 10) - 1`，最终对 unit 求和。
- 报告同时输出 per-subset metrics 和 overall metrics。per-subset metrics 按该 subset 的 test units 计算；overall MAE/RMSE 按所有 selected subsets 的 test unit prediction 全局聚合；overall NASA score 为 selected subsets 的 NASA score 直接求和；`subset_count` 为 selected subsets 数量。
- raw 缺失时状态固定为 `blocked_missing_cmapss_raw`；raw schema mismatch 时状态固定为 `blocked_cmapss_raw_schema_mismatch`。

### FU13-like Forecasting Reference

第一轮不读取 FU13 真实数据。runner 使用 `simulate_dataset` 在内存中生成 FU13-like canonical observations，再复用 `build_model_windows`、`RobustStageForecaster`、`StageSeasonalNaiveForecaster` 和 `forecasting_metrics`：

- 默认使用小规模模拟天数，保证测试和本机 smoke run 快速完成。
- 默认 `context_length` / `prediction_length` 小于 README 中真实 FU13 示例，避免 CI 压力。
- 输出 robust baseline 与 seasonal baseline 的 MAE、RMSE、coverage、residual ranking。
- 报告明确这只是 forecasting reference，不是 RUL ground truth。

确定性默认值：

- 模拟参数由 local config 固定，默认 `days: 3`、`seed: 42`。
- 默认窗口参数为 `context_length: 32`、`prediction_length: 8`、`max_windows: 60`。
- 建窗使用 `allow_cross_stage: true`、`stride: prediction_length`，并按生成顺序截断到 `max_windows`。
- 至少需要 2 个窗口；按时间顺序 70/30 split，前 70% fit，后 30% evaluation；test 至少 1 个窗口。
- split index 使用 `max(1, int(window_count * 0.7))`，如果该结果等于 `window_count`，则改为 `window_count - 1`，确保 test 至少 1 个窗口。
- `RobustStageForecaster` 和 `StageSeasonalNaiveForecaster` 只在 train windows 上 fit，只在 test windows 上计算指标。
- 报告字段使用 `mae`、`rmse`、`interval_coverage`、`count`，与现有 `forecasting_metrics` 对齐。
- residual ranking 不是模型排名，而是单个 baseline 内部的误差解释表。每个 baseline 计算 test residual 的 mean absolute error，按 `sensor_id` 聚合后降序取 `top_k: 5`，输出字段为 `rank`、`sensor_id`、`mean_abs_residual`。
- 报告可以比较 robust 与 seasonal 的 forecasting metrics，但不得把 forecasting baseline 与 C-MAPSS RUL baseline 合成一个总榜。

### Runner 和报告

现有 `c32_open_model_cross_dataset_evaluation.py` 扩展为：

- contract-only 路径保持不变。
- local execution 路径在配置显式开启后运行两个独立 evaluation block。
- `C32RunResult` 增加可选 `rul_baseline_result` 和 `forecasting_reference_result`。
- `render_c32_report` 增加 `C-MAPSS RUL Baseline Evaluation`、`FU13-like Forecasting Reference` 和 `Separated Metric Interpretation`。

报告状态建议：

- 默认配置：`contract_ready_local_execution_blocked`。
- 本机执行成功：`local_execution_baseline_reference_ready`。
- 本机 raw 缺失或 schema mismatch：返回 blocked 状态并写明原因，不生成部分 leaderboard。

### 安全边界

- 默认 C3.2 命令行为不变，不触碰 raw、processed、cache、adapter。
- local execution 只允许读 configured raw dir，不允许下载，不允许写 processed。
- FU13-like 模拟数据默认在内存中运行；如配置输出路径，也必须落在 ignored 目录且不得纳入 Git。
- local execution 仍不 import open model adapters。
- 报告生成在 `reports/` 或 `/tmp`，不提交。

### 测试

新增或扩展测试覆盖：

- 默认 C3.2 仍 contract-only，no-touch sentinel 测试保持通过。
- local execution example config 是显式 opt-in，且拒绝 network/download/model cache/training/write processed。
- C-MAPSS 小型 fixture 能计算 RUL MAE/RMSE/NASA score。
- FU13-like 小型模拟能计算 forecasting baseline metrics 和 residual ranking。
- CLI `experiment c-stage-c32 --config configs/local/c_stage_c32_explicit_local_execution.example.yaml --output <tmp>` 在测试临时 raw fixture 配置下返回 0。
- 报告包含 separated metrics、no leaderboard、no open model execution、no training。
- README 和 `details.md` 记录新阶段、命令和限制。

## 验收标准

- 默认 C3.2 contract CLI 行为不回退。
- 本机 explicit local execution 配置可以执行 baseline-only C-MAPSS RUL 与 FU13-like forecasting reference。
- RUL 和 forecasting 指标在报告中分开解释，不出现合成排名。
- 全量测试通过。
- Git 不跟踪 raw/zip/parquet/cache/generated report。
- README 和 `details.md` 说明当前阶段、执行方式、安全边界和下一阶段计划。

## 本阶段完成后的下一步

如果本阶段通过，下一阶段建议进入 C3.3 open model single-candidate local evaluation design。范围仍应克制：只选择一个最可能在 forecasting 上可运行的 open model candidate（优先 TTM，因为已有真实 FU13 路径和 cache 经验），只在 FU13-like forecasting reference 上验证 adapter/cache/依赖链路；C-MAPSS RUL 仍先保持 baseline，不急于做 open model RUL。
