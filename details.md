# B08 设备时序基础模型进展台账

更新日期：2026-06-09

## 1. 当前阶段

项目当前处于 **C3 公开数据 registry 已完成，准备进入 C3.1 单数据集最小接入与 schema validation** 阶段。

已经完成的主线基础包括：FU13 真实多 CSV 到 canonical observations 的装配、数据诊断、cycle 重构、baseline / TTM 真实窗口 forecasting、`leak_current_monitoring` 场景评测样例、C1 最小证据执行框架、C2 开源模型系统评测、C2.1 六模型 executable adapter 尝试入口、C2.2 默认离线安全配置与 frontier watchlist audit，以及 C3 公开数据 registry 配置、CLI 入口、字段验证和报告渲染。

当前 C3 的定位不是“大规模公开数据整理”或“跨数据模型训练”，而是在 registry 边界下先确认公开数据来源、许可、任务语义、schema mapping、split policy、泄漏风险和 go/no-go 条件。C3 第一轮已经完成 registry 层；下一轮 C3.1 应选择一个公开数据集做深一点，进入最小下载边界、schema mapping dry-run、split/leakage 校验和可复核报告。

当前默认入口：

```bash
uv run b08-model-core experiment c-stage-c3 \
  --config configs/c_stage_c3_public_dataset_registry.yaml \
  --output reports/c_stage_c3_public_dataset_registry.md
```

默认边界保持不变：不下载公开数据、不提交公开数据文件、不运行模型训练、不提交真实数据、不提交本机 cache；任何联网、下载、权重路径和 cache 使用都必须通过显式本机配置进入，并在报告中记录。

## 2. 每日更新

| 日期 | 当日完成内容 |
| --- | --- |
| 2026-06-09 | 完成 C3 公开数据 registry 第一轮并通过 PR #11 合并到 `main`：新增 `configs/c_stage_c3_public_dataset_registry.yaml`、CLI `experiment c-stage-c3`、registry loader / validator / report renderer、字段完整性和安全边界测试；README 增加 C3 入口命令和不下载公开数据、不提交数据文件、不运行模型训练边界；完成 C3.1 NASA C-MAPSS 单数据集最小接入与 schema validation 设计，锁定 NASA PCoE #6 经典 C-MAPSS，明确 source/license preflight、最小下载边界、schema mapping dry-run、split/leakage guard 和不运行模型训练的边界。 |
| 2026-06-08 | 完成 C2.2 升级版开源模型真实执行与审计入口：新增 `configs/c_stage_c22_open_model_executable_upgrade.yaml`、CLI `experiment c-stage-c22`、版本化核心模型目标矩阵、C2.1 runner wrapper、strict required-attempt 检查、cache manifest、frontier watchlist audit 和报告渲染；同步更新 README、details、C2.2 spec 和 implementation plan，并通过 PR 合并到 `main`。 |
| 2026-06-07 | 完成 README / details 第一轮入口文档整理；完成 2025-2026 开源时序基础模型补充调研，确认 Chronos-2、TimesFM 2.5、Moirai 2.0 需要进入 C2.2 版本化目标，Time-MoE、Sundial、Timer-S1 / Timer-XL、Kairos、Toto、IBM FlowState / TSPulse、TabPFN-TS 先进入 watchlist audit；完成 C2.1 设计与实现合并。 |
| 2026-06-06 | C2.1 开源模型真实执行评测进入执行入口：核心配置为 `configs/c_stage_c21_executable_open_model_evaluation.yaml`，命令为 `uv run b08-model-core experiment c-stage-c21 --config configs/c_stage_c21_executable_open_model_evaluation.yaml --output reports/c_stage_c21_executable_open_model_evaluation.md`；建立六模型 executable adapter contract、task matrix、真实 adapter 优先、结构化失败记录兜底和默认离线安全边界。 |
| 2026-06-05 | 完成 C1 最小证据执行框架和 C2 开源模型系统评测入口：固定 E1 forecasting residual、E2 representation、E3 imputation 的证据口径，并为 TTM、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS 建立 audit、model-task attempt 和结构化失败报告。 |
| 2026-06-04 | 收束 A 阶段学术主线和 C 阶段最小证据规划：明确短期知识成果、工程化产品承接线、`configs/c_stage_minimum_evidence.yaml`、研究资产入口和 C 阶段 Go / No-Go 证据边界。 |
| 2026-06-03 | 完成 `leak_current_monitoring` 第一版 scenario-filtered evaluation，把 baseline / TTM forecasting residual 汇总为候选异常信号样例；该结果只用于业务语境复核，不代表生产告警或维修建议。 |
| 2026-06-02 | 完成 FU13 真实数据闭环：多 CSV 装配、canonical observation schema、连续炉 cycle 重构、数据质量诊断和真实窗口 forecasting；形成 4,126,789 行标准观测、8 个传感器、8 个阶段、428 个重构 cycle。 |
| 2026-06-01 | 将本地研发流程收束到 `uv`、optional TTM 依赖、本机权重 cache、Markdown / HTML 报告和 baseline / TTM 同口径实验；TTM 在 FU13-like 窗口上跑通并可与 baseline 比较。 |
| 2026-05-31 | 建立模型核心沙盒：模拟数据、canonical schema、窗口构建、baseline、benchmark、真实数据 schema map、validation CLI 和 forecasting 实验脚手架。 |

