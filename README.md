# B08 设备时序基础模型

## 项目定位

本项目是面向设备时序数据的基础模型研发与评测项目。当前 FU13 真实数据 pipeline、TTM 真实推理和漏液电流场景评测，是为了验证基础模型研发所需的数据标准化、窗口构建、模型输入输出、评测指标和候选信号映射能力。

FU13 是当前第一台真实设备样例，用于把现场多 CSV 数据装配为 canonical observations，并在统一窗口、统一指标和统一报告口径下评测 baseline 与基础时序模型候选。`leak_current_monitoring` 是模型输出进入业务语境的验证样例，不是项目终点，也不能被解释为生产告警或维修决策闭环已经完成。

项目主线：

```text
设备时序数据
  -> canonical observations
  -> 模型窗口
  -> baseline / foundation model 评测
  -> residual / trend / spike / representation 等候选信号
  -> 支撑开源模型适配、轻量微调或自研训练 Go / No-Go 决策
```

## 当前可复现资产

- FU13 真实多 CSV 数据装配为 `data/processed/fu13_real_observations.parquet`。
- canonical observation schema 验证、连续炉 cycle 重构和数据诊断报告。
- baseline 与 TTM 在 FU13 真实数据窗口上的同口径 forecasting 验证。
- `leak_current_monitoring` 场景评测验证样例：比较质量过滤、等待态、rolling baseline 与 baseline/TTM residual candidate signal。
- `uv` + `pytest` 的本地研发验证路径。

当前事实基础：

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

## 标准研发流程

```text
data/real/
  -> real-data assemble-fu13
  -> data/processed/fu13_real_observations.parquet
  -> real-data diagnose-fu13
  -> reports/real_scenario_diagnostics.md
  -> real-data forecast-fu13 --model baseline
  -> reports/real_baseline_forecasting.md
  -> real-data forecast-fu13 --model ttm
  -> reports/real_ttm_forecasting.md
  -> real-data evaluate-scenario
  -> reports/real_leak_current_scenario_evaluation_*.md
```

## 1. 准备环境

需要 Python 3.11+。项目 Python 环境建议使用 `uv` 管理，依赖锁定在 `uv.lock`。

```bash
uv sync --extra dev
```

常规测试：

```bash
uv run python -m pytest -q
```

TTM 是 optional dependency。只有需要运行 TTM 推理时才安装：

```bash
uv sync --extra dev --extra foundation-ttm
```

TTM 权重和 Hugging Face cache 放在本机目录，例如 `hf_cache/`。本项目不会把 cache 上传到 Git。

## 2. 装配 FU13 canonical observations

把 FU13 现场导出的多 CSV 文件放在 ignored 的本机目录：

```text
data/real/
```

当前文件名来自 `configs/fu13_real_data_schema.yaml`。装配命令会按配置读取 CSV，并生成 canonical observations：

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

## 3. 运行数据诊断

```bash
uv run b08-model-core real-data diagnose-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_scenario_diagnostics.md
```

诊断报告用于检查 scenario 行数、invalid 行数、传感器覆盖和阶段覆盖。当前 scenario 是指标分组，不是 scenario-filtered 建窗。

## 4. 运行 baseline / TTM forecasting

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

当前标准口径是 `window-mode=cross-stage`、`context-length=90`、`prediction-length=16`、`max-windows=40`。baseline 用于提供同口径工程对照；TTM 用于验证开源基础时序模型候选是否能在真实 FU13 窗口上运行并输出可比较指标。

## 5. 运行业务场景评测样例

`leak_current_monitoring` 是验证样例，不是项目终点。它只使用 `LeakElec` 作为核心传感器，并比较 related stages、waiting stage、质量标记过滤和 baseline/TTM 同口径 forecasting residual。

baseline 复跑命令：

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

TTM 离线 cache 复跑命令：

```bash
HF_HOME=hf_cache uv run b08-model-core real-data evaluate-scenario \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_leak_current_scenario_evaluation_ttm.md \
  --scenario leak_current_monitoring \
  --model ttm \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --rolling-window-size 8 \
  --model-cache-dir hf_cache \
  --no-download
```

完整本地报告仍写入 ignored 的 `reports/real_*.md`，不要提交；tracked 文档只汇总关键结论和业务边界。

## 6. 阅读报告与边界

