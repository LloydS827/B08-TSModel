# B08 能源设备时空智能样板

## 项目定位

B08 是公司时空智能在能源设备时序方向的核心样板项目，目标是把真实设备数据、统一观测表、模型窗口、baseline、开源基础时序模型、候选信号和评测报告连接成可复现链路，为设备状态理解、运行优化建议输入、异常候选识别和后续系统级协同提供证据。基础模型评测是项目的重要技术路线，但项目目标不是追求模型排行榜，而是判断开源模型复用、轻量适配和条件性自研的工程可行性。

在公司 MAS 中，A 对应时空智能。船舶制造偏空间，重点是空间可达、大型构件空间约束、工位布局和仿真验证；能源偏时序，重点是设备状态、运行过程、时间序列、调度约束和状态演化。B08 是 A 能力在能源侧的证据项目。

本文档是项目入口，面向首次阅读者说明项目定位、快速开始、标准运行命令、关键目录和安全边界。阶段进展、每日更新和下一步计划维护在 [details.md](details.md)。

当前主线可以概括为：

```text
设备时序数据
  -> canonical observations
  -> cycle / stage / window
  -> baseline / open model evaluation
  -> candidate signals
  -> 工程解释与专家复核
  -> 运行优化建议输入或系统协同事件候选
```

`FU13` 是当前第一台真实设备样例，用于验证从现场多 CSV 导出到 canonical observations、模型窗口和评测报告的完整链路。`leak_current_monitoring` 是模型输出进入业务语境的验证样例，不代表生产告警、故障概率、RUL 或维修建议已经完成。

## 输出层级与接口

B08 当前按四个层级组织输出：

| 层级 | 输出 | 当前支撑 |
| --- | --- | --- |
| 数据层 | canonical observations、cycle 重构、窗口生成、质量标记 | FU13 observations、cycle / window、数据诊断 |
| 评测层 | baseline、TTM、MOMENT、Chronos、TimesFM、Moirai 等模型适配性证据 | C1、C2、C2.1、C2.2、C3、C3.1、C3.2、C3.3 |
| 信号层 | residual、trend、spike、representation、imputation 候选信号 | `leak_current_monitoring`、C1 task evidence |
| 应用输入层 | 设备状态解释输入、异常候选、运行优化建议输入、系统协同事件候选 | `candidate_signal_report`、B08 -> S01 event candidate |

对外接口保持草案级口径，详见 [候选信号与系统事件接口草案](docs/candidate-signal-and-system-event-interface.md)：

- B08 -> B06：canonical observations、cycle / window 和质量标记形成 `equipment_timeseries_observation_package` profile。
- B08 -> S01：候选信号转为 system event candidate，例如设备状态变化候选、风险候选和运行优化建议输入；字段包含设备、时间、阶段、信号、置信度、影响范围、建议动作和复核状态。
- B08 -> IP：支撑 P0-06“设备时序标准观测表”、P0-07“周期重构与窗口生成”、P0-08“设备时序基础模型适配性评测”。

## 当前可复现资产

项目当前已经具备：

- FU13 真实多 CSV 数据装配：生成 `data/processed/fu13_real_observations.parquet`。
- FU13 observations、canonical observation schema 验证、连续炉 cycle / window 重构和数据诊断报告。
- baseline 与 TTM 在 FU13 真实窗口上的同口径 forecasting 验证。
- `leak_current_monitoring` 场景评测样例：输出 residual candidate signal。
- C1 证据执行框架：统一 E1 forecasting residual、E2 representation、E3 imputation 的报告口径。
- C2/C2.1/C2.2 开源模型适配性证据入口：覆盖核心模型 audit、task attempt、adapter 尝试、版本化目标矩阵、frontier watchlist audit 和结构化失败记录。
- C3/C3.1/C3.2/C3.3 公开数据、跨数据 contract 与单候选本机评测：验证 C-MAPSS RUL baseline evaluation、FU13-like forecasting reference 和 TTM adapter/cache evidence 的分离指标口径，不生成 leaderboard。
- `uv` + `pytest` 的本地可复现研发验证路径。

当前 FU13 canonical observations 事实基础：

