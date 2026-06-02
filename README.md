# B08 设备时序基础模型

B08 是设备时序基础模型的研发沙盒。当前重点不是搭一个完整业务系统，而是把真实设备数据转换为可复现的 canonical observations，并用同一套窗口、指标和报告口径验证 baseline 与时序基础模型候选。

FU13 是本阶段选定的第一台示例设备编号，指一台真空速凝炉。它不是算法名称，也不是模型名称，而是当前用于定义和验证时序模型输入输出的业务对象。

## 当前状态

当前阶段为 **FU13 real data pipeline + TTM real-data forecasting validation**。

已经跑通：

- FU13 真实多 CSV 数据装配为 `data/processed/fu13_real_observations.parquet`。
- canonical observation schema 验证、连续炉 cycle 重构和 scenario 诊断。
- baseline 与 TTM 在 FU13 真实数据窗口上的同口径 forecasting 验证。
- TTM 本机 cache 离线推理链路，当前真实数据报告状态为 `available_and_ran`。

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

下一步是固化评测口径并为模型开发做准备：先治理窗口质量、scenario 过滤、质量标记、等待态和 baseline 对照，再进入模型选择或轻量微调；不是马上横向堆更多模型名字。

## 适用读者

- 内部研发人员：按标准流程复现真实数据 pipeline，修改配置，阅读 baseline/TTM 报告，并开展下一阶段模型开发。
- 项目管理者：理解当前已经证明了什么、还没有证明什么，以及为什么下一阶段先做评测口径固化。
- 现场数据方：知道真实数据放在哪里、哪些数据质量问题会被报告、以及原始数据不会进入 Git。

## 标准开发流程

标准流程如下：

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
  -> docs/ttm-real-data-evaluation.md
```

## 1. 准备环境

需要 Python 3.11+。项目 Python 环境建议使用 `uv` 管理，依赖锁定在 `uv.lock`。

开发环境：

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

## 2. 放置真实数据

把 FU13 现场导出的多 CSV 文件放在：

```text
data/real/
```

`data/real/` 是本机数据目录，必须保持 ignored。真实原始数据不提交、不上传。

如果在 worktree 中没有 `data/real/`，可以使用原工作区的绝对路径作为 `--input-dir`，但仍不要把真实数据复制进 Git 跟踪范围。

当前文件名来自 `configs/fu13_real_data_schema.yaml`。装配命令会按配置读取这些 CSV：

| 文件 | 必需列 | 说明 |
| --- | --- | --- |
| `stage_data.csv` | `time`, `stage_name` | 工艺阶段时间线 |
| `FU13_Record_O2Content2.csv` | `time`, `value` | 下料口氧含量 |
| `FU13_CrucibleForwardPressure.csv` | `time`, `value` | 坩埚前倾压力 |
| `FU13_CrucibleReturnPressure.csv` | `time`, `value` | 坩埚回程压力 |
| `FU13_Pump_01_PumpShake1.csv` | `time`, `value` | 机械泵振动1 |
| `FU13_Pump_02_PumpShake2.csv` | `time`, `value` | 机械泵振动2 |
| `FU13_Record_LeakElec.csv` | `time`, `value` | 泄漏电流 |
| `FU13_Record_O2Content.csv` | `time`, `value` | 真空管氧含量 |
| `FU13_SysSelfPressure.csv` | `time`, `value` | 系统压力 |

`time` 需要能被 pandas 解析为时间；当前配置使用 `timezone_policy: UTC`。CSV 建议使用 UTF-8 编码。

## 3. 装配 canonical observations

运行 FU13 多 CSV 装配：

```bash
uv run b08-model-core real-data assemble-fu13 \
  --input-dir data/real \
  --config configs/fu13_real_data_schema.yaml \
  --output data/processed/fu13_real_observations.parquet \
  --report reports/real_data_validation.md
```

如果本 worktree 没有 `data/real/`，使用原工作区真实数据目录：

```bash
uv run b08-model-core real-data assemble-fu13 \
  --input-dir "/Users/lloyd/Nutstore Files/Nutstore/CavLAB/P00-Projects/分类0-核心研发/B08-设备时序基础模型/data/real" \
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

## 4. 运行数据诊断

```bash
uv run b08-model-core real-data diagnose-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_scenario_diagnostics.md
```

诊断报告用于检查 scenario 行数、invalid 行数、传感器覆盖和阶段覆盖。当前 scenario 是指标分组，不是 scenario-filtered 建窗。

## 5. 运行 baseline

```bash
uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_baseline_forecasting.md \
  --model baseline \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40
```

