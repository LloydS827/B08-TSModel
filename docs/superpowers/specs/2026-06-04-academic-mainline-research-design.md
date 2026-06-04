# A 阶段学术主线与模型训练路线设计

## 背景

B08 项目已经完成设备时序基础模型研发所需的第一批工程基础：

- FU13 真实多 CSV 数据可以装配为 canonical observations。
- 真实数据可以完成 schema 验证、cycle 重构、数据诊断和窗口构建。
- baseline 与 TTM 已经在同一批 FU13 真实窗口上完成 forecasting 对比。
- `leak_current_monitoring` 已经形成第一版 scenario-filtered evaluation，把模型输出转化为 residual candidate signal。
- README、`details.md` 和 docs 入口已经把项目主线收束为“设备时序基础模型研发与评测”，下一阶段按 A -> C -> B 推进。

这些基础说明项目已经具备进入 A 阶段的条件。A 阶段不是泛泛整理资料，而是要从主流开源时序基础模型及其论文、预测性维护和设备健康管理数据集中，提炼 B08 自己的学术主线、专利主线和模型训练路线。

本设计文档定义 A 阶段的 brainstorming 结论和后续调研规格。

## 核心判断

A 阶段应同时服务两个目标：

- 第一目标：凝练论文和专利主线。
- 第二目标：为后续模型训练、开源模型适配和自研方案设计提供依据。

这两个目标不是并列分散的任务。论文和专利主线必须落到可训练、可评测、可对照的模型路线；模型训练也不是附属工程，而是证明学术主线成立的核心证据。

因此，A 阶段的工作应围绕下面的主线展开：

```text
面向小样本工业物联设备健康管理的时序基础模型
```

英文占位名称：

```text
A Time-Series Foundation Model for Few-Shot Industrial IoT Equipment Health Management
```

核心命题：

```text
在工业设备真实故障样本稀缺、设备类型多样、工况阶段强结构化、传感器多物理域耦合的条件下，
构建设备时序基础模型，使其通过无标签或弱标签预训练学习通用设备运行表征，
并以少量样本适配预测性维护相关任务。
```

长期愿景是具备跨场景泛化能力的工业时序基础模型。当前落点先限定在工业物联设备场景，优先服务预测性维护和设备健康管理。

## 问题框架

B08 不应被表述为“再做一个时序预测模型”。主流时序基础模型已经在 forecasting 上给出强基线，但工业物联设备预测性维护还有一组更具体的矛盾：

- 真实故障样本少，甚至没有完整 run-to-failure 样本。
- 设备类型、工况、批次和现场环境差异大。
- 多传感器、多量纲、多物理域之间存在耦合。
- 工艺阶段或设备状态切换会改变正常时序分布。
- 时间戳噪声、缺失、重复、无效值和维护停机片段常见。
- 维护记录、告警记录和人工标注通常不完整或不同步。
- 下游目标不止 forecasting，还包括补全、表征、异常候选信号、退化趋势和设备健康状态识别。

因此，B08 的学术空间在于：

```text
如何让基础时序模型在小样本、弱标签、强结构的工业设备场景中有效。
```

## 三条候选路线与推荐顺序

### 路线一：学术框架优先

主题：

```text
面向工业物联设备健康管理的小样本时序基础模型框架
```

该路线优先回答为什么通用时序基础模型和传统预测性维护方法不足以覆盖 B08 场景。它适合支撑论文引言、相关工作、专利背景和项目路线论证。

优点：

- 方向稳，容易承接现有 FU13 pipeline。
- 适合解释为什么要从业务场景验证回到基础模型研发。
- 能把预测性维护、设备健康管理、时序基础模型和小样本学习连接起来。

风险：

- 如果停留在框架层，方法创新不够硬。
- 需要后续训练和评测结果支撑，否则容易变成路线说明。

### 路线二：模型方法创新优先

主题：

```text
阶段感知、多传感器、多任务工业设备时序基础模型
```

该路线直接面向模型机制，围绕设备、传感器、物理域、工艺阶段、质量标记、batch/cycle 等结构信息设计基础模型和训练目标。

优点：

- 学术味最强，最接近基础模型方法创新。
- 能直接形成论文方法章节和专利权利要求。
- 能拉开 B08 与 forecasting-only foundation model 的差异。

风险：

- 难度最高，需要训练数据、实现和评测闭环支撑。
- 如果数据规模不足，需要先证明最小原型而不是承诺大规模基础模型。

### 路线三：数据与 benchmark 优先

主题：

