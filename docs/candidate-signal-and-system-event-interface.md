# 候选信号与系统事件接口草案

本文档定义 B08 能源设备时空智能样板在“候选信号 -> 专家复核 -> 系统协同事件候选”之间的轻量接口口径。当前文档只描述候选数据结构、交付映射和 Go / No-Go 判断，不新增生产服务、CLI 或自动化闭环。

## 1. 定位

B08 的 C2/C3 工作产出应被解释为“模型适配性证据”，不是开源模型排名，也不生成 leaderboard。相关报告用于回答：

- 哪些开源基础时序模型可以在本项目离线边界、依赖约束和任务矩阵下复用。
- 哪些任务需要轻量适配才能稳定产生可解释候选信号。
- 哪些关键设备状态理解问题可能需要进入条件性自研模型设计。

因此，本文档中的输出均为候选输入，不代表最终业务判断。

## 2. `candidate_signal_report`

`candidate_signal_report` 是信号层向应用输入层传递候选证据的报告口径。它聚合 baseline、TTM、open model evaluation reports、C1/C2/C3 任务结果或场景评测中的异常与状态变化线索，用于专家复核和下游系统事件候选构造。

建议字段如下：

| 字段 | 含义 |
| --- | --- |
| `report_id` | 候选信号报告 ID |
| `device_id` | 设备 ID，例如 `FU13` |
| `time_range` | 候选信号覆盖的起止时间 |
| `stage` | 工艺阶段、运行阶段或 `cross-stage` |
| `signal_type` | 信号类型：residual、trend、spike、representation、imputation |
| `sensor_id` | 关联传感器或传感器集合 |
| `evidence_source` | 证据来源，例如 baseline、TTM、open model、scenario evaluation |
| `signal_summary` | 候选信号摘要 |
| `engineering_interpretation` | 工程解释，说明候选信号可能对应的设备状态或数据质量含义 |
| `confidence` | low、medium、high 或数值置信度 |
| `affected_scope` | 影响范围，例如 sensor、stage、cycle、window、device |
| `expert_review_required` | 是否需要专家或维护人员复核 |
| `review_status` | pending、confirmed、rejected、needs_more_data |

signal 类型口径：

- residual：预测残差、重构残差或同阶段参考残差异常。
- trend：缓慢漂移、阶段内斜率变化或跨周期趋势偏移。
- spike：短时尖峰、突变或孤立异常点。
- representation：表征空间中的状态聚类、相似性或分布变化。
- imputation：缺失修复、质量标记或插补结果暴露出的数据完整性问题。

## 3. B08 -> S01 事件候选

B08 可以把已形成工程解释的候选信号转写为 S01 system event candidate，但该候选仍需专家复核或业务系统确认后才能进入正式事件流。

S01 事件候选字段如下：

| 字段 | 含义 |
| --- | --- |
| `event_id` | 系统事件候选 ID |
| `device_id` | 设备 ID |
| `time_range` | 事件候选覆盖时间 |
| `stage` | 工艺阶段或运行阶段 |
| `signal_type` | residual、trend、spike、representation、imputation |
| `signal_summary` | 事件候选摘要 |
| `confidence` | low、medium、high 或数值置信度 |
| `affected_scope` | 影响范围，例如 sensor、stage、cycle、window、device |
| `suggested_action` | 建议动作输入，例如 expert_review、watch、adjust_operation_candidate |
| `review_status` | pending、confirmed、rejected、needs_more_data |
| `source_report` | 来源 `candidate_signal_report` ID 或报告路径 |

`suggested_action` 只表示“建议进入哪类人工复核或运行优化输入”，不是维修建议，也不是自动工单。

## 4. B08 -> B06 观测包

B08 -> B06 的输出建议定义为 `equipment_timeseries_observation_package`。该 profile 面向设备时序观测资产复用，包含：

- canonical observations：统一后的设备时序标准观测表。
- quality flags：缺失、异常、插补、采样间隔和阶段边界等质量标记。
- cycle reconstruction：周期重构结果。
- window artifacts：窗口切片、上下文长度、预测长度和任务矩阵引用。
- candidate signals：从 residual、trend、spike、representation、imputation 中抽取的候选信号摘要。

该观测包的目标是让 B06 复用 B08 的数据治理和时序观测结构，而不是复用未经确认的告警结论。

## 5. B08 -> IP 映射

| IP 编号 | B08 支撑资产 | 说明 |
| --- | --- | --- |
| P0-06 | canonical observations / quality flags | 对应设备时序标准观测表、质量标记和可复查的数据契约 |
| P0-07 | cycle reconstruction / window artifacts | 对应周期重构、窗口生成、上下文切片和任务样本构造 |
| P0-08 | baseline / TTM / open model evaluation reports | 对应 baseline、TTM 与开源模型评测报告形成的模型适配性证据 |

其中 P0-08 的口径是“模型适配性证据”，不生成 leaderboard，不把不同任务、不同数据集或不同指标强行合成为单一排名。

## 6. Go / No-Go 决策

| 决策 | Go 条件 | No-Go / 暂缓条件 |
| --- | --- | --- |
| 复用开源模型 | 离线可运行；依赖、cache、权重路径和 adapter 可控；在目标任务上稳定产生可解释 `candidate_signal_report`；专家复核认为候选信号有工程价值 | 依赖不可控、权重不可审计、任务失败频繁、输出难解释或无法进入候选信号口径 |
| 轻量适配 | 开源模型基础输出有效，但在 FU13、C-MAPSS 或目标阶段上存在稳定偏差；少量适配可改善候选信号质量、质量标记或窗口任务表现 | 适配需要大量标签、训练成本接近自研、收益只体现在一次性指标波动或疑似 leaderboard 叙事 |
| 条件性自研模型设计 | 真实数据、公开数据、候选信号和专家复核均显示开源模型不能覆盖关键设备状态理解；已有 canonical observations、quality flags、cycle reconstruction、window artifacts 和评测报告支撑设计 | 故障标签、寿命定义、维护闭环或专家复核证据不足；开源模型尚未完成公平适配验证 |

## 7. 当前边界

本文档当前不是生产告警、不是故障概率、不是 RUL 精确估计、不是维修建议、也不是自动工单。它只定义候选信号、系统事件候选和外部接口映射，用于后续人工复核、模型路线判断和 IP 证据组织。
