# B08 设备时序基础模型进展台账

更新日期：2026-06-11

## 1. 当前阶段

项目当前处于 **C3.2 open model cross-dataset evaluation contract scaffold 已完成，下一步进入 explicit local execution design** 阶段。

已经完成的主线基础包括：FU13 真实多 CSV 到 canonical observations 的装配、数据诊断、cycle 重构、baseline / TTM 真实窗口 forecasting、`leak_current_monitoring` 场景评测样例、C1 最小证据执行框架、C2 开源模型系统评测、C2.1 六模型 executable adapter 尝试入口、C2.2 默认离线安全配置与 frontier watchlist audit、C3 公开数据 registry，C3.1 NASA PCoE #6 经典 C-MAPSS 的默认离线配置、loader、parser、schema mapping dry-run、RUL target metadata、split/leakage guard、CLI report 和回归测试，以及 C3.2 cross-dataset evaluation contract scaffold。

当前 C3.2 的定位不是“直接跑完整公开 benchmark 或开源模型排行榜”，而是在默认离线边界下把 C-MAPSS classic RUL、FU13 real forecasting evidence、FU13-like simulated forecasting、baseline / open model candidates、metric contract 和 Go / No-Go 写成可执行报告。C3.1 explicit local raw mapping review 已验证完整经典 C-MAPSS schema、RUL metadata 和 split/leakage guard，状态为 `schema_validated_ready_for_c32`，readiness detail 为 `full_classic_cmapss_validated`。C3.2 默认报告状态为 `contract_ready_local_execution_blocked`，可以进入 local execution design，但默认 local raw、download、model cache、processed write、scoring 和模型训练仍保持 disabled。

当前默认入口：

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output reports/c_stage_c31_cmapss_minimal_ingestion.md
```

C3.2 默认入口：

```bash
uv run b08-model-core experiment c-stage-c32 \
  --config configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml \
  --output reports/c_stage_c32_open_model_cross_dataset_evaluation.md
```

默认边界保持不变：不下载公开数据、不读取本机 raw files、不读取 C-MAPSS raw、不读取 FU13 real、不检查 model cache、不写 processed data、不运行模型训练、不生成 leaderboard、不提交公开数据文件、不提交真实数据、不提交本机 cache；任何联网、下载、raw mapping、权重路径和 cache 使用都必须通过显式本机配置进入，并在报告中记录。

## 2. 每日更新

| 日期 | 当日完成内容 |
| --- | --- |
| 2026-06-11 | 完成 C3.2 open model cross-dataset evaluation contract scaffold：新增默认安全 config、loader/validator、runner、Markdown report 和 CLI `experiment c-stage-c32`；报告默认状态为 `contract_ready_local_execution_blocked`，记录 C3.1 prerequisite、dataset view matrix、task compatibility、model candidate status、metric contract、Go / No-Go 和 invalid claims；默认不下载公开数据、不读取 C-MAPSS raw、不读取 FU13 real、不检查 model cache、不实例化 open model adapter、不运行模型训练、不计算模型分数、不生成 leaderboard。 |
| 2026-06-11 | 完成 C3.1 NASA C-MAPSS explicit local raw mapping review：在 ignored 本机目录下载并校验 Zenodo `CMAPSSData.zip`，验证 size `12425978` 和 MD5 `79a22f36e80606c69d0e9e4da5bb2b7a`，只抽取 12 个经典 raw text 文件；通过 `configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml` 执行本机 opt-in review，得到 `schema_validated_ready_for_c32` / `full_classic_cmapss_validated`，确认 observation rows 6,366,144、trajectory count 1,416、RUL target rows 265,256、split/leakage guard 全 0 或 none；未提交 raw、zip、parquet、cache 或生成报告。 |
| 2026-06-10 | 完成 C3.1 NASA C-MAPSS 最小接入实现、default preflight review、source/license review 和 license evidence update：新增默认离线 config、loader、NASA PCoE #6 经典文件 contract、raw parser、canonical mapping、RUL target metadata、split/leakage guard、Markdown report、CLI `experiment c-stage-c31`、README / details 入口和回归测试；确认 source/download target 已校准，并记录 Zenodo CC BY 4.0 证据，将 C-MAPSS 推进到可设计 explicit local raw mapping review；默认仍保持不下载公开数据、不读取本机 raw files、不写 processed data、不运行模型训练，C3.2 继续 blocked。 |
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

下一步主线是设计 C3.2 explicit local execution；不是继续停留在 C3.1 授权或 raw mapping，也不是直接训练自研基础模型、扩大到多个未审计公开数据集，或生成跨任务 leaderboard。C3.2 contract scaffold 已经完成，下一步应该在显式本机 opt-in 下设计最小可运行评估。

具体计划如下：

1. 设计 C3.2 explicit local execution：第一轮只允许 C-MAPSS RUL baseline evaluation 和 FU13-like forecasting reference，不进入完整 open model 竞赛。
2. 保持指标分离：C-MAPSS RUL 使用 RUL MAE / RMSE / NASA score；FU13-like forecasting 使用 forecasting MAE / RMSE / residual ranking；不生成 leaderboard，不把二者合成单一排名。
3. 继续保留安全边界：默认不下载公开数据、不提交 raw / zip / parquet / cache、不运行训练；任何 raw、权重、cache、联网执行都必须使用 explicit local opt-in 配置。
4. 保留 fallback：如果 Zenodo / CC BY evidence 后续被推翻或撤回，则回到 C3 registry，选择许可证更清晰的数据集做 C3.1b 单数据集深入。
5. 继续维护文档分工：README 作为任何读者的项目入口，负责项目定位、快速开始、标准运行命令、关键目录和安全边界；`details.md` 只维护当前阶段、每日更新和下一步计划；阶段解释和执行细节优先写入对应 spec / plan / report，避免与 README 重复。