```text
真机数据 + 开源预测性维护数据驱动的工业设备时序基础模型评测基准
```

该路线优先整理 FU13 真机数据和相关开源设备健康数据，建立统一数据语料、任务定义和评测协议。

优点：

- 最可执行，直接服务后续训练。
- 能解决小样本基础模型必须面对的数据来源问题。
- 能为开源模型对比和自研训练提供统一证据。

风险：

- 如果没有方法创新，容易退化成数据集整理或 benchmark 工程。
- 需要控制数据范围，避免泛化到所有通用时序数据。

### 推荐顺序

推荐采用组合路线：

```text
先用路线一建立学术问题框架；
再用路线三建立数据和评测证据；
最后收束到路线二的方法创新。
```

换句话说，A 阶段不是在三条路线里选一条，而是按下面的递进关系推进：

```text
工业设备小样本预测性维护问题
  -> 真机 + 开源设备健康数据统一语料
  -> 阶段感知、多传感器、多任务时序基础模型
  -> 与 TTM / MOMENT / Chronos / TimesFM / Moirai / UniTS 对比
  -> 论文、专利和模型训练路线共同成立
```

## 主流开源模型论文调研范围

A 阶段优先调研两类时序基础模型。

第一类是 forecasting-first 模型：

| 模型 | 重点 | A 阶段关注问题 |
| --- | --- | --- |
| TTM / TinyTimeMixer | 轻量 zero/few-shot 多变量 forecasting | 是否适合资源受限的工业部署；是否能作为预测残差基线 |
| Chronos / Chronos-Bolt | 将时序预测转化为 token 或语言模型式问题 | 是否适合工业传感器值域、离散化和不确定性预测 |
| TimesFM | decoder-only forecasting foundation model | 是否适合短期正常轨迹预测和趋势预测对照 |
| Moirai / Uni2TS | universal probabilistic forecasting | 是否适合跨数据集、跨变量数量、跨频率的 forecasting 对比 |

第二类是 multi-task / representation 模型：

| 模型 | 重点 | A 阶段关注问题 |
| --- | --- | --- |
| MOMENT | forecasting、imputation、classification、anomaly、representation | 是否适合作为多任务设备时序基础模型对照 |
| UniTS | 统一 predictive / generative time-series tasks | 任务 token 化和多任务统一机制是否能迁移到工业设备 |
| TSPulse / Granite Time Series | 表征、预测、补全、分类、异常等时间序列能力 | 是否适合设备状态表征和异常候选信号路线 |

调研时不只记录模型名字，应统一记录：

- 论文主张。
- 预训练数据来源。
- 支持任务。
- 输入输出限制。
- 是否支持多变量。
- 是否支持 metadata、covariates 或 exogenous signals。
- 是否支持 embedding。
- 是否支持 fine-tuning 或 adapter。
- 开源代码、权重、许可证和部署成本。
- 对工业设备小样本预测性维护的适配缺口。

## 预测性维护与设备健康数据调研范围

开源数据不应泛化到所有时间序列数据。A 阶段优先围绕预测性维护、设备健康管理、RUL、故障诊断和退化过程数据。

数据来源分三层：

```text
第一层：FU13 真机数据
作为当前真实设备样例和 pipeline 验证入口。

第二层：开源预测性维护 / 设备健康数据
用于扩展设备类型、工况形态、故障标签和 RUL 任务覆盖。

第三层：模拟或退化注入数据
用于补充弱标签、异常片段、退化趋势和预训练任务验证。
```

开源数据筛选优先级：

```text
1. 有 run-to-failure 或 RUL 的数据。
2. 有故障类型、健康状态或退化阶段标签的数据。
3. 有正常/异常标签的工业多传感器数据。
4. 无标签但具有真实工业运行形态的数据。
```

第一批候选数据集：

| 数据集 | 类型 | 价值 |
| --- | --- | --- |
| NASA C-MAPSS | 涡扇发动机退化 / RUL | run-to-failure 与 RUL 任务经典数据 |
| NASA IMS Bearing | 轴承退化 / 故障 | 设备健康和退化过程候选数据 |
| PRONOSTIA / FEMTO-ST | 轴承加速退化 / RUL | RUL、退化趋势和小样本适配候选 |
| Tennessee Eastman Process | 工业过程故障诊断 | 多变量过程监测、异常和故障分类候选 |
| 其他预测性维护公开数据 | 按质量筛选 | 扩展设备类型和任务覆盖 |

每个数据集应记录：

