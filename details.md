# B08 设备时序基础模型进展台账

更新日期：2026-06-10

## 1. 当前阶段

项目当前处于 **C3.1 NASA C-MAPSS 默认 preflight review 已执行，source/download target 已校准但 local raw opt-in 和 C3.2 继续 blocked** 阶段。

已经完成的主线基础包括：FU13 真实多 CSV 到 canonical observations 的装配、数据诊断、cycle 重构、baseline / TTM 真实窗口 forecasting、`leak_current_monitoring` 场景评测样例、C1 最小证据执行框架、C2 开源模型系统评测、C2.1 六模型 executable adapter 尝试入口、C2.2 默认离线安全配置与 frontier watchlist audit、C3 公开数据 registry，以及 C3.1 NASA PCoE #6 经典 C-MAPSS 的默认离线配置、loader、parser、schema mapping dry-run、RUL target metadata、split/leakage guard、CLI report 和回归测试。

当前 C3.1 的定位不是“下载 NASA C-MAPSS 数据并训练模型”，而是在默认离线边界下把 source/license review、schema validation、canonical observation mapping、RUL 标签语义、split/leakage 风险和 C3.2 Go / No-Go 写成可复核报告。2026-06-10 review 已确认 NASA PCoE #6 source 和 S3 download target 身份，但 license、redistribution、research training/evaluation use 仍未明确；因此 local raw opt-in 和 C3.2 继续 blocked。

当前默认入口：

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output reports/c_stage_c31_cmapss_minimal_ingestion.md
```

默认边界保持不变：不下载公开数据、不读取本机 raw files、不写 processed data、不运行模型训练、不提交公开数据文件、不提交真实数据、不提交本机 cache；任何联网、下载、raw mapping、权重路径和 cache 使用都必须通过显式本机配置进入，并在报告中记录。

## 2. 每日更新

| 日期 | 当日完成内容 |
| --- | --- |
| 2026-06-10 | 完成 C3.1 NASA C-MAPSS 最小接入实现、default preflight review 和报告增强：新增默认离线 config、loader、NASA PCoE #6 经典文件 contract、raw parser、canonical mapping、RUL target metadata、split/leakage guard、Markdown report、CLI `experiment c-stage-c31`、README / details 入口和回归测试；完成 source/license review 文档，确认 source/download target 已校准但 license / redistribution / research training-evaluation use 未明确，local raw opt-in 和 C3.2 继续 blocked；默认仍保持不下载公开数据、不读取本机 raw files、不写 processed data、不运行模型训练。 |
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

下一步主线是获取明确的 C-MAPSS 使用授权，或选择 C3 registry 中下一个公开数据集继续 source/license review；不是直接下载公开数据、整理多个公开数据集、跑跨数据模型评测或进入 B 阶段自研训练。C3.1 默认 preflight 已完成并确认 blocked / No-Go 符合当前 source/license 状态；只有 license、redistribution 和 training-use 边界明确后，才允许本机 ignored raw mapping 或后续 C3.2。

具体计划如下：

1. 获取 C-MAPSS 明确使用授权或可复核 license / redistribution / research training-evaluation use 结论；如果无法澄清，则选择 C3 registry 中下一个公开数据集做同等 source/license review。
2. 决策 local raw opt-in：只有 license、redistribution 和 training-use 明确后，才允许在 ignored 本机目录放置 C-MAPSS raw files，并通过显式配置打开 `allow_local_raw_data: true`；仍不提交 raw、zip、parquet、报告产物或 cache。
3. 执行本机 raw mapping review：在 opt-in 条件满足时，复核 parser、schema validation、canonical observation mapping、RUL target metadata、split policy 和 leakage guard 的报告输出；发现 schema 或标签语义不匹配时先修正 C3.1，不推进 C3.2。
4. 决策 C3.2：只有完整经典 C-MAPSS schema validation 通过、source/license/training-use 明确、split/leakage guard 无阻断后，才允许设计 C3.2 open model cross-dataset evaluation；C3.2 前仍不下载公开数据到仓库、不提交数据、不训练模型。
5. 继续维护文档分工：README 作为任何读者的项目入口，负责项目定位、快速开始、标准运行命令、关键目录和安全边界；`details.md` 只维护当前阶段、每日更新和下一步计划；阶段解释和执行细节优先写入对应 spec / plan / report，避免与 README 重复。
