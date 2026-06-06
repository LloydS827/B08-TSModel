# C2.1 Open Model Executable Evaluation Design

## Goal

C2.1 的目标是把当前 C2 开源模型系统评测从 status-only runner 推进到 executable evaluation runner。当前 C2 已经完成统一入口、六模型登记、audit、model-task attempt 和结构化失败报告；C2.1 在此基础上增加真实 adapter 执行能力，让六个核心开源模型都进入同一窗口、同一任务、同一指标和同一报告口径下的真实执行尝试。

C2.1 的成功标准不是让六个模型全部成功运行，而是让每个模型从宽泛的 `needs_review` 或 status-only 记录推进到可审计的 executable evidence：成功模型输出可比指标，失败模型输出具体失败状态、失败阶段、依赖/权重/cache/接口证据和下一步处理建议。

核心目标：

- 定义最小 open model adapter contract，覆盖 forecasting、representation 和 imputation 三类任务。
- 新增 C2.1 executable runner，按真实 adapter 优先、结构化失败兜底的方式执行。
- 六个核心模型全部进入真实执行尝试：TTM、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS。
- 输出 C2.1 decision report，支撑 C2 -> C3 公开数据集验证和 C2 -> B 自研判断，但不直接做 C3 或 B。
- 保持项目默认路径可用：默认测试不依赖真实联网、外部权重或本机 cache。

## Non-Goals

C2.1 不做以下事项：

- 不接入公开数据集，不实现 C3 dataset schema registry。
- 不进入 B 阶段自研模型训练，不设计自研 backbone。
- 不做生产告警、RUL、维修建议、工单或维护闭环。
- 不把某个模型跑通解释为模型选型终局。
- 不强制所有模型支持所有任务。
- 不把外部模型依赖、模型权重或本机 cache 加入 Git。
- 不把本机已有 cache 当作隐式默认依赖。
- 不把联网下载失败解释为模型能力失败；必须区分依赖、权重、接口、窗口形状和真实运行能力。

## Current State

当前项目已经具备以下基础：

- FU13 canonical observations pipeline。
- FU13 数据诊断、baseline forecasting、TTM real-data forecasting 和 `leak_current_monitoring` 场景评测样例。
- C0 最小证据契约：`configs/c_stage_minimum_evidence.yaml`。
- C1 证据执行框架：`configs/c_stage_c1_execution.yaml` 和 `experiment c-stage-c1`。
- C2 开源模型系统评测入口：`configs/c_stage_c2_open_model_evaluation.yaml` 和 `experiment c-stage-c2`。
- C2 六个核心模型 registry、audit record、model-task attempt、failure taxonomy 和 Markdown report。

当前 C2 的限制是：runner 仍以 status-only 为主，没有真正把六个外部模型都接入 adapter 执行。C2.1 的工作就是补上这条真实执行闭环。

## Scope

C2.1 的范围包括：

- 新增 C2.1 配置、CLI、runner、result schema、report renderer 和 tests。
- 新增或拆出 open model adapter contract。
- 为六个模型建立 adapter 模块或 adapter stub，执行真实 import/load/run 尝试。
- 复用 FU13 canonical observations、C2 六模型 registry、现有窗口构建和 baseline metric 计算。
- 在允许联网配置下支持模型权重下载或加载，并记录 cache manifest。
- 继续保留 C2 status-only 入口，不破坏 `experiment c-stage-c2`。

C2.1 的主任务映射如下：

| model_id | display_name | C2.1 主任务 |
| --- | --- | --- |
| `ttm` | TTM / TinyTimeMixer | forecasting |
| `chronos` | Chronos / Chronos-Bolt | forecasting |
| `timesfm` | TimesFM | forecasting |
| `moirai_uni2ts` | Moirai / Uni2TS | forecasting |
| `moment` | MOMENT | representation, imputation |
| `units` | UniTS | representation, imputation |

