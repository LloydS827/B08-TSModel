# C3 Public Dataset Registry And Cross-Dataset Validation Design

## Goal

C3 的目标是建立公开预测性维护 / 工业时序数据进入 B08 评测体系的准入框架，而不是立刻下载大量数据或跑大规模模型。

本轮 C3 采用 **dataset registry first** 路线：先把候选公开数据集的来源、许可、任务语义、schema mapping、split policy、泄漏风险和 go/no-go 条件记录清楚，再决定哪些数据进入下一轮最小下载、转换和跨数据验证。

少量最新数据源校准作为 registry 的一部分完成：只用于确认现有候选清单是否过时，或是否存在明显应加入 watchlist 的 2025-2026 工业设备健康 / 预测性维护数据源。不把本轮扩大成独立大型调研。

## Current State

项目当前已经具备：

- FU13 真实设备数据 pipeline、canonical observation schema、cycle 重构和 baseline / TTM forecasting 验证。
- C1 最小证据执行框架。
- C2 / C2.1 / C2.2 开源模型评测入口和结构化失败记录。
- `docs/research/predictive-maintenance-dataset-matrix.md`：已有第一批候选数据集，包括 FU13、NASA C-MAPSS、NASA IMS Bearing、PRONOSTIA / FEMTO-ST、Tennessee Eastman Process。
- `docs/research/task-metric-matrix.md`：已有 forecasting、imputation、representation、weak-label、fault classification、RUL 等任务和指标边界。
- `configs/c_stage_minimum_evidence.yaml` 中已有 `open_data_pm_mapping_v1` 证据项，要求公开数据进入前完成 official source、license、schema、label 和 split policy 审计。

当前缺口是：公开数据仍停留在研究矩阵和候选描述，没有形成可执行、可测试、可追溯的 registry。C3 第一轮要补齐这层结构，而不是直接把公开数据接入训练。

## Scope

本轮 C3 包括：

- 新增一个机器可读 dataset registry 配置。
- 为 registry 增加字段完整性和安全边界验证。
- 从现有候选数据集起步，建立第一批 registry 条目。
- 为每个条目记录 task family、label semantics、schema mapping 状态、split policy 和 invalid claims。
- 增加少量最新数据源校准字段，用于记录是否需要把新数据源加入 watchlist。
- 输出一个简洁可读的 C3 registry 报告，汇总哪些数据可进入下一轮、哪些需要补齐来源 / license / mapping。

本轮 C3 不包括：

- 不下载公开数据原始文件。
- 不提交公开数据或派生 parquet。
- 不实现完整 schema mapper。
- 不跑开源模型跨数据评测。
- 不进入 B 阶段自研模型设计。
- 不把公开数据结果解释为 FU13 现场能力、生产告警、RUL 精确估计或维修建议。

## Documentation Policy

为避免文档系统继续膨胀，本轮只保留两个 C3 产物：

1. `configs/c_stage_c3_public_dataset_registry.yaml`
   - 机器可读 registry。
   - 作为后续 C3 下载、mapping、评测的唯一配置入口。

2. `reports/c_stage_c3_public_dataset_registry.md`
   - registry 的可读摘要报告。
   - 由 CLI 或 helper 生成，记录准入结论、缺口和下一步动作。

不新增单独的 `docs/c3-public-dataset-registry.md`、`docs/c3-cross-dataset-validation-design.md` 或其他旁支说明。长期说明继续沉淀在 README、`details.md` 和本 spec 中。

## Registry Contract

每个 dataset registry 条目必须包含以下字段：

| 字段 | 含义 |
| --- | --- |
| `dataset_id` | 稳定唯一标识，例如 `fu13_internal`, `nasa_cmapss`, `ims_bearing` |
| `display_name` | 人类可读名称 |
| `dataset_role` | `internal_anchor`, `open_benchmark_candidate`, `watchlist_candidate` |
| `source_type` | `internal`, `official_public`, `paper_hosted`, `repository`, `unknown` |
| `official_source_url` | 官方或 primary source URL；未知时必须标记为 `needs_review` |
| `source_status` | `verified`, `needs_review`, `unavailable`, `deprecated` |
| `license_status` | `verified`, `needs_review`, `restricted`, `unknown` |
| `redistribution_status` | `allowed`, `not_allowed`, `needs_review`, `unknown` |
| `training_use_status` | `allowed`, `research_only`, `needs_review`, `not_allowed`, `unknown` |
| `task_families` | 可支持任务族，例如 forecasting、imputation、fault classification、RUL |
| `label_semantics` | 标签含义、置信度和限制 |
| `schema_mapping_status` | `mapped`, `partial`, `planned`, `blocked`, `needs_review` |
| `canonical_mapping_notes` | 与 B08 canonical observation schema 的映射说明 |
| `split_policy` | 按 unit / run / device / time / condition 切分的策略 |
| `leakage_risks` | 同一 unit/run/fault trajectory 泄漏等风险 |
| `allowed_metrics` | 当前标签语义允许使用的指标 |
| `go_no_go_prerequisites` | 进入下一轮下载 / mapping / 评测前必须满足的条件 |
| `invalid_claims` | 禁止解释，例如生产告警、FU13 已具备 RUL、自动维修建议 |
| `next_action` | 下一步动作 |
| `risk_level` | `low`, `medium`, `high` |