- 是否真实设备或高保真仿真。
- 设备类型和传感器数量。
- 是否多变量。
- 时间频率和长度。
- 是否有故障、退化、健康状态或 RUL 标签。
- 是否适合无监督预训练。
- 是否适合 few-shot / zero-shot 适配评测。
- 是否能映射到 B08 canonical observation schema。
- 许可证和下载限制。

## 模型训练路线

模型训练路线应从可控原型开始，不直接承诺大规模训练。

第一阶段：统一数据语料

```text
FU13 canonical observations
  + 开源预测性维护数据映射
  + 必要的模拟 / 退化注入数据
  -> 统一窗口、metadata 和任务标签
```

第二阶段：基础预训练任务

```text
masked sensor reconstruction
next-window forecasting
cross-sensor imputation
stage-aware representation learning
contrastive normal/abnormal representation
residual / trend / spike candidate signal generation
```

第三阶段：小样本适配任务

```text
stage classification
quality flag prediction
fault classification
degradation trend detection
RUL prediction
maintenance-event lead-time analysis
```

第四阶段：与开源模型对照

```text
forecasting-first 对照：TTM、Chronos、TimesFM、Moirai
multi-task / representation 对照：MOMENT、UniTS、TSPulse
工程 baseline：rolling baseline、robust baseline、seasonal naive、重构误差、变点检测
```

## 方法创新候选

第一版方法创新不应只是“训练一个 Transformer”。建议围绕结构感知建模展开：

```text
结构感知的工业设备时序基础模型
```

候选结构信息：

```text
device_id
sensor_id
physical_domain
process_stage
quality_flag
batch/cycle
sampling pattern
weak degradation/failure proxy
```

候选机制：

- 工艺阶段 token：表达不同阶段下正常模式分布不同。
- 传感器 token：表达不同 sensor_id 的统计特征和物理含义。
- 物理域 token：表达 thermal、mechanical、atmosphere、hydraulic 等子系统差异。
- 质量标记 token：表达 missing、invalid、unassigned_cycle、maintenance 等质量语义。
- batch/cycle encoding：表达连续炉或批次过程中的上下文边界。
- 多任务 head：同时支持 forecasting、imputation、representation、anomaly candidate signal 和 classification。
- 弱标签适配：利用 quality_flag、failure_proxy、stage、residual high-percentile 等弱监督信号。

这些机制可形成专利方向，也可作为后续自研模型的最小创新原型。

## 评测任务分层

预测性维护是第一下游验证目标，但第一版不应直接承诺生产告警、RUL 精确估计或维修建议。评测应分三层推进。

第一层：无标签可验证任务

```text
forecasting
imputation
masked reconstruction
embedding consistency
cross-sensor reconstruction
```

第二层：弱标签或业务代理任务

```text
stage classification
quality_flag prediction
sensor domain discrimination
residual high-percentile detection
trend / spike candidate signal
normal vs abnormal proxy separation
```

第三层：预测性维护目标任务

```text
fault classification
degradation trend detection
RUL
maintenance-event lead time
expert-reviewed anomaly relevance
```

当前 FU13 数据优先支持第一层和第二层。第三层需要依赖开源预测性维护数据、后续维修记录、停机记录或专家复核。

## 论文与专利主线

论文主线建议分两档。

第一档是框架与验证型论文：

```text
面向小样本工业物联设备健康管理的时序基础模型框架与验证
```

目标是证明问题定义、数据语料、任务谱系、开源模型缺口和最小训练/评测框架。

第二档是方法创新型论文：

```text
阶段感知、多传感器、多任务工业设备时序基础模型
```

目标是在第一档基础上提出具体结构、预训练目标和实验结果。

专利方向建议围绕：

- 工艺阶段与传感器物理域联合编码方法。
- 工业设备小样本预测性维护的基础时序模型预训练方法。
- 无故障标签条件下的设备异常候选信号生成方法。
- 真机数据与开源设备健康数据融合的设备时序基础模型训练方法。
- 基于多任务输出的设备状态表征、预测残差和退化趋势联合评估方法。

## A -> C -> B 衔接

A 阶段产物应直接服务 C 和 B。

C 阶段输入：

- 主流开源模型论文和能力矩阵。
- 可运行模型优先级。
- 统一 adapter contract 的任务需求。
- FU13 与开源设备健康数据上的统一评测口径。
- 每个模型的失败原因记录模板。

B 阶段输入：

- 自研模型必须解决的开源模型缺口。
- 第一版设备时序预训练语料设计。
- 结构感知建模机制。
- 预训练目标候选。
- 最小原型训练计划。
- Go / No-Go 条件。

