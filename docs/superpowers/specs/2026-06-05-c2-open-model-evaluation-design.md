# C2 开源模型系统评测框架与核心模型全覆盖测试设计

## 元信息

- 日期：2026-06-05
- 阶段：C2 开源模型系统评测
- 状态：供规格评审与用户审阅
- 上游规格：`docs/superpowers/specs/2026-06-05-c1-evidence-execution-design.md`
- 上游执行配置：`configs/c_stage_c1_execution.yaml`
- HTML 阅读版：`docs/superpowers/specs/2026-06-05-c2-open-model-evaluation-design.html`

## 背景

C1 已经把 FU13 真实数据、baseline/TTM forecasting、representation、imputation 和结构化失败记录收束为第一版证据执行框架。C1 的作用是完成前期 pipeline、任务口径、报告结构和最小证据账本。C2 的职责是在此基础上进入开源时序基础模型的系统评测。

C2 不应只挑 2-3 个最容易跑通的模型，也不应扩大成公开数据集整理、生产告警系统或自研模型训练。当前阶段的关键任务是让核心开源模型全部进入同一套评测和审计框架，形成“结果或结构化失败”的证据，为后续 C2 阶段计划、C3 公开数据整理和 B 阶段自研判断提供依据。

## 目标

1. 建立 C2 开源模型评测配置、运行入口、模型审计表、评测结果结构和 Markdown 报告。
2. 将六个核心模型全部纳入同一口径：TTM / TinyTimeMixer、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS。
3. 对 forecasting-first 模型执行 FU13 同窗口 forecasting 评测，或记录结构化失败。
4. 对 representation / imputation / multi-task 模型执行 FU13 表征或补全评测，或记录结构化失败。
5. 输出模型级 audit record，覆盖来源、许可证边界、依赖、权重/cache、任务接口、输入形状、离线可运行性和失败原因。
6. 形成 C2 -> C3、C2 -> B 的阶段性决策记录，但不直接给出自研训练 Go 结论。

## 非目标

1. 不把 C2 设计成公开数据集接入阶段。公开预测性维护数据来源、许可证、schema mapping、标签语义和 split policy 进入 C3。
2. 不进入 B 阶段自研模型训练，不实现自研 backbone、预训练目标或训练循环。
3. 不要求六个模型全部成功运行。C2 的成功标准是全部模型被审计并进入同一评测尝试或结构化失败记录。
4. 不将 TSPulse、FlowState 纳入 C2 核心必测集合。二者保留为扩展候选，待 C2 报告或 C3 资料核对后再决定是否纳入后续核心对比。
5. 不默认联网下载权重，不要求测试依赖外部网络、私有 FU13 数据或本机模型 cache。
6. 不把 forecasting residual、embedding probe、reconstruction error 或候选异常信号解释为生产告警、RUL、维修建议或专利授权结论。

## 范围决策

C2 采用“全覆盖模型登记 + 分任务评测 + 结构化失败”的方式推进。

| 层级 | 范围 | 验收强度 |
| --- | --- | --- |
| 模型审计 | 六个核心模型的来源、许可证、依赖、权重、接口、任务覆盖、输入限制 | 每个核心模型必须有 audit record |
| forecasting 评测 | TTM、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS，UniTS 若接口支持则记录 | 必须尝试运行或记录结构化失败 |
| representation 评测 | MOMENT、UniTS，其他模型若接口支持则可记录为补充 | 必须尝试运行或记录结构化失败 |
| imputation / reconstruction 评测 | MOMENT、UniTS，其他模型若接口支持则可记录为补充 | 必须尝试运行或记录结构化失败 |
| C2 报告 | 模型矩阵、任务结果、失败原因、invalid claims、C3/B 承接记录 | 必须生成 Markdown 报告 |
| C3 承接 | 公开数据集整理、许可证与 schema mapping | C2 只记录 handoff，不执行 |

## 核心模型集合

| 模型 | C2 主任务 | C2 记录重点 |
| --- | --- | --- |
| TTM / TinyTimeMixer | forecasting | 继承 C1 锚点，记录与 baseline 同窗口指标、TTM adapter 状态、cache/权重边界 |
| MOMENT | representation、imputation，可选 forecasting | 多任务接口、embedding/reconstruction 能力、输入排除说明、任务头可用性 |
| Chronos / Chronos-Bolt | forecasting | token 化或 Bolt 接口、概率预测输出、单变量/多变量适配方式、horizon 约束 |
| TimesFM | forecasting | decoder-only forecasting 接口、context/horizon/frequency 约束、外生变量处理边界 |
| Moirai / Uni2TS | probabilistic forecasting | 预测分布输出、变量组织方式、跨频率/多变量接口、依赖与权重状态 |
| UniTS | representation、imputation、multi-task，可选 forecasting | 任务 token、多任务接口、输入 schema 重构要求、工业 metadata 边界 |

