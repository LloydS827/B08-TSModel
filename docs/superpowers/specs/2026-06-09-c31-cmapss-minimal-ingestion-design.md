# C3.1 NASA C-MAPSS Minimal Ingestion And Schema Validation Design

## Goal

C3.1 的目标是把 C3 registry 中的一个公开数据集做深一点，验证它能否在可控来源、许可、下载和本机数据边界下进入 B08 canonical observation / task / split 体系。

本轮锁定 **NASA PCoE #6 Turbofan Engine Degradation Simulation Data Set**，也就是经典 C-MAPSS 涡扇发动机退化数据。选择它的原因是：它有清晰的 unit / run-to-failure 结构、operational settings、sensor channels 和 RUL / degradation 任务语义，最适合验证 B08 从 FU13 真机样例走向公开退化 benchmark 的最小接入闭环。

C3.1 不追求多个公开数据集覆盖，也不运行开源模型跨数据评测。它只回答一个问题：在不破坏默认安全边界的情况下，C-MAPSS 是否能被审计、最小下载、schema mapping、split / leakage 校验并生成可复核报告。

## Current State

项目当前已经完成：

- FU13 canonical observations、cycle 重构、baseline / TTM forecasting 和 `leak_current_monitoring` 场景样例。
- C1、C2、C2.1、C2.2 的开源模型证据与执行入口。
- C3 public dataset registry：`configs/c_stage_c3_public_dataset_registry.yaml`、`experiment c-stage-c3`、registry validation 和报告渲染。
- `nasa_cmapss` 已在 C3 registry 中作为 `open_benchmark_candidate`，但 source、license、training use、schema mapping 和 split policy 仍需要进入 C3.1 复核。

当前缺口是：C-MAPSS 仍停留在 registry 条目，没有变成可执行的 source/license preflight、最小下载边界、schema mapping dry-run、split/leakage guard 和 C3.2 Go / No-Go 报告。

## Source Calibration

C3.1 只锁定经典 C-MAPSS，不把相近入口混在一起：

| Source | C3.1 handling | Reason |
| --- | --- | --- |
| NASA PCoE #6 Turbofan Engine Degradation Simulation Data Set | primary target | 经典 C-MAPSS，包含 engine unit、cycle、operational settings、sensor channels、train/test/RUL 文件，适合最小接入。 |
| PHM08 Challenge Data Set | calibration note only | 也是 NASA PCoE 页面上的相近数据，但下载和 RUL label 可用性存在额外限制，不作为第一轮目标。 |
| NASA Open Data Portal C-MAPSS Aircraft Engine Simulator Data | calibration note only | 入口可能指向 C-MAPSS / C-MAPSS40K 的不同版本，且页面可能出现 license 或 data availability 不明确，不作为 C3.1 下载入口。 |
| C-MAPSS-2 / real flight conditions | watchlist only | 更复杂、更接近真实飞行条件，适合 C3.2 或后续第二公开数据集，不进入本轮最小接入。 |

C3.1 spec 使用以下 source URLs 作为实现阶段的核对入口：

- NASA PCoE data set repository: `https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/`
- NASA PCoE #6 current download target: `https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip`
- NASA Open Data Portal calibration URL: `https://data.nasa.gov/dataset/c-mapss-aircraft-engine-simulator-data`
- NASA NTRS C-MAPSS-2 calibration URL: `https://ntrs.nasa.gov/citations/20205001125`

实现阶段不得把 source calibration note 当成可下载数据入口。只有 primary target 通过 source/license preflight 后，才允许进入最小下载和 mapping。
download target 只作为 C3.1 配置中的 target URL 记录；默认配置不得访问该 URL。

## Expected Classic C-MAPSS Files

C3.1 的完整数据集范围锁定为经典 C-MAPSS 的四个 subset：FD001、FD002、FD003、FD004。每个 subset 需要 train、test 和 RUL 三类标准文件，因此完整本机接入目标是 12 个文件：

| Subset | Required files | Role |
| --- | --- | --- |
| FD001 | `train_FD001.txt`, `test_FD001.txt`, `RUL_FD001.txt` | single operating condition, single fault mode |
| FD002 | `train_FD002.txt`, `test_FD002.txt`, `RUL_FD002.txt` | multiple operating conditions, single fault mode |
| FD003 | `train_FD003.txt`, `test_FD003.txt`, `RUL_FD003.txt` | single operating condition, multiple fault modes |
| FD004 | `train_FD004.txt`, `test_FD004.txt`, `RUL_FD004.txt` | multiple operating conditions, multiple fault modes |

