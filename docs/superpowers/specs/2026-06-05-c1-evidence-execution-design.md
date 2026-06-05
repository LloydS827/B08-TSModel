# C1 证据执行框架与 E1-E3 首批实验闭环设计

## 元信息

- 日期：2026-06-05
- 阶段：C1 证据执行与首批实验闭环
- 状态：供规格评审与用户审阅
- 上游规格：`docs/superpowers/specs/2026-06-04-c-stage-minimum-evidence-design.md`
- 上游契约：`configs/c_stage_minimum_evidence.yaml`
- HTML 阅读版：`docs/superpowers/specs/2026-06-05-c1-evidence-execution-design.html`

## 背景

B08 已经完成 FU13 真实数据 pipeline、baseline / TTM 同口径 forecasting、`leak_current_monitoring` 场景 residual 样例、A 阶段研究资产和 C0 最小证据契约。C0 已经定义 `E1-E5`、`CT4_decision_gate`、`P1-P5` 和报告模板，但当前仍主要停留在契约层。

C1 的职责是把前期工作收束为第一版可执行证据体系。它不应只保守地完成单点 E1，也不应无限扩展为通用实验平台。C1 应同时推进三件事：E1 真实实验闭环、E1-E5 可复用的最小证据框架、E2/E3 模型扩展入口。完成 C1 后，项目应具备进入系统开源模型评测和 B 阶段自研判断的工程证据基础。

## 目标

1. 将 `E1_forecasting_residual` 从 C0 契约推进到可运行、可报告、可审计的真实实验闭环。
2. 建立 C 阶段最小 evidence framework，统一配置读取、证据登记、执行结果、模型状态、报告字段和 C -> B gate 字段。
3. 将 `E2_representation` 和 `E3_imputation` 纳入同一执行框架，形成可复现 baseline、任务口径、报告输出和候选开源模型状态记录。
4. 为下一阶段系统评测 TTM、MOMENT、Chronos、TimesFM、Moirai / Uni2TS、UniTS 等开源模型预留清晰接口，但不要求 C1 跑完所有候选模型。
5. 保持文档系统克制：本规格只新增 Markdown 与同名 HTML 阅读版，不新增研究入口、不改导航、不拆分多份设计文档。

## 非目标

1. 不进入 B 阶段自研模型训练，不实现自研 backbone、预训练目标或训练循环。
2. 不把 C1 做成泛化实验平台、插件市场、完整模型管理系统或生产级预测性维护系统。
3. 不接入公开预测性维护数据集。`E4_open_data_pm` 保持 C2 候选方向，避免 C1 同时承担许可证、下载、schema mapping 和标签语义核对。
4. 不把 residual、probe、reconstruction error 或弱标签结果解释为生产告警、FU13 RUL、自动维修建议或专利授权结论。
5. 不要求测试依赖真实 FU13 私有数据、外部网络、Hugging Face 权重或本机模型 cache。
6. 不进行与 C1 无关的源码重排、文档迁移或历史资料清理。

## 范围决策

C1 采用并行综合推进方式，但验收重点分层。

| 层级 | 范围 | 验收强度 |
| --- | --- | --- |
| E1 真实闭环 | FU13 forecasting residual，baseline 与 TTM 状态，残差候选样例，失败案例 | 必须有真实运行入口；baseline 路径必须可运行；TTM 可运行或输出结构化失败 |
| 统一证据框架 | C1 execution config、registry、runner、result schema、report renderer | 必须实现，且只抽象 C 阶段复用字段 |
| E2 representation | simple statistical embedding baseline，MOMENT / UniTS adapter 状态，probe 输入排除说明 | 必须有可执行入口、baseline 和报告；候选模型可运行或结构化失败 |
| E3 imputation | deterministic mask strategy，simple reconstruction baseline，MOMENT / UniTS adapter 状态 | 必须有可执行入口、baseline 和报告；候选模型可运行或结构化失败 |
| E4/E5 | open-data 与专利效果承接 | C1 报告中保留状态和缺口，不执行公开数据接入或专利效果总结 |