baseline 报告用于给 TTM 和后续模型开发提供同口径对照。当前标准配置是 `window-mode=cross-stage`、`context-length=90`、`prediction-length=16`、`max-windows=40`。

## 6. 运行 TTM

先确认 optional dependency 已安装：

```bash
uv sync --extra dev --extra foundation-ttm
```

如果本机已经有 `hf_cache/`，使用离线 cache 运行：

```bash
HF_HOME=hf_cache uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_ttm_forecasting.md \
  --model ttm \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --model-cache-dir hf_cache \
  --no-download
```

如果 worktree 中没有 `hf_cache/`，可以指向原工作区 cache：

```bash
HF_HOME="/Users/lloyd/Nutstore Files/Nutstore/CavLAB/P00-Projects/分类0-核心研发/B08-设备时序基础模型/hf_cache" uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_ttm_forecasting.md \
  --model ttm \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --model-cache-dir "/Users/lloyd/Nutstore Files/Nutstore/CavLAB/P00-Projects/分类0-核心研发/B08-设备时序基础模型/hf_cache" \
  --no-download
```

如果需要首次下载权重，必须显式允许下载：

```bash
HF_HOME=hf_cache uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_ttm_forecasting.md \
  --model ttm \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --model-cache-dir hf_cache \
  --allow-download
```

TTM 命令的退出码和报告状态约定：

| 情况 | 报告状态 | 退出码 |
| --- | --- | ---: |
| baseline 默认模式 | `skipped_by_user` | 0 |
| TTM 依赖未安装 | `missing_dependency` | 1 |
| TTM cache 命中并完成推理 | `available_and_ran` | 0 |
| TTM cache 未命中且禁止下载 | `missing_or_blocked_weights` | 1 |
| TTM 下载、加载或推理失败 | `missing_or_blocked_weights`、`unsupported_window_shape` 或 `runtime_failed` | 1 |

常用参数边界：

| 参数 | 当前可用值或约束 | 说明 |
| --- | --- | --- |
| `--model` | `baseline` 或 `ttm` | `baseline` 不需要 TTM 依赖；`ttm` 会加载基础模型 |
| `--window-mode` | `stage-local` 或 `cross-stage` | 当前真实数据标准评测使用 `cross-stage` |
| `--context-length` | 正整数 | 当前标准值为 `90` |
| `--prediction-length` | 正整数 | 当前标准值为 `16` |
| `--max-windows` | 正整数 | 按当前窗口构建顺序取 first-N，再做 70/30 顺序切分 |

如果需要复跑本阶段 first-N `20/40/80` 口径，可以使用下面的完整命令。baseline：

```bash
for n in 20 40 80
do
  uv run b08-model-core real-data forecast-fu13 \
    --dataset data/processed/fu13_real_observations.parquet \
    --config configs/fu13_real_data_schema.yaml \
    --output "reports/real_baseline_forecasting_w${n}.md" \
    --model baseline \
    --window-mode cross-stage \
    --context-length 90 \
    --prediction-length 16 \
    --max-windows "$n"
done
```

TTM 离线 cache：

```bash
for n in 20 40 80
do
  HF_HOME=hf_cache uv run b08-model-core real-data forecast-fu13 \
    --dataset data/processed/fu13_real_observations.parquet \
    --config configs/fu13_real_data_schema.yaml \
    --output "reports/real_ttm_forecasting_w${n}.md" \
    --model ttm \
    --window-mode cross-stage \
    --context-length 90 \
    --prediction-length 16 \
    --max-windows "$n" \
    --model-cache-dir hf_cache \
    --no-download
done
```

## 7. 如何阅读报告

- `schema_valid=True`：canonical schema 验证通过。它不等于数据质量完美，只说明字段、类型和基本结构满足装配要求。
- `quality_counts`：各类质量标记的计数。当前 `unassigned_cycle` 和 `invalid` 是下一阶段数据治理重点。
- `available_and_ran`：TTM 依赖、权重和推理链路成功运行。它不代表模型可以用于告警。
- `Baseline Comparison`：baseline 报告中的整体 MAE/RMSE 对照，通常包含 robust stage fallback 与 seasonal naive 等基线。
- `Foundation Metrics`：TTM 报告中的基础模型整体指标，当前 TTM 指标在本地报告中以 `foundation` 行输出。
- `Sensor Metrics`：按传感器拆分的误差，用于识别哪个传感器受量纲、离散值、等待态或质量标记影响更大。
- `Scenario Metrics`：按 scenario 映射聚合的误差。当前它是分组指标，不是 scenario-filtered training/evaluation。

阅读报告时要注意：`cross-stage` 窗口可能包含等待阶段或跨阶段混合片段；当前还没有做 `good` only、去除 `invalid`、去除 `unassigned_cycle` 等过滤评测。

