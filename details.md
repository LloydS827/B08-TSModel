# B08 设备时序基础模型进展说明

更新日期：2026-06-08

## 当前阶段判断

项目已经完成到 **C2.2 升级版开源模型真实执行与审计实现入口**：当前具备默认离线安全配置、CLI `experiment c-stage-c22`、版本化核心模型目标矩阵、frontier watchlist audit、adapter contract 复用、task matrix、audit、task attempt 和结构化失败报告。

下一步主线应执行和复核 **C2.2 open model executable evaluation upgrade**：在 FU13 真实 processed parquet 优先、可控 cache、显式 opt-in 联网/下载边界下，把 C2.1 从“六模型结构化尝试”推进为“升级版开源模型真实执行与 frontier watchlist 审计”的可决策报告。

C2.2 的设计前校准已经补充了 2025-2026 最新模型调研：Chronos-2、TimesFM 2.5、Moirai 2.0、Sundial、Time-MoE、Timer-S1 / Timer-XL、Kairos、Toto、IBM FlowState / TSPulse、TabPFN-TS 等模型和路线需要纳入版本更新或 watchlist 审计。结论是：C2.1/C2.2 的评测闭环仍然有意义，但不能把 2024 年模型清单冻结为当前前沿。

## 一句话说明

这个项目正在为设备预测性维护方向建设一个“底层时序模型研发与评测工作台”。它先验证设备传感器数据能否被整理、预测、补全、表征和比较，再判断是否能直接使用开源时序基础模型，是否需要轻量适配，或者是否有证据进入自研模型设计。

它不是完整生产告警系统，也不是已经训练好的设备大模型。当前阶段的价值是：把真实 FU13 数据、模型窗口、baseline、开源模型执行尝试和统一报告口径跑通，并把失败原因记录成可决策证据。

## 近期阶段台账

| 日期 | 记录 |
| --- | --- |
| 2026-06-08 | C2.2 升级版开源模型真实执行与审计进入实现入口：新增默认离线安全配置 `configs/c_stage_c22_open_model_executable_upgrade.yaml`、CLI `experiment c-stage-c22`、版本化核心模型目标矩阵和 frontier watchlist audit；默认不联网、不下载权重，真实执行只通过显式 opt-in 配置进入。 |
| 2026-06-07 | README / details 入口文档重新整理：`README.md` 收束为任何读者的项目入口、核心运行命令和边界说明；`details.md` 收束为阶段进展、更新日志和下一步台账。 |
| 2026-06-07 | 完成 2025-2026 开源时序基础模型补充调研：确认 C2.2 需要将 Chronos 目标升级为 Chronos-2 优先，将 TimesFM 目标升级为 TimesFM 2.5，将 Moirai 目标升级到 Moirai 2.0 / Uni2TS 当前接口，并新增 frontier watchlist 审计层。 |
| 2026-06-07 | C2.1 实现与设计均已通过远端 PR 合并，本地分支和远端临时分支已清理，主分支回到干净状态。 |
| 2026-06-06 | C2.1 开源模型真实执行评测进入执行入口：核心配置为 `configs/c_stage_c21_executable_open_model_evaluation.yaml`，命令为 `uv run b08-model-core experiment c-stage-c21 --config configs/c_stage_c21_executable_open_model_evaluation.yaml --output reports/c_stage_c21_executable_open_model_evaluation.md`；该阶段在默认离线安全边界下覆盖 TTM、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、MOMENT、UniTS 的 executable adapter 尝试、统一 task matrix、结构化失败和 C2 -> C3 / C2 -> B 决策报告。 |
| 2026-06-05 | C2 开源模型系统评测进入执行入口：核心配置为 `configs/c_stage_c2_open_model_evaluation.yaml`，命令为 `uv run b08-model-core experiment c-stage-c2 --config configs/c_stage_c2_open_model_evaluation.yaml --output reports/c_stage_c2_open_model_evaluation.md`；该阶段固定覆盖 TTM、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS，成功标准是 audit + model-task attempt + 结构化失败记录，不要求全部模型成功运行。 |
| 2026-06-05 | C1 证据执行框架进入实施：把 FU13 pipeline、C0 契约、baseline/TTM、E1-E3 任务口径和统一报告收束为可执行评测准备，而不是继续扩写文档或直接进入 B 阶段自研训练。 |
| 2026-06-04 | C 阶段最小证据实验规划进入执行入口：核心契约为 `configs/c_stage_minimum_evidence.yaml`，阅读入口为 `docs/research/c-stage-minimum-evidence-register.html`，报告模板为 `reports/c_stage_minimum_evidence_template.md`；该阶段只建立 `E1-E5` 证据包、`P1-P5` 技术效果样例和 `CT4_decision_gate`，不直接进入 B 阶段自研基础模型训练。 |
| 2026-06-04 | A 阶段学术主线 spec 和执行资产已收束：短期第一目标聚焦论文、专利、学术综述和模型路线等知识成果；第二目标承接统一数据语料、开源模型适配、训练评测 workflow 等工程化产品成果。 |