## 架构

C1 采用“C0 契约 + C1 执行配置 -> registry -> runner -> result -> report”的结构。

```text
configs/c_stage_minimum_evidence.yaml
  + configs/c_stage_c1_execution.yaml
  -> C1 evidence registry
  -> C1 evidence runner
     -> E1 forecasting residual
     -> E2 representation probe
     -> E3 imputation / reconstruction
  -> C1 evidence results
  -> reports/c_stage_c1_evidence_report.md
```

### C1 执行配置

新增 `configs/c_stage_c1_execution.yaml`，只记录本轮执行参数，不复制 C0 的完整证据表。建议字段包括：

| 字段 | 含义 |
| --- | --- |
| `contract_path` | 指向 `configs/c_stage_minimum_evidence.yaml` |
| `stage` | 固定为 `C1_evidence_execution` |
| `dataset` | FU13 canonical observations 路径、配置路径和本机数据边界说明 |
| `enabled_evidence` | C1 默认启用 `E1_forecasting_residual`、`E2_representation`、`E3_imputation` |
| `window` | context length、prediction length、max windows、window mode |
| `models` | baseline、TTM、MOMENT、UniTS 的启用状态、cache 路径和下载策略 |
| `outputs` | C1 Markdown report、可选 artifact 目录 |
| `execution_policy` | no network by default、record failure、do not over-claim |

配置不得写入用户机器的绝对私有路径，不得默认允许下载外部权重。

### Evidence Registry

registry 负责读取 C0/C1 配置，并把要执行的证据项解析为稳定对象。它只回答“本轮要跑什么、边界是什么、禁止解释什么”，不直接跑模型。

最小职责：

- 校验 C1 启用的 evidence 均存在于 C0 contract。
- 继承 `experiment_id`、`task_id`、`primary_metric`、`comparison`、`invalid_claims`、`data_label_audit` 和 `decision_gate` 字段。
- 保留 E4/E5 的非执行状态，避免报告读者误以为 C1 已完成公开数据或专利效果结论。

### Evidence Runner

runner 按 evidence 类型调度现有能力，不做单一巨型通用引擎。

| evidence | 执行策略 |
| --- | --- |
| E1 | 复用 FU13 real-data forecasting / scenario residual 能力，至少跑 baseline，并记录 TTM 状态 |
| E2 | 从 FU13 窗口生成 simple statistical embedding baseline；候选模型走 `embed` adapter 或返回状态 |
| E3 | 对 FU13 多变量窗口生成 deterministic mask；跑 simple reconstruction baseline；候选模型走 imputation adapter 或返回状态 |

第一版允许 E2/E3 的候选模型因为依赖、权重、任务头或输入形状不可用而失败，但必须进入统一状态结构。

### Result Schema

三类 evidence 都落到同一种结果结构：

| 字段 | 要求 |
| --- | --- |
| `evidence_id` | C0 中的 evidence id |
| `experiment_id` | C0 中的 experiment id |
| `task_id` | C0 中的 task id |
| `status` | evidence 层状态 |
| `dataset_boundary` | 数据来源、内部边界、是否使用真实 FU13 |
| `split_policy` | 时间、run、batch 或评测窗口切分说明 |
| `model_results` | baseline 和候选模型的状态、指标、失败原因 |
| `primary_metrics` | C0 预先声明的主指标 |
| `failure_reasons` | evidence 层失败原因汇总；模型级失败仍保留在 `model_results` |
| `artifact_outputs` | 报告、样例、指标表、失败案例路径或内联摘要 |
| `invalid_claims` | 从 C0 继承，不允许省略 |
| `decision_gate_notes` | 对 CT4 gate 的支持、不足和下一步 |

### Report Renderer

新增统一 C1 Markdown 报告，例如 `reports/c_stage_c1_evidence_report.md`。报告只记录 C1 证据账本，不写论文结论。

报告必须包含：