TSPulse 和 FlowState 不属于 C2 核心必测集合。C2 报告可以在“扩展候选观察”中保留二者状态，但不得因此扩大 C2 的验收范围。

## 架构

C2 复用 C1 的证据思路，但把中心从 evidence item 扩展为 model-task attempt。

```text
configs/c_stage_c1_execution.yaml
  + configs/c_stage_c2_open_model_evaluation.yaml
  -> C2 model registry
  -> C2 audit runner
  -> C2 task runner
     -> forecasting attempts
     -> representation attempts
     -> imputation attempts
  -> C2 evaluation results
  -> reports/c_stage_c2_open_model_evaluation.md
```

### C2 执行配置

新增 `configs/c_stage_c2_open_model_evaluation.yaml`，只记录 C2 本轮执行参数，不复制 C1/C0 的完整证据表。

建议字段：

| 字段 | 含义 |
| --- | --- |
| `stage` | 固定为 `C2_open_model_evaluation` |
| `upstream_c1_config` | 指向 `configs/c_stage_c1_execution.yaml` |
| `dataset` | FU13 canonical observations、schema config 和本机数据边界 |
| `window` | context length、prediction length、max windows、mask policy、seed |
| `core_models` | 固定列出 TTM、MOMENT、Chronos、TimesFM、Moirai / Uni2TS、UniTS |
| `task_policy` | forecasting、representation、imputation 的模型任务映射 |
| `model_cache_policy` | no network by default、cache path 可配置、失败可记录 |
| `execution_policy` | candidate failure does not fail whole command、strict mode 可选 |
| `outputs` | C2 Markdown report 和可选 artifact 目录 |

配置不得写入用户机器的绝对私有路径，不得默认允许下载外部权重。

### Model Registry

registry 负责解析核心模型集合和任务映射。它不运行模型，只生成稳定的 model-task attempt 列表。

最小职责：

- 校验六个核心模型全部出现在 `core_models`。
- 校验每个模型至少有一个主任务映射。
- 继承 C1 的 FU13 数据边界、窗口口径和 invalid claims。
- 允许扩展候选被记录为非核心观察，但不得影响 C2 核心验收。

### Audit Runner

audit runner 先于任务评测执行。每个核心模型必须生成 audit record。

Audit record 至少包含：

| 字段 | 要求 |
| --- | --- |
| `model_id` | 稳定模型 id，例如 `ttm`、`moment`、`chronos`、`timesfm`、`moirai_uni2ts`、`units` |
| `display_name` | 报告展示名称 |
| `source_kind` | paper、official_repo、model_card、local_adapter 等 |
| `source_ref` | 论文、官方仓库、本地 adapter 或资料登记项的引用 |
| `model_card_ref` | 模型卡或权重说明引用；没有时写明 `not_available` 或 `needs_review` |
| `license_note` | 许可证和使用边界记录；不确定时写 `needs_review` |
| `dependency_status` | 依赖是否存在或缺失 |
| `weights_status` | 权重/cache 是否存在、下载是否被禁用或受阻 |
| `supported_tasks` | adapter 或官方接口可支持的任务 |
| `input_constraints` | context、horizon、变量数、频率、mask 或 token 化约束 |
| `offline_feasibility` | 在 no-network 默认策略下是否可运行 |
| `audit_status` | 见状态语义 |

### Task Runner

task runner 按 model-task attempt 执行。第一版不需要把所有模型包成复杂插件系统，只需为每个核心模型提供薄 adapter 或结构化 status checker。

| 任务 | C2 最小执行口径 |
| --- | --- |
| forecasting | 使用 C1/FU13 同窗口策略，输出 MAE、RMSE、MAPE 或 C1 已采用的主指标，并记录 residual summary |
| representation | 使用 FU13 窗口生成 embedding 或 statistical baseline，对 probe 输入排除和标签边界做记录 |
| imputation | 使用 deterministic mask policy，输出 reconstruction metrics，并明确 mask 不等同真实缺失 |

若模型因依赖、权重、任务头、输入形状或运行时错误无法完成，task runner 必须捕获原因并写入 attempt record。