MOMENT 和 UniTS 的 representation 与 imputation 都是 C2.1 主任务，必须各自进入真实执行尝试。MOMENT 和 UniTS 的 forecasting 可作为 optional task 记录，但不作为 C2.1 第一版验收主任务。C2.1 不要求每个模型跑所有三类任务。

## Architecture

建议新增 C2.1 窄模块和 open model adapter 目录：

```text
src/b08_model_core/experiments/c21_executable_open_model_evaluation.py
src/b08_model_core/adapters/open_models/
  __init__.py
  base.py
  ttm.py
  chronos.py
  timesfm.py
  moirai_uni2ts.py
  moment.py
  units.py
```

职责边界：

- `c21_executable_open_model_evaluation.py` 负责任务编排、配置加载、registry 继承、窗口构建、baseline、runner、结果聚合、报告渲染和 CLI 返回策略。
- `adapters/open_models/base.py` 定义 adapter contract、任务输入输出对象、readiness/result/error schema。
- 各模型 adapter 模块只处理该模型的 import、dependency check、model load、task execution 和 output normalization。
- 现有 `c2_open_model_evaluation.py` 保留 status-only 行为，C2.1 复用其模型 registry 和状态语义，但不把六模型真实执行细节继续塞进 C2 模块。

## Adapter Contract

Adapter contract 应保持最小但足够，不做泛化插件平台。建议每个 open model adapter 实现以下能力：

```text
inspect_environment(context) -> AdapterReadiness
load(context) -> LoadedAdapter
run_forecasting(windows, context) -> AdapterTaskOutput
run_representation(windows, context) -> AdapterTaskOutput
run_imputation(windows, mask_policy, context) -> AdapterTaskOutput
```

其中：

- `inspect_environment` 检查 Python 依赖、模型包、权重/cache、联网策略、许可证/接口待审状态，并返回结构化 readiness。
- `load` 在配置允许时加载模型或权重；失败必须能分类为依赖、权重/cache、接口、运行时或 timeout。
- `run_forecasting` 输入统一 `ModelWindow` 列表，输出预测数组、可选概率/分位数和运行元信息。
- `run_representation` 输入统一窗口，输出每个窗口的 embedding 或 representation summary。
- `run_imputation` 输入窗口和 deterministic mask policy，输出重构值、mask 和重构指标所需信息。

每个 adapter 不支持的任务必须显式返回 `unsupported_task`，不能退回宽泛 `needs_review`。

## Model-Task Metrics

Forecasting 指标：

- `mae`
- `rmse`
- `interval_coverage` 或 quantile metrics，如模型提供概率/分位数输出
- `runtime_seconds`
- `used_windows`
- `failed_windows`

Representation 指标：

- `embedding_count`
- `embedding_dim`
- `finite_value_ratio`
- optional probe / clustering note，仅记录为后续承接，不在 C2.1 默认实现或解释为语义学习能力
- `runtime_seconds`

Imputation 指标：

- `reconstruction_mae`
- `reconstruction_rmse`
- `mask_ratio`
- `masked_value_count`
- `runtime_seconds`

Baseline 必须始终保留：

- Forecasting 对照：`RobustStageForecaster`。
- Representation 对照：`statistical_embedding`。
- Imputation 对照：`simple_reconstruction_baseline`，使用 deterministic mask policy。

## Config And CLI

C2.1 应新增独立配置文件：

```text
configs/c_stage_c21_executable_open_model_evaluation.yaml
```

该配置是仓库提交的默认配置，必须离线安全，不允许隐式联网或下载权重：

```yaml
stage: C2_1_executable_open_model_evaluation
upstream_c2_config: configs/c_stage_c2_open_model_evaluation.yaml

dataset:
  fu13_observations: data/processed/fu13_real_observations.parquet
  fu13_config: configs/fu13_real_data_schema.yaml
  boundary: internal_fu13_no_raw_data_committed

window:
  window_mode: cross-stage
  context_length: 90
  prediction_length: 16
  max_windows: 40
  mask_ratio: 0.2
  seed: 7

execution_policy:
  allow_network: false
  allow_download: false
  strict_model_success: false
  record_failure: true
  do_not_over_claim: true
  continue_on_model_failure: true
  timeout_seconds_per_model: 900

model_cache_policy:
  cache_dir: hf_cache
  reuse_existing_cache: true
  write_cache_manifest: true

outputs:
  report: reports/c_stage_c21_executable_open_model_evaluation.md
  cache_manifest: reports/c_stage_c21_model_cache_manifest.md
```

