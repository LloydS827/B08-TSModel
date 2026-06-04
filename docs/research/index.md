# B08 A 阶段研究资产入口

## 定位

A 阶段用于把 B08 从“真实数据与模型评测沙盒”推进到“面向小样本工业物联设备健康管理的时序基础模型”学术主线。

短期第一目标是知识成果，包括论文主线、专利方向、学术综述和模型路线论证；第二目标是工程化产品成果，包括统一数据语料、模型训练路线、开源模型适配和可复现评测 workflow。

本入口用于连接整体重构蓝图和后续研究文档，帮助项目成员先理解主线、边界和阅读顺序，再进入具体综述、矩阵、训练路线和工程化承接材料。

## 两条主线

**知识成果优先线**：面向论文、专利、学术综述、模型路线、数据/任务矩阵和阶段性研究判断。该主线负责定义 B08 的研究问题、适用场景、方法假设、任务边界和评价口径。

**工程化产品承接线**：面向统一数据语料、开源模型适配、训练评测 workflow 和可复现模型研发工作台。该主线负责把知识成果中的问题定义和方法假设转化为可复现验证、可持续迭代和后续交付基础。

两条主线的关系是：知识成果定义问题与方法，工程化产品提供可复现验证和后续交付基础。工程化产品不应脱离知识主线做孤立平台化建设，知识成果也不应停留在不可验证的叙述层。

## 研究资产列表

| 文件 | 状态 | 职责 |
| --- | --- | --- |
| [project-mainline-refactor-blueprint.md](project-mainline-refactor-blueprint.md) | 已创建 | 定义 B08 下一阶段整体重构蓝图、两条主线、资产归属、执行门和后续重构判定规则。 |
| [mainline-refactor-audit.md](mainline-refactor-audit.md) | 已创建 / 已通过 Task 12 review | 记录是否需要立即代码重构、必要重构执行门、后续 C/B 阶段重构触发条件。 |
| [academic-mainline-review.md](academic-mainline-review.md) | 已创建 / 已通过 Task 4 review | 沉淀 A 阶段学术主线综述，明确小样本工业物联设备健康管理、时序基础模型和预测性维护之间的研究定位。 |
| [open-source-model-paper-matrix.md](open-source-model-paper-matrix.md) | 已创建 / 已通过 Task 5 review | 建立开源时序基础模型与关键论文矩阵，比较模型假设、输入输出、任务覆盖、适配成本和可复现条件。 |
| [predictive-maintenance-dataset-matrix.md](predictive-maintenance-dataset-matrix.md) | 已创建 / 已通过 Task 6 review | 梳理预测性维护与工业设备健康管理数据集矩阵，记录数据来源、设备对象、传感器形态、标签类型、公开性和适配风险。 |
| [task-metric-matrix.md](task-metric-matrix.md) | 已创建 / 已通过 Task 7 review | 定义 B08 A 阶段任务与指标矩阵，明确异常检测、故障诊断、健康状态识别、RUL 相关任务和评测口径。 |
| [foundation-model-training-route.md](foundation-model-training-route.md) | 已创建 / 已通过 Task 8 review | 跨线资产：知识成果优先线负责方法假设、任务口径和路线论证；工程化产品承接线负责 workflow、adapter、训练评测承接和验证门。 |
| [paper-patent-directions.md](paper-patent-directions.md) | 已创建 / 已通过 Task 9 review | 汇总论文主线、专利方向和可沉淀创新点，区分短期可写作主题、中期方法创新和长期系统化成果。 |
| [source-registry.md](source-registry.md) | 已创建 / Task 2 skeleton | 统一登记外部论文、仓库、模型卡、数据集和专利来源，要求每条来源挂接 claim/evidence/patent ID，避免碎片化文档。 |
| [productization-roadmap.md](productization-roadmap.md) | 已创建 / 已通过 Task 10 review | 承接工程化产品路线，定义统一数据语料、开源模型适配、训练评测 workflow 和可复现模型研发工作台的后续建设路径。 |

## 知识成果优先线

知识成果优先线是 A 阶段的第一目标，核心任务是把 B08 的研究对象、问题边界、方法路线和评价口径说清楚，并形成可持续扩展的论文、专利、综述和模型路线资产。

该主线优先回答以下问题：