| 项目 | 当前值 |
| --- | ---: |
| observations | 4,126,789 |
| sensors | 8 |
| stages | 8 |
| reconstructed cycles | 428 |
| complete cycles | 247 |
| `good` rows | 3,391,823 |
| `unassigned_cycle` rows | 529,790 |
| `invalid` rows | 205,176 |

## 快速开始

需要 Python 3.11+。项目建议使用 `uv` 管理 Python 环境，依赖锁定在 `uv.lock`。

```bash
uv sync --extra dev
uv run python -m pytest -q
```

TTM 和其他开源基础模型依赖均为 optional dependency。默认开发环境不安装大模型依赖，不下载权重，不改变本机 cache。

运行 TTM 推理时再安装：

```bash
uv sync --extra dev --extra foundation-ttm
```

模型权重和 Hugging Face cache 建议放在本机目录，例如 `hf_cache/`。cache、真实数据、生成 parquet 和临时报告不提交到 Git。

## 标准运行流程

### 1. 装配 FU13 canonical observations

把 FU13 现场导出的多 CSV 文件放在 ignored 的本机目录：

```text
data/real/
```

当前文件名和字段映射来自 `configs/fu13_real_data_schema.yaml`。

```bash
uv run b08-model-core real-data assemble-fu13 \
  --input-dir data/real \
  --config configs/fu13_real_data_schema.yaml \
  --output data/processed/fu13_real_observations.parquet \
  --report reports/real_data_validation.md
```

canonical observation schema 摘要：

| 字段 | 含义 |
| --- | --- |
| `timestamp` | 采样时间 |
| `device_id` | 设备 ID，例如 `FU13` |
| `batch_id` | 批次或重构批次 |
| `stage` | 工艺阶段 |
| `sensor_id` | 规范化传感器 ID |
| `value` | 数值读数 |
| `unit` | 工程单位 |
| `domain` | 物理域，例如 mechanical、thermal、atmosphere |
| `quality_flag` | good、missing、invalid、maintenance 等质量标记 |
| `degradation_label` | 弱退化标签，默认 `normal` |
| `failure_proxy` | 弱故障代理标签 |

### 2. 运行数据诊断

```bash
uv run b08-model-core real-data diagnose-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_scenario_diagnostics.md
```

诊断报告用于检查 scenario 行数、invalid 行数、传感器覆盖和阶段覆盖。当前 scenario 是指标分组，不是 scenario-filtered 建窗。

### 3. 运行 baseline / TTM forecasting

baseline 命令：

```bash
uv run b08-model-core real-data forecast-fu13 --model baseline \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_baseline_forecasting.md \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40
```

TTM 离线 cache 命令：

```bash
HF_HOME=hf_cache uv run b08-model-core real-data forecast-fu13 --model ttm \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_ttm_forecasting.md \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --model-cache-dir hf_cache \
  --no-download
```

如果需要首次下载权重，必须显式允许下载，把 `--no-download` 改为 `--allow-download`。

### 4. 运行业务场景评测样例

`leak_current_monitoring` 只使用 `LeakElec` 作为核心传感器，并比较 related stages、waiting stage、质量标记过滤和 baseline/TTM 同口径 forecasting residual。

```bash
uv run b08-model-core real-data evaluate-scenario \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_leak_current_scenario_evaluation_baseline.md \
  --scenario leak_current_monitoring \
  --model baseline \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --rolling-window-size 8
```

TTM 版本在同一命令中把 `--model baseline` 改为 `--model ttm`，并补充 `--model-cache-dir hf_cache --no-download`。

## C 阶段实验入口

C 阶段先做最小证据实验和开源模型适配性证据，不直接进入大规模自研训练，也不生成 leaderboard。

C 阶段最小证据契约保存在 `configs/c_stage_minimum_evidence.yaml`，用于约束 C1-C2 之前的证据包、任务口径和 Go / No-Go 检查项。

### C1. 证据执行框架

```bash
uv run b08-model-core experiment c-stage-c1 \
  --config configs/c_stage_c1_execution.yaml \
  --output reports/c_stage_c1_evidence_report.md
```

C1 默认执行 `E1_forecasting_residual`、`E2_representation` 和 `E3_imputation`，用于统一任务、指标和报告口径。

### C2. 开源模型适配性证据

```bash
uv run b08-model-core experiment c-stage-c2 \
  --config configs/c_stage_c2_open_model_evaluation.yaml \
  --output reports/c_stage_c2_open_model_evaluation.md
```