字段允许保留 `needs_review`，但不得省略。C3 的价值之一就是把未知项显式暴露，而不是用空字段或模糊描述掩盖。

## Initial Dataset Set

第一批 registry 条目从现有研究矩阵起步：

| dataset_id | 初始角色 | C3 用途 |
| --- | --- | --- |
| `fu13_internal` | internal anchor | 保持真实设备 pipeline 和现场语义基准 |
| `nasa_cmapss` | open benchmark candidate | RUL / run-to-failure / degradation trend 候选 |
| `ims_bearing` | open benchmark candidate | bearing degradation / fault process 候选 |
| `pronostia_femto` | open benchmark candidate | bearing accelerated degradation / RUL 候选 |
| `tennessee_eastman_process` | open benchmark candidate | process monitoring / fault classification / anomaly 候选 |

少量最新数据源校准只允许新增 `watchlist_candidate` 条目，除非其 official source、license、任务语义和 split policy 均已清楚。watchlist 不进入默认下载和评测。

## C3 Flow

C3 第一轮流程：

1. 加载 registry 配置。
2. 验证所有 dataset 条目字段完整性。
3. 验证安全边界：不得把 `license_status: unknown` 或 `training_use_status: unknown` 的数据标记为可训练；不得把 `source_status: needs_review` 的数据标记为 verified。
4. 验证 task mapping：每个 task family 必须能映射到 `task-metric-matrix.md` 中的任务层级，或标记为 `task_mapping_needs_review`。
5. 验证 split policy：run-to-failure / RUL 数据必须有 unit/run 级 split，工业过程故障数据必须声明故障轨迹或工况泄漏风险。
6. 生成 C3 registry 报告。
7. 报告输出 go/no-go：哪些数据可进入下一轮最小下载与 schema mapping，哪些继续 needs_review，哪些只保留 watchlist。

## Report Structure

`reports/c_stage_c3_public_dataset_registry.md` 应包含：

- Registry Summary
- Dataset Readiness Table
- Source And License Audit
- Task And Metric Mapping
- Canonical Schema Mapping Status
- Split Policy And Leakage Guard
- Latest Source Calibration Notes
- Go / No-Go For Next C3 Loop
- Invalid Claims

报告不得声称任何公开数据已经被下载、清洗、映射或用于训练，除非对应实现和 artifact 已经存在。

## CLI Shape

推荐新增实验入口：

```bash
uv run b08-model-core experiment c-stage-c3 \
  --config configs/c_stage_c3_public_dataset_registry.yaml \
  --output reports/c_stage_c3_public_dataset_registry.md
```

第一版 CLI 只做 registry validation 和 report rendering，不做数据下载。

## Success Criteria

C3 第一轮完成时应满足：

- `configs/c_stage_c3_public_dataset_registry.yaml` 存在，并覆盖初始五个数据集条目。
- 每个条目都有 source、license、training use、task、schema mapping、split policy、invalid claims 和 next action 字段。
- 字段完整性和安全边界有自动测试。
- `experiment c-stage-c3` 能生成 registry 报告。
- 报告能明确区分：ready for next mapping、needs source/license review、task mapping review、watchlist only。
- 默认 workflow 不下载公开数据，不提交数据文件，不改变现有 C1/C2/C2.1/C2.2 入口。

## Handoff

C3 第一轮完成后，下一轮可在 registry 结果基础上选择一到两个数据集进入最小下载 / schema mapping / dry-run validation。只有 registry 条目满足 source、license、task mapping 和 split policy 前置条件时，才允许进入真实数据工程。

B 阶段仍然不在本轮启动。只有当 C3 后续跨数据验证证明开源模型在关键任务上存在稳定缺口，且缺口不能通过模型选择、轻量 adapter、依赖补齐或任务口径调整解决时，才进入 B 阶段自研设计。