1. B08 面向的工业物联设备健康管理问题是什么，哪些问题适合用时序基础模型表达。
2. 小样本、真实设备数据、传感器时序、多任务评测和可复现 workflow 之间的关系如何建立。
3. 现有开源模型、公开论文和预测性维护数据集能支持哪些实验假设，哪些假设仍需要谨慎保留。
4. 论文主线、专利方向和模型路线论证应如何对齐，避免研究叙述与工程验证脱节。

现有 `academic-mainline-review.md`、`open-source-model-paper-matrix.md`、`predictive-maintenance-dataset-matrix.md`、`task-metric-matrix.md` 和 `paper-patent-directions.md` 均属于该主线资产。`foundation-model-training-route.md` 是跨线资产，在知识成果优先线中只负责方法假设、任务口径和路线论证，不应被写成完整工程执行方案。

## 工程化产品承接线

工程化产品承接线是 A 阶段的第二目标，核心任务是为知识成果提供可复现验证和后续交付基础，而不是在学术问题尚未收敛前启动孤立平台化建设。

该主线重点承接以下能力：

1. 统一数据语料：把真实数据、公开数据集、schema map 和任务切片纳入可追溯的数据资产规则。
2. 模型训练路线：围绕预训练、微调、adapter 和任务头建立阶段性训练与评测路径。
3. 开源模型适配：明确开源时序基础模型的输入格式、依赖边界、适配成本和实验可复现条件。
4. 可复现评测 workflow：让数据准备、模型适配、训练评测、结果报告和阶段 review 能够被重复执行和审计。

现有 `productization-roadmap.md` 是该主线的主要承接资产。`foundation-model-training-route.md` 是跨线资产，在工程化产品承接线中只负责 workflow、adapter、训练评测承接和验证门，并与知识成果优先线中的方法假设、任务口径和路线论证保持引用关系。

## 执行边界

A 阶段不直接启动大规模模型训练，不承诺生产告警、RUL 精确估计或自动维修建议；必要重构不后置为模糊债务，但代码重构必须经过证据、验证和回滚路径判定。

A 阶段的默认产出优先是研究判断、资产矩阵、训练路线论证和可复现 workflow 设计。任何涉及 `src/`、CLI、configs、tests、reports、data 或模型缓存边界的实际代码重构，都必须先证明其已经阻碍知识成果优先线或工程化产品承接线，并通过独立 spec、plan、验证门和回滚路径执行。

本入口不替代 README、details、docs/index 或具体执行计划，也不暗示未来新增研究资产会自动完成。后续新增文件只有在独立任务中完成并通过 review 后，才应纳入本索引并标注状态。

## 计划阅读顺序

本节为建议阅读顺序，所有列出资产均已创建，实际执行时仍以各文档最新状态为准。

1. 先读 [project-mainline-refactor-blueprint.md](project-mainline-refactor-blueprint.md)，理解整体重构蓝图、两条主线、资产归属和执行门。
2. 再读 [mainline-refactor-audit.md](mainline-refactor-audit.md)（已创建 / 已通过 Task 12 review），理解是否需要立即代码重构、必要重构执行门和 C/B 阶段前的触发条件。
3. 接着读 [academic-mainline-review.md](academic-mainline-review.md)（已创建 / 已通过 Task 4 review），建立 A 阶段学术主线、研究问题和方法定位。
4. 然后读 [open-source-model-paper-matrix.md](open-source-model-paper-matrix.md)（已创建 / 已通过 Task 5 review）、[predictive-maintenance-dataset-matrix.md](predictive-maintenance-dataset-matrix.md)（已创建 / 已通过 Task 6 review）和 [task-metric-matrix.md](task-metric-matrix.md)（已创建 / 已通过 Task 7 review），对齐模型、数据和任务评价口径。
5. 最后读 [foundation-model-training-route.md](foundation-model-training-route.md)（已创建 / 已通过 Task 8 review）、[paper-patent-directions.md](paper-patent-directions.md)（已创建 / 已通过 Task 9 review；可选配套证据登记表：[source-registry.md](source-registry.md)）和 [productization-roadmap.md](productization-roadmap.md)（已创建 / 已通过 Task 10 review），进入训练路线、论文专利方向和工程化产品承接路线。