## 已经具备的能力

### 1. FU13 canonical data pipeline

项目可以把 `data/real/` 中的 FU13 现场导出多 CSV 装配为 canonical observations，并完成数据诊断、cycle 重构和真实窗口评测准备。

当前事实基础：

- 装配得到 4,126,789 行标准观测。
- 覆盖 8 个传感器和 8 个工艺阶段。
- 重构 428 个 cycle，其中 247 个完整 cycle。
- 识别出 `good`、`unassigned_cycle`、`invalid` 三类质量标记。
- 当前 cycle 重构会把等待态归入相邻重构 cycle；是否从训练和评测窗口中剔除，放到后续数据治理和评测策略中处理。

### 2. 模型输入格式与窗口构建

项目已经定义 canonical observation schema，并能把标准观测表切成模型窗口。统一观测表包含时间、设备、批次、工艺阶段、传感器、数值、单位、物理域、质量标记、弱退化标签和弱故障代理标签。

这一步保证后续无论使用 baseline、开源模型、轻量适配模型还是自研模型，都有同一数据入口和可比较评测口径。

### 3. baseline / TTM 真实 forecasting 验证

项目已经在 FU13 真实窗口上完成 baseline 与 TTM 的同口径 forecasting 验证。TTM 作为 optional dependency 使用，本机 cache 和权重路径显式配置，默认 workflow 不下载权重。

当前已验证的标准口径是：

- `window-mode=cross-stage`
- `context-length=90`
- `prediction-length=16`
- `max-windows=40`

baseline 不是最终模型，而是最低工程对照；TTM 是当前已跑通的开源基础时序模型 anchor。

### 4. `leak_current_monitoring` 场景评测样例

项目已经完成 `leak_current_monitoring` 第一版 scenario-filtered evaluation。它按漏液电流监测场景过滤相关窗口，在同一场景口径下比较 baseline 与 TTM forecasting residual，并把模型输出汇总为候选异常信号样例。

这个样例只证明模型输出可以进入业务语境复核，不代表生产告警、故障概率、RUL 精确估计或自动维修建议已经具备。

### 5. C1 最小证据执行框架

C1 已把前期 pipeline、C0 契约、baseline/TTM 和任务口径收束为可执行证据框架，默认覆盖：

- `E1_forecasting_residual`
- `E2_representation`
- `E3_imputation`

C1 的定位是评测体系和流程准备，不是开源模型最终能力结论。

### 6. C2 / C2.1 开源模型评测入口

C2 已建立开源模型系统评测入口，C2.1 已进一步建立真实 executable adapter 尝试入口。

当前核心模型矩阵：

| 模型 | 当前任务定位 |
| --- | --- |
| TTM / TinyTimeMixer | forecasting anchor |
| Chronos / Chronos-Bolt | forecasting |
| TimesFM | forecasting |
| Moirai / Uni2TS | probabilistic forecasting |
| MOMENT | representation + imputation |
| UniTS | representation + imputation + multi-task 接口核验 |

C2.1 默认离线安全边界为 `allow_network: false`、`allow_download: false`。联网、下载、权重路径和 cache 只允许通过显式本机 opt-in 配置或 override 启用，并必须记录。

失败不会被写成“阶段失败”，而是进入结构化失败分类，例如：

- `missing_dependency`
- `missing_or_blocked_weights`
- `interface_review`
- unsupported window/task
- `runtime_failed`
- `timeout`

### 7. 知识成果和研究资产

项目已经把论文、专利、benchmark、模型资产和预测性维护数据矩阵纳入 A 阶段研究资产。当前研究资产入口是 `docs/research/index.md`，其中包含学术主线综述、开源模型论文矩阵、预测性维护数据矩阵、任务指标矩阵、训练路线和产品化承接路线。