即使 audit record 进入 `needs_license_review`、`needs_dependency_review`、`needs_interface_review` 或 `audit_failed`，registry 仍应为该模型生成 model-task attempt。task runner 可将 attempt 写成 `license_or_interface_needs_review`、`missing_dependency` 或其他结构化失败状态；只有整体配置、数据窗口或报告输出不可用时，命令才应在生成报告前终止。

## 状态语义

C2 区分 audit 状态和 model-task attempt 状态。

### Audit Status

| 状态 | 含义 |
| --- | --- |
| `audit_passed` | 来源、许可证边界、依赖、权重策略和任务接口已记录，未发现阻断 |
| `needs_license_review` | 许可证或使用边界需要人工核对 |
| `needs_dependency_review` | 依赖、安装方式或运行环境需要核对 |
| `needs_interface_review` | 官方接口、adapter contract 或输入输出形状需要核对 |
| `audit_failed` | 审计过程本身失败，原因必须记录 |

### Model-Task Status

| 状态 | 含义 |
| --- | --- |
| `available_and_ran` | 依赖、权重、输入形状和任务头可用，模型完成运行 |
| `missing_dependency` | Python 包或运行时依赖缺失 |
| `missing_or_blocked_weights` | 权重缺失、下载被禁用、下载失败或 cache 不可用 |
| `unsupported_task` | adapter 或官方接口不支持当前任务 |
| `unsupported_window_shape` | 当前窗口、变量数、horizon、mask 或 token 形式不被模型支持 |
| `runtime_failed` | 运行时异常，已捕获并写入报告 |
| `license_or_interface_needs_review` | 许可证或接口边界不足以安全执行，需要人工核对 |
| `skipped_by_config` | C2 配置主动跳过，默认核心模型不应出现该状态 |

不得把 `missing_dependency`、`missing_or_blocked_weights`、`unsupported_task`、`unsupported_window_shape`、`runtime_failed`、`license_or_interface_needs_review` 或 `skipped_by_config` 写成模型成功。

## Result Schema

每个 model-task attempt 落到同一种结果结构：

| 字段 | 要求 |
| --- | --- |
| `model_id` | 核心模型 id |
| `task_id` | `forecasting`、`representation` 或 `imputation` |
| `status` | model-task status |
| `dataset_boundary` | FU13 数据来源、内部边界、是否使用真实数据 |
| `window_policy` | context、horizon、mask、seed、窗口数量 |
| `metrics` | 成功运行时的指标；失败时为空并给出原因 |
| `baseline_reference` | 与 C1 baseline 或 statistical/reconstruction baseline 的对照关系 |
| `failure_reason` | 失败状态的简短原因 |
| `error_detail` | 可审计但不过度展开的错误摘要 |
| `artifact_outputs` | 报告、指标表、样例或本机 artifact 路径 |
| `invalid_claims` | 禁止解释，必须继承 C1/C0 |
| `decision_notes` | 对 C3/B 的阶段性提示 |

## 报告设计

建议新增本机报告：

```text
reports/c_stage_c2_open_model_evaluation.md
```

报告必须包含：

1. report metadata：run id、配置路径、C1 上游配置、执行时间、环境边界。
2. C2 scope：六个核心模型、核心任务、扩展候选不纳入验收的说明。
3. model audit table：每个核心模型的 audit record。
4. model-task result matrix：每个核心模型在主任务上的 `available_and_ran` 或失败状态。
5. forecasting section：TTM、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS 的同窗口结果或失败原因。
6. representation / imputation section：MOMENT、UniTS 的结果或失败原因。
7. baseline comparison：C1 baseline 和 C2 开源模型结果之间的可比字段。
8. failure taxonomy：依赖、权重、接口、窗口形状、任务不匹配、运行时失败的汇总。
9. C2 -> C3 handoff：需要公开数据集进一步验证的任务、模型和 schema 需求。
10. C2 -> B decision notes：开源模型已覆盖、未覆盖和仍需观察的能力缺口。
11. invalid claims：不得解释为生产告警、RUL、维修建议、模型选型终局或自研训练 Go 结论。

## CLI 设计

建议新增一个窄命令：

```bash
uv run b08-model-core experiment c-stage-c2 \
  --config configs/c_stage_c2_open_model_evaluation.yaml \
  --output reports/c_stage_c2_open_model_evaluation.md
```

默认行为：

- 不联网、不自动下载外部模型权重。
- 六个核心模型都必须进入 audit 和 task attempt 列表。
- 单个候选模型失败不导致整个命令失败；失败写入报告。
- 若 C2 配置无效、核心模型缺失、FU13 数据无法构建评测窗口、报告无法写出，应返回非零。
- 可通过配置开启 `strict_model_success`，用于后续更严格的本机集成验证；默认 `false`。