C2 固定审计并尝试 TTM、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS，用于判断依赖、adapter、任务口径和候选信号输出是否具备工程适配性。模型失败写入结构化状态，不等同于阶段失败，也不用于模型排行榜。

### C2.1. 开源模型真实执行适配性入口

```bash
uv run b08-model-core experiment c-stage-c21 \
  --config configs/c_stage_c21_executable_open_model_evaluation.yaml \
  --output reports/c_stage_c21_executable_open_model_evaluation.md
```

C2.1 在默认离线安全边界下执行六类 executable adapters / task matrix，并把失败原因写入结构化分类。它验证的是开源模型复用链路是否可控，而不是生成 leaderboard。默认配置保留 `allow_network: false` 和 `allow_download: false`；联网、下载、权重路径和 cache 只能通过显式本机 opt-in 启用。

### C2.2. 升级版开源模型真实执行与适配性审计

```bash
uv run b08-model-core experiment c-stage-c22 \
  --config configs/c_stage_c22_open_model_executable_upgrade.yaml \
  --output reports/c_stage_c22_open_model_executable_upgrade.md
```

C2.2 是 C2.1 的升级入口：补充版本化核心模型目标矩阵、frontier watchlist audit、cache manifest 和可决策报告。报告服务于复用、轻量适配或条件性自研的 Go / No-Go，而不是跨模型排名。详细阶段说明和下一步执行计划见 [details.md](details.md)，设计与实现计划见文档入口中的 C2.2 spec / plan。

### C3. 公开数据 registry 与跨数据验证准备

```bash
uv run b08-model-core experiment c-stage-c3 \
  --config configs/c_stage_c3_public_dataset_registry.yaml \
  --output reports/c_stage_c3_public_dataset_registry.md
```

C3 第一轮只验证公开数据 registry、来源/许可证/任务/schema/split 边界和报告，不下载公开数据、不提交数据文件、不运行模型训练。

### C3.1. NASA C-MAPSS 最小接入与 schema validation

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output reports/c_stage_c31_cmapss_minimal_ingestion.md
```

C3.1 锁定 NASA PCoE #6 经典 C-MAPSS，验证 source/license preflight、最小下载边界、schema mapping dry-run、RUL target metadata、split/leakage guard 和 C3.2 Go / No-Go。默认配置保持：

```yaml
allow_network: false
allow_download: false
allow_local_raw_data: false
allow_write_processed: false
```

2026-06-10 source/license review 见 [C3.1 C-MAPSS Source And License Review](docs/reviews/2026-06-10-c31-cmapss-source-license-review.md)；license evidence update 见 [C3.1 C-MAPSS License Evidence Update](docs/reviews/2026-06-10-c31-cmapss-license-evidence-update.md)。2026-06-11 local raw mapping review 见 [C3.1 C-MAPSS Local Raw Mapping Review](docs/reviews/2026-06-11-c31-cmapss-local-raw-mapping-review.md)。当前结论是 NASA PCoE #6 source 和 download target 已完成校准，Zenodo CC BY 4.0 记录已提供可复核授权依据；在 explicit local raw mapping review 中，经典 C-MAPSS 12 个 raw text 文件通过 schema validation、RUL metadata 和 split/leakage guard，状态为 `schema_validated_ready_for_c32`，readiness detail 为 `full_classic_cmapss_validated`。C3.1 不再阻塞 C3.2 设计，可进入 C3.2 open model cross-dataset evaluation 的设计阶段。

默认路径不下载公开数据、不读取本机 raw files、不写 processed data、不运行模型训练。local raw opt-in 只通过 [configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml](configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml) 这样的显式本机配置开启；仍只允许读取 ignored 本机数据目录或生成 ignored 派生产物，不能提交 raw、zip、parquet、cache 或生成报告。

### C3.2. Open model cross-dataset evaluation

```bash
uv run b08-model-core experiment c-stage-c32 \
  --config configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml \
  --output reports/c_stage_c32_open_model_cross_dataset_evaluation.md
