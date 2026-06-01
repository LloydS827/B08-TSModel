# B08 设备时序基础模型

B08 聚焦设备预测性维护项目中的核心时序模型：用真空速凝炉 FU13 场景梳理模型真实输入输出，验证开源时序基础模型是否可以直接引用、轻量微调，或是否需要后续自研领域模型。

本仓库不是完整预测性维护系统，也不是已经训练完成的基础模型。它当前是一个可运行的模型核心沙盒，用于内部研发人员完成数据对齐、模型 IO 定义、基线评测、开源模型适配评估和知识成果沉淀。

## 当前阶段

当前阶段为 **model-core MVP sandbox**。

已经具备：

- FU13-like 模拟数据生成。
- canonical observation schema 和模型窗口构建。
- 阶段感知 baseline 与 benchmark 报告。
- 真实数据 schema map 和 validation CLI。
- 第一轮 forecasting 实验脚手架。
- 开源模型候选矩阵和 adapter optional dependency 检查。
- 专利、论文、benchmark、模型资产等知识成果规划。

尚未完成：

- 未接入真实 FU13 导出数据并完成 schema map 实测。
- 未下载或运行外部大模型权重。
- 未完成 TTM、TimesFM、Chronos、Moirai 等模型的真实 zero-shot/frozen inference 对比。
- 未训练自研设备时序基础模型。

## FU13 是什么

FU13 是本课题当前选定的第一台示例设备编号，指一台真空速凝炉。它在数据表中作为 `device_id` 使用，也作为模拟数据场景的设备代号。

换句话说，FU13 不是算法名称，也不是模型名称，而是“我们先用哪台设备/哪类设备场景来定义和验证时序模型”的业务对象。后续如果接入更多设备，可以沿用同一套 schema 和模型流程，把其他设备编号加入 `device_id`。

## 核心判断

项目交付目标不是先做一个庞大的预测性维护系统，而是先把“底层时序模型能不能工作”验证清楚。

当前路线是：

1. 用模拟数据定义模型输入输出和评测闭环。
2. 用真实数据 validation 判断实际导出能否映射为模型输入。
3. 先跑稳健 baseline 和开源 forecasting 模型。
4. 如果开源模型可用，优先 direct reuse 或轻量微调。
5. 只有当开源路线无法覆盖阶段、传感器、物理域和退化任务时，再考虑领域自训。

## 模型输入输出摘要

模型本体的输入不同于业务系统输入。业务侧可能提供设备、传感器、工单、报警、日报等信息；模型侧需要先转为时序窗口和上下文 token。

### Canonical Observation Schema

真实数据和模拟数据最终都应映射为以下观测表字段：

| 字段 | 含义 |
| --- | --- |
| `timestamp` | 采样时间 |
| `device_id` | 设备 ID，例如 `FU13` |
| `batch_id` | 生产批次或重构批次 |
| `stage` | 工艺阶段 |
| `sensor_id` | 规范化传感器 ID |
| `value` | 数值读数 |
| `unit` | 工程单位 |
| `domain` | 物理域，例如 mechanical、thermal、atmosphere |
| `quality_flag` | good、missing、invalid、maintenance 等质量标记 |
| `degradation_label` | 弱退化标签，默认 `normal` |
| `failure_proxy` | 弱故障代理标签 |

### 模型窗口输入

- `X`: 多传感器数值窗口，形状近似为 `B x L x C`。
- `mask`: 缺失、停机、异常采样标记。
- `delta_t`: 相邻采样时间间隔。
- `stage_token`: 工艺阶段 token。
- `sensor_token`: 传感器身份、单位、量纲 token。
- `domain_token`: 机械、液压、热、气氛、电气、流体等物理域 token。
- `device_token`: 设备身份 token。

### 预期输出头

- Forecasting: 未来轨迹、分位数、置信区间。
- Imputation: 缺失点补全。
- Reconstruction: 当前窗口重构。
- Representation: 窗口、阶段、子系统 embedding。
- Degradation: 异常分数、退化分数、变点、趋势。
- Adaptation: 少量标签后的风险概率或 RUL 适配输出。

## 快速开始

需要 Python 3.11+。项目 Python 环境建议使用 `uv` 管理，依赖锁定在 `uv.lock`。

```bash
uv sync --extra dev
uv run pytest -q
```

生成 45 天 FU13 模拟数据：

```bash
uv run b08-model-core simulate \
  --days 45 \
  --seed 42 \
  --output data/simulated/furnace_fu13_45d.parquet
```

生成模型路线评估摘要：

```bash
uv run b08-model-core benchmark \
  --dataset data/simulated/furnace_fu13_45d.parquet \
  --output reports/model_core_evaluation.md
```

验证真实数据导出：

```bash
uv run b08-model-core real-data validate \
  --input path/to/real_export.csv \
  --schema-map configs/real_data_schema_map.template.yaml \
  --output reports/real_data_validation.md
```

运行第一轮 forecasting 实验脚手架：

```bash
uv run b08-model-core experiment forecasting \
  --dataset data/simulated/furnace_fu13_45d.parquet \
  --output reports/forecasting_experiment.md \
  --max-windows 40
```

## 真实数据对齐流程