进入 C 阶段前必须回答：

- 当前主流时序基础模型在哪些任务上已经足够强。
- 哪些模型只适合作为 forecasting 对照。
- 哪些模型适合作为 representation 或 multi-task 对照。
- 工业设备预测性维护场景的核心缺口是什么。

进入 B 阶段前必须回答：

- 开源模型在统一窗口、统一数据和统一指标下的主要缺口是什么。
- 缺口能否通过 adapter、prompt、轻量微调或数据预处理解决。
- 自研训练是否有明确优于开源模型的目标任务和可验证指标。
- 当前数据规模、算力和维护成本是否支撑最小原型。

## A 阶段交付物

A 阶段建议产出以下文档和表格：

- 学术主线综述：说明 B08 的问题定义、相关工作和学术缺口。
- 开源模型论文矩阵：TTM、MOMENT、Chronos、TimesFM、Moirai、UniTS、TSPulse 等。
- 预测性维护数据集矩阵：FU13、C-MAPSS、IMS、PRONOSTIA、TEP 等。
- 任务与指标矩阵：forecasting、imputation、representation、anomaly、classification、RUL。
- 模型训练路线草案：数据语料、预训练任务、小样本适配任务和最小原型。
- 论文/专利方向清单：区分框架型成果和方法型成果。
- C 阶段开源模型适配优先级：按任务和可运行性排序。

建议默认文件位置：

```text
docs/research/academic-mainline-review.md
docs/research/open-source-model-paper-matrix.md
docs/research/predictive-maintenance-dataset-matrix.md
docs/research/task-metric-matrix.md
docs/research/foundation-model-training-route.md
docs/research/paper-patent-directions.md
```

如果后续希望延续现有中文目录，也可以使用：

```text
docs/调研资料/学术主线综述.md
docs/调研资料/开源模型论文矩阵.md
docs/调研资料/预测性维护数据集矩阵.md
docs/调研资料/任务指标矩阵.md
docs/调研资料/基础模型训练路线.md
docs/调研资料/论文专利方向.md
```

建议优先采用 `docs/research/`，原因是后续会进入持续扩展的研究资产管理，英文目录更利于脚本、链接和长期维护。

## 不做事项与边界

A 阶段不做：

- 不直接启动大规模模型训练。
- 不承诺生产级预测性维护能力。
- 不把 `leak_current_monitoring` 写成项目终点。
- 不把 RUL 和维修建议作为第一版必须达成目标。
- 不泛化调研到金融、交通、天气、电力负荷等通用时间序列数据。
- 不因为某个开源模型名字先进就跳过统一评测。
- 不把自研训练写成已经决定；自研仍是 A/C 之后的条件性路线。

RUL 不被删除，只放入第三层目标。当开源数据或后续真机维修记录能支撑 RUL 评测时，再纳入训练和评估。

## 成功标准

A 阶段完成时，应能回答：

- B08 的论文主线是什么。
- B08 的专利主线是什么。
- 主流开源时序基础模型分别解决什么任务。
- 主流开源模型对工业物联设备小样本预测性维护有什么缺口。
- 第一批可用的预测性维护或设备健康开源数据有哪些。
- FU13 真机数据和开源数据如何共同服务预训练和评测。
- 第一版模型训练路线应先做哪些任务。
- 哪些任务可以由开源模型直接对照，哪些任务可能需要自研结构。
- 进入 C 阶段时优先适配哪些模型。
- 进入 B 阶段前需要哪些 Go / No-Go 证据。

## 参考资料入口

- [Tiny Time Mixers (TTMs): Fast Pre-trained Models for Enhanced Zero/Few-Shot Forecasting of Multivariate Time Series](https://arxiv.org/abs/2401.03955)
- [MOMENT: A Family of Open Time-series Foundation Models](https://arxiv.org/abs/2402.03885)
- [Chronos: Learning the Language of Time Series](https://arxiv.org/abs/2403.07815)
- [A decoder-only foundation model for time-series forecasting](https://arxiv.org/abs/2310.10688)
- [Unified Training of Universal Time Series Forecasting Transformers](https://arxiv.org/abs/2402.02592)
- [UniTS: A Unified Multi-Task Time Series Model](https://arxiv.org/abs/2403.00131)
- [IBM Granite Time Series](https://www.ibm.com/granite/docs/models/time-series)
- [NASA Prognostics Center of Excellence](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/)
- [NASA C-MAPSS Jet Engine Simulated Data](https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data)
- [NASA IMS Bearings](https://data.nasa.gov/dataset/ims-bearings)