## TTM 当前结论

完整结论见 [TTM 真实数据能力复核报告](docs/ttm-real-data-evaluation.md)。

当前可以确认：

- TTM 可以从本机 cache 离线运行，w20/w40/w80 的状态均为 `available_and_ran`。
- TTM 是有意义的 forecasting 候选模型；在同一批 constructed windows、同一套 baseline、同一套 MAE/RMSE 指标下，TTM 输出了真实推理结果。
- first-N `max-windows=20/40/80` 结果中，TTM 整体 MAE/RMSE 均低于 `RobustStageForecaster` 和 `StageSeasonalNaiveForecaster`。
- `max-windows=20/40/80` 是按当前窗口构建顺序取前 N 个窗口的嵌套规模敏感性证据，不是随机抽样，也不是统计稳健性证明。

## 不能得出的结论

当前报告是 forecasting 能力复核，不是故障预测验收。

不能从当前结果推出：

- 设备故障概率。
- RUL。
- 维护建议。
- 生产告警。
- TTM 可以直接用于现场业务闭环。
- TTM 已经具备预测性维护系统能力。

原因是当前缺少真实故障标签、维修记录、停机事件标签、寿命标签和退化过程定义，也还没有完成 scenario-filtered evaluation、质量标记过滤、等待态处理和更强 baseline 对照。

## 下一阶段开发任务

下一阶段顺序建议：

1. window quality governance：治理窗口构建质量，记录跨阶段、等待态、异常时间间隔和质量标记分布。
2. scenario-filtered evaluation：把 hydraulic、leak、atmosphere、pump 等从指标聚合升级为场景内窗口评测。
3. quality-flag filtering：比较 `good` only、去除 `invalid`、去除 `unassigned_cycle` 后的指标变化。
4. waiting-stage handling：评估等待态保留、剔除和单独建模对 forecasting 误差的影响。
5. stronger baselines：增加按传感器/阶段的 rolling、lag、分位数或轻量机器学习 baseline。
6. then model selection/fine-tuning：在评测口径稳定后，再进入模型选择、轻量微调或领域模型训练。

## 关键目录

```text
AGENTS.md                               # 后续 Agent 工作规则和阶段边界
details.md                              # 面向用户和非技术人员的项目进展台账
uv.lock                                 # uv 生成的可复现 Python 依赖锁文件
configs/
  real_data_schema_map.template.yaml    # 真实数据映射模板
  fu13_real_data_schema.yaml            # FU13 真实多 CSV 装配配置
data/
  real/                                 # 本机真实数据目录，ignored
  processed/                            # 生成 parquet，ignored
docs/
  index.html                            # 文档总入口
  ttm-real-data-evaluation.md           # TTM 真实数据能力复核报告
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

- [Agent 工作规则](AGENTS.md)
- [项目进展说明](details.md)
- [docs/index.html](docs/index.html)
- [TTM 真实数据能力复核报告](docs/ttm-real-data-evaluation.md)
- [模型输入输出定义](docs/model-io-definition.html)
- [真实基础模型推理验证方案](docs/foundation-model-inference-design.html)
- [真实基础模型推理实施计划](docs/foundation-model-inference-plan.html)
- [基础模型验证分析报告](docs/foundation-model-verification-report.html)
- [模型路线决策](docs/model-route-decision.html)
- [开源时序基础模型调研](docs/调研资料/开源时序基础模型调研.md)
- [真实数据 Schema Map](docs/reviews/real-data-schema-map.md)
- [Code Review 与下一阶段计划](docs/reviews/2026-05-31-code-review-and-next-stage.md)

## Agent 维护规则

`details.md` 是项目进展台账，面向用户、管理者和非技术人员。后续 Agent 在完成任何实质性项目推进后，都要检查并及时更新该文件。

必须检查 `details.md` 的场景：

- 新增或改变了项目能力，例如真实数据接入、模型实验、评测指标、报告输出。
- 改变了当前阶段判断。
- 改变了下一步计划、优先级、路线选择或 Go/No-Go 判断。
- 发现新的风险、阻塞项、数据问题或模型适配问题。
- 完成了一轮关键验证、code review、实验、提交或推送。

更新 `details.md` 时遵守：

- 用非技术人员能理解的语言说明项目现在在做什么。
- 分清“已经具备的能力”和“后续需要补充的能力”。
- 更新“下一阶段计划”和“近期更新记录”。
- 保留上下文，不只写一句技术提交说明。
- 如果本轮工作不影响项目进展，也要在最终回复中说明已检查且无需更新。

本任务只允许修改 README 时，不更新 `details.md`。

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