- `schema_valid=True`：canonical schema 验证通过。它不等于数据质量完美，只说明字段、类型和基本结构满足装配要求。
- `quality_counts`：各类质量标记的计数。当前 `unassigned_cycle` 和 `invalid` 是后续数据治理重点。
- `available_and_ran`：TTM 依赖、权重和推理链路成功运行。它不代表模型可以用于告警。
- `Baseline Comparison`：baseline 报告中的整体 MAE/RMSE 对照。
- `Foundation Metrics`：TTM 报告中的基础模型整体指标。
- `Sensor Metrics`：按传感器拆分的误差，用于识别哪个传感器受量纲、离散值、等待态或质量标记影响更大。
- `Scenario Metrics`：按 scenario 映射聚合的误差。当前它是分组指标，不是故障预测验收。

当前不能推出设备故障概率、RUL、维护建议、生产告警或 TTM 已经具备预测性维护系统能力。原因是项目仍缺少真实故障标签、维修记录、停机事件标签、寿命标签和退化过程定义。

## 下一阶段研发路线

下一阶段按 **A -> C -> B** 推进：

### C 阶段最小证据实验入口

C 阶段先执行最小证据契约，不直接启动大规模自研训练。执行入口是 `configs/c_stage_minimum_evidence.yaml`，阅读入口是 `docs/research/c-stage-minimum-evidence-register.html`，报告模板是 `reports/c_stage_minimum_evidence_template.md`。

C1 是当前执行环节：把前期 pipeline、C0 契约、baseline/TTM、representation 和 imputation 任务口径收束成第一版证据执行框架。C1 的作用是完成评测体系和流程的前期准备，不是直接完成全部开源模型系统评测，也不是进入自研训练。

```bash
uv run b08-model-core experiment c-stage-c1 \
  --config configs/c_stage_c1_execution.yaml \
  --output reports/c_stage_c1_evidence_report.md
```

C1 默认执行 `E1_forecasting_residual`、`E2_representation` 和 `E3_imputation`。其中 E1 以真实 baseline 路径为锚点，输出 forecasting metrics、residual summary 和 top-k candidate examples；E2/E3 建立 statistical embedding、deterministic mask 和 simple reconstruction baseline，并记录 MOMENT / UniTS 等候选模型的结构化状态。E4 公开数据和 E5 专利效果样例保留为 C2 之后的承接项。

C2 是开源时序基础模型系统评测入口。它固定审计并尝试 TTM / TinyTimeMixer、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS 六个核心模型；模型失败默认写入结构化状态，不等同于阶段失败。

```bash
uv run b08-model-core experiment c-stage-c2 \
  --config configs/c_stage_c2_open_model_evaluation.yaml \
  --output reports/c_stage_c2_open_model_evaluation.md
```

`reports/c_stage_c2_open_model_evaluation.md` 是本机 ignored 报告输出，用于记录 model audit table、model-task result matrix、failure taxonomy、C2 -> C3 handoff 和 C2 -> B decision notes。

C2.1 是开源模型真实执行评测入口。由于 Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、MOMENT、UniTS 的 API 和安装组合仍处于结构化尝试阶段，这些包、权重和 cache 均保持本机 opt-in，不加入默认依赖，也不改变 `uv sync --extra dev` 的默认可复现路径。

```bash
uv run b08-model-core experiment c-stage-c21 \
  --config configs/c_stage_c21_executable_open_model_evaluation.yaml \
  --output reports/c_stage_c21_executable_open_model_evaluation.md
```

默认 C2.1 配置是离线安全边界：`allow_network: false`、`allow_download: false`。C2.1 使用六类 executable adapters / task matrix：

| Adapter | 任务 |
| --- | --- |
| TTM | forecasting |
| Chronos / Chronos-Bolt | forecasting |
| TimesFM | forecasting |
| Moirai / Uni2TS | forecasting |
| MOMENT | representation + imputation |
| UniTS | representation + imputation |

模型未运行成功时写入结构化失败，而不是让默认 workflow 依赖 optional open model packages。失败类型包括：`missing_dependency`、`missing_or_blocked_weights`、`interface_review`、unsupported window/task、`runtime_failed`、`timeout`。C2.1 报告不输出生产告警、RUL、维护建议，也不形成 B 阶段自研训练 Go decision；联网、下载、权重路径和 cache 只允许通过显式本机 opt-in 配置或 override 启用，并必须记录。

后续关键任务按以下顺序推进，避免重复讨论路线：

```text
C1. 证据执行框架与 E1-E3 首批实验闭环
  -> C2. 开源时序基础模型系统评测：TTM、MOMENT、Chronos、TimesFM、Moirai / Uni2TS、UniTS
  -> C2 支线. 开源生态数据集整理：公开数据来源、许可证、schema mapping、任务标签和 split policy
  -> B. 条件性自研模型准备：只有 C1/C2 证明开源路线存在关键缺口后，才进入最小自研原型方案
```

