# C3.3 Single-Candidate Open Model Local Evaluation Design

Date: 2026-06-22

## 项目理解

B08 当前定位是公司时空智能在能源设备时序方向的核心样板项目。主线不是做模型排行榜，而是把真实设备数据、canonical observations、cycle / window、baseline、开源基础时序模型、候选信号和评测报告连接成可复现证据链，用于判断开源模型复用、轻量适配和条件性自研的工程可行性。

截至 C3.2，项目已经完成：

- FU13 真实数据到 canonical observations、cycle / window、baseline / TTM forecasting 和场景样例。
- C1/C2/C2.1/C2.2 开源模型适配性证据与 executable adapter 失败记录。
- C3/C3.1 公开数据 registry 和 NASA C-MAPSS classic schema / RUL metadata / split leakage guard。
- C3.2 默认 contract-only 报告，以及 explicit local execution 下的 C-MAPSS RUL baseline 和 FU13-like forecasting baseline reference。

因此 C3.3 的合理推进不是扩大 benchmark，也不是训练自研模型，而是在 C3.2 的本机执行基础上，验证一个候选 open model 的 adapter/cache/依赖链路是否能在本机、显式 opt-in、安全边界内跑通。

## 问题

C3.2 已证明 baseline-only local execution 可以产生分离的 RUL 与 forecasting 指标，但 open model candidate 仍停留在 contract / adapter audit 口径。项目还缺少一个最小证据：在不下载默认数据、不提交 cache、不生成 leaderboard 的前提下，单个候选 open model 能否通过本机 cache 和 optional dependency，在 FU13-like forecasting reference 上执行并生成可解释状态。

如果直接进入多模型、多数据集或 C-MAPSS open model RUL，会同时引入任务不匹配、依赖安装、权重 cache、指标解释和 overclaim 风险。C3.3 应只回答一个更窄的问题：TTM 作为单个候选，在 FU13-like forecasting 上的本机 adapter/cache 链路是否可控。

## 目标

- 新增 C3.3 阶段设计，用于 single-candidate open model local evaluation。
- 只选择一个候选 open model：TTM / TinyTimeMixer。
- 只执行一个 open model 任务：FU13-like simulated forecasting。
- 复用 C3.2 FU13-like forecasting baseline reference，增加 TTM adapter 执行状态和 metrics。
- 默认配置继续不运行 open model、不读本机 cache、不下载权重、不联网、不训练。
- 显式本机 opt-in 配置允许读取本机 model cache，并可选择是否允许下载；默认 example 仍建议 `allow_download: false`。
- C-MAPSS RUL 继续 baseline-only，只作为 C3.2 anchor 被引用，不进入 C3.3 open model 执行。
- RUL 与 forecasting 指标继续分开解释，不生成 leaderboard。
- 更新 README 与 `details.md`，记录 C3.3 阶段入口、边界和下一步。

## 非目标

- 不新增多个 open model 候选。
- 不在 C-MAPSS RUL 上运行 open model。
- 不训练、微调或自研基础模型。
- 不下载公开数据或提交 raw / zip / parquet / cache / generated report。
- 不读取 FU13 real data。
- 不把 TTM 与 C-MAPSS RUL baseline 合成单一排名。
- 不宣称生产 RUL、故障概率、维修建议、生产告警或自研模型优越性。

## 关键假设

- TTM 是当前最合适的单候选，因为项目已有 `TTMForecastAdapter`、`TTMOpenModelAdapter`、FU13 real TTM 命令和 optional dependency 经验。
- FU13-like simulated forecasting 是 C3.3 的合适执行对象：它可在默认仓库内生成，不需要真实数据，不牵涉 C-MAPSS RUL 任务适配。
- C3.3 的“成功”不要求本机一定已有 TTM 权重；缺依赖、缺 cache、权重被 offline policy 阻塞都应形成结构化报告，而不是阶段失败。
- 如果用户显式开启下载，必须同时设置 `allow_network: true` 和 `allow_download: true`；否则配置报错。报告必须记录 `actual_network_used` 或 `download_allowed_not_verified`，但默认文档路径不推荐把下载作为阶段验收条件。
- C3.2 的 C-MAPSS RUL baseline 仍是公开 RUL baseline bar；C3.3 只补充 open model forecasting adapter/cache evidence。

## 方案比较

### 方案 A：只写 C3.3 设计，不加执行入口

风险最低，但推进不足。C3.2 已经有 local execution 和 TTM adapter 资产，继续只写文档会让 open model 本机链路仍停留在 C2.x adapter audit。

### 方案 B：单候选 TTM + FU13-like forecasting local evaluation

