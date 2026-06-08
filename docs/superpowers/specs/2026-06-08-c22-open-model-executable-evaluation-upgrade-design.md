# C2.2 Open Model Executable Evaluation Upgrade Design

## Goal

C2.2 的目标是在 C2.1 已有 open model executable evaluation runner 基础上，把开源时序基础模型评测升级到 2025-2026 最新模型版本和可决策审计口径。

C2.1 已经完成统一入口、六模型登记、adapter contract 雏形、task matrix、audit、task attempt、cache manifest 和结构化失败报告。C2.2 不推翻这套结构，而是在其上增加三件事：

- 将核心模型目标版本升级到当前前沿：Chronos-2、TimesFM 2.5、Moirai 2.0 / Uni2TS 当前接口。
- 让优先模型在 FU13 真实窗口、可控 cache 和显式 opt-in 联网/下载边界下尽可能真实运行。
- 增加 frontier watchlist audit，记录 2025-2026 新模型是否值得进入 C2.2 实跑候选、C3 跨数据验证或 B 阶段缺口判断。

C2.2 的成功标准不是所有模型全部跑通，而是产出一份能支持决策的报告：哪些模型可运行，哪些模型需要依赖、权重、接口、窗口形状、任务头、许可证或资源补齐，哪些模型任务不匹配，哪些能力值得进入 C3 或 B 阶段判断。

## Non-Goals

C2.2 不做以下事项：

- 不接入公开数据集，不整理 C3 dataset registry。
- 不进入 B 阶段自研模型训练，不设计自研 backbone。
- 不做生产告警、RUL、维修建议、工单或维护闭环。
- 不把 frontier watchlist 全部提升为必跑模型。
- 不把某个模型跑通解释为模型选型终局。
- 不把联网下载、外部权重或本机 cache 加入默认 workflow。
- 不把本机已有 cache 当作隐式依赖。
- 不把外部模型失败简单解释为模型能力不足；必须区分依赖、权重、接口、窗口形状、任务头、许可证和资源限制。

## Current State

当前项目已经具备：

- FU13 canonical observations pipeline 和 `data/processed/fu13_real_observations.parquet`。
- FU13 数据诊断、baseline forecasting、TTM real-data forecasting 和 `leak_current_monitoring` 场景评测样例。
- C1 证据执行框架：`configs/c_stage_c1_execution.yaml` 和 `experiment c-stage-c1`。
- C2 开源模型系统评测入口：`configs/c_stage_c2_open_model_evaluation.yaml` 和 `experiment c-stage-c2`。
- C2.1 开源模型真实执行入口：`configs/c_stage_c21_executable_open_model_evaluation.yaml` 和 `experiment c-stage-c21`。
- `src/b08_model_core/adapters/open_models/` 中的 open model adapter contract 与六模型 adapter。
- C2.1 报告结构：adapter readiness table、model-task result matrix、failure taxonomy、cache manifest、C2 -> C3 handoff 和 C2 -> B decision notes。

C2.1 的限制是：核心模型仍以 2024 版本矩阵命名，Chronos / TimesFM / Moirai 的最新目标版本没有被显式建模；Time-MoE、Sundial、Timer-S1、Kairos、Toto、IBM FlowState / TSPulse、TabPFN-TS 等 2025-2026 模型也没有进入结构化审计。C2.2 的工作就是补上这层版本化目标和前沿模型审计，而不是重写 runner。

## Scope

C2.2 的范围包括：

- 新增 C2.2 独立配置、CLI 入口、runner wrapper、result schema 扩展、report renderer 和 tests。
- 复用 C2.1 的 `OpenModelAdapter` contract、窗口构建、baseline metrics、failure taxonomy、cache manifest 和默认 offline-safe 策略。
- 为核心模型增加 versioned target metadata：primary target、fallback target、model ref、expected package、license note、resource note、task fit。
- 将 Chronos adapter 目标升级为 Chronos-2 primary、Chronos-Bolt fallback。
- 将 TimesFM adapter 目标升级为 TimesFM 2.5。
- 将 Moirai / Uni2TS adapter 目标升级为 Moirai 2.0 / 当前 Uni2TS 接口。
- 保留 MOMENT / UniTS 的 representation、imputation 和 multi-task 接口核验定位。
- 新增 frontier watchlist audit，仅做结构化审计，不默认真实执行。
- 输出 C2.2 decision report，支撑 C2.2 -> C3 和 C2.2 -> B 判断。