实现阶段可以使用人工构造的 synthetic fixture 覆盖一到两个 subset 来测试 parser、mapping 和 leakage guard，但不能把单个 subset 的 fixture 通过解释为 C3.1 完成。报告必须区分：

- `full_classic_cmapss_validated`：四个 subset 的 12 个文件均存在并完成 schema / split 校验。
- `partial_subset_validated`：只有显式选择的 subset 通过本机 dry-run，可用于调试，但不能作为 C3.2 Go。
- `blocked_by_missing_raw_files`：未满足当前配置要求的 expected files。

## Scope

C3.1 包括：

- 新增一个 C3.1 配置，描述 C-MAPSS source、license、download、mapping、split 和 output 边界。
- 新增 source/license preflight：确认 primary source、citation、下载 URL、license/training/redistribution 状态和是否允许本轮最小接入。
- 新增最小下载边界：只下载或读取 C3.1 需要的 C-MAPSS 文件，默认不联网、不下载；联网和下载必须显式 opt-in。
- 新增 C-MAPSS schema mapping dry-run：把 unit、cycle、operational settings、sensor channels、RUL 和 subset metadata 映射到 B08 canonical observation 语义。
- 新增 split/leakage guard：按 engine unit / trajectory / subset 切分，禁止同一 unit 或 run-to-failure 轨迹跨 train/validation/test。
- 新增 C3.1 报告：输出 source/license 结论、文件摘要、schema mapping 状态、split policy、leakage checks、任务支持和 C3.2 Go / No-Go。
- 同步 README 和 `details.md`，但 README 只记录已存在或即将实现的 C3.1 入口与安全边界，不写夸大能力。

C3.1 不包括：

- 不下载多个公开数据集。
- 不提交 C-MAPSS 原始数据、派生 parquet、cache 或本机报告。
- 不运行 TTM、Chronos、TimesFM、Moirai、MOMENT、UniTS 或其他开源模型。
- 不训练自研模型。
- 不把 C-MAPSS RUL 结果解释为 FU13 现场 RUL、生产告警或自动维修建议。
- 不替代 C2.2 的开源模型真实执行结论。

## Safety And Data Boundary

C3.1 默认配置必须保持：

```yaml
allow_network: false
allow_download: false
allow_local_raw_data: false
allow_write_processed: false
```

这些开关必须能独立表达不同边界，不得把“读取本机 raw files”强制绑定为“联网下载”：

| allow_network | allow_download | allow_local_raw_data | allow_write_processed | Valid use |
| --- | --- | --- | --- | --- |
| false | false | false | false | 默认 preflight，只输出 source/license/download boundary 报告。 |
| true | false | false | false | 只做 live source preflight，例如检查 NASA PCoE 页面和 target URL 可达性；不得下载、读取 raw files 或写 processed。 |
| false | false | true | false | 读取已存在的本机 raw files，做 schema mapping dry-run 和 split/leakage report，不联网、不下载、不写 processed。 |
| false | false | true | true | 读取本机 raw files，并允许写 ignored processed summary / dry-run artifact。 |
| true | true | true | false | 显式联网下载到 ignored raw dir，读取 raw files，但不写 processed。 |
| true | true | true | true | 显式联网下载、读取 raw files、写 ignored processed artifact。 |

以下组合必须被拒绝为不安全或无意义配置：

- `allow_download: true` 但 `allow_network: false`。
- `allow_download: true` 但 `allow_local_raw_data: false`。
- `allow_write_processed: true` 但 `allow_local_raw_data: false`。

完整 opt-in 示例：

```yaml
allow_network: true
allow_download: true
allow_local_raw_data: true
allow_write_processed: true
```

但 opt-in 必须满足以下前置条件：

- `source_status` 不是 `needs_review`、`unavailable` 或 `deprecated`。
- `license_status`、`training_use_status` 和 `redistribution_status` 已在配置和报告中明确；如果仍为 `needs_review` 或 `unknown`，runner 必须输出 `blocked_by_license_review`，不得下载或 mapping。
- 下载目录必须位于 ignored 本机路径，例如 `data/public/cmapss/raw/`。
- 派生输出必须位于 ignored 本机路径，例如 `data/processed/cmapss/`。
- 报告可以写入 `reports/`，但默认报告不应提交到 Git，除非项目后续明确需要提交样例报告。
- 原始文件、zip、txt、csv、parquet、manifest cache 和本机下载日志不得提交。

如果用户本机已经有 C-MAPSS 文件，C3.1 仍必须先通过 source/license preflight；不能因为文件已存在就跳过来源和许可审计。

