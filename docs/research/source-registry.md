# B08 论文/专利主线来源登记表

## 定位

本文件只登记支撑 B08 论文/专利主线的外部 primary sources，不写长篇读书笔记，不替代论文综述正文。

每条来源必须挂接至少一个 `supports_claim_id`、`patent_id` 或 `evidence_id`。不能挂接的资料不进入本表。

## 文档预算

- 第一轮最多登记 18 条 accepted/candidate 来源。
- rejected/needs-review 审计行最多额外保留 4 条，且必须解释重要排除原因。
- 不为单篇论文、单个模型、单个数据集或单个专利创建独立文档。
- 原始 PDF、模型权重、数据下载包不得放入 `docs/`。
- 二手博客、排行榜和新闻稿只能作为线索，不能作为主要证据。

## ID 字典

### supports_claim_id

| id | 含义 |
| --- | --- |
| C1_problem_definition | 小样本工业物联设备健康管理问题定义 |
| C2_related_work_map | 相关工作分层 |
| C3_industrial_gap | 工业 metadata / 弱标签 / 多任务缺口 |
| C4_framework_design | 数据-任务-模型-评测框架 |
| C5_validation_path | FU13 + 开源数据验证路径 |
| C6_boundary_claims | 边界和禁止过度承诺 |

### patent_id

| id | 含义 |
| --- | --- |
| P1_stage_sensor_encoding | 工艺阶段与传感器物理域联合编码 |
| P2_small_sample_pretraining | 小样本工业设备基础模型预训练 |
| P3_weak_label_anomaly_signal | 无故障标签异常候选信号生成 |
| P4_real_open_data_fusion | 真机与开源设备健康数据融合训练 |
| P5_multitask_health_evaluation | 多任务设备状态与退化趋势评估 |

### evidence_id

| id | 含义 |
| --- | --- |
| E1_forecasting_residual | forecasting residual 证据 |
| E2_representation | representation / probe 证据 |
| E3_imputation | imputation / reconstruction 证据 |
| E4_open_data_pm | run-to-failure / fault / RUL 开源数据证据 |
| E5_patent_effect | 专利技术效果证据 |

## 来源登记表