C2.2 不应删除或破坏 C2 和 C2.1 入口。`experiment c-stage-c2` 和 `experiment c-stage-c21` 必须继续可用。

## Recommended Approach

采用“平衡升级路线”：

- TTM 作为 anchor / control，继续复核同口径 forecasting。
- Chronos-2 / Chronos-Bolt fallback 和 TimesFM 2.5 作为 priority real execution targets。
- Moirai 2.0 / Uni2TS、MOMENT、UniTS 作为 core run/review targets。
- Time-MoE、Sundial、Timer-S1 / Timer-XL、Kairos、Toto、IBM FlowState / TSPulse、TabPFN-TS 作为 frontier watchlist audit targets。

不采用保守路线，因为只升级原六模型会无法回应 2025-2026 前沿模型是否改变候选矩阵的问题。

不采用激进路线，因为把 watchlist 全部纳入真实 adapter 尝试，会让 C2.2 变成依赖、权重、GPU 和接口的大集成任务，削弱当前最重要的目标：让核心模型先产出可决策证据。

## Architecture

C2.2 应作为 C2.1 的窄升级模块，而不是新评测平台：

```text
configs/c_stage_c22_open_model_executable_upgrade.yaml
src/b08_model_core/experiments/c22_open_model_executable_upgrade.py
tests/test_c22_open_model_executable_upgrade.py
```

可选小型扩展：

```text
src/b08_model_core/adapters/open_models/
  versioned_targets.py
  frontier_watchlist.py
```

职责边界：

- `c22_open_model_executable_upgrade.py` 负责配置加载、versioned targets、priority/core/watchlist 分层、C2.1 runner 复用、watchlist audit、结果聚合、报告渲染和 CLI 返回策略。
- `versioned_targets.py` 如有需要，保存核心模型的目标版本、fallback、model ref、package hint、license note 和 resource note。
- `frontier_watchlist.py` 如有需要，保存 watchlist 审计条目和 audit taxonomy。
- 现有 C2.1 adapter 继续负责真实 import/load/run 尝试；C2.2 只补充目标版本和审计上下文。

## Model Target Matrix

C2.2 核心模型矩阵：

| model_id | C2.2 target | fallback | primary tasks | C2.2 role |
| --- | --- | --- | --- | --- |
| `ttm` | TTM / TinyTimeMixer current local adapter | none | forecasting | anchor |
| `chronos` | Chronos-2 | Chronos-Bolt | forecasting | priority real execution |
| `timesfm` | TimesFM 2.5 | previous TimesFM package/interface if needed | forecasting | priority real execution |
| `moirai_uni2ts` | Moirai 2.0 / current Uni2TS | Moirai 1.x interface if latest cannot run | probabilistic forecasting | core run/review |
| `moment` | MOMENT current open interface | none | representation, imputation | core interface |
| `units` | UniTS current open interface | none | representation, imputation, multi-task interface review | core interface |

Frontier watchlist：

| model_or_route | C2.2 handling | reason |
| --- | --- | --- |
| Time-MoE | audit only | 2025 MoE route, likely high dependency/resource cost |
| Sundial | audit, possible promotion if lightweight path is clear | 2025 strong TSFM candidate |
| Timer-S1 / Timer-XL | audit only | frontier long-context / billion-scale route, resource risk |
| Kairos | audit only | new adaptive / parameter-efficient TSFM route |
| Toto | audit only | observability / telemetry relevance |
| IBM FlowState / TSPulse | audit only | industrial/time-series foundation model relevance |
| TabPFN-TS | audit only | strong non-traditional zero-shot baseline candidate |

Watchlist targets are not C2.2 required real execution attempts unless the implementation explicitly promotes one under clear criteria.

## Config And CLI