新增 `c-stage-c33` 配置、runner、CLI 和报告。默认配置为 contract-only；显式本机配置才运行 FU13-like simulation、baseline reference 和 TTM adapter。报告输出 dependency、weight、cache、runtime、input/output shape、forecasting MAE/RMSE、residual ranking 和 separated interpretation。C-MAPSS RUL 只引用 C3.2 baseline-only 状态。

这是推荐方案。它规模克制，贴近项目路线，能真实验证 adapter/cache/依赖链路，又不会把 C3.3 变成模型竞赛。

### 方案 C：多 open model 或 C-MAPSS RUL open model 执行

短期看更有“benchmark”味道，但会过早扩大变量：Chronos/TimesFM/Moirai 依赖、权重接口和任务口径不同，C-MAPSS RUL 也不是当前 open forecasting adapter 的自然任务。该方案容易生成误导性 leaderboard，不符合 B08 当前“证据先行、边界清晰”的节奏。

## 推荐设计

### 阶段入口

新增阶段：

```bash
uv run b08-model-core experiment c-stage-c33 \
  --config configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml \
  --output reports/c_stage_c33_single_candidate_open_model_local_evaluation.md
```

默认报告状态为 `contract_ready_single_candidate_local_execution_blocked`。默认入口只验证配置、前置条件、模型候选、任务和指标契约，不实例化 open model adapter。

显式本机执行样例：

```bash
HF_HOME=hf_cache uv run b08-model-core experiment c-stage-c33 \
  --config configs/local/c_stage_c33_ttm_fu13_like_local_evaluation.example.yaml \
  --output reports/c_stage_c33_ttm_fu13_like_local_evaluation.md
```

### 配置

新增默认配置 `configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml`：

- `stage`: `C3_3_single_candidate_open_model_local_evaluation`
- `safety_policy`: 默认 `allow_network: false`、`allow_download: false`、`allow_model_cache: false`、`allow_local_execution: false`、`allow_training: false`、`allow_write_processed: false`
- `prerequisites`: 引用 C3.2 explicit local execution design/status，不要求读取 C-MAPSS raw。
- `candidate`: 固定 `model_id: ttm`、`task_id: forecasting_residual`、`dataset_view: fu13_like_simulated_forecasting`
- `local_execution`: 默认缺失或 disabled。
- `metric_contract`: forecasting metrics 与 adapter/cache status，`leaderboard_allowed: false`
- `outputs`: report path

新增本机 opt-in 样例 `configs/local/c_stage_c33_ttm_fu13_like_local_evaluation.example.yaml`：

```yaml
stage: C3_3_single_candidate_open_model_local_evaluation
safety_policy:
  allow_network: false
  allow_download: false
  allow_model_cache: true
  allow_local_execution: true
  allow_training: false
  allow_write_processed: false
prerequisites:
  c32_design_doc: docs/superpowers/specs/2026-06-16-c32-explicit-local-execution-design.md
  c32_local_status: local_execution_baseline_reference_ready
candidate:
  model_id: ttm
  model_ref: ibm-granite/granite-timeseries-ttm-r2
  task_id: forecasting_residual
  dataset_view: fu13_like_simulated_forecasting
metric_contract:
  forecasting_metrics: [forecasting_mae, forecasting_rmse, residual_ranking]
  adapter_status_fields:
    - dependency_status
    - weight_status
    - adapter_status
    - runtime_seconds
    - input_shape
    - output_shape
    - actual_network_used
  leaderboard_allowed: false
local_execution:
  enabled: true
  model_cache_dir: hf_cache
  fu13_like:
    days: 3
    seed: 42
    context_length: 32
    prediction_length: 8
    max_windows: 60
    residual_top_k: 5
outputs:
  report: reports/c_stage_c33_ttm_fu13_like_local_evaluation.md
```

允许用户复制该样例并把 `allow_network` 与 `allow_download` 同时改为 true 做首次 cache 准备；只改 `allow_download: true` 而保持 `allow_network: false` 必须报配置错误。仓库默认示例和 README 推荐离线 cache-first。

### 执行流程

默认路径：

1. 读取 C3.3 config。
2. 验证 stage、single candidate、task、metric contract 和 safety policy。
3. 生成 contract report，不 import heavy runtime，不检查 cache，不运行 TTM。

显式本机路径：

1. 验证 `local_execution.enabled: true`、`allow_local_execution: true`、`allow_model_cache: true`。
2. 保持 `allow_training: false`、`allow_write_processed: false`。
3. 生成 FU13-like observations 和 forecasting windows。
4. 按 C3.2 同口径跑 baseline reference。
5. 构造 `AdapterExecutionContext`，调用 `TTMOpenModelAdapter.run_forecasting`。
6. 如果 TTM 返回 `AVAILABLE_AND_RAN`，计算 forecasting metrics 和 residual ranking。
7. 如果 TTM 返回 missing dependency、missing/blocked weights、unsupported shape 或 runtime failed，报告结构化状态，不把阶段视为不可用。
8. 报告中明确：C3.3 只验证 TTM forecasting adapter/cache 链路，不评价 C-MAPSS RUL，不生成 leaderboard。