- report metadata：run id、配置路径、契约路径、执行时间、环境边界。
- C1 summary：E1/E2/E3 状态、E4/E5 保留状态、是否满足进入下一阶段的基础条件。
- E1/E2/E3 分节：数据、split、baseline、candidate、指标、失败原因、artifact、invalid claims。
- adapter status table：模型是否可用、失败类型、失败原因、是否需要后续安装或接口核对。
- CT4 decision gate draft：只给阶段性证据，不给最终 B 阶段 Go 结论。
- forbidden interpretations：继承 C0 模板中的禁止过度解释。

## 数据流与任务路径

### E1 forecasting residual

```text
FU13 canonical observations
  -> C1 window policy
  -> baseline forecasting
  -> optional TTM forecasting
  -> residual metrics and top-k examples
  -> E1 report section
```

E1 是 C1 的锚点。baseline 路径必须可运行；TTM 在依赖和 cache 具备时应真实运行，否则输出结构化失败。残差候选样例必须能追溯到 sensor、timestamp、stage 和 quality policy，不能只输出汇总分数。

### E2 representation probe

```text
FU13 windows
  -> statistical embedding baseline
  -> optional MOMENT / UniTS embed adapter
  -> probe labels with input exclusion note
  -> probe or clustering metrics
  -> E2 report section
```

E2 重点是表征口径和输入排除。若 stage、quality_flag 或 failure_proxy 作为输入 metadata 被候选模型读取，报告必须说明对应 probe 不能解释为模型自主学到该语义。

### E3 imputation / reconstruction

```text
FU13 multivariate windows
  -> deterministic mask strategy
  -> simple reconstruction baseline
  -> optional MOMENT / UniTS imputation adapter
  -> reconstruction metrics by sensor and mask type
  -> E3 report section
```

mask 策略必须固定 seed、mask ratio、mask type 和评测窗口范围。mask 只在评测窗口内生成，不改变原始数据，不与真实缺失语义混淆。

## 模型状态语义

C1 统一使用以下模型状态：

| 状态 | 含义 |
| --- | --- |
| `available_and_ran` | 依赖、权重、输入形状和任务头可用，模型完成运行 |
| `missing_dependency` | Python 包或运行时依赖缺失 |
| `missing_or_blocked_weights` | 权重缺失、下载被禁用、下载失败或 cache 不可用 |
| `unsupported_task` | adapter 存在，但不支持当前 forecasting / embed / imputation 任务 |
| `unsupported_window_shape` | 当前窗口形状、变量数、horizon 或 mask 形式不被模型支持 |
| `runtime_failed` | 运行时异常，已捕获并写入报告 |
| `skipped_by_config` | C1 配置主动跳过 |
| `planned_not_executed` | C0 已规划但 C1 不执行，例如 E4/E5 |

不得把 `missing_dependency`、`missing_or_blocked_weights`、`unsupported_task`、`unsupported_window_shape`、`runtime_failed` 或 `planned_not_executed` 写成实验成功。

## 文件影响范围

实施 C1 时建议只触碰以下范围。若计划阶段发现必须扩大范围，应先在实施计划中说明原因。

| 文件或目录 | 操作 | 职责 |
| --- | --- | --- |
| `configs/c_stage_c1_execution.yaml` | 新增 | C1 执行参数，引用 C0 contract |
| `src/b08_model_core/experiments/` | 新增少量模块 | registry、runner、result schema、report renderer |
| `src/b08_model_core/adapters/` | 小幅扩展 | 统一 adapter 状态和 E2/E3 任务能力边界 |
| `src/b08_model_core/cli.py` | 小幅扩展 | 增加 C1 执行命令，例如 `experiment c-stage-c1` |
| `tests/` | 新增聚焦测试 | 配置、registry、状态、report、mask/probe 口径 |
| `reports/` | 新增模板或示例报告 | C1 本机报告路径和可提交摘要边界 |

不修改 `docs/index.html`，不迁移历史文档，不清理旧资料。