C2.2 应新增默认离线安全配置：

```text
configs/c_stage_c22_open_model_executable_upgrade.yaml
```

建议结构：

```yaml
stage: C2_2_open_model_executable_upgrade
upstream_c21_config: configs/c_stage_c21_executable_open_model_evaluation.yaml

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

model_targets:
  ttm:
    role: anchor
    target: ttm_current_local_adapter
    tasks: [forecasting]
  chronos:
    role: priority_real_execution
    target: chronos_2
    fallback: chronos_bolt
    tasks: [forecasting]
  timesfm:
    role: priority_real_execution
    target: timesfm_2_5
    tasks: [forecasting]
  moirai_uni2ts:
    role: core_run_review
    target: moirai_2_0_current_uni2ts
    tasks: [forecasting]
  moment:
    role: core_interface
    target: moment_current_interface
    tasks: [representation, imputation]
  units:
    role: core_interface
    target: units_current_interface
    tasks: [representation, imputation]

frontier_watchlist:
  audit_only: true
  promote_to_real_execution: false
  targets:
    - time_moe
    - sundial
    - timer_s1_timer_xl
    - kairos
    - toto
    - ibm_flowstate_tspulse
    - tabpfn_ts

outputs:
  report: reports/c_stage_c22_open_model_executable_upgrade.md
  cache_manifest: reports/c_stage_c22_model_cache_manifest.md
```

新增 CLI：

```bash
uv run b08-model-core experiment c-stage-c22 \
  --config configs/c_stage_c22_open_model_executable_upgrade.yaml \
  --output reports/c_stage_c22_open_model_executable_upgrade.md
```

默认配置必须保持 `allow_network: false` 和 `allow_download: false`。联网真实执行只允许通过本机 opt-in 配置或显式 override，例如：

```text
configs/local/c_stage_c22_open_model_executable_upgrade.network.yaml
```

该本机配置可以开启：

```yaml
execution_policy:
  allow_network: true
  allow_download: true
```

`configs/local/` 下的联网配置不应成为默认测试、默认文档命令或仓库依赖。若后续提交样例，只能提交不含私有路径、token、权重信息的 template。

## Adapter Behavior

C2.2 复用 C2.1 的 adapter contract：

```text
inspect_environment(context) -> AdapterReadiness
load(context) -> LoadedAdapter
run_forecasting(windows, context) -> AdapterTaskOutput
run_representation(windows, context) -> AdapterTaskOutput
run_imputation(windows, mask_policy, context) -> AdapterTaskOutput
```

C2.2 不新增通用插件平台。需要增加的是 versioned target evidence：

- `target_model_ref`
- `fallback_model_ref`
- `target_package_hint`
- `target_license_note`
- `target_resource_note`
- `target_task_fit`
- `promotion_recommendation`

Chronos adapter：

- primary target 是 Chronos-2。
- fallback 是 Chronos-Bolt。
- 如果 dependency 或 interface 仍不能安全真实运行，必须记录具体 dependency/module/package、model ref、fallback 是否可尝试、失败阶段和下一步。

TimesFM adapter：

- primary target 是 TimesFM 2.5。
- 记录 package/API 是否支持当前 Python 环境、输入 shape、forecast horizon、quantile output 和 cache/download 边界。

Moirai / Uni2TS adapter：

- primary target 是 Moirai 2.0 / 当前 Uni2TS。
- 记录 license、probabilistic forecast output、输入 shape、patch/size 要求和模型权重状态。

MOMENT / UniTS adapter：

- 保留 representation / imputation / multi-task interface review。
- 不把 forecasting 作为 C2.2 必验任务，除非官方接口和当前 adapter 已经稳定。

## Frontier Watchlist Audit

Watchlist 审计不是简单论文清单，而是一个可提升为工程候选的结构化表。每个 watchlist target 至少记录：

- `model_or_route`
- `latest_known_version_or_paper`
- `primary_tasks`
- `repository_or_model_card`
- `package_availability`
- `weight_availability`
- `license_status`
- `resource_requirement`
- `input_output_fit`
- `fu13_task_fit`
- `default_c22_action`
- `promotion_condition`