## 3. 下一步计划

下一步主线是 C3.1 单数据集最小接入与 schema validation，而不是直接整理多个公开数据集、跑跨数据模型评测或进入 B 阶段自研训练。整体思路是：先从 C3 registry 中选择一个最适合做深的数据集，把来源、许可、下载边界、schema mapping、split policy、泄漏风险和报告闭环跑通；只有该闭环可复核后，再进入 C3.2 跨数据模型评测。

具体计划如下：

1. 选择一个 C3.1 深入数据集：优先从 `nasa_cmapss`、`pronostia_femto`、`ims_bearing`、`tennessee_eastman_process` 中挑选 source/license 最容易确认、任务语义最清楚、schema mapping 对 B08 最有价值的候选。
2. 做 source/license preflight：确认 official source、下载入口、许可和 training use 边界；若许可或来源不能确认，则不得进入下载和 mapping。
3. 设计最小下载边界：只允许下载或引用 C3.1 需要的最小原始文件，不提交原始数据、派生 parquet 或本机 cache；下载路径必须保持 ignored。
4. 建立 schema mapping dry-run：把数据集的 unit/run/cycle、timestamp 或 sample index、sensor/channel、value、condition、label 等字段映射到 B08 canonical observation schema。
5. 建立 split/leakage guard：根据数据集类型明确 unit/run/condition/time/fault trajectory 切分策略，并用测试防止同一运行轨迹或相邻窗口泄漏。
6. 输出 C3.1 报告：报告应记录 source/license 结论、schema mapping 状态、样本规模摘要、split policy、可支持任务、不可声明内容和 C3.2 Go / No-Go。
7. 暂不运行开源模型跨数据评测：C3.1 的成功标准是数据进入 B08 评测体系的可复核接入闭环；模型评测放到 C3.2。
8. 若 C3.1 证明单数据集接入可行，再扩展到第二个公开数据集或进入 C3.2 open model cross-dataset evaluation。
9. 若 C3.1 暴露公开数据和 FU13 任务语义差距过大，应先回到 registry 修正任务边界，而不是仓促进入 B 阶段自研模型设计。
10. 后续文档维护继续保持分工：README 作为任何读者的项目入口，负责项目定位、快速开始、标准运行命令、关键目录和安全边界；`details.md` 只维护当前阶段、每日更新和下一步计划；阶段解释和执行细节优先写入对应 spec / plan / report，避免与 README 重复。