这些资产的作用是让 C 阶段实验服务明确研究问题，而不是孤立地比较模型名字。

### 8. Python / uv workflow 可复现

项目使用 `uv` 管理 Python 环境：

```bash
uv sync --extra dev
uv run python -m pytest -q
```

开源基础模型依赖按 optional extra 管理，避免默认开发环境被大模型依赖、模型权重和网络下载破坏。

## 目前还没有具备的能力

### 1. 还没有完成 C2.2 报告后的能力结论

C2.2 已经建立实现入口和结构化审计边界，但还没有把 C2.2 报告结论沉淀为跨数据验证或自研 Go / No-Go 判断。下一步需要执行和复核 C2.2 报告，确认 Chronos-2、TimesFM 2.5、Moirai 2.0 等最新版本的真实尝试结果，并用 Time-MoE、Sundial、Timer-S1 / Timer-XL、Kairos、Toto、IBM FlowState / TSPulse、TabPFN-TS 等 frontier watchlist 审计支撑后续候选提升。

### 2. 还没有完成开源生态公开数据集整理

公开数据集整理更适合承接 C2.2 之后的 C3，而不是抢在 C2.2 前面。它需要基于 C2.2 的模型能力结果，判断哪些模型、任务和指标值得跨数据集验证。

### 3. 还没有设计自研设备时序基础模型

B 阶段仍是条件性路线。项目目前还没有决定自研训练，也没有完成自研模型输入格式、预训练目标、训练/验证切分、数据规模需求、算力预算、最小原型或 Go / No-Go 条件。

只有当 C2/C3 证据显示开源路线无法覆盖关键缺口时，才应进入 B 阶段自研模型设计。

### 4. 还没有形成生产级预测性维护系统

项目目前不会直接生成工单、维护建议、日报或正式告警。当前真实数据可以产生数据质量诊断、窗口预测指标和候选异常信号，但还没有接入维修记录、故障事件、停机原因、RUL 标签或现场维护闭环。

## 下一阶段计划

### C2.2. 升级版开源模型真实执行与审计（已有实现入口）

当前入口：

```bash
uv run b08-model-core experiment c-stage-c22 \
  --config configs/c_stage_c22_open_model_executable_upgrade.yaml \
  --output reports/c_stage_c22_open_model_executable_upgrade.md
```

目标：在 C2.1 已有统一入口、adapter contract、task matrix 和结构化失败报告基础上，让核心开源模型尽可能真实运行；不能运行的模型，也要把原因推进到具体依赖、权重、接口、窗口形状、任务头、许可证或资源限制。

当前执行边界：

- 数据优先使用 `data/processed/fu13_real_observations.parquet`。
- 保持 `uv sync --extra dev` 默认 workflow 不变。
- 允许新增 optional dependency groups，例如 `foundation-chronos`、`foundation-timesfm`。
- 联网和首次权重下载仅在 C2.2 显式 opt-in 配置下启用，并记录 cache manifest。
- 不接公开数据集，不做大规模训练，不做生产告警。

推荐核心矩阵：

| 层级 | 模型/路线 | C2.2 处理方式 |
| --- | --- | --- |
| Anchor | TTM | 已跑通 control，继续保持同口径复核 |
| Priority run | Chronos-2 / Chronos-Bolt fallback | forecasting 真实执行优先 |
| Priority run | TimesFM 2.5 | forecasting 真实执行优先 |
| Core run/review | Moirai 2.0 / Uni2TS | probabilistic forecasting，优先真实执行，失败结构化记录 |
| Core interface | MOMENT | representation / imputation |
| Core interface | UniTS | representation / imputation / multi-task 接口核验 |
| Frontier watchlist | Time-MoE、Sundial、Timer-S1 / Timer-XL、Kairos、Toto、IBM FlowState / TSPulse、TabPFN-TS | 默认 audit-only；满足依赖、权重、接口、资源和 license 条件后再提升为实跑候选 |

C2.2 成功标准不应是“所有模型都跑通”，而是：

- TTM 作为 anchor 保持可复核。
- Chronos-2 / Chronos-Bolt fallback 和 TimesFM 2.5 至少优先进入真实执行尝试。
- 所有核心模型都有明确 task attempt 或结构化失败原因。
- watchlist 模型形成可决策审计表。
- 报告能支持 C2 -> C3 和 C2 -> B 的下一步判断。

### C3. 公开数据集与跨数据验证

