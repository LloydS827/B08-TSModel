# 基础模型训练路线

## 定位

本训练路线用于把知识成果主线落到可验证实验。A 阶段不直接启动大规模训练，而是定义统一数据语料、预训练目标、小样本适配任务、对照模型和最小自研原型条件。

本文是 B08 的跨线资产：知识成果优先线负责方法假设、任务口径和路线论证；工程化产品承接线负责 workflow、adapter、训练评测承接和验证门。两条线应保持同一套任务定义、数据语义和证据边界，避免把研究假设写成已经交付的模型能力。

本路线的目标不是证明 B08 已经训练出基础模型，而是为后续 C 阶段开源模型适配、B 阶段自研原型判断和工程化复现实验提供统一口径。进入任何训练或评测前，都应先明确数据来源、任务分层、强基线、指标和失败条件。

## 数据语料

第一版训练语料应由三类数据共同构成：FU13 canonical observations、开源预测性维护数据映射，以及必要的模拟/退化注入数据。

FU13 canonical observations 是当前真实工业设备 pipeline 的第一入口，应优先用于验证统一 schema、窗口构建、质量标记、工艺阶段、cycle/batch 重构和弱标签任务是否可运行。FU13 的价值在于提供真实现场语义和多传感器设备时序结构，但当前不应被解释为已经覆盖完整故障闭环、RUL 或自动维护决策。

开源预测性维护数据用于补足 FU13 当前缺少的 run-to-failure、RUL、明确故障分类和退化过程证据。候选方向包括 C-MAPSS、IMS Bearing、PRONOSTIA / FEMTO-ST、Tennessee Eastman Process 等，但它们只能作为候选补充语料和评测入口。开源数据来源、授权、再分发边界、引用要求、标签语义、schema 映射和训练用途仍需逐项核对，不能默认进入正式训练或对外成果描述。

模拟/退化注入数据只用于冷启动、任务调试、schema 调试和弱标签候选信号验证。它可以帮助检查 masked reconstruction、趋势/尖峰候选信号和 residual candidate generation 是否具备基本可运行性，但不能单独作为真实设备预测性维护能力的证据。

统一语料构建时应至少记录 `source_dataset`、`source_file`、`license_status`、`training_use_status`、`mapping_status`、`label_confidence`、`split_policy` 和 `version/download_date`。任何不能可靠映射的字段应保留为空、标记为 unknown，或放入 dataset-level metadata，避免制造伪精确标签。

## 输入结构

输入结构应围绕设备运行窗口组织，而不是只保留裸数值序列。第一版候选字段包括：

- `device_id`：设备或 unit 标识，用于设备内/跨设备切分和泛化评测。
- `sensor_id`：传感器标识，用于多传感器窗口、跨传感器补全和结构感知 token。
- `physical_domain`：传感器物理域，例如热、力、压力、电流、气氛或运动状态。
- `process_stage`：工艺阶段或 operating condition，用于阶段感知表征与阶段切分评测。
- `quality_flag`：质量标记或数据可用性语义，用于过滤、弱标签任务和输入排除实验。
- `batch/cycle`：批次、run、cycle 或退化轨迹标识，用于窗口归属和防泄漏切分。
- `sampling pattern`：采样频率、时间间隔、缺失模式、重复采样或不规则采样信息。
- `weak degradation/failure proxy`：弱退化、异常候选或 failure proxy 信号，用于业务代理任务和专家复核入口。

这些字段不一定在第一版全部直接输入模型。若某字段作为输入 metadata 使用，则对应的 probe 任务必须排除该字段或另设任务解释边界。例如，若 `process_stage` 已直接进入输入，则 stage classification 的结果不能被解释为模型从时序中自主学习到阶段表征；若 `quality_flag` 已直接进入输入，则 quality_flag prediction 只能说明模型利用了显式字段，不能说明模型理解质量标记语义。

## 预训练任务

预训练任务应优先选择能在无标签或弱标签条件下验证的目标，并与设备健康管理主线保持关系。第一版候选任务包括：

- `masked sensor reconstruction`：遮蔽同一窗口内部分传感器或时间片段，评估模型恢复局部设备运行结构的能力。
- `next-window forecasting`：预测下一窗口或短期 horizon，用于正常轨迹、趋势信号和 forecasting-first 强基线对照。
- `cross-sensor imputation`：利用其他传感器补全目标传感器，验证多物理域耦合和跨传感器关系。
- `stage-aware representation learning`：在窗口表征中保留工艺阶段结构，避免把正常阶段切换误写成异常。
- `contrastive normal/abnormal representation`：基于弱标签、质量标记、退化注入或候选异常片段构造正常/异常代理表征对比。
- `residual / trend / spike candidate signal generation`：生成残差、趋势和尖峰候选信号，供后续弱标签评测和专家复核使用。

