# 设备时序基础模型研究路线

## 目的

本文档是下一阶段研究路线脚手架，不是已经完成的学术综述或模型选型结论。它用于把项目从单一业务场景验证，收束到“设备时序基础模型研发与评测”的主线，并为后续调研、开源模型适配和条件性自研训练方案设计提供入口。

当前下一步不是直接进入大规模训练，而是先确定 foundation-model research direction：设备时序基础模型应该学习什么任务、使用什么评测口径、优先复用哪些开源模型，以及在什么证据下才需要设计自研训练方案。

## 当前基础

项目已经具备最小数据与评测闭环：

- FU13 真实数据 pipeline：从多 CSV 原始数据装配到 canonical observations。
- 标准窗口与评测桥接：支持 baseline / TTM forecasting 同口径评测。
- 场景评测样例：`leak_current_monitoring` 已验证模型输出可以被映射为 residual candidate signal。
- 可复现研发流程：已有 uv、CLI、测试和报告生成入口。

这些基础说明项目已经能承接 foundation model 的输入输出验证。真实维修记录、生产告警闭环和现场维护策略仍然重要，但它们主要是工程应用 concern，不是唯一研究 blocker；模型研发下一步还需要先回答任务谱系、模型能力、数据规模和评测口径问题。

## A. 学术 / 行业 / 模型路线调研

A 阶段目标是建立设备时序基础模型的任务、数据和模型路线判断，避免在没有证据的情况下直接进入自研训练。

需要整理的 task taxonomy：

- forecasting：预测未来窗口、趋势和关键指标变化。
- imputation：补全缺失传感器读数或不规则采样片段。
- representation：学习设备状态、工况阶段和健康趋势表征。
- anomaly：识别偏离正常工况的残差、突变、漂移或模式变化。
- classification：识别工况、阶段、质量状态或已知事件类别。
- RUL：估计 remaining useful life 或退化风险相关的时间尺度。

需要明确的工业时序特点：

- 多传感器、多量纲、强相关输入。
- 工艺阶段和设备状态切换会改变时序分布。
- 非均匀采样、缺失值、重复记录和时间戳噪声常见。
- 维护事件、生产告警和质量标记可能不完整或不同步。
- 设备间差异、批次差异和现场环境差异会影响泛化。
- 研究评测需要区分模型能力问题、数据质量问题和业务标签缺失问题。

待调研的 models / papers / route：

- Time-series foundation models：TTM、MOMENT、Chronos、TimesFM、Moirai、UniTS。
- Forecasting-oriented foundation models 与 zero-shot / few-shot forecasting 论文。
- Masked time-series modeling、contrastive representation learning、multi-task time-series learning。
- Industrial time-series、predictive maintenance、equipment health management 相关综述。
- Anomaly detection、RUL、stage-aware forecasting 和 multivariate sensor representation 的评测基准。

A 阶段产物应是资料清单、任务/指标清单和优先评测模型列表，而不是直接给出“必须自研”的结论。

## C. 开源基础时序模型系统适配与对比

C 阶段目标是在同一套设备窗口、指标和报告口径下验证开源基础时序模型，判断是否能作为本项目核心基座。

候选模型：

- TTM
- MOMENT
- Chronos
- TimesFM
- Moirai
- UniTS

比较维度：

- task coverage：forecasting、imputation、representation、anomaly、classification、RUL 的支持范围。
- input constraints：单变量/多变量、上下文长度、预测长度、采样频率、缺失值、归一化要求。
- dependency cost：框架依赖、模型权重体积、下载方式、许可证和部署复杂度。
- inference speed：CPU/GPU 推理耗时、批处理能力、缓存策略和内存占用。
- fine-tuning support：是否支持轻量微调、全量微调、adapter、prompt/patch 级适配。

C 阶段需要记录模型失败原因：依赖不可用、窗口形状不匹配、任务不支持、推理成本过高，或模型能力不足。只有在这些证据清楚之后，才讨论是否进入 B 阶段。

## B. 自研设备时序基础模型训练方案设计

B 阶段是 A 和 C 之后的条件性设计问题，不是已经决定的路线。只有当调研和开源模型对比说明现有模型不能覆盖核心设备时序需求，才进入最小自研训练方案设计。

条件性设计问题：

- data format：是否沿用 canonical observations、窗口 parquet 和多传感器字段组织；如何表达工况阶段、设备 ID、质量标记和缺失值。
- 预训练目标：masked reconstruction、next-window forecasting、contrastive representation、stage-aware prediction 或 multi-task learning 是否适合当前数据。
- validation split：按时间、设备、工况阶段或批次切分；如何避免数据泄漏和过拟合单一 FU13 设备。
- minimal prototype：最小模型结构、最小数据规模、最小训练轮次和必须对照的 baseline / 开源模型。
- compute budget：本地 CPU/GPU、云端训练、模型缓存、实验追踪和长期维护成本。

B 阶段成功标准应包括：自研模型要解决的开源模型缺口、最小原型的可验证指标，以及继续投入训练的 Go / No-Go 条件。

## 资料清单

后续资料整理建议按以下结构维护：

- 学术综述：时间序列基础模型、工业设备时序、预测性维护、设备健康管理。
- 模型资料：TTM、MOMENT、Chronos、TimesFM、Moirai、UniTS 的论文、仓库、模型卡和许可证。
- 任务资料：forecasting、imputation、representation、anomaly、classification、RUL 的数据集和指标。
- 项目资料：FU13 pipeline、TTM 真实数据能力复核、`leak_current_monitoring` 场景评测、schema map。
- 决策资料：开源模型能力矩阵、失败原因记录、训练目标候选和 Go / No-Go 结论。

## Go / No-Go 问题

进入 C 阶段前需要回答：

- 设备时序基础模型的核心任务优先级是什么？
- 当前 FU13 数据能支持哪些任务，不能支持哪些任务？
- 哪些数据缺口属于模型研发问题，哪些属于工程应用闭环问题？

进入 B 阶段前需要回答：

- TTM、MOMENT、Chronos、TimesFM、Moirai、UniTS 在统一窗口和指标下的主要缺口是什么？
- 缺口能否通过 adapter、prompt、轻量微调或数据预处理解决？
- 自研训练是否有明确优于开源模型的目标任务和可验证指标？
- 当前数据规模、算力和维护成本是否支撑最小原型？

No-Go 条件示例：

- A 阶段尚未明确任务谱系和指标口径。
- C 阶段尚未完成同口径开源模型对比。
- 自研目标只是“更贴合设备数据”，但没有明确缺口、数据来源和验证指标。

## 与业务场景评测的关系

`leak_current_monitoring` 是基础模型输出到候选业务信号的验证样例，不是基础模型研发路线的终点。

业务场景评测应继续保留为模型输出进入业务语境的接口验证：它可以检验 residual、trend、spike、representation 等候选信号是否有解释价值，也可以暴露数据质量、时间对齐和阈值策略问题。但下一阶段研发主线仍应按 A -> C -> B 推进：先完成学术 / 行业 / 模型路线调研，再系统适配开源基础时序模型，最后在证据充分时设计自研设备时序基础模型训练方案。