联网真实执行应通过单独的 opt-in 本机配置或显式 override 执行，例如：

```text
configs/local/c_stage_c21_executable_open_model_evaluation.network.yaml
```

该本机配置可以设置：

```yaml
execution_policy:
  allow_network: true
  allow_download: true
```

`configs/local/` 下的联网配置不应成为默认测试或默认文档命令依赖；如后续提交样例，只能提交不含私有路径和权重信息的 template。

新增 CLI：

```bash
uv run b08-model-core experiment c-stage-c21 \
  --config configs/c_stage_c21_executable_open_model_evaluation.yaml \
  --output reports/c_stage_c21_executable_open_model_evaluation.md
```

第一版不强制新增独立 `c-stage-c21-check` 命令。runner 内部先执行 readiness check，再执行真实 adapter。后续如果真实依赖准备流程变复杂，再单独设计 check/prepare 命令。

## Network And Cache Policy

C2.1 的默认仓库配置禁止联网和下载，保证默认路径可复现：

- `allow_network: false`
- `allow_download: false`

C2.1 同时允许本机真实联网执行，但必须由 opt-in 配置或显式 override 开启：

- `allow_network: true`
- `allow_download: true`

行为规则：

- CLI 不隐式改变配置。
- 如果配置禁止联网，runner 必须离线执行，并把缺失依赖或权重记录为结构化失败。
- 如果配置允许联网，adapter 可以下载模型权重或触发官方加载流程，但必须记录模型来源、模型卡/权重标识、cache 目录和运行环境。
- 即使允许联网，模型失败也不等于阶段失败；默认 `strict_model_success: false`。
- 如果 `strict_model_success: true`，任一核心模型声明的任一 C2.1 主任务 attempt 不是 `available_and_ran` 时 CLI 返回非零，但仍尽量写报告。对 MOMENT 和 UniTS，这意味着 representation 与 imputation 两项主任务都必须成功。
- 报告必须区分 `config_allows_network`、`config_allows_download`、`actual_network_used`、`cache_dir`、`model_weight_ref`、`dependency_status` 和 `adapter_runtime_status`。

cache manifest 至少记录：

| 字段 | 含义 |
| --- | --- |
| `model_id` | C2.1 模型 ID |
| `model_ref` | 模型卡、仓库或权重引用 |
| `cache_dir` | 本机 cache 目录 |
| `local_availability` | 本机是否发现可用权重/cache |
| `download_allowed` | 配置是否允许下载 |
| `actual_network_used` | 本次是否实际使用网络，未知时记录 `unknown` |
| `known_limitations` | 许可证、接口、依赖或权重限制 |

## Model Execution References

C2.1 implementation plan 应在实际编码前核对以下模型引用和 adapter mode。表中引用用于第一轮真实尝试定位，不代表许可证或接口审查已经完成。

| model_id | intended package/import | model or repo ref | first-attempt adapter mode |
| --- | --- | --- | --- |
| `ttm` | `tsfm_public`, `torch`, `transformers` | `ibm-granite/granite-timeseries-ttm-r2` | reuse existing TTM forecasting path where possible |
| `chronos` | `chronos` or official Chronos-Bolt package path | Chronos / Chronos-Bolt official repo or model card | forecasting |
| `timesfm` | `timesfm` | TimesFM official package/model ref | forecasting |
| `moirai_uni2ts` | `uni2ts` | Moirai / Uni2TS official repo or model card | probabilistic forecasting |
| `moment` | `momentfm` | MOMENT official package/model ref | representation and imputation |
| `units` | UniTS official package/import path to verify | UniTS official repo/model ref | representation and imputation |

## Runner Flow