真实数据入口使用 schema map，而不是直接把原始导出喂给模型。

1. 从一个具体 FU13 导出片段开始。
2. 复制并修改 `configs/real_data_schema_map.template.yaml`。
3. 明确 long 或 wide 格式。
4. 映射时间、设备、批次、阶段、传感器和值字段。
5. 为每个传感器补充 `sensor_id`、`unit`、`domain`。
6. 运行 `real-data validate` 生成报告。
7. 根据报告修复未知传感器、未映射阶段、时间解析错误、非数值读数、重复点、缺失 sensor 列等问题。

validation CLI 的约定：

- `schema_valid=True` 时退出码为 `0`。
- 能完成解析但发现数据问题时，仍写出报告，退出码为 `1`。
- 非法命令参数由 argparse 拒绝，例如 `--max-windows 0`。

## 模型路线

当前优先级是先验证开源模型能否作为可交付模块，而不是一开始自训基础模型。

| 路线 | 进入条件 | 退出条件 | 主要产出 |
| --- | --- | --- | --- |
| 直接引用 | zero-shot 或 frozen inference 稳定优于 baseline | 无法表达阶段/传感器/物理域上下文 | adapter、评测报告、工程引用建议 |
| 轻量微调 | 开源模型有效但领域偏差明显 | 收益低于 baseline 波动或部署成本过高 | 阶段 adapter、微调权重、应用论文/专利素材 |
| 领域自训 | 开源路线无法覆盖核心 IO 和任务头 | 真实数据量或算力不足 | 小型设备时序基础模型、benchmark、论文/专利 |

第一轮 forecasting 候选：

- FlowState / IBM Granite Time Series。
- IBM TinyTimeMixer / TTM。
- TimesFM。
- Chronos。
- Moirai / Uni2TS。

第二轮 representation、imputation、anomaly 候选：

- MOMENT。
- TSPulse。
- UniTS。
- 工程化基线，如 Merlion、Darts、EWMA、CUSUM、变点检测。

## 关键目录

```text
AGENTS.md                              # 后续 Agent 工作规则和阶段边界
details.md                              # 面向用户和非技术人员的项目进展台账
uv.lock                                # uv 生成的可复现 Python 依赖锁文件
configs/
  real_data_schema_map.template.yaml   # 真实数据映射模板
docs/
  index.html                           # 文档总入口
  model-io-definition.html             # 模型输入输出定义
  foundation-model-inference-design.html # 真实基础模型推理验证方案
  model-route-decision.html            # 直接引用/微调/自训路线决策
  reviews/real-data-schema-map.md      # 真实数据对齐检查表
src/b08_model_core/
  simulation/                          # FU13-like 数据生成
  tasks/                               # schema 和窗口构建
  baselines/                           # 稳健 baseline
  evaluation/                          # benchmark 和候选模型矩阵
  real_data/                           # 真实数据 schema map 与 validation
  experiments/                         # 第一轮模型实验脚手架
tests/                                 # 回归测试
```

## 文档入口

- [Agent 工作规则](AGENTS.md)
- [项目进展说明](details.md)
- [docs/index.html](docs/index.html)
- [模型输入输出定义](docs/model-io-definition.html)
- [真实基础模型推理验证方案](docs/foundation-model-inference-design.html)
- [模型路线决策](docs/model-route-decision.html)
- [开源时序基础模型调研](docs/调研资料/开源时序基础模型调研.md)
- [真实数据 Schema Map](docs/reviews/real-data-schema-map.md)
- [Code Review 与下一阶段计划](docs/reviews/2026-05-31-code-review-and-next-stage.md)

## Agent 维护规则

`details.md` 是项目进展台账，面向用户、管理者和非技术人员。后续 Agent 在完成任何实质性项目推进后，都要检查并及时更新该文件。

必须检查 `details.md` 的场景：

- 新增或改变了项目能力，例如真实数据接入、模型实验、评测指标、报告输出。
- 改变了当前阶段判断，例如从沙盒阶段进入真实数据验证阶段。
- 改变了下一步计划、优先级、路线选择或 Go/No-Go 判断。
- 发现新的风险、阻塞项、数据问题或模型适配问题。
- 完成了一轮关键验证、code review、实验、提交或推送。

更新 `details.md` 时遵守：

- 用非技术人员能理解的语言说明项目现在在做什么。
- 分清“已经具备的能力”和“后续需要补充的能力”。
- 更新“下一阶段计划”和“近期更新记录”。
- 保留上下文，不只写一句技术提交说明。
- 如果本轮工作不影响项目进展，也要在最终回复中说明已检查且无需更新。

## 当前验收口径

现阶段工作可认为完成当且仅当：

- 全量测试通过。
- 真实数据 validation CLI 可运行并能报告关键数据问题。
- forecasting 实验脚手架可在模拟数据上生成报告。
- README 和 docs 能解释当前阶段、模型边界、运行命令和下一步路线。
- git 工作区除忽略产物和用户未纳入的文件外保持干净。

下一步建议：拿一份真实 FU13 导出数据填充 schema map，先完成真实数据 validation，再进入 TTM、TimesFM、Chronos、Moirai 等开源模型的 frozen inference 对比。