C3 应承接 C2.2 的模型结果。只有知道哪些模型和任务值得跨数据验证后，再整理公开数据集、license、schema mapping、任务标签和 split policy。

### B. 条件性自研模型准备

B 阶段只有在 C2/C3 证明开源模型存在关键缺口后才进入。它应先形成可审查训练方案，而不是直接大规模训练。

## 风险与边界

### 数据风险

FU13 当前只有一台真实设备样例，且存在 `unassigned_cycle` 和 `invalid` 行。后续需要判断这些信号分别来自工艺等待、采样问题、维护行为还是设备真实异常。

### 开源模型适配风险

开源时序基础模型更新很快，且 API、依赖、模型权重、许可证和输入形状差异明显。C2.2 必须记录失败原因，不能把“没跑通”简单解释为“模型不好”。

### 评测风险

时间序列基础模型公开 benchmark 可能存在训练/测试泄漏、领域重叠和任务口径不一致问题。因此 FU13 本地真实数据闭环仍然重要，但也不能因为单设备结果就夸大模型能力。

### 自研模型风险

自研基础模型需要大量数据、算力和长期维护。当前不建议直接进入自研，除非开源路线被验证不足，并且自研目标、指标、数据来源和 Go / No-Go 条件都已经明确。

## 阶段汇总记录

| 阶段 | 阶段判断 |
| --- | --- |
| 模型核心沙盒成型（2026-05-31） | 建立模拟数据、canonical schema、窗口构建、baseline、benchmark、真实数据 schema map、validation CLI 和 forecasting 实验脚手架，形成设备时序基础模型研发的最小沙盒。 |
| 基础模型推理与可复现 workflow（2026-06-01） | 将本地研发流程收束到 `uv`、optional TTM 依赖、本机权重 cache、Markdown/HTML 报告和 baseline/TTM 同口径实验；TTM 在 FU13 模拟窗口上以 `context_length=90`、`prediction_length=16` 跑通并可与 baseline 比较。 |
| FU13 真实数据闭环（2026-06-02） | 完成 FU13 真实多 CSV 装配、连续炉 cycle 重构、数据质量诊断和真实窗口 forecasting：形成 4,126,789 行 canonical observations，覆盖 8 个传感器、8 个工艺阶段、428 个 cycle，baseline 与 TTM 均在真实窗口上跑通，TTM 状态为 `available_and_ran`。 |
| 场景评测桥梁（2026-06-03） | 完成 `leak_current_monitoring` 第一版 scenario-filtered evaluation，把 baseline/TTM forecasting residual 汇总为候选异常信号样例；该结果只证明模型输出可进入业务语境复核，不代表生产告警、故障概率、RUL 精确估计或自动维修建议已经具备。 |
| A 阶段主线收束（2026-06-04） | 建立论文、专利、学术综述、开源模型论文矩阵、预测性维护数据矩阵和模型训练路线等知识成果骨架，并将工程化产品承接线限定为统一数据语料、开源模型适配、训练评测 workflow 和可复现研发工作台。 |
| C 阶段最小证据框架（2026-06-04 至 2026-06-05） | 固定 C 阶段最小证据契约，完成 C1 证据执行框架入口，明确 E1 forecasting residual、E2 representation、E3 imputation 的统一报告口径。 |
| C2 开源模型系统评测（2026-06-05） | 建立 TTM、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS 六模型系统评测入口，完成 audit、model-task attempt 和结构化失败报告。 |
| C2.1 开源模型真实执行入口（2026-06-06 至 2026-06-07） | 建立 executable adapter contract、六模型 task matrix、真实 adapter 优先和失败结构化记录兜底；保持默认离线安全边界，联网下载仅允许显式 opt-in。 |
| C2.2 升级版开源模型真实执行与审计入口（2026-06-08） | 建立默认离线安全配置、CLI `experiment c-stage-c22`、版本化核心模型目标矩阵和 frontier watchlist audit；默认不联网、不下载权重，真实执行只通过显式 opt-in 配置进入。 |

## 当前结论

项目已经从“单模型真实数据跑通”推进到“升级版开源模型真实执行与审计入口”。下一步不应直接进入 B 阶段自研训练，也不应先做大规模公开数据集整理；更合适的是执行和复核 C2.2，在真实 FU13 数据、统一任务口径和结构化失败 taxonomy 下产出一份能真正支撑 C3 或 B 阶段判断的报告。