```

C3.2 第一轮是 cross-dataset evaluation contract scaffold：把 C-MAPSS classic RUL、FU13 real forecasting evidence、FU13-like simulated forecasting、baseline / open model candidates、metric contract 和 Go / No-Go 写成默认安全报告。默认状态为 `contract_ready_local_execution_blocked`，表示可以进入下一步 local execution design，但本轮不运行真实评测，不把 RUL 与 forecasting 合并为单一排名。

默认配置保持：

```yaml
allow_network: false
allow_download: false
allow_local_raw_data: false
allow_model_cache: false
allow_training: false
allow_write_processed: false
```

默认路径不下载公开数据、不读取 C-MAPSS raw、不读取 FU13 real、不检查 model cache、不实例化 open model adapter、不运行模型训练、不计算模型分数、不生成 leaderboard。

显式本机执行路径使用 ignored 的本机 C-MAPSS raw 目录：

```bash
uv run b08-model-core experiment c-stage-c32 \
  --config configs/local/c_stage_c32_explicit_local_execution.example.yaml \
  --output reports/c_stage_c32_explicit_local_execution.md
```

该 explicit local execution 需要用户先把 C-MAPSS classic raw text 文件放在 `data/public/cmapss/raw` 下；这些 raw、zip、parquet、cache 和生成报告都不提交到 Git。成功报告状态为 `local_execution_baseline_reference_ready`，只运行 C-MAPSS RUL baseline evaluation 和 FU13-like forecasting reference。

本机执行仍不下载公开数据、不写 processed data、不检查 model cache、不运行 open model adapter、不训练、不生成 leaderboard。RUL metrics 和 forecasting metrics separated：C-MAPSS RUL 使用 RUL MAE / RMSE / NASA score；FU13-like forecasting 使用 forecasting MAE / RMSE / residual ranking；二者不合成为单一排名。

### C3.3. Single-candidate open model local evaluation

默认 contract-only 入口：

```bash
uv run b08-model-core experiment c-stage-c33 \
  --config configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml \
  --output reports/c_stage_c33_single_candidate_open_model_local_evaluation.md
```

C3.3 在 C3.2 explicit local execution 之后只验证一个开源模型候选：TTM on FU13-like forecasting。默认状态为 `contract_ready_single_candidate_local_execution_blocked`，默认路径不联网、不下载、不检查 model cache、不实例化 TTM、不运行模型训练、不写 processed data、不生成 leaderboard。

显式本机 TTM 执行入口：

```bash
HF_HOME=hf_cache uv run b08-model-core experiment c-stage-c33 \
  --config configs/local/c_stage_c33_ttm_fu13_like_local_evaluation.example.yaml \
  --output reports/c_stage_c33_ttm_fu13_like_local_evaluation.md
```

该 explicit local opt-in 会重跑 FU13-like baseline reference，然后只尝试 TTM adapter on FU13-like forecasting，并记录 dependency status、weight status、adapter status、runtime、input/output shape、actual network used 和 download allowed not verified。C-MAPSS RUL remains baseline-only：C3.3 不在 C-MAPSS RUL 上运行 open model adapter，C-MAPSS RUL 仍沿用 C3.2 的 RUL baseline evaluation。RUL metrics 和 forecasting metrics separated：RUL MAE / RMSE / NASA score 与 forecasting MAE / RMSE / residual ranking 不合并为单一排名。

本阶段仍不下载公开数据、不读取本机 raw files、不写 processed data、不运行模型训练、不生成 leaderboard，不提交 raw / cache / report。任何本机权重、cache 或联网下载尝试都必须通过显式本机配置进入，并在报告中保留结构化证据；生成的 Markdown report、模型 cache 和 raw / zip / parquet 文件仍保持 ignored。

## 项目边界

当前不能推出：

- 设备故障概率。
- RUL 精确估计。
- 维修建议。
- 生产告警。
- 自动工单。
- 自研基础模型已经优于开源模型。

原因是项目仍缺少真实故障标签、维修记录、停机事件标签、寿命标签和退化过程定义。维修记录、生产告警和现场维护闭环属于应用侧后续承接事项，不应被写成当前 C 阶段的唯一 blocker。

## 关键目录

```text
AGENTS.md                               # Agent 工作规则和阶段边界
details.md                              # 项目进展、更新日志和下一步台账
uv.lock                                 # uv 生成的可复现 Python 依赖锁文件
configs/
  fu13_real_data_schema.yaml            # FU13 真实多 CSV 装配配置
  c_stage_c*_*.yaml                     # C 阶段实验配置
