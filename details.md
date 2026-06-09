# B08 设备时序基础模型进展台账

更新日期：2026-06-09

## 1. 当前阶段

项目当前处于 **C2.2 升级版开源模型真实执行与审计入口已完成，准备进入报告执行与复核** 阶段。

已经完成的主线基础包括：FU13 真实多 CSV 到 canonical observations 的装配、数据诊断、cycle 重构、baseline / TTM 真实窗口 forecasting、`leak_current_monitoring` 场景评测样例、C1 最小证据执行框架、C2 开源模型系统评测、C2.1 六模型 executable adapter 尝试入口，以及 C2.2 默认离线安全配置、CLI 入口、版本化核心模型目标矩阵和 frontier watchlist audit。

当前 C2.2 的定位不是“大规模训练”或“生产告警”，而是在 FU13 真实数据、统一 task matrix、本机 cache、显式 opt-in 联网/下载边界下，把核心开源时序基础模型尽可能真实运行；无法运行的模型必须输出具体原因，例如依赖、权重、接口、窗口形状、任务头、许可证或资源限制。C2.2 报告将用于判断后续是否进入 C3 跨数据验证，或是否具备进入 B 阶段条件性自研模型设计的证据。

当前默认入口：

```bash
uv run b08-model-core experiment c-stage-c22 \
  --config configs/c_stage_c22_open_model_executable_upgrade.yaml \
  --output reports/c_stage_c22_open_model_executable_upgrade.md
```

默认边界保持不变：不联网、不下载权重、不提交真实数据、不提交本机 cache；任何联网、下载、权重路径和 cache 使用都必须通过显式本机配置进入，并在报告或 cache manifest 中记录。

## 2. 每日更新

| 日期 | 当日完成内容 |
| --- | --- |
| 2026-06-09 | 完成 C3 公开数据 registry 入口文档同步：README 增加 `experiment c-stage-c3` 命令和不下载公开数据、不提交数据文件、不运行模型训练边界，并保留 details 三段式台账结构。 |
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

下一步主线是执行和复核 C2.2，而不是直接进入公开数据集整理或 B 阶段自研训练。整体思路是：先把 C2.2 报告跑成可复核证据，再根据模型真实运行结果决定是否进入 C3 跨数据验证；只有当 C2.2 / C3 证明开源模型存在关键缺口时，才进入 B 阶段条件性自研模型准备。

具体计划如下：

1. 做 C2.2 preflight：确认 `data/processed/fu13_real_observations.parquet` 是否存在、默认配置是否保持 `allow_network: false` / `allow_download: false`、本机 cache 路径是否可控、optional dependency 是否只在显式需要时安装。
2. 先跑默认离线 C2.2：生成 `reports/c_stage_c22_open_model_executable_upgrade.md` 和 `reports/c_stage_c22_model_cache_manifest.md`，确认报告能覆盖六个核心模型和 watchlist audit。
3. 以 TTM 作为 anchor / control：复核其在当前 FU13 窗口口径下是否仍可运行，确保 C2.2 报告至少有一个本机真实运行对照。
4. 分批尝试 priority forecasting 模型：优先 Chronos-2 / Chronos-Bolt fallback、TimesFM 2.5、Moirai 2.0 / Uni2TS；每个模型都要记录目标版本、实际 adapter 版本、依赖状态、权重状态、接口状态、窗口兼容性和失败分类。
5. 复核 representation / imputation 模型：MOMENT 和 UniTS 先聚焦 representation、imputation 和 multi-task 接口核验；除非官方接口稳定，否则 forecasting 只作为补充记录。
6. 保持 watchlist audit-only：Time-MoE、Sundial、Timer-S1 / Timer-XL、Kairos、Toto、IBM FlowState / TSPulse、TabPFN-TS 先按依赖、权重、接口、资源、license 和任务匹配度审计，不默认提升为必跑模型。
7. 产出 C2.2 决策结论：明确哪些模型可运行，哪些需要补依赖、权重、接口、任务头或资源，哪些能力值得进入 C3，哪些缺口可能支持 B 阶段条件性自研判断。
8. 若 C2.2 证明某些模型和任务值得继续验证，再进入 C3 公开数据与跨数据验证准备：整理公开数据集、license、schema mapping、任务标签、split policy 和跨数据指标。C3 的目标是判断模型能力是否能离开单台 FU13 样例，而不是替代 C2.2 的本机真实执行。
9. 若 C2.2 / C3 证据显示开源模型无法覆盖关键需求，且缺口足够稳定、数据规模和算力预算可被说明，再进入 B 阶段条件性自研模型设计。进入 B 阶段前应先形成可审查方案，包括输入格式、预训练目标、微调任务、训练 / 验证切分、最小原型、成本估计和 Go / No-Go 条件。
10. 后续文档维护继续保持分工：README 作为任何读者的项目入口，负责项目定位、快速开始、标准运行命令、关键目录和安全边界；`details.md` 只维护当前阶段、每日更新和下一步计划；阶段解释和执行细节优先写入对应 spec / plan / report，避免与 README 重复。
