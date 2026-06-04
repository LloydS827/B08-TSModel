# 任务与指标矩阵

## 目的

本矩阵用于把 B08 的预测性维护目标拆成可验证任务层级，服务开源模型适配、模型训练路线和知识成果论证；它不是生产验收指标清单。

因此，本文件关注研究任务如何定义、当前证据能够支持到哪一层、后续需要哪些数据或标签补充。矩阵中的指标用于统一比较不同模型和路线，不应被直接解释为生产告警阈值、维修建议或现场交付验收标准。

## 三层任务结构

B08 的任务验证按三层推进：

1. 第一层是无标签可验证任务，包括 forecasting、imputation / reconstruction 和 representation consistency。这一层适合预训练、开源模型对照和 FU13 当前无故障标签场景。
2. 第二层是弱标签或业务代理任务，包括 stage classification、quality_flag prediction、residual high-percentile detection 和 trend/spike candidate signal。这一层用于验证模型是否学习到工艺阶段、质量标记和候选异常信号相关语义。
3. 第三层是预测性维护目标任务，包括 fault classification、degradation trend / RUL 和 maintenance lead time。这一层依赖开源 run-to-failure 数据、维修记录、停机记录或专家复核补充。

当前 FU13 优先支持第一层和第二层；第三层需要开源 run-to-failure 数据、维修记录、停机记录或专家复核补充，不能从现有 FU13 证据直接推出。

| 层级 | 任务 | 指标 | 当前 FU13 支持 | 开源数据支持 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 无标签 | forecasting | MAE、RMSE、coverage | 已支持 | 候选支持 / 待来源与授权核对 | TTM 已在 FU13 跑通 |
| 无标签 | imputation / reconstruction | MAE、mask reconstruction error | 待实现 | 候选支持 / 待来源与授权核对 | 适合 MOMENT / UniTS / 自研预训练 |
| 无标签 | representation consistency | clustering、linear probe | 待实现 | 候选支持 / 待来源与授权核对 | 支持状态表征主线 |
| 弱标签 | stage classification | accuracy、F1 | 字段与输入排除口径确认后可支持 | 候选支持 / 待来源与授权核对 | 验证工艺阶段表征 |
| 弱标签 | quality_flag prediction | accuracy、F1 | 字段与输入排除口径确认后可支持 | 候选支持 / 待来源与授权核对 | 验证质量标记语义 |
| 弱标签 | residual high-percentile detection | precision@k、expert review hit rate | 可支持 | 候选支持 / 待来源与授权核对 | 对接候选异常信号 |
| 预测性维护 | fault classification | accuracy、F1、AUROC | 需标签 | 候选支持 / 待来源与授权核对 | 依赖公开故障数据 |
| 预测性维护 | degradation trend / RUL | MAE、RMSE、lead-time metric | 需标签 | 候选支持 / 待来源与授权核对 | 第三层目标 |
| 预测性维护 | maintenance lead time | lead-time recall、precision@k、提前量分布 | 需标签 | 候选支持 / 待来源与授权核对 | 需要维护事件、停机时间或故障确认时间 |

## 指标口径与无效解释

以下契约用于约束 C / B 阶段评测记录，不展开为完整实验方案。每个任务在进入比较前都应记录 `primary_metric`、`valid_when`、`split_policy`、`aggregation` 和 `invalid_interpretation`。

