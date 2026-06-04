# 开源时序基础模型论文矩阵

## 目的

本矩阵用于把主流开源时序基础模型及其论文/模型卡整理为 C 阶段开源模型适配和 B 阶段自研训练判断的依据；它是初版研究资产，不是最终选型结论。

对 B08 来说，开源模型首先是能力对照和适配入口，而不是可直接替代预测性维护系统的完整方案。本矩阵关注模型在 forecasting、imputation、representation、anomaly、classification、RUL 等任务上的覆盖范围、输入约束、适配方式和工业设备缺口，后续仍需要在统一数据、统一窗口和统一指标下逐步核对。

## 候选模型分层说明

本矩阵把 C 阶段候选分为核心比较对象和扩展/待核对对象。核心比较对象是 TTM、MOMENT、Chronos、TimesFM、Moirai / Uni2TS、UniTS，应优先进入统一窗口、统一 adapter contract 和统一指标下的系统对比。

扩展/待核对对象包括 TSPulse、FlowState。TSPulse 因已有公开资料和初步任务接口信息，暂在 Multi-task / representation 表中保留为扩展候选，但不等同于核心 C 阶段比较对象；FlowState 当前只作为扩展/待核对候选记录，资料、开源可运行性、许可证和接口形态仍待核对，因此不强行补入详细矩阵正文。

## 调研字段

| 字段 | 含义 |
| --- | --- |
| paper | 论文或模型卡 |
| open source | 代码或权重是否可用 |
| task coverage | 支持 forecasting、imputation、representation、anomaly、classification、RUL 中哪些任务 |
| input constraints | 单变量/多变量、上下文长度、预测长度、采样频率、metadata 支持 |
| training data | 预训练数据来源 |
| adaptation | zero-shot、few-shot、fine-tuning、adapter 支持 |
| B08 fit | 对小样本工业物联预测性维护的适配价值 |
| gap | 不能直接覆盖的缺口 |

## Forecasting-first 模型

这类模型优先证明跨数据集 forecasting 能力，适合作为 B08 的预测残差、正常轨迹预测、概率预测和资源受限部署候选对照。它们不应被写成完整预测性维护模型，后续需要外部补充设备结构、工艺阶段、质量标记、物理域和维护语义。

| 模型 | 论文/资料 | 核心能力 | B08 价值 | 主要缺口 |
| --- | --- | --- | --- | --- |
| TTM / TinyTimeMixer | arXiv:2401.03955；IBM Granite TTM model card | 轻量 zero/few-shot 多变量 forecasting | 预测残差基线、资源受限部署候选 | 主要偏 forecasting，设备结构 metadata 需要外部处理 |
| Chronos / Chronos-Bolt | arXiv:2403.07815；Chronos 官方仓库 | token 化时序 forecasting | zero-shot forecasting 对照 | 对工业物理域、阶段和多任务表征支持有限 |
| TimesFM | arXiv:2310.10688；TimesFM 官方仓库 | decoder-only forecasting foundation model | 正常轨迹预测对照 | 主要偏 forecasting |
| Moirai / Uni2TS | arXiv:2402.02592；Uni2TS 官方仓库 | universal probabilistic forecasting | 概率预测和跨数据集 forecasting 对照 | 预测性维护任务需额外适配 |