这些任务应被写成训练目标和评测目标，不应被直接解释为生产告警、RUL 精确估计或自动维修建议。尤其是 residual、trend 和 spike 只能作为候选信号，需要预先定义阈值口径、top-k 规则、复核样本和失败条件。

## 小样本适配任务

小样本适配任务应连接 `task-metric-matrix.md` 的三层任务结构，按证据强度逐步推进。

第一层是无标签可验证任务，包括 forecasting、imputation / reconstruction 和 representation consistency。该层适合 FU13 当前无完整故障标签的条件，也适合开源模型对照和预训练目标评估。指标可包括 MAE、RMSE、coverage、mask reconstruction error、clustering 或 linear probe 结果，但低预测误差或低重构误差不能被解释为已经具备故障预警能力。

第二层是弱标签或业务代理任务，包括 stage classification、quality_flag prediction、residual high-percentile detection 和 trend/spike candidate signal。FU13 当前优先支持这一层以及第一层任务，前提是字段来源、输入排除口径、弱标签构造方式、时间切分策略和专家复核口径被清楚记录。弱标签任务用于判断模型是否学习到工艺阶段、质量标记和候选异常信号相关语义，不等于真实故障诊断或生产告警。

第三层是预测性维护目标任务，包括 RUL、fault classification 和 maintenance lead time。此类任务依赖开源 run-to-failure 数据，或后续真实维修记录、停机记录、故障确认时间和专家复核。缺少这些证据时，B08 只能把第三层保留为路线目标和候选评测方向，不能从 FU13 当前证据直接推出 RUL 精确估计、故障分类能力或维护提前量预测能力。

小样本适配实现上应优先比较冻结 backbone + linear probe、轻量 adapter、少量 fine-tuning 和任务头训练。每个适配实验都应记录 `required_data`、`required_label`、`baseline`、`primary_metric`、`split_policy`、`gate`、`artifact_output` 和 `known_invalid_claims`。

## 开源模型对照

开源模型对照应先覆盖 forecasting-first，再覆盖 multi-task / representation，最后保留传统工程 baseline。对照目标是判断现有模型和简单基线能否满足 B08 的任务口径，而不是默认进入自研训练。

forecasting-first 对照包括 TTM、Chronos、TimesFM 和 Moirai。这类模型适合验证正常轨迹预测、短期趋势预测、概率 forecasting 和预测残差候选信号。它们应作为 B08 的强 forecasting 对照，但不能被直接写成完整预测性维护模型，因为设备结构 metadata、工艺阶段、多物理域、质量标记和维护语义通常需要外部适配。

multi-task / representation 对照包括 MOMENT、UniTS 和 TSPulse。这类模型更接近设备状态 embedding、补全、异常候选信号和小样本适配需求，应重点验证 representation consistency、imputation / reconstruction、弱标签 probe 和异常候选生成能力。它们仍需在统一 FU13 schema、公开预测性维护数据和同口径任务指标下验证，不应仅凭通用 benchmark 结论替代 B08 证据。

工程 baseline 包括 rolling baseline、robust baseline、seasonal naive、重构误差和变点检测。它们是进入复杂模型前必须保留的下限对照：如果简单 rolling 或 seasonal naive 已能覆盖 forecasting，或者重构误差/变点检测已能提供足够稳定的候选信号，则不应过早扩大模型复杂度。

所有对照应使用统一窗口、统一 split policy、统一指标和统一报告模板。若模型因输入长度、变量形式、任务头缺失、依赖环境、许可证或权重可用性无法运行，应记录失败原因，而不是用缺失结果替代评估。

## 最小自研原型

只有当 C 阶段证明 forecasting-first 模型无法覆盖设备状态表征、弱标签任务或预测性维护候选信号生成时，才进入最小自研原型。最小原型应优先验证结构感知 token、masked reconstruction、stage-aware representation 和 weak-label probing，而不是直接追求大模型规模。