```text
A. 学术 / 行业 / 模型路线调研
  -> C. 开源基础时序模型系统适配与对比
    -> B. 自研设备时序基础模型训练方案设计
```

A 阶段短期第一目标是**知识成果**：凝练论文主线、专利方向、学术综述、开源模型论文矩阵、预测性维护数据矩阵和模型训练路线。第二目标是**工程化产品**成果：把研究主线沉淀为统一数据语料、模型 adapter、训练/评测 workflow 和可复现研发工作台；这些工程化成果是承接路线，不应写成已经完成的生产系统能力。

A 先做，因为项目要先判断设备时序基础模型应该学什么、评测什么，以及它与通用时间序列模型和业务告警系统的差异。产物应包括任务谱系、数据特点、学术/行业资料综述、开源模型能力矩阵、训练目标候选和数据规模判断。

C 第二，因为要先系统验证开源 foundation models，再决定是否自研。这里要在同一批设备窗口、同一套指标、同一套报告口径下比较 TTM、MOMENT、Chronos、TimesFM、Moirai、UniTS 等候选模型，并解释失败原因是依赖问题、窗口形状问题、任务不匹配，还是模型能力不足。

B 是 A/C 之后的自研条件性路线，不能写成已经决定训练。只有当 A 和 C 给出足够证据，说明开源模型无法覆盖本项目的关键缺口时，才进入自研设备时序基础模型训练方案设计；该阶段也应先形成可审查方案，而不是直接大规模训练。

## 关键目录

```text
AGENTS.md                               # 后续 Agent 工作规则和阶段边界
details.md                              # 项目进展与阶段判断台账
uv.lock                                 # uv 生成的可复现 Python 依赖锁文件
configs/
  real_data_schema_map.template.yaml    # 真实数据映射模板
  fu13_real_data_schema.yaml            # FU13 真实多 CSV 装配配置
data/
  real/                                 # 本机真实数据目录，ignored
  processed/                            # 生成 parquet，ignored
docs/
  index.html                            # 文档总入口
  research/                             # A 阶段研究资产：知识成果优先线与工程化产品承接线
  ttm-real-data-evaluation.md           # TTM 真实数据能力复核报告
  leak-current-scenario-evaluation.md   # 漏液电流监测场景评测摘要
  reviews/real-data-schema-map.md       # 真实数据对齐检查表
reports/
  model_core_evaluation.md              # 仓库白名单报告
  model_route_decision.md               # 仓库白名单报告
  real_*.md                             # 本阶段本机临时报告，ignored
src/b08_model_core/
  simulation/                           # FU13-like 数据生成
  tasks/                                # schema 和窗口构建
  baselines/                            # 稳健 baseline
  evaluation/                           # benchmark 和候选模型矩阵
  real_data/                            # 真实数据配置、装配、诊断与 forecasting
  experiments/                          # 第一轮模型实验脚手架
tests/                                  # 回归测试
hf_cache/                               # 本机 Hugging Face cache，ignored
```

## 文档入口

- [项目进展说明](details.md)
- [docs/index.html](docs/index.html)
- [A 阶段研究资产索引](docs/research/index.html)
- [项目主线与研发路线收束设计](docs/superpowers/specs/2026-06-04-project-mainline-roadmap-refactor-design.md)
- [TTM 真实数据能力复核报告](docs/ttm-real-data-evaluation.md)
- [漏液电流监测场景评测报告](docs/leak-current-scenario-evaluation.md)
- [开源时序基础模型调研](docs/调研资料/开源时序基础模型调研.md)
- [真实数据 Schema Map](docs/reviews/real-data-schema-map.md)

## Agent 维护规则

`details.md` 是项目进展台账。后续 Agent 在完成任何实质性项目推进后，都要检查是否需要更新该文件；如果本轮工作只允许修改 README，则不要顺手改 `details.md`，但要在最终回复中说明边界。

更新项目文档时遵守：

- 分清“已经具备的能力”和“后续需要补充的能力”。
- 不把业务场景验证写成项目终点。
- 不把自研训练写成已经决定的路线。
- 不扩大到代码重构，除非任务明确要求。
- 保留当前可复现命令，避免破坏研发执行者入口。

## Git 安全边界

真实数据、生成 parquet、临时报告和模型 cache 都是本机验证资产。不要把这些文件上传到 GitHub。

不要提交：

- `data/real/`
- `data/processed/*.parquet`
- 本阶段临时 `reports/real_*.md`
- `hf_cache/`
- `model_cache/`
- `models/`

白名单 reports 例外不要被误否定：`reports/model_core_evaluation.md` 和 `reports/model_route_decision.md` 是仓库已有可跟踪报告，不属于本阶段本机临时 `reports/real_*` 输出。