| 模型 | open source | task coverage | input constraints | training data | adaptation | B08 fit | gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TTM / TinyTimeMixer | IBM Granite / Hugging Face 权重和 `granite-tsfm` 仓库可用 | forecasting | 支持多变量 forecasting；上下文长度和预测长度按模型分支选择；部分版本支持频率前缀、exogenous / categorical 信息注入 | 论文和模型卡说明使用公开时序数据预训练；具体版本数据规模按模型卡核对 | zero-shot、few-shot、fine-tuning | 已适合作为 B08 forecasting 参考和预测残差基线候选 | 不直接建模设备层级、工艺阶段、传感器物理域和维护语义 |
| Chronos / Chronos-Bolt | Chronos 官方仓库提供代码和模型 checkpoint；Chronos-Bolt 具体接口需按官方仓库继续核对 | forecasting | 将连续值缩放、量化后作为 token；主要面向概率 forecasting；工业多传感器结构需要外部组织 | 公开数据集与合成数据组合 | zero-shot forecasting；fine-tuning 机制需按 C 阶段运行接口核对 | 适合作为 token 化 forecasting 路线的横向对照 | 对阶段、物理域、设备 metadata 和 multi-task representation 覆盖不足 |
| TimesFM | Google Research 官方仓库可用 | forecasting | decoder-only forecasting；论文强调可跨历史长度、预测长度和时间粒度工作；具体 horizon、频率和外生变量接口需按仓库版本核对 | 论文说明使用大规模时序语料预训练；细分数据来源需按论文和仓库核对 | zero-shot forecasting；fine-tuning / adapter 能力需按官方实现核对 | 适合作为正常轨迹预测和趋势预测对照 | 主要面向 forecasting，不直接覆盖工业设备健康表征和维护语义 |
| Moirai / Uni2TS | Uni2TS 官方仓库提供代码、数据和权重 | probabilistic forecasting | 面向跨频率、任意变量数量和不同分布属性的 universal forecasting；具体输入 schema 需按 adapter 实现核对 | LOTSA，大规模开放时序归档，覆盖多个领域 | zero-shot forecasting；fine-tuning 需按仓库接口核对 | 适合作为概率预测和跨数据集泛化能力对照 | 预测性维护、异常候选信号和 RUL 需要额外任务定义与适配 |

## Multi-task / representation 模型

这类模型更接近 B08 对设备状态表征、补全、异常候选信号和小样本适配的需求。它们仍需要在工业物联语境下验证：模型是否能有效利用设备、传感器、物理域、工艺阶段、质量标记、batch/cycle 和弱标签，而不是只在通用 benchmark 上成立。

| 模型 | 论文/资料 | 核心能力 | B08 价值 | 主要缺口 |
| --- | --- | --- | --- | --- |
| MOMENT | arXiv:2402.03885；MOMENT 官方仓库 | forecasting、imputation、classification、anomaly、representation | 多任务基础模型重要对照 | 工业设备结构和预测性维护语义需适配 |
| UniTS | arXiv:2403.00131；UniTS 官方仓库 | unified time-series tasks | 多任务统一机制参考 | 工业 metadata 与设备健康任务需重构 |
| TSPulse / Granite Time Series | IBM Granite Time Series docs；TSPulse model card | 表征、预测、补全、分类、异常等 | 设备状态表征和异常候选信号对照 | 具体开源可运行性和任务接口需核对 |

| 模型 | open source | task coverage | input constraints | training data | adaptation | B08 fit | gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MOMENT | 官方仓库、Hugging Face 模型和 Time Series Pile 可用 | forecasting、imputation、classification、anomaly、representation | 通用时序 patch / embedding 路线；具体多变量、上下文长度和任务头需按仓库接口核对 | Time Series Pile，公开时序数据集合 | minimal-data / task-specific fine-tuning；zero-shot 能力需按任务区分 | 适合作为 B08 多任务和表征学习首批对照 | 不直接包含工业工艺阶段、传感器物理域、设备健康标签和维护事件语义 |
| UniTS | 官方仓库和数据集入口可用 | forecasting、imputation、classification、anomaly，以及统一 predictive / generative tasks | 通过 task tokenization 统一任务；支持多域、多采样率、多时间尺度数据；工业 schema 需重构 | 多域异构预训练数据集 | few-shot、prompt 和下游任务适配能力需按官方实现核对 | 适合参考多任务统一机制和任务 token 设计 | 工业 metadata、质量标记、设备健康任务、RUL 和维护提前量需要重新定义 |
| TSPulse / Granite Time Series | IBM Granite Time Series 文档、Hugging Face 模型卡和 `granite-tsfm` 仓库可用 | representation、imputation、classification、anomaly、similarity search；Granite Time Series 家族也覆盖 forecasting | 模型卡显示轻量模型和 GPU-free inference；TSPulse 基础上下文长度为 512，不同任务有不同输入长度建议 | TSPulse 模型卡列出多个公开时序数据集；Granite Time Series 具体模型按版本核对 | zero-shot imputation、anomaly detection、similarity search、classification 示例；fine-tuning 脚本和任务接口需按版本核对 | 适合作为设备状态 embedding、补全和异常候选信号的重点候选 | 工业设备结构语义、任务接口稳定性、版本差异和实际部署依赖仍需 C 阶段核对 |

## 对 B08 的适配缺口