C2.1 runner 流程：

```text
load config
  -> load upstream C2 registry / six model specs
  -> load FU13 observations
  -> build shared windows
  -> build shared baselines
  -> for each model-task attempt:
       inspect_environment
       load adapter/model
       execute task
       normalize output
       compute metrics
       record runtime/cache/dependency evidence
       catch and classify failures
  -> render C2.1 report
  -> render optional cache manifest
  -> return CLI exit code by strict_model_success policy
```

Model failure isolation is required. 一个模型失败不能阻止其他模型继续执行，除非配置、数据、窗口构建或报告写入失败。

## Result Schema And Status Semantics

C2.1 task status：

| status | meaning |
| --- | --- |
| `available_and_ran` | adapter 真实执行成功，并输出可计算指标 |
| `missing_dependency` | Python 包或运行时依赖缺失 |
| `missing_or_blocked_weights` | 权重缺失、下载被禁用、下载失败或 cache 不可用 |
| `unsupported_task` | adapter 或官方接口不支持当前任务 |
| `unsupported_window_shape` | 当前窗口、变量数、horizon、mask 或 token 形式不被模型支持 |
| `runtime_failed` | 真实执行时出现异常，已捕获并记录 |
| `timeout` | 单模型或单任务执行超过配置超时 |
| `license_or_interface_needs_review` | 许可证或官方接口边界不足以安全执行 |
| `skipped_by_config` | 配置主动跳过；核心模型主任务默认不应出现 |

每个失败结果至少记录：

- `model_id`
- `task_id`
- `status`
- `failure_stage`: `inspect`、`load`、`execute`、`normalize`、`metric`、`report`
- `failure_reason`
- `error_type`
- `error_detail`
- `dependency_status`
- `weight_status`
- `input_shape`
- `expected_shape_or_constraint`
- `adapter_name`
- `runtime_seconds`

成功结果至少记录：

- `model_id`
- `task_id`
- `status=available_and_ran`
- `metrics`
- `baseline_metrics`
- `input_shape`
- `output_shape`
- `runtime_seconds`
- `adapter_name`
- `model_ref`
- `cache_dir`
- `actual_network_used`

## Report Structure

C2.1 报告建议结构：

```text
# C2.1 Executable Open Model Evaluation Report

## Report Metadata
## Executive Summary
## Adapter Readiness Table
## Model-Task Result Matrix
## Forecasting Comparison
## Representation And Imputation Results
## Failure Taxonomy
## Cache Manifest
## C2 -> C3 Handoff
## C2 -> B Decision Notes
## Invalid Claims
```

`Executive Summary` 必须包含：

- `available_and_ran` 的模型列表。
- 按失败类别分组的模型列表。
- task coverage summary。
- strongest comparable forecasting result，如有。
- representation / imputation availability summary。
- C2 -> C3 recommendation。
- C2 -> B caution / no-go / pending evidence。

`Forecasting Comparison` 必须对照 TTM、Chronos、TimesFM、Moirai / Uni2TS 与 `RobustStageForecaster`，在同一 window policy 下报告 MAE/RMSE 和可选概率指标。

`Representation And Imputation Results` 必须对照 MOMENT、UniTS 与 simple statistical / reconstruction baseline，报告 embedding/reconstruction 指标和 mask policy。

`Invalid Claims` 必须包含：

- 不得解释为生产告警。
- 不得解释为 FU13 RUL。
- 不得解释为自动维修建议。
- 不得解释为模型选型终局。
- 不得解释为自研训练 Go 结论。

## CLI Exit Policy

默认策略：

- 配置、数据窗口、runner 编排和报告写入成功时返回 0。
- 单个或多个模型失败时默认仍返回 0，并在报告中结构化记录。
- 数据集缺失、窗口无法构建、配置无效、报告无法写入时返回非零。
- `strict_model_success=true` 时，任一核心模型声明的任一 C2.1 主任务 attempt 未 `available_and_ran` 返回非零，但仍尽量写报告。对 MOMENT 和 UniTS，representation 与 imputation 两项主任务都纳入 strict 判断。