## CLI 设计

建议新增一个窄命令：

```bash
uv run b08-model-core experiment c-stage-c1 \
  --config configs/c_stage_c1_execution.yaml \
  --output reports/c_stage_c1_evidence_report.md
```

默认行为：

- 不联网、不自动下载外部模型权重。
- baseline 路径可运行时返回成功。
- 若启用的候选模型失败，命令仍写报告；是否返回非零由 C1 配置中的 `strict_model_success` 控制，默认 `false`。
- 若 E1 baseline 无法运行、C0 contract 无法读取、C1 配置无效或报告无法写出，应返回非零。

## 错误处理

1. 配置错误：C1 配置无法读取、启用不存在的 evidence、缺少输出路径时，命令失败并给出明确错误。
2. 数据错误：FU13 dataset 路径缺失或 schema 无法满足窗口构建时，E1/E2/E3 标记为 failed，命令返回非零。
3. 候选模型错误：依赖、权重、输入形状、任务头或 runtime 失败均进入 `model_results`，报告保留失败原因。
4. 指标错误：如果窗口不足、类别极端不均衡或 mask 策略不可解释，应给 evidence 标记失败或 needs-review，不输出伪指标。
5. 报告错误：report renderer 必须在部分模型失败时仍生成报告；只有报告无法生成时命令失败。

## 测试策略

单元测试不得依赖真实 FU13 私有数据、网络或模型权重。测试使用小型 fixture 或 synthetic observations 验证行为。

必须覆盖：

- C1 配置可以引用并继承 C0 contract 中的 E1/E2/E3。
- registry 拒绝不存在的 evidence，并保留 E4/E5 为 `planned_not_executed`。
- result schema 要求 `invalid_claims`、`failure_reasons`、`decision_gate_notes` 不可缺失。
- report renderer 在候选模型失败时仍输出模型状态、失败原因和 forbidden interpretations。
- E2 的 probe 输入排除说明被写入结果。
- E3 的 deterministic mask 在固定 seed 下可复现。
- CLI 在配置错误、数据错误、baseline 成功、候选模型失败四类场景下返回符合预期的 exit code。
- 默认 `uv run python -m pytest -q` 通过。

真实 FU13 + TTM 可作为本机 smoke verification，不作为自动测试前提。

## 验收标准

C1 完成时必须满足：

1. 存在一条 C1 CLI 命令，能从 C1 配置生成 Markdown 报告。
2. E1 baseline 路径真实运行，并输出 forecasting metrics、residual summary、top-k candidate examples 或明确失败原因。
3. TTM 状态被记录为 `available_and_ran` 或结构化失败状态，不留空白。
4. E2 有 statistical embedding baseline、probe 输入排除说明、候选 MOMENT / UniTS 状态和报告分节。
5. E3 有 deterministic mask、simple reconstruction baseline、候选 MOMENT / UniTS 状态和报告分节。
6. 报告继承 C0 invalid claims，并明确 C1 不构成生产告警、RUL、自动维修或专利授权结论。
7. E4/E5 在 C1 报告中显示为未执行承接项，不被误写成完成。
8. 文档新增保持克制：只新增本规格 Markdown 与同名 HTML 阅读版，不强制新增导航或多份说明文档。
9. 默认测试通过，且测试不依赖私有数据、外部网络或模型权重。

## C1 之后的衔接

C1 完成后，下一阶段建议进入 C2：系统开源模型评测。C2 再扩展 Chronos、TimesFM、Moirai / Uni2TS、MOMENT、UniTS 的真实适配，并决定是否接入 E4 公开数据 mapper。只有当 C1/C2 证据显示开源模型和工程 baseline 无法覆盖 representation、imputation、weak-label candidate signal 等关键缺口时，才进入 B 阶段自研最小原型设计。

C1 的最终价值不是证明某个模型已经可生产使用，而是让项目从“前期 pipeline 与契约已完成”过渡到“开源模型系统评测与自研判断有统一证据入口”。