| 任务 | primary_metric | valid_when | split_policy | aggregation | invalid_interpretation |
| --- | --- | --- | --- | --- | --- |
| forecasting | MAE 或 RMSE，概率模型补 coverage | 预测窗口、horizon、目标变量和缺失处理一致 | 按时间或 run 切分，避免未来信息泄漏 | 按变量、设备或 run 汇总后报告均值和关键分位数 | 低预测误差不等于故障预警能力 |
| imputation / reconstruction | mask reconstruction error 或 MAE | mask 策略、可见上下文和被遮蔽变量一致 | mask 位置在评测集内生成，训练与评测窗口隔离 | 按 mask 类型、变量和设备汇总 | 补全好不等于已识别异常或维修需求 |
| representation consistency | linear probe F1 或 clustering score | embedding 固定，probe 标签不参与表征训练 | 按设备、run 或时间切分，probe 训练集与测试集隔离 | 按 split 汇总，必要时报告类别加权指标 | 聚类结构不等于真实健康状态分级 |
| stage classification | macro F1 | stage 标签来源明确，且 stage 未作为输入 metadata 被直接读取 | 按时间、batch 或 run 切分，避免同批次泄漏 | 按 stage 类别和整体 macro 汇总 | 如果 stage 进入输入，准确率不能解释为表征能力 |
| quality_flag prediction | macro F1 | quality_flag 标签来源明确，且 quality_flag 未作为输入 metadata 被直接读取 | 按时间、batch 或 run 切分，避免同源规则泄漏 | 按 flag 类别、设备和整体 macro 汇总 | 如果 quality_flag 进入输入，准确率不能解释为语义理解 |
| residual high-percentile detection | precision@k 或 expert review hit rate | 残差定义、top-k 比例和专家复核口径预先确定 | 候选生成窗口与复核窗口分离，避免后验挑选 | 按设备、时间段和候选批次汇总 | 高命中率不等于生产告警阈值或维修建议 |
| fault classification | macro F1 或 AUROC | 故障类型标签、故障时间和正常样本定义明确 | 按设备、run 或工况切分，避免同一故障轨迹泄漏 | 按故障类型和整体指标汇总 | 公开故障分类结果不等于 FU13 已有故障诊断能力 |
| degradation trend / RUL | RUL MAE / RMSE 或 lead-time metric | 存在 run-to-failure、退化标签或可信 RUL 构造规则 | 按 unit / run 切分，禁止同一退化轨迹跨集合 | 按 unit、工况和 horizon 汇总 | RUL 指标不等于当前可精确估计真实设备寿命 |
| maintenance lead time | lead-time recall 或 precision@k | 存在维护事件、停机时间或故障确认时间，事件定义可追溯 | 按事件或 run 切分，避免同一事件前后泄漏 | 按事件类型、提前量区间和设备汇总 | 提前命中不等于自动维修建议或现场处置闭环 |

## 无标签任务

无标签任务是 B08 当前最稳健的基础评测层，适合用于预训练目标、开源模型对照和缺少故障标签的真实设备数据场景。forecasting 可以评估模型对正常轨迹和短期趋势的拟合能力；imputation / reconstruction 可以评估模型对缺失、遮蔽或跨传感器片段的恢复能力；representation consistency 可以评估窗口或设备状态 embedding 是否形成稳定结构。

这类任务能够证明模型具备时间序列建模、补全或表征能力，但不代表模型已经具备业务告警能力。尤其是 forecasting residual 只能作为后续候选信号来源，不能直接等同于异常告警、设备故障或维护建议。

## 弱标签 / 业务代理任务

弱标签或业务代理任务用于连接真实设备语义和模型表征能力。stage classification 关注工艺阶段是否被模型区分；quality_flag prediction 关注质量标记是否能被时序上下文解释；residual high-percentile detection、trend/spike candidate signal 关注模型输出是否能产生值得进一步复核的候选异常信号。

这些任务的标签通常来自业务字段、规则构造或人工复核，不一定等同于真实故障标签。residual high-percentile、trend/spike candidate 都应被写成候选信号，不是告警阈值、维修建议或生产处置策略。进入后续阶段前，需要明确样本构造方式、时间切分策略、候选信号定义和专家复核口径。

## 预测性维护目标任务

预测性维护目标任务包括 fault classification、degradation trend / RUL 和 maintenance lead time。它们更接近 B08 的长期设备健康管理目标，但也对数据证据要求最高。

fault classification 需要明确故障类型标签；RUL 需要完整或近似完整的退化过程和 run-to-failure 记录；maintenance lead time 需要维护事件、停机记录、故障确认时间或专家复核结果。缺少这些证据时，不能从 FU13 当前 forecasting、残差或弱标签结果直接推出模型已经具备故障分类、RUL 精确估计或维护提前量预测能力。

## FU13 当前支持情况

FU13 当前最适合作为真实工业设备 pipeline 和第一、第二层任务的验证入口。已有证据支持 forecasting 路线，其中 TTM 已在 FU13 上跑通，可作为 forecasting-only 基线和残差候选信号来源。

FU13 可继续支持 stage classification、quality_flag prediction 和 residual high-percentile detection 等弱标签任务，前提是阶段字段、质量标记、输入排除口径和候选信号构造口径被清楚记录。stage classification 与 quality_flag prediction 只有在确认字段来源、标签是否参与输入、是否经过专家复核或业务规则复核后，才适合解释为表征能力验证。