## Proposed Artifacts

实现阶段建议新增：

```text
configs/c_stage_c31_cmapss_minimal_ingestion.yaml
src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py
tests/test_c31_cmapss_minimal_ingestion.py
```

建议 CLI：

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output reports/c_stage_c31_cmapss_minimal_ingestion.md
```

默认 CLI 只做 preflight 和 blocked / ready report，不下载数据。真实下载或读取本机 raw files 需要配置显式 opt-in。

## Config Contract

C3.1 配置应包含以下顶层字段：

| Field | Meaning |
| --- | --- |
| `stage` | 固定为 `C3_1_cmapss_minimal_ingestion` |
| `dataset_id` | 固定为 `nasa_cmapss` |
| `source` | primary source、calibration sources、citation 和 source status |
| `license_review` | license、training use、redistribution、citation requirement 和 review decision |
| `download_policy` | allow_network、allow_download、raw_dir、checksum policy、expected files |
| `mapping_policy` | subset、unit、cycle、setting、sensor、RUL、canonical field mapping |
| `split_policy` | unit / trajectory split、validation policy、forbidden leakage modes |
| `outputs` | report、optional processed directory、optional manifest |

License review 必须支持以下 decision：

| Decision | Behavior |
| --- | --- |
| `approved_for_schema_validation` | 允许 C3.1 读取本机 raw files 并做 mapping dry-run，不代表允许训练或再分发。 |
| `approved_for_research_training` | 允许后续 C3.2 作为研究训练 / 评测候选，但仍不允许提交数据。 |
| `blocked_by_license_review` | 不允许下载、读取 raw files 或 mapping，只输出 blocked report。 |
| `needs_review` | 与 blocked 等价，直到人工确认。 |

## C-MAPSS Schema Mapping

经典 C-MAPSS 文件通常包含：

- train trajectories：engine unit、cycle、operational settings、sensor readings。
- test trajectories：engine unit、cycle、operational settings、sensor readings。
- RUL labels：test unit 的 remaining useful life target。
- subsets：如 FD001、FD002、FD003、FD004，代表不同 operating condition / fault mode 组合。

C3.1 canonical observation mapping：

| C-MAPSS field | B08 canonical field | Notes |
| --- | --- | --- |
| subset id, e.g. FD001 | `stage` 或 dataset metadata | 不应直接作为 label；用于 condition/fault mode context 和 split summary。 |
| engine unit id + file role | `device_id` | 必须避免 train/test 本地 unit id 冲突，建议格式 `cmapss_<subset>_<file_role>_unit_<id>`。 |
| cycle index | `timestamp` | C-MAPSS 没有真实 wall-clock timestamp；C3.1 必须生成 deterministic pseudo timestamp，同时可在 metadata 中保留原始 cycle index。 |
| subset + file role + engine unit id | `batch_id` | 表示一条 train run-to-failure trajectory 或 test partial trajectory，建议与 `trajectory_id` 一致。 |
| operational setting columns | `sensor_id` 或 metadata | 可作为 `setting_1..setting_3`，domain 为 `operational_condition`。 |
| sensor columns | `sensor_id` | 可作为 `sensor_01..sensor_21`，domain 为 `turbofan_sensor`。 |
| numeric reading | `value` | 必须转 float，保留缺失和异常解析记录。 |
| train complete trajectory | `degradation_label` | 可以标记为 `run_to_failure_known`，但不等于 FU13 故障标签。 |
| computed RUL | `failure_proxy` or metadata | 不建议逐行写 bool；RUL 更适合存入 task metadata / target table。 |

由于 B08 当前 canonical observation schema 没有 `rul` 专用列，C3.1 不应把 RUL 生硬塞进 `failure_proxy`。推荐输出两类 artifact：

1. canonical observations dry-run summary：只验证观测级字段是否能映射。
2. task target metadata summary：记录 per unit / per cycle 的 RUL target 构造规则和哪些任务可以使用。

如果实现阶段确实需要写入 parquet，应保持 processed output ignored，并把 RUL target 存成单独 metadata 或 target table，而不是改变 FU13 现有 schema。

Trajectory identity 规则固定为：

```text
trajectory_id = cmapss_<subset>_<file_role>_unit_<unit_id>
device_id = trajectory_id
batch_id = trajectory_id
```

其中 `file_role` 只能是 `train` 或 `test`。经典 C-MAPSS 的 train/test 文件各自有本地 unit 编号，不能把 `FD001 train unit 1` 和 `FD001 test unit 1` 视为同一条轨迹。split 和 leakage guard 都应使用 `trajectory_id`，而不是只使用 raw unit id。

Pseudo timestamp 规则固定为：

```text
timestamp = 2000-01-01 00:00:00 UTC + cycle_index seconds
```

其中 `cycle_index` 来自 C-MAPSS 原始 cycle 列，必须为正整数。同一 subset / unit 内 timestamp 应随 cycle 单调递增。这个 timestamp 只用于满足 B08 canonical observation schema 和窗口构造接口，不代表真实采样时间；报告必须写明这是 deterministic pseudo timestamp。

RUL target metadata 规则固定为：

```text
train_last_cycle = max(cycle_index for each train trajectory)
train_rul_at_cycle = train_last_cycle - cycle_index