最小自研原型的核心问题是：显式引入设备结构、传感器物理域、工艺阶段、质量标记和弱退化代理信号，是否能在同口径任务上稳定优于 forecasting-first 和 multi-task / representation 开源模型。若不能回答这个问题，就不应扩大预训练数据规模、模型参数规模或工程复杂度。

第一版原型可以采用轻量结构感知输入层、窗口 encoder、masked reconstruction head、next-window forecasting head、stage-aware representation objective 和 weak-label probing head。任务头应保持可替换，方便与开源模型 adapter 共用训练/评测配置。

原型验证应优先覆盖至少一个 representation / imputation / weak-label 任务，并与 TTM、Chronos、TimesFM、Moirai、MOMENT、UniTS、TSPulse 以及工程 baseline 做同口径比较。若只在单一 forecasting 指标上取得小幅结果，且不能支撑设备状态表征或弱标签任务，则不应进入更大规模自研训练。

## Go / No-Go 条件

进入自研前必须预先指定主任务、强基线、最低增益、多 seed / 置信区间或失败 No-Go 条件；不能后验挑选表现好的任务。每个候选实验都应在训练前写清楚 `primary_metric`、`valid_when`、`split_policy`、`aggregation`、`baseline`、`minimum_gain`、`seed_policy`、`confidence_interval_policy` 和 `invalid_interpretation`。

Go 条件至少应包括：

- 主任务已预先指定，并能映射到无标签、弱标签或预测性维护目标三层任务之一。
- 数据来源、授权状态、schema 映射、标签置信度和 split policy 已记录。
- 强基线已确定，至少包含 forecasting-first 对照和必要工程 baseline。
- 最低绝对或相对增益已在实验前定义，不能在结果后调整。
- 多 seed、置信区间、bootstrap 或其他不确定性报告方式已预先确定。
- 失败时的 No-Go 条件已明确，例如低于强基线、置信区间重叠、只在后验挑选任务上有效，或结果无法复现。

No-Go 条件至少应包括：

- C 阶段开源模型和工程 baseline 已能覆盖当前主任务，且自研结构没有明确增益。
- 自研原型只在后验挑选任务上表现较好，或主指标、数据切分、top-k 规则在结果后被调整。
- representation / imputation / weak-label 任务没有相对 forecasting-only 模型的稳定收益。
- 开源数据来源、授权、训练用途或标签语义无法核对。
- FU13 或公开数据证据不足以支撑目标任务，尤其是 RUL、fault classification 和 maintenance lead time。

证据不足时，只保留路线假设，不进入大规模训练。任何 Go 决策都应形成可追溯记录，包括成功指标、失败指标、限制条件和下一步承接方式。

## 工程化产品承接

工程化产品承接线需要把本文路线转化为可复现 workflow，而不是一次性脚本或不可追溯实验。至少应沉淀以下资产：

- 统一数据语料构建命令：从 FU13 canonical observations、开源预测性维护数据映射和必要模拟/退化注入数据生成统一窗口与 metadata，并记录 source、license、mapping、split 和 label_confidence。
- 模型 adapter contract：为 TTM、Chronos、TimesFM、Moirai、MOMENT、UniTS、TSPulse、工程 baseline 和后续最小自研原型提供统一输入输出接口。
- 训练/评测配置：用配置文件固定 task_id、数据切分、目标变量、mask 策略、horizon、模型 adapter、primary_metric、baseline、seed 和 gate。
- 报告模板：统一输出指标表、失败原因、候选样本列表、专家复核入口、invalid claims 和 Go / No-Go 结论。
- 模型缓存策略：记录模型权重来源、版本、许可证、缓存路径、校验信息、离线可用性和清理策略，避免隐式下载或不可复现实验。
- 可复现 workflow：提供从数据语料构建、adapter 调用、训练/推理、指标计算、报告生成到阶段 review 的完整命令链，并能在失败时保留原因。

工程化承接不应改变知识成果线的证据边界。workflow 可以支撑训练和评测，但不能把候选异常信号包装成生产告警，不能把公开 RUL benchmark 结果解释为 FU13 已具备 RUL 精确估计，也不能把弱标签 probe 结果解释为自动维修建议。

后续拆分为代码或实验计划时，建议先落地最小闭环：统一语料构建命令、一个 forecasting-first adapter、一个 multi-task / representation adapter、一个工程 baseline、一个无标签任务、一个弱标签任务和一份 Go / No-Go 报告。该闭环通过后，再考虑扩展更多模型、更多公开数据和最小自研原型。