**forecasting-only 缺口**：TTM、Chronos、TimesFM、Moirai 等主要证明未来值预测或概率预测能力。B08 需要的设备状态表征、补全、异常候选信号、阶段识别、弱标签适配和 RUL 等任务，不能只靠 forecasting 误差直接推出。

**industrial metadata 缺口**：主流模型通常以数值窗口为核心输入，对 `device_id`、`sensor_id`、物理域、工艺阶段、batch/cycle、质量标记、维护片段和现场环境等结构信息支持有限。B08 需要在 adapter、prompt、特征工程或自研结构中显式处理这些语义。

**小样本/弱标签缺口**：公开模型可以提供 zero-shot、few-shot 或 fine-tuning 起点，但工业设备真实故障、维护事件和退化标签稀缺。B08 需要把无标签任务、弱标签代理任务和少量专家复核任务分层推进，避免把弱证据写成完整预测性维护结论。

**多任务评测缺口**：不同模型的任务接口、输入长度、输出形式和指标口径差异较大。B08 需要统一窗口、统一任务定义和统一指标，分别评估 forecasting、imputation、representation、anomaly、classification 和 RUL，而不是只比较单一 benchmark 分数。

**工程依赖/部署成本缺口**：轻量模型更适合资源受限环境，但仍需核对依赖、许可证、模型权重、推理速度、CPU/GPU 需求、批处理方式和离线部署可行性。较大的 forecasting-first 模型可能适合研究对照，但未必适合作为默认工程路径。

## C 阶段优先级

C 阶段优先级不是按模型名气排序，而是按 B08 任务覆盖排序：核心候选先保留 TTM 作为已跑通 forecasting 参考，再补 MOMENT / UniTS 的 representation 与 multi-task 能力对照，同时用 Chronos / TimesFM / Moirai / Uni2TS 作为 forecasting-first 横向比较。TSPulse 和 FlowState 先作为扩展/待核对候选保留，待资料、许可证、开源可运行性和接口形态核对后，再决定是否并入核心系统对比。

建议顺序如下：

1. TTM / TinyTimeMixer：保留为已跑通 forecasting 参考，继续沉淀预测残差、资源受限部署和统一 adapter contract。
2. MOMENT / UniTS：优先补齐 representation、imputation、classification、anomaly 和 multi-task 对照，重点观察是否能形成设备状态 embedding 与异常候选信号。
3. Chronos / TimesFM / Moirai / Uni2TS：作为 forecasting-first 横向比较，验证 zero-shot forecasting、概率预测和跨数据集预测能力是否优于或补充 TTM。
4. TSPulse / FlowState：作为扩展/待核对候选，先核对资料、许可证、开源可运行性和 adapter 接口，再决定是否进入核心系统对比。
5. 自研训练判断：只有当统一评测证明开源模型在工业 metadata、小样本弱标签、多任务表征或设备健康语义上存在稳定缺口时，才进入 B 阶段自研结构和预训练目标设计。

本优先级不代表任何模型已经适合生产告警、RUL 精确估计或完整预测性维护。它只是 C 阶段 adapter 和评测工作的初版排序依据。

## 参考链接

- TTM / TinyTimeMixer paper: <https://arxiv.org/abs/2401.03955>
- IBM Granite TTM model card: <https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2>
- IBM Granite Time Series docs: <https://www.ibm.com/granite/docs/models/time-series>
- TSPulse model card: <https://huggingface.co/ibm-granite/granite-timeseries-tspulse-r1>
- MOMENT paper: <https://arxiv.org/abs/2402.03885>
- MOMENT official repository: <https://github.com/moment-timeseries-foundation-model/moment>
- Chronos paper: <https://arxiv.org/abs/2403.07815>
- Chronos official repository: <https://github.com/amazon-science/chronos-forecasting>
- Chronos-Bolt specific model card / interface: 待进一步核对。
- TimesFM paper: <https://arxiv.org/abs/2310.10688>
- TimesFM official repository: <https://github.com/google-research/timesfm>
- Moirai / Uni2TS paper: <https://arxiv.org/abs/2402.02592>
- Uni2TS official repository: <https://github.com/SalesforceAIResearch/uni2ts>
- UniTS paper: <https://arxiv.org/abs/2403.00131>
- UniTS official repository: <https://github.com/mims-harvard/UniTS>