| source_id | type | title | url_or_doi | primary_source | supports_claim_id | patent_id | evidence_id | relevance | key_claim | checked_at | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S001_TTM_2024 | paper | Tiny Time Mixers (TTMs): Fast Pre-trained Models for Enhanced Zero/Few-Shot Forecasting of Multivariate Time Series | https://arxiv.org/abs/2401.03955 | yes | C2_related_work_map |  | E1_forecasting_residual | TTM 作为轻量级 TSFM 基线，适合对比 B08 设备时序场景的部署成本与预测能力。 | TTM 是约 1M 参数起的轻量预训练模型，面向多变量零/少样本预测，并强调 CPU-only 可用性。 | 2026-06-04 | accepted |
| S002_MOMENT_2024 | paper | MOMENT: A Family of Open Time-series Foundation Models | https://arxiv.org/abs/2402.03885 | yes | C2_related_work_map |  | E2_representation | MOMENT 支撑通用时序表征与多任务 related-work 边界。 | MOMENT 提出开放时序基础模型家族与 Time Series Pile，用于有限监督下的通用时序分析评测。 | 2026-06-04 | accepted |
| S003_CHRONOS_2024 | docs | Chronos: Learning the Language of Time Series | https://www.amazon.science/code-and-datasets/chronos-learning-the-language-of-time-series | yes | C2_related_work_map |  | E1_forecasting_residual | Chronos 支撑“把时序离散化为 token 后用语言模型预测”的 TSFM 路线。 | Chronos 将时间序列缩放量化为 token，用语言模型训练，并通过采样生成概率预测。 | 2026-06-04 | accepted |
| S004_TIMESFM_2023 | paper | A decoder-only foundation model for time-series forecasting | https://arxiv.org/abs/2310.10688 | yes | C2_related_work_map |  | E1_forecasting_residual | TimesFM 是解码器式 forecasting-only TSFM 的核心相关工作。 | TimesFM 使用 patched-decoder attention 预训练，支持不同历史长度、预测长度和时间粒度下的零样本预测。 | 2026-06-04 | accepted |
| S005_MOIRAI_2024 | paper | Unified Training of Universal Time Series Forecasting Transformers | https://arxiv.org/abs/2402.02592 | yes | C4_framework_design |  | E1_forecasting_residual | Moirai/Uni2TS 支撑跨频率、任意变量数和大规模开放数据预训练的框架设计参考。 | Moirai 针对 cross-frequency、any-variate 和分布差异问题设计 universal forecasting transformer，并在 LOTSA 上预训练。 | 2026-06-04 | accepted |
| S006_UNITS_2024 | paper | UniTS: A Unified Multi-Task Time Series Model | https://arxiv.org/abs/2403.00131 | yes | C4_framework_design |  | E3_imputation | UniTS 支撑 B08 多任务接口设计，尤其是预测、生成、插补等任务统一。 | UniTS 用 task tokenization 统一预测与生成任务，并覆盖 forecasting、classification、anomaly detection、imputation。 | 2026-06-04 | accepted |
| S007_TSPULSE_EXTENSION | paper | TSPulse: Tiny Pre-Trained Models with Disentangled Representations for Rapid Time-Series Analysis | https://arxiv.org/abs/2505.13033 | yes | C5_validation_path |  | E2_representation | TSPulse 可作为 B08 诊断型扩展候选，补充 anomaly/search/imputation/classification 证据接口。 | TSPulse 学习 temporal、spectral、semantic 三类解耦表征，并面向零样本诊断任务和 GPU-free 部署；后续仍需核对官方模型卡/代码发布状态。 | 2026-06-04 | candidate |
| S008_CMAPSS | dataset | Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation / NASA C-MAPSS | https://c3.ndc.nasa.gov/dashlink/static/media/publication/2008_IEEEPHM_CMAPPSDamagePropagation.pdf | yes | C5_validation_path |  | E4_open_data_pm | 航空发动机多变量退化时序与 RUL benchmark，可支撑开放退化验证路径。 | C-MAPSS 数据用于 run-to-failure/prognostics/RUL 任务，可作为 B08 退化时序验证路径；不证明 FU13 已具备生产 RUL 能力。 | 2026-06-04 | accepted |
| S009_IMS_BEARING | dataset | NASA PCoE Bearing Data Set, IMS University of Cincinnati | https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ | yes | C5_validation_path |  | E4_open_data_pm | 轴承状态监测/故障诊断/预测性维护公开数据，可支撑第三层目标任务候选验证。 | NASA PCoE 将 IMS Bearing 列为 prognostic repository 数据；可支持轴承退化/故障诊断/预测性维护验证，不应外推为 FU13 生产能力。 | 2026-06-04 | accepted |
| S010_PRONOSTIA | dataset | PRONOSTIA: An Experimental Platform for Bearings Accelerated Degradation Tests | https://publiweb.femto-st.fr/tntnet/entries/1528/documents/author/data | yes | C5_validation_path |  | E4_open_data_pm | 真实轴承加速退化、RUL challenge 数据，可支撑开放全寿命退化验证。 | PRONOSTIA 提供振动/温度等轴承全寿命退化数据，用于 fault detection、diagnostics、prognostics/RUL 评估；仅支持开放验证路径。 | 2026-06-04 | accepted |
| S011_TEP | dataset | Additional Tennessee Eastman Process Simulation Data for Anomaly Detection Evaluation | https://doi.org/10.7910/DVN/6C3JR1 | yes | C5_validation_path |  | E4_open_data_pm | 工业过程监控/异常检测/故障分类 benchmark，可支撑过程异常与故障分类验证。 | TEP Dataverse 数据面向 anomaly detection evaluation，可支持过程监控与故障检测/分类验证；不是 RUL 或预测性维护生产证据。 | 2026-06-04 | accepted |
| S012_PM_RUL_REVIEW | review | Prognostics and health management for predictive maintenance: A review | https://doi.org/10.1016/j.jmsy.2024.05.021 | yes | C2_related_work_map |  | E4_open_data_pm | PdM、PHM、RUL 相关工作边界，支撑问题定义和文献分层。 | 综述将 PHM/PdM 与健康评估、RUL 预测、维护调度关联；适合支撑 B08 问题定义和边界，不支撑 FU13 已实现完整 PdM。 | 2026-06-04 | accepted |
| S013_INDUSTRIAL_ANOMALY_REVIEW | review | Survey on data-driven industrial process monitoring and diagnosis | https://doi.org/10.1016/j.arcontrol.2012.09.004 | yes | C2_related_work_map |  | E1_forecasting_residual | 工业过程异常检测、故障诊断、SPM 任务定义，支撑异常/残差监控相关工作。 | 数据驱动过程监控覆盖 fault detection、diagnosis、reconstruction、quality monitoring；适合支撑 B08 工业异常/残差监控相关工作，不等同于 RUL。 | 2026-06-04 | accepted |
| S014_PRIOR_ART_P1 | patent | Anomaly detection and remedial recommendation | https://patents.google.com/patent/US11410891B2/en | yes |  | P1_stage_sensor_encoding |  | 多步骤制造场景 prior-art 线索，可能接近工艺阶段编码与工具/recipe 上下文。 | 提示多步骤半导体制造中按工艺步骤采集时间序列传感器数据、结合工具状态与 recipe 建模；可能接近“工艺阶段编码”和“传感器物理域/子系统上下文”的部分，但未直接限定联合编码结构。 | 2026-06-04 | needs-review |
| S015_PRIOR_ART_P2 | patent | Industrial large model platform and its system | https://patents.google.com/patent/CN119443259A/en | yes |  | P2_small_sample_pretraining |  | 工业基础大模型与小样本适配 prior-art 线索，但不是设备健康时序专门方案。 | 提示工业基础大模型预训练、小规模特定数据集二次训练、工业领域知识嵌入和小样本伪标签自训练；可能接近“小样本工业基础模型预训练/微调”主题。 | 2026-06-04 | needs-review |
| S016_PRIOR_ART_P3 | patent | Method for generating abnormal data | https://patents.google.com/patent/US20210124989A1 | yes |  | P3_weak_label_anomaly_signal |  | 弱标签/无故障标签异常候选信号 prior-art 线索。 | 提示在工业/半导体设备数据集中可含未标注数据或仅正常数据，通过数据变换生成异常数据并赋予伪异常标签；可能接近“无故障标签下生成异常候选信号/弱标签”的部分。 | 2026-06-04 | candidate |
| S017_PRIOR_ART_P4 | patent | Predictive maintenance for industrial machines | https://patents.google.com/patent/WO2022258835A1/en | yes |  | P4_real_open_data_fusion |  | 多机器、多域历史时序和迁移学习 prior-art 线索，但未直接出现开源设备健康数据融合。 | 提示多台工业机器、多域历史机器时序数据、数据 harmonizer、迁移学习和域自适应提取域不变特征；可能接近“真机/多来源设备健康数据融合训练”的部分。 | 2026-06-04 | needs-review |
| S018_PRIOR_ART_P5 | patent | Multi task learning with incomplete labels for predictive maintenance | https://patents.google.com/patent/US11231703B2/en | yes |  | P5_multitask_health_evaluation |  | 多任务预测性维护和标签不完整 prior-art 线索。 | 提示预测性维护中 RUL、故障预测、故障检测、性能退化检测等多任务共享建模，并处理标签不完整；可能接近“多任务设备状态与退化趋势评估”的核心任务组合。 | 2026-06-04 | candidate |

### 字段取值与格式约束

- `source_id` 使用 `S###_SHORT_NAME` 格式，例如 `S001_TTM_2024`。
- `type` 只能填写 `paper`、`repo`、`model-card`、`dataset`、`patent`、`review` 或 `docs`。
- `primary_source` 只能填写 `yes` 或 `no`。
- `supports_claim_id`、`patent_id`、`evidence_id` 至少一个非空；prior-art 来源可以只填写 `patent_id`。
- `relevance` 用一句话说明该来源和 B08 的关系。
- `checked_at` 使用 `YYYY-MM-DD` 格式。
- `status` 只能填写 `accepted`、`candidate`、`rejected` 或 `needs-review`。

## 使用规则

- `key_claim` 只记录与 B08 直接相关的最小证据。
- `status=accepted` 表示该来源已被主线文档引用。
- `status=candidate` 表示可用于后续核对，但尚未进入主线论证。
- `status=rejected` 表示核对后不采用，并需简述原因。
- `status=needs-review` 表示来源可靠性、许可证、接口或适用性仍需复核。