data/
  real/                                 # 本机真实数据目录，ignored
  processed/                            # 生成 parquet，ignored
docs/
  research/                             # 研究资产：论文、数据集、任务指标、训练路线
  superpowers/specs/                    # 已批准的阶段设计文档
  superpowers/plans/                    # 阶段执行计划
  ttm-real-data-evaluation.md           # TTM 真实数据能力复核报告
  leak-current-scenario-evaluation.md   # 漏液电流监测场景评测摘要
reports/
  model_core_evaluation.md              # 可跟踪报告
  model_route_decision.md               # 可跟踪报告
  real_*.md                             # 本机临时报告，ignored
src/b08_model_core/
  simulation/                           # FU13-like 数据生成
  tasks/                                # schema 和窗口构建
  baselines/                            # 稳健 baseline
  evaluation/                           # benchmark 和候选模型矩阵
  real_data/                            # 真实数据配置、装配、诊断与 forecasting
  experiments/                          # C 阶段实验入口
tests/                                  # 回归测试
hf_cache/                               # 本机 Hugging Face cache，ignored
```

## 文档入口

- [项目进展台账](details.md)：当前阶段、每日更新、下一步计划。
- [A 阶段研究资产索引](docs/research/index.md)
- [项目主线与研发路线收束设计](docs/superpowers/specs/2026-06-04-project-mainline-roadmap-refactor-design.md)
- [C2 开源模型评测设计](docs/superpowers/specs/2026-06-05-c2-open-model-evaluation-design.md)
- [C2.1 开源模型真实执行设计](docs/superpowers/specs/2026-06-06-c21-open-model-executable-evaluation-design.md)
- [C2.2 开源模型真实执行升级设计](docs/superpowers/specs/2026-06-08-c22-open-model-executable-evaluation-upgrade-design.md)
- [C2.2 开源模型真实执行升级计划](docs/superpowers/plans/2026-06-08-c22-open-model-executable-evaluation-upgrade-plan.md)
- [C3 公开数据 registry 设计](docs/superpowers/specs/2026-06-09-c3-public-dataset-registry-design.md)
- [C3.1 C-MAPSS 最小接入设计](docs/superpowers/specs/2026-06-09-c31-cmapss-minimal-ingestion-design.md)
- [C3.2 open model cross-dataset evaluation 设计](docs/superpowers/specs/2026-06-11-c32-open-model-cross-dataset-evaluation-design.md)
- [C3.2 open model cross-dataset evaluation 计划](docs/superpowers/plans/2026-06-11-c32-open-model-cross-dataset-evaluation-plan.md)
- [C3.2 explicit local execution 设计](docs/superpowers/specs/2026-06-16-c32-explicit-local-execution-design.md)
- [C3.2 explicit local execution 计划](docs/superpowers/plans/2026-06-16-c32-explicit-local-execution.md)
- [C3.3 single-candidate open model local evaluation 设计](docs/superpowers/specs/2026-06-22-c33-single-candidate-open-model-local-evaluation-design.md)
- [C3.3 single-candidate open model local evaluation 计划](docs/superpowers/plans/2026-06-22-c33-single-candidate-open-model-local-evaluation-plan.md)
- [候选信号与系统事件接口草案](docs/candidate-signal-and-system-event-interface.md)
- [TTM 真实数据能力复核报告](docs/ttm-real-data-evaluation.md)
- [漏液电流监测场景评测报告](docs/leak-current-scenario-evaluation.md)
- [开源时序基础模型调研](docs/调研资料/开源时序基础模型调研.md)
- [真实数据 Schema Map](docs/reviews/real-data-schema-map.md)

## Git 安全边界

真实数据、生成 parquet、临时报告和模型 cache 都是本机验证资产。不要提交，也不要把这些文件上传到 GitHub：

- `data/real/`
- `data/processed/*.parquet`
- 本阶段临时 `reports/real_*.md`
- `hf_cache/`
- `model_cache/`
- `models/`

白名单 reports 例外不要被误否定：`reports/model_core_evaluation.md` 和 `reports/model_route_decision.md` 是仓库已有可跟踪报告，不属于本阶段本机临时 `reports/real_*` 输出。