如果 stage 或 quality_flag 作为输入 metadata 被模型直接读取，则不能把分类准确率解释为模型学到了阶段表征或质量标记语义；此时结果最多说明模型能够利用显式字段完成读出任务。imputation / reconstruction 与 representation consistency 尚待实现，不应写成当前已完成能力。

FU13 当前不应被表述为已经支撑完整预测性维护闭环。fault classification、RUL、maintenance lead time 仍需要真实故障标签、维修记录、停机记录或专家复核补充。

## 开源数据补充情况

开源预测性维护数据用于补足 FU13 暂时缺少的第三层证据，但当前只能写成候选支持 / 待来源与授权核对。C-MAPSS 更偏 RUL 和退化轨迹评测；IMS Bearing、PRONOSTIA / FEMTO-ST 更偏轴承退化和 run-to-failure 过程；Tennessee Eastman Process 更偏过程故障分类、异常监控和多变量过程状态评测，不应笼统覆盖所有第三层任务。

这些数据适合作为公开 benchmark、方法对照和第三层目标验证入口，但不能替代 FU13 的现场语义。进入正式训练或对外成果前，需要逐项核对来源、许可证、再分发边界、标签语义、schema 映射和 split policy，避免把公开数据实验直接解释为生产预测性维护能力。

## 训练路线接口

为了让任务矩阵能被后续训练路线引用，建议每个候选实验条目至少保留以下字段：

| 字段 | 含义 |
| --- | --- |
| task_id | 任务唯一标识，例如 `fu13_forecasting_v1` 或 `cmapps_rul_v1`，用于追踪数据、模型和报告 |
| stage | 所属阶段，例如 A 研究定义、C 开源模型适配、B 自研原型判断 |
| required_data | 任务需要的数据类型，例如 FU13 窗口、公开 run-to-failure 数据、维护事件表或专家复核样本 |
| required_label | 任务需要的标签或弱标签，例如 stage、quality_flag、fault_type、RUL、maintenance_event；无标签任务应明确为 none |
| baseline | 必须对照的强基线，例如 TTM forecasting-only、简单统计补全、冻结 embedding + linear probe |
| candidate_model_type | 候选模型类型，例如 forecasting-first 开源模型、multi-task / representation 开源模型、自研原型 |
| primary_metric | 预先指定的主指标，只能在评测前确定，不能后验挑选 |
| gate | 进入下一阶段的门槛，包括最低相对 / 绝对增益、是否需要多 seed 或置信区间、失败时 No-Go 条件 |
| artifact_output | 需要沉淀的产物，例如指标表、失败原因记录、候选样本列表、专家复核记录或模型适配说明 |
| known_invalid_claims | 明确禁止的解释，例如生产告警、RUL 精确估计、自动维修建议、由弱标签直接推出故障诊断能力 |

## 进入 C / B 阶段的指标要求

C 阶段要求每个开源模型在可支持任务上给出同口径指标或明确失败原因。同口径至少包括统一数据窗口、统一任务定义、统一指标计算方式和可追溯的失败记录；如果模型因输入长度、变量形式、依赖环境、任务头缺失或许可证边界无法运行，应明确记录原因，而不是用缺失结果替代评估。

B 阶段不得后验挑选任务。进入自研原型前，必须预先指定主任务、强基线、最低相对 / 绝对增益、是否需要多 seed 或置信区间，以及失败时 No-Go 条件。自研原型至少应在一个 representation / imputation / weak-label 任务上显示相对 forecasting-only 模型的明确增益，否则不进入更大规模训练。

这里的增益可以来自更好的补全误差、更稳定的状态表征、更高的弱标签分类指标，或更高质量的专家复核候选命中率；但所有增益都需要在同一数据切分、同一指标口径和预先声明的 gate 下比较。

若 C 阶段只证明 forecasting-only 模型已经足够，或自研原型无法在 representation / imputation / weak-label 任务上提供明确收益，则应优先沉淀开源模型适配和评测流程，而不是扩大自研预训练规模。

如果没有足够数据、标签、复核记录或统计证据支撑，上述任务只能保留为路线假设，不进入大规模训练。