## Testing Strategy

C2.1 测试分三层。

Unit tests：

- C2.1 config loader。
- C2.1 registry 继承 C2 六个核心模型。
- adapter contract 输入输出 schema。
- task result schema。
- failure classification。
- report renderer。
- strict_model_success exit policy。

Mocked executable tests：

- fake adapter `available_and_ran`。
- fake adapter `missing_dependency`。
- fake adapter `missing_or_blocked_weights`。
- fake adapter `unsupported_task`。
- fake adapter `unsupported_window_shape`。
- fake adapter `runtime_failed`。
- fake adapter `timeout`。
- runner 在单模型失败时继续执行其他模型。

Integration / smoke tests：

- 使用小 fixture 数据构建窗口。
- 运行 C2.1 CLI 并生成报告。
- 默认不联网、不下载真实权重。
- 可选本机真实执行命令不作为默认 pytest 验收。

默认自动化测试不得依赖真实联网、外部权重或本机 Hugging Face cache。真实联网执行路径作为本机人工验证或后续显式 smoke workflow。

## Acceptance Criteria

C2.1 验收标准：

1. 新增 `experiment c-stage-c21` CLI，能读取 C2.1 config 并生成报告。
2. 六个核心模型都出现在 C2.1 registry、adapter readiness table 和 model-task result matrix。
3. 每个核心模型都必须完成声明的 C2.1 主任务真实执行尝试；forecasting 模型各一项，MOMENT 和 UniTS 各两项：
   - TTM: forecasting
   - Chronos / Chronos-Bolt: forecasting
   - TimesFM: forecasting
   - Moirai / Uni2TS: forecasting
   - MOMENT: representation / imputation
   - UniTS: representation / imputation
4. 成功执行的模型输出可比指标、输入输出形状、runtime 和权重/cache 信息。
5. 失败模型输出具体失败状态，不停留在泛泛 `needs_review`。
6. 报告包含 forecasting comparison、representation/imputation results、failure taxonomy、cache/network evidence、C2 -> C3 handoff、C2 -> B decision notes 和 invalid claims。
7. 默认测试不依赖联网或真实权重。
8. 现有 `experiment c-stage-c2` status-only 入口继续可用。
9. 全量 pytest 通过。

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| 六模型依赖生态差异大，安装或加载失败 | adapter 逐模型隔离，失败结构化记录，不阻断其他模型 |
| 外部模型权重过大或下载不稳定 | 允许配置联网，但记录 cache manifest；默认测试不依赖下载 |
| 官方接口变化导致 adapter 失效 | 报告记录模型版本、依赖状态、接口失败阶段和错误类型 |
| CPU/GPU 资源不足导致运行过慢 | 配置 `timeout_seconds_per_model`，并记录 `timeout` |
| 把依赖或下载失败误判为模型能力失败 | failure taxonomy 区分 dependency、weight/cache、interface、window shape 和 runtime |
| 报告被误读为生产能力或自研 Go 结论 | 固定 invalid claims 和 C2 -> B pending/no-go notes |
| C2.1 改动破坏 C2 默认入口 | 新增 C2.1 模块和 CLI，C2 status-only 入口保留回归测试 |

## Implementation Handoff

后续 implementation plan 应按小步执行，但不得缩小 C2.1 的六模型范围。建议计划拆分：

1. C2.1 config、result schema、status semantics、report renderer 和 tests。
2. open model adapter contract 和 fake adapter 测试。
3. C2.1 runner 编排：shared windows、shared baselines、model-task execution、failure isolation。
4. TTM adapter 作为 anchor/control。
5. Forecasting 组 adapter：Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS。
6. Representation / imputation 组 adapter：MOMENT、UniTS。
7. CLI、cache manifest、strict mode 和 report 完整性。
8. 默认 pytest、C2 回归、可选本机联网 smoke 命令文档。

每一步都应保留系统默认可用性；真实外部模型失败时记录证据，不以模拟成功替代真实尝试。