test_last_observed_cycle = max(cycle_index for each test trajectory)
test_final_rul = value from RUL_<subset>.txt for the same test unit order
test_rul_at_cycle = test_final_rul + (test_last_observed_cycle - cycle_index)
```

C3.1 不使用 capped RUL。若后续 C3.2 需要 capped RUL，例如常见的 125-cycle cap，必须作为单独 task config 显式声明，不能改变 C3.1 target metadata。RUL target 只能进入 target metadata / target table，不得进入 observation input feature。

## Split And Leakage Guard

C3.1 必须把 split policy 作为核心产物，而不是实现细节。

最低要求：

- 同一 `trajectory_id` 不得同时出现在多个 split。
- 同一 `subset + file_role + raw unit id` 不得同时出现在多个 split。
- `train` 和 `test` 文件中的相同 raw unit id 不是同一条轨迹，允许分别存在于 train-derived split 和 test split，但报告必须按 `trajectory_id` 展示。
- train / validation / test 的 split 必须按 `trajectory_id` 分组。
- 如果从 train trajectories 中切 validation，必须按 unit 切，不得按窗口随机切。
- test trajectories 与 RUL label 合并时，只能在 target construction 阶段使用 RUL 文件；不得把 target RUL 作为输入 feature。
- operational setting 和 subset metadata 可以作为 context，但如果后续 task 是 condition/fault probe，相关字段必须从输入中排除或在报告中说明。
- 相邻 cycle window 不得跨 split。

Runner 应输出 leakage check summary：

| Check | Required result |
| --- | --- |
| trajectory id overlap across splits | zero overlap |
| subset + file_role + raw unit overlap across splits | zero overlap |
| trajectory overlap across splits | zero overlap |
| target columns in input features | zero forbidden columns |
| RUL file used before target construction | false |
| window adjacency leakage | zero cross-split adjacency |

## Report Structure

`reports/c_stage_c31_cmapss_minimal_ingestion.md` 应包含：

- C3.1 Summary
- Source And License Preflight
- Source Calibration Notes
- Download Boundary And Local Paths
- Expected C-MAPSS Files
- Raw File Presence / Download Status
- Schema Mapping Dry-Run
- Canonical Observation Compatibility
- RUL / Degradation Target Metadata
- Split Policy And Leakage Guard
- Supported Tasks And Metrics
- Invalid Claims
- C3.2 Go / No-Go

报告必须能清楚表达四个顶层状态：

- `blocked`
- `ready_for_local_mapping`
- `schema_validated_pending_training_use_review`
- `schema_validated_ready_for_c32`

顶层状态和细分原因的关系固定为：

| Top-level status | Allowed detailed reasons |
| --- | --- |
| `blocked` | `blocked_by_source_review`, `blocked_by_license_review`, `blocked_by_download_policy`, `blocked_by_missing_raw_files`, `blocked_by_raw_schema_mismatch`, `blocked_by_mapping_schema`, `blocked_by_leakage_guard`, `blocked_by_label_semantics` |
| `ready_for_local_mapping` | source/license approved, local raw read allowed, expected files pending or partially present |
| `schema_validated_pending_training_use_review` | `full_classic_cmapss_validated`; no leakage guard failure; `license_review.decision` is `approved_for_schema_validation`; training/evaluation use is not yet approved |
| `schema_validated_ready_for_c32` | `full_classic_cmapss_validated`; no leakage guard failure; `license_review.decision` is `approved_for_research_training` or equivalent explicit training/evaluation use approval |

`partial_subset_validated` 可以出现在 detailed readiness 中，但不得提升为 `schema_validated_pending_training_use_review` 或 `schema_validated_ready_for_c32`。

每个 blocked reason 还应带一个 remediation category，避免把工程问题误写成合规问题：

| Detailed reason | Remediation category |
| --- | --- |
| `blocked_by_source_review` | source_review |
| `blocked_by_license_review` | license_review |
| `blocked_by_download_policy` | config_policy |
| `blocked_by_missing_raw_files` | local_data_presence |
| `blocked_by_raw_schema_mismatch` | parser_or_raw_schema |
| `blocked_by_mapping_schema` | canonical_mapping |
| `blocked_by_leakage_guard` | split_policy |
| `blocked_by_label_semantics` | target_semantics |

## Error Handling

C3.1 runner 应把失败写成结构化状态，而不是直接把阶段判为失败：

| Failure | Status |
| --- | --- |
| primary source URL missing or not approved | `blocked_by_source_review` |
| license/training/redistribution decision missing | `blocked_by_license_review` |
| network/download requested without opt-in | `blocked_by_download_policy` |
| expected raw files missing | `blocked_by_missing_raw_files` |
| malformed raw file shape | `blocked_by_raw_schema_mismatch` |
| canonical fields missing after mapping | `blocked_by_mapping_schema` |
| unit overlap or target leakage detected | `blocked_by_leakage_guard` |
| RUL target construction ambiguous | `blocked_by_label_semantics` |

默认离线路径下，缺少 raw files 是正常报告状态，不应导致 CLI 崩溃。只有配置语法错误、未知 enum、必填字段缺失或不安全 opt-in 才应抛出配置错误。

## Testing Strategy

C3.1 实现应先写测试，再写实现。最低测试覆盖：

- 默认配置 `allow_network: false` / `allow_download: false` / `allow_local_raw_data: false`，CLI 能生成 blocked / preflight report。
- source/license decision 为 `needs_review` 时，runner 不下载、不读取 raw files、不做 mapping。
- source/license approved 但 raw files 缺失时，状态为 `blocked_by_missing_raw_files`。
- 使用小型 synthetic C-MAPSS fixture 时，mapping 能生成 B08 required observation columns。
- RUL target 不进入 observation input feature。
- split guard 拒绝同一 unit 跨 split。
- split guard 拒绝窗口相邻泄漏。
- malformed raw shape 输出 `blocked_by_raw_schema_mismatch`。
- README / details 文档包含 C3.1 入口和默认安全边界。
- 现有 C1/C2/C2.1/C2.2/C3 CLI help 不被破坏。

测试 fixture 必须是人工构造的小型文本样例，不使用真实 C-MAPSS 原始数据，不提交任何公开数据文件。

## Documentation Policy

C3.1 文档只新增本 spec 和后续 implementation plan。实现阶段允许更新：

- `README.md`：增加 C3.1 命令、默认不下载数据边界、source/license preflight 说明。
- `details.md`：更新当前阶段、当日完成内容和下一步计划。

不新增独立 `docs/cmapss.md`、`docs/c3.1.md` 或大型数据集说明文档。C3.1 的细节沉淀在 spec、plan、config 和 generated report 中。

## Success Criteria

C3.1 完成时应满足：

- `experiment c-stage-c31` 存在，并能在默认离线配置下生成可读报告。
- 默认路径不联网、不下载、不读取本机 raw data、不写 processed data。
- 配置可以显式记录 source/license preflight，并在未批准时阻止下载和 mapping。
- 对 synthetic fixture 的 schema mapping dry-run 能验证 required canonical observation columns。
- split/leakage guard 能阻止 unit overlap、trajectory overlap、target leakage 和 window adjacency leakage。
- 报告能明确区分 blocked、ready for local mapping、schema validated pending training-use review 和 schema validated ready for C3.2。
- README 和 `details.md` 已同步 C3.1 状态与安全边界。
- 没有公开数据原始文件、派生 parquet、cache 或本机下载日志进入 Git。
- C1/C2/C2.1/C2.2/C3 入口保持可用。

## Handoff

C3.1 完成后，若 C-MAPSS source/license、schema mapping、split/leakage guard 均通过，可进入 C3.2：在同一 split policy 下尝试开源模型跨数据评测。

如果 C3.1 被 source/license 阻塞，则下一步不是绕过下载，而是回到 C3 registry：要么补齐人工许可确认，要么选择 PRONOSTIA / IMS Bearing 作为新的单数据集深入对象。

如果 C3.1 schema mapping 通过但 C-MAPSS 任务语义与 FU13 差距过大，则 C3.2 应把 C-MAPSS 限定为公开 RUL / degradation benchmark，不把结果外推到 FU13 生产告警或现场维修建议。
