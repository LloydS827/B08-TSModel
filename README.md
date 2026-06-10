# B08 设备时序基础模型

## 项目定位

B08 是面向设备时序数据的基础模型研发与评测工作台。项目目标不是直接交付生产告警系统，而是先把真实设备数据、统一观测表、模型窗口、baseline、开源基础时序模型和评测报告连接成一条可复现链路，用证据判断后续应直接复用开源模型、做轻量适配，还是进入条件性自研模型设计。

本文档是项目入口，面向首次阅读者说明项目定位、快速开始、标准运行命令、关键目录和安全边界。阶段进展、每日更新和下一步计划维护在 [details.md](details.md)。

当前主线可以概括为：

```text
设备时序数据
  -> canonical observations
  -> 模型窗口
  -> baseline / foundation model 评测
  -> residual / trend / spike / representation / imputation 等候选信号
  -> 支撑 C 阶段开源模型评测与 B 阶段自研 Go / No-Go 判断
```

`FU13` 是当前第一台真实设备样例，用于验证从现场多 CSV 导出到 canonical observations、模型窗口和评测报告的完整链路。`leak_current_monitoring` 是模型输出进入业务语境的验证样例，不代表生产告警、故障概率、RUL 或维修建议已经完成。

## 当前可复现资产

项目当前已经具备：

- FU13 真实多 CSV 数据装配：生成 `data/processed/fu13_real_observations.parquet`。
- canonical observation schema 验证、连续炉 cycle 重构和数据诊断报告。
- baseline 与 TTM 在 FU13 真实窗口上的同口径 forecasting 验证。
- `leak_current_monitoring` 场景评测样例：输出 residual candidate signal。
- C1 证据执行框架：统一 E1 forecasting residual、E2 representation、E3 imputation 的报告口径。
- C2/C2.1/C2.2 开源模型评测入口：覆盖核心模型 audit、task attempt、adapter 尝试、版本化目标矩阵、frontier watchlist audit 和结构化失败记录。
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

C 阶段先做最小证据实验和开源模型评测，不直接进入大规模自研训练。

C 阶段最小证据契约保存在 `configs/c_stage_minimum_evidence.yaml`，用于约束 C1-C2 之前的证据包、任务口径和 Go / No-Go 检查项。

### C1. 证据执行框架

```bash
uv run b08-model-core experiment c-stage-c1 \
  --config configs/c_stage_c1_execution.yaml \
  --output reports/c_stage_c1_evidence_report.md
```

C1 默认执行 `E1_forecasting_residual`、`E2_representation` 和 `E3_imputation`，用于统一任务、指标和报告口径。

### C2. 开源模型系统评测

```bash
uv run b08-model-core experiment c-stage-c2 \
  --config configs/c_stage_c2_open_model_evaluation.yaml \
  --output reports/c_stage_c2_open_model_evaluation.md
```

C2 固定审计并尝试 TTM、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS。模型失败写入结构化状态，不等同于阶段失败。

### C2.1. 开源模型真实执行入口

```bash
uv run b08-model-core experiment c-stage-c21 \
  --config configs/c_stage_c21_executable_open_model_evaluation.yaml \
  --output reports/c_stage_c21_executable_open_model_evaluation.md
```

C2.1 在默认离线安全边界下执行六类 executable adapters / task matrix，并把失败原因写入结构化分类。默认配置保留 `allow_network: false` 和 `allow_download: false`；联网、下载、权重路径和 cache 只能通过显式本机 opt-in 启用。

### C2.2. 升级版开源模型真实执行与审计

```bash
uv run b08-model-core experiment c-stage-c22 \
  --config configs/c_stage_c22_open_model_executable_upgrade.yaml \
  --output reports/c_stage_c22_open_model_executable_upgrade.md
```

C2.2 是 C2.1 的升级入口：补充版本化核心模型目标矩阵、frontier watchlist audit、cache manifest 和可决策报告。详细阶段说明和下一步执行计划见 [details.md](details.md)，设计与实现计划见文档入口中的 C2.2 spec / plan。

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

默认路径不下载公开数据、不读取本机 raw files、不写 processed data、不运行模型训练。只有显式 opt-in 且 source/license/training-use 边界被记录后，才允许读取 ignored 本机数据目录或生成 ignored 派生产物。

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