C3.3 local path 会引用 C3.2 的 FU13-like baseline 口径，并在本阶段重新计算 baseline reference，保证同一批 local windows 可同时服务 baseline 与 TTM adapter evaluation。

### 报告

报告包含：

- Summary：stage、status、candidate、task、dataset view、decision。
- Safety Policy：所有 flags。
- C3.2 Anchor：引用 C3.2 的 C-MAPSS RUL baseline-only 结论与 FU13-like baseline 口径；C3.3 local path 会重新计算本阶段 baseline reference。
- Candidate Contract：TTM model ref、dependency requirements、cache dir、download policy。
- Baseline Forecasting Reference：robust / seasonal baseline metrics。
- TTM Adapter Execution：status、dependency_status、weight_status、adapter_status、runtime_seconds、input_shape、output_shape、actual_network_used、failure reason。
- TTM Forecasting Metrics：仅在 adapter available and ran 时输出 MAE/RMSE/residual ranking。
- Separated Metric Interpretation：forecasting-only，不与 RUL 合并。
- Invalid Claims：no production RUL、no production alarms、no maintenance recommendation、no leaderboard、no self-developed superiority。

### 状态定义

- `contract_ready_single_candidate_local_execution_blocked`: 默认配置；可进入本机 opt-in。
- `local_execution_ttm_forecasting_ready`: TTM adapter 可运行并产出 forecasting metrics。
- `local_execution_ttm_missing_dependency`: optional dependency 未安装。
- `local_execution_ttm_missing_or_blocked_weights`: cache/权重被 offline policy 阻塞或缺失。
- `local_execution_ttm_unsupported_window_shape`: adapter 与窗口 shape 不兼容。
- `local_execution_ttm_runtime_failed`: adapter runtime 抛出非 cache 类错误。
- `blocked_insufficient_fu13_like_windows`: FU13-like 参数无法产生足够窗口。

CLI 退出码约定：

- 配置错误、文件写入错误或 Python 异常返回 1。
- 默认 contract-only 状态返回 0。
- `local_execution_ttm_forecasting_ready` 返回 0。
- `local_execution_ttm_missing_dependency`、`local_execution_ttm_missing_or_blocked_weights`、`local_execution_ttm_unsupported_window_shape`、`local_execution_ttm_runtime_failed` 返回 0，因为它们是 C3.3 要记录的结构化 adapter/cache/依赖证据。
- `blocked_insufficient_fu13_like_windows` 返回 0，并在报告中给出需要调整 local execution 参数的原因。

### 测试策略

- 默认 config contract-only：不允许 network/download/cache/training/write processed，不实例化 TTM adapter。
- local config 是显式 opt-in：允许 model cache 和 local execution，但仍禁止 training / write processed。
- local config 若启用 execution 但禁用 model cache，应抛 config error。
- fake TTM adapter 成功路径：验证 baseline metrics、TTM metrics、residual ranking 和报告章节；residual ranking 复用现有 `forecasting_residual_ranking` 口径，按 sensor mean absolute residual 降序解释。
- fake TTM adapter missing dependency / missing weights 路径：验证结构化状态和报告 failure reason。
- insufficient FU13-like windows 路径：验证 blocked 状态。
- CLI `experiment c-stage-c33` 默认和 fake local 配置返回 0 并写报告。
- README / details / experiment scaffold 测试新增 C3.3 命令与文档入口。
- 全量 `uv run python -m pytest -q` 通过。

## 验收标准

- 默认 C3.3 CLI 可离线运行并生成 contract report。
- 显式本机配置只运行 TTM on FU13-like forecasting，不读取 C-MAPSS raw，不读取 FU13 real，不写 processed，不训练。
- 本机 TTM 缺依赖/缺 cache 时报告结构化状态，不伪造成功。
- TTM 成功时报告 forecasting metrics，但不生成 leaderboard。
- C-MAPSS RUL 继续 baseline-only，RUL 与 forecasting 指标分开解释。
- README 和 `details.md` 同步 C3.3 阶段入口、边界和下一步。
- 不提交 raw、zip、parquet、cache 或 generated report。

## 下一阶段建议

如果 C3.3 通过，下一阶段建议进入 C3.4：基于 C3.3 的 TTM 结果和 C2.2 frontier watchlist，只做“候选模型扩展是否值得”的决策评审。除非 C3.3 表明 TTM 链路可控且指标/失败原因有解释价值，否则不要扩大到 Chronos/TimesFM/Moirai；C-MAPSS RUL 仍保持 baseline-only，直到有明确 RUL adapter 设计。