## 错误处理

1. 配置错误：缺少核心模型、任务映射为空、输出路径缺失或字段非法时，命令失败。
2. 数据错误：若 FU13 dataset 缺失、schema 不满足窗口构建或窗口数量不足导致所有核心任务都无法形成评测窗口，命令返回非零；若只有单个模型或单个任务无法适配已构建窗口，则写入该 model-task 的结构化失败记录。
3. 审计错误：许可证、依赖、权重或接口无法确认时，audit record 必须进入 needs-review 或 failed 状态。
4. 候选模型错误：依赖、权重、输入形状、任务头或 runtime 失败均进入 model-task attempt，不中断其他模型。
5. 报告错误：部分模型失败时仍必须生成报告；只有 report renderer 无法写出时命令失败。

## 测试策略

单元测试不得依赖真实 FU13 私有数据、网络或模型权重。测试使用小型 fixture、fake adapter 和 synthetic observations 验证 C2 行为。

必须覆盖：

- C2 配置必须列出六个核心模型，缺一即失败。
- registry 为每个核心模型生成至少一个主任务 attempt。
- audit runner 能在依赖或权重缺失时生成 needs-review / failure record，而不是抛出未处理异常。
- task runner 能把 fake adapter 的成功、依赖缺失、权重缺失、unsupported task、unsupported window shape 和 runtime failed 写入统一状态。
- report renderer 必须包含六个核心模型、任务矩阵、失败分类、invalid claims、C3 handoff 和 B decision notes。
- CLI 在核心模型失败但报告成功写出时默认返回 0；在配置、数据或报告错误时返回非零。
- `uv run python -m pytest -q` 保持通过。

可选本机 smoke：

```bash
uv run b08-model-core experiment c-stage-c2 \
  --config configs/c_stage_c2_open_model_evaluation.yaml \
  --output reports/c_stage_c2_open_model_evaluation.md
```

若本机没有外部模型依赖或 cache，smoke 仍应生成报告，并把候选模型记录为结构化失败。

## 文件影响范围

实施 C2 时建议只触碰以下范围。若计划阶段发现必须扩大范围，应先在实施计划中说明原因。

| 文件或目录 | 操作 | 职责 |
| --- | --- | --- |
| `configs/c_stage_c2_open_model_evaluation.yaml` | 新增 | C2 执行参数和六个核心模型配置 |
| `src/b08_model_core/experiments/` | 新增少量模块 | C2 registry、audit runner、task runner、result schema、report renderer |
| `src/b08_model_core/adapters/` | 小幅扩展 | 六个核心模型的 adapter/status checker；已有 adapter 优先复用 |
| `src/b08_model_core/cli.py` | 小幅扩展 | 增加 `experiment c-stage-c2` 命令 |
| `tests/` | 新增聚焦测试 | 配置、registry、状态语义、report、CLI 行为 |
| `reports/` | 本机输出 | C2 报告路径，不要求提交真实私有数据结果 |

不修改 `docs/index.html`，不迁移历史文档，不清理旧资料。

## 验收标准

1. C2 配置存在，并固定列出 TTM / TinyTimeMixer、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS 六个核心模型。
2. C2 CLI 可以生成 Markdown 报告，且不要求六个模型全部成功运行。
3. 每个核心模型都有 audit record。
4. 每个核心模型至少有一个 model-task attempt，状态为成功或结构化失败。
5. forecasting-first 模型在 FU13 同窗口策略下被尝试，或记录明确失败原因。
6. MOMENT 和 UniTS 在 representation / imputation / multi-task 口径下被尝试，或记录明确失败原因。
7. 报告包含 model audit table、model-task result matrix、failure taxonomy、invalid claims、C2 -> C3 handoff 和 C2 -> B decision notes。
8. 测试不依赖真实 FU13 私有数据、外部网络或本机权重 cache。
9. 默认项目状态保持可安装、可测试、可运行；C2 未完成模型成功不破坏 C1 已完成路径。

## 下一步边界

C2 完成后，优先根据报告判断：

- 哪些开源模型已经能覆盖 FU13 forecasting、representation 或 imputation 的基础口径。
- 哪些失败属于工程依赖、权重/cache、接口形状或任务不匹配。
- 哪些缺口需要 C3 引入公开预测性维护数据集进一步验证。
- 是否存在足够稳定的开源模型缺口，值得进入 B 阶段最小自研模型方案。

C2 的最终价值不是证明某个开源模型已经可生产使用，而是让六个核心候选在同一评测账本中接受审计、尝试和失败归因。