推荐审计状态：

| status | meaning |
| --- | --- |
| `audit_only` | 只记录，不进入真实执行 |
| `promote_candidate` | 满足依赖、权重、license、接口和资源条件，可在后续提升为实跑 |
| `blocked_by_dependency` | 依赖或包不可稳定安装 |
| `blocked_by_weights` | 权重不可获得、过大、下载受限或 cache 不可控 |
| `blocked_by_license` | 许可证不适合当前路线 |
| `blocked_by_resource` | 本机资源明显不足 |
| `task_mismatch` | 任务与 FU13 当前 C2.2 口径不匹配 |
| `needs_research_review` | 信息不足，需要继续资料核对 |

C2.2 第一版 watchlist 默认不真实调用模型，不下载权重。

## Report Structure

C2.2 Markdown 报告应包含：

- Executive Summary
- Versioned Model Target Matrix
- Priority Real Execution Results
- Core Model-Task Result Matrix
- Frontier Watchlist Audit
- Failure Taxonomy
- Cache / Download Manifest
- C2.2 -> C3 Handoff
- C2.2 -> B Decision Notes
- Invalid Claims

报告必须明确：

- 哪些模型真实运行成功。
- 哪些模型失败但失败原因已经具体化。
- 哪些模型只是 watchlist audit，不应被解释为实跑失败。
- 哪些模型适合进入 C3 跨数据验证。
- 哪些缺口可能构成 B 阶段自研或轻量适配理由。
- 哪些结论不能用于生产告警、RUL、维修建议或自动工单。

## Success Criteria

C2.2 完成时应满足：

- 默认配置 offline-safe：`allow_network=false`、`allow_download=false`。
- 显式 opt-in 配置允许联网和首次下载，但必须写 cache manifest。
- TTM anchor 保持可复核。
- Chronos-2 / Chronos-Bolt fallback 和 TimesFM 2.5 至少进入优先真实执行尝试。
- Moirai 2.0、MOMENT、UniTS 至少完成真实尝试或具体失败归因。
- 所有核心模型不得停留在宽泛 `needs_review`。
- Watchlist 至少输出依赖、权重、接口、license、资源、任务匹配和是否建议提升为实跑候选。
- C2.2 报告能支持 C2.2 -> C3 和 C2.2 -> B 的下一步判断。
- C2 与 C2.1 现有入口继续可用。

## Testing

C2.2 应增加 focused tests：

- Config tests：默认配置离线安全，stage、upstream C2.1 config、model targets、watchlist 完整。
- Target matrix tests：priority/core/audit-only 分层正确。
- Runner tests：C2.2 能复用 C2.1 runner result，并补充 versioned target metadata。
- Watchlist tests：每个 watchlist target 输出结构化 audit record。
- Report tests：报告包含 versioned matrix、priority results、watchlist audit、failure taxonomy、handoff notes 和 invalid claims。
- CLI tests：`experiment c-stage-c22` 能写报告；strict 模式失败仍写报告。
- Regression tests：`experiment c-stage-c2` 和 `experiment c-stage-c21` 不被破坏。

测试不应依赖联网、外部权重或本机 cache。真实联网下载验证只能作为本机 opt-in 手工命令或单独记录，不进入默认 CI / pytest。

## Implementation Notes

实现时建议按以下原则推进：

- 先实现配置、target matrix、watchlist audit 和报告结构，再推进真实 adapter 版本升级。
- 不为 watchlist 建立真实 adapter，除非某个模型满足 promotion condition 且用户明确批准。
- 新 optional extras 只能在包名、版本、Python 兼容性和安装方式明确后加入 `pyproject.toml`。
- 任何模型权重下载必须通过显式 allow-download 配置，并写入 cache manifest。
- 真实 adapter 失败时，优先保留可决策信息，不让单模型失败中断整轮 C2.2 报告。

## User Review Gate

Spec review 通过后，需要用户 review 本文件并确认是否进入 implementation plan。下一步应调用 `superpowers:writing-plans`，为 C2.2 生成逐步执行计划。
