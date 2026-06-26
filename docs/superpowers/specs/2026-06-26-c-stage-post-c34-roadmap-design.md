# C Stage Post-C3.4 Roadmap Design

Date: 2026-06-26

## 项目理解

B08 当前已经完成从真实 FU13 数据闭环到 C3.4 open model expansion decision review 的主线推进。项目定位不是开源模型排行榜，也不是直接训练自研基础模型，而是公司时空智能在能源设备时序方向的核心样板：用 canonical observations、cycle / window、baseline、open model adapter/cache evidence、candidate signal 和系统事件候选接口，形成可复核证据链。

当前 C 阶段已经具备三类基础：

1. 真实设备链路：FU13 多 CSV 装配、canonical observations、cycle / window、数据诊断、baseline / TTM forecasting 和 `leak_current_monitoring` candidate signal。
2. 开源模型适配链路：C1-C2.2 的 evidence framework、模型矩阵、adapter attempt、failure taxonomy、frontier watchlist 和离线安全边界。
3. 公开数据补证链路：C3-C3.4 的 C-MAPSS source/license/schema/RUL baseline、FU13-like forecasting reference、TTM single-candidate local evidence gate 和 candidate expansion review。

因此，下一步不应只是机械追加 C3.5、C3.6、C3.7，也不应跳过 gate 进入 B 阶段训练。更稳妥的方向是把 C 阶段收束成“证据闭环 -> 单候选扩展 -> 多任务补证 -> C -> B 决策门”的路线，并把这条路线写入 README 作为后续工作的默认指引。

## 问题

C3.4 已经把是否扩展第二 forecasting open model 变成了可审查决策，但项目还缺少一个面向后续工作的总路线：

- 如果 C3.4 仍是默认 hold，团队需要知道下一步应先补 C3.3 TTM local evidence，而不是直接做 C3.5。
- 如果 C3.4 达到 `candidate_expansion_design_ready`，团队需要知道 C3.5 只能做 single second forecasting candidate design，而不是多模型竞赛。
- 即使 C3.5 完成，继续只扩 forecasting 模型也会让项目停留在 E1 forecasting residual，无法支撑 E2 representation、E3 imputation/reconstruction、E5 patent effect 和 C -> B 决策。
- README 当前有阶段入口和安全边界，但缺少一段清晰的后续路线，把短期 C3.4/C3.5、中期多任务证据、后期 C -> B gate 连接起来。

如果这轮直接新增 C3.5 executable adapter，会把工作变成模型依赖问题；如果只写一句“下一步做 C3.5”，又不足以指导项目后续发展。

## 目标

- 形成 C 阶段后 C3.4 的路线 spec，明确后续默认方向。
- 更新 README，把后续路线写成项目入口级指引。
- 更新 `details.md`，把当前阶段和下一步台账从单一 C3.5 入口升级为 C 阶段证据闭环路线。
- 保留 C3.4 gate：没有 ready TTM local evidence 时，不进入第二候选。
- 定义 C3.5 的范围：仅在 gate 通过后设计一个 second forecasting candidate，不执行多模型竞赛，不生成 leaderboard。
- 定义 C3.6 / C3.x 后续合理方向：从 forecasting-only 转向 representation、imputation/reconstruction、weak-label candidate signal review 和 patent effect evidence。
- 定义 C -> B 决策门：只有开源模型和工程 baseline 在 representation / imputation / weak-label 任务上存在明确缺口时，才进入 B minimal prototype。
- 保持 README 和 details 的文档分工：README 负责路线入口和稳定指引，details 负责当前状态、每日更新和下一步台账。

## 非目标

- 不实现新的 C3.5 CLI、adapter、配置或真实模型执行。
- 不新增 Chronos、TimesFM、Moirai 或其他模型依赖。
- 不运行本机 raw、model cache、权重下载或训练流程。
- 不改变 C3.4 已实现的决策逻辑。
- 不改变 C-MAPSS RUL baseline-only 边界。
- 不生成 leaderboard，不混合 RUL 与 forecasting 指标。
- 不宣称生产告警、故障概率、RUL 精确估计、自动维修建议或自研模型优越性。

## 关键假设

- 用户已经认可“论文/专利证据优先，工程样板承接，模型原型暂缓到 gate 后”的路线。
- C3.4 当前默认状态仍应视为 hold；仓库默认路径不能假设本机已存在 ready TTM evidence。
- C3.5 的合理前提是 C3.4 explicit review 达到 `candidate_expansion_design_ready`。
- C3.5 的合理形态是 design-first、single-candidate-only，优先选择最低新增风险的 forecasting model route；具体候选不在本轮定死为可执行实现。
- C 阶段后半段的价值不在继续扩大 forecasting 模型数量，而在补齐 E2/E3/E5，使项目能判断是否有必要进入 B minimal prototype。

## 方案比较

### 方案 A：只在 details 追加下一步计划

改动最小，但 README 仍缺少项目入口级路线。首次阅读者只能看到 C3.4 命令和当前台账，难以理解为什么 C3.5 不能无条件启动，也难以看到 C -> B 决策门。

### 方案 B：新增 README 后续路线并同步 details

这是推荐方案。README 新增“后续发展路线”章节，按短期、中期、后期说明：

1. 短期：C3.4 gate 与 C3.5 single second forecasting candidate design。
2. 中期：E2 representation、E3 imputation/reconstruction、weak-label candidate signal review 和 E5 patent effect。
3. 后期：C -> B Go / Stay / Knowledge-only / No-Go 决策。

`details.md` 同步当前阶段和下一步计划，保持台账性质。新增 tests 保护 README/details 中的核心路线词条，防止后续文档回退。

### 方案 C：直接实现 C3.5 second candidate adapter

短期看最像“继续推进”，但不符合当前 gate。C3.4 默认是 hold，没有显式 ready evidence 时直接实跑第二候选会绕过 C3.4 设计，并扩大依赖、cache、shape、资源和指标解释风险。

## 推荐设计

### README 路线章节

在 README 的“当前可复现资产”之后、“快速开始”之前新增“后续发展路线”章节。理由是这部分属于项目入口级信息，应该在读者进入命令细节前看到。

章节结构：

1. 总原则：C 阶段后续以论文/专利证据为主，工程样板承接为辅，B 阶段自研原型必须等 C -> B gate。
2. 短期：先完成 C3.4 evidence review；若 hold，则补 C3.3 TTM local evidence；若 ready，进入 C3.5 single second forecasting candidate design。
3. 中期：从 forecasting-only 转向多任务证据，补 E2 representation、E3 imputation/reconstruction、weak-label candidate review、E5 patent effect。
4. 后期：形成 C -> B 决策表，分为 `go_to_b_minimal_prototype`、`stay_in_c_adaptation`、`knowledge_only_consolidation` 和 `no_go_hold`。
5. 禁止路径：不在 gate 前扩多模型，不做 leaderboard，不混合 RUL/forecasting，不直接训练自研模型。

README 应保留简洁，不展开 spec 级细节。详细执行逻辑由 spec / plan / reports 承接。

### details 台账

`details.md` 更新：

- 更新日期为 2026-06-26。
- 当前阶段从单纯 C3.4 implemented 调整为 “C3.4 implemented; post-C3.4 C-stage roadmap documented”。
- 每日更新新增 2026-06-26 行，说明本轮完成后续路线写入 README/details，并保持 C3.4/C3.5 gate。
- 下一步计划改成 gate-based 路线，而不是只列 C3.5。

### C3.4 / C3.5 决策

C3.4 状态决定下一步：

| C3.4 decision | 下一步 |
| --- | --- |
| `hold_candidate_expansion_pending_ttm_local_evidence` | 先运行或复核 C3.3 explicit local TTM evidence |
| `blocked_candidate_expansion_due_to_ttm_evidence_gap` | 修 TTM dependency/cache/shape/runtime blocker |
| `candidate_expansion_design_ready` | 进入 C3.5 single second forecasting candidate design |

C3.5 只能设计一个 second forecasting candidate。默认候选顺序仍是低风险优先：Chronos-Bolt route、TimesFM route、Moirai / Uni2TS route。C3.5 不应在本轮文档中被写成“执行第二候选”或“多模型对比”。

### C 阶段后半段路线

C3.5 之后不应继续线性堆模型，而应转向 C 阶段证据闭环：

- C3.6 / E2：FU13 representation / probe contract，明确 stage、quality_flag、failure_proxy 的输入排除与泄漏边界。
- C3.7 / E3：FU13 imputation / reconstruction contract，明确 mask policy、变量级重建误差和 invalid claims。
- C3.8 / weak-label review：把 residual、reconstruction error、trend/spike candidate 与专家复核入口连接起来。
- C3.9 / E5：把 P1-P5 的最小技术效果样例整理成技术交底前证据材料。

这些编号是路线占位，不要求本轮创建 CLI 或代码。后续每一步仍应按独立 spec -> plan -> implementation 执行。

### C -> B 决策门

C 阶段后半段完成后，形成 C -> B decision review。默认判断口径：

| 决策 | 条件 |
| --- | --- |
| `go_to_b_minimal_prototype` | 开源模型和工程 baseline 在 representation / imputation / weak-label 任务上存在稳定缺口，且结构感知输入、阶段编码、多任务头或弱标签目标有明确实验必要性 |
| `stay_in_c_adaptation` | 开源模型可覆盖主要任务，但 adapter、数据映射、报告和复核流程仍需补齐 |
| `knowledge_only_consolidation` | 证据足以支撑框架论文、专利背景和路线判断，但不足以支撑方法创新或自研训练 |
| `no_go_hold` | 数据许可、标签语义、split policy、模型可运行性或复核条件不足，继续扩大实验会制造伪证据 |

任何进入 B 的判断都必须预先指定主任务、强基线、最低增益、多 seed 或置信区间口径，以及失败条件。

## 测试策略

- 新增或更新文档测试，确保 README 包含后续路线、C3.4 gate、C3.5 single-candidate-only、多任务证据和 C -> B decision gate。
- 新增或更新 details 测试，确保 details 保持 3 个主章节，不膨胀成重复 README 的长文档。
- 运行 `uv run python -m pytest tests/test_experiment_scaffold.py -q`。
- 运行全量 `uv run python -m pytest -q`。

## 验收标准

- README 写入后续发展路线，且明确短期、中期、后期三段。
- README 明确 C3.4 / C3.5 gate：C3.5 只能在 C3.4 ready 后进行 single second forecasting candidate design。
- README 明确后续不应只扩 forecasting 模型，而要补 E2/E3/weak-label/E5。
- README 明确 C -> B decision gate，且不承诺自研训练已开始。
- `details.md` 更新当前阶段、每日更新和下一步计划。
- 文档测试覆盖路线关键词并通过。
- 不改动默认实验行为，不新增模型依赖，不提交 raw、zip、parquet、cache 或 generated report。

## 下一阶段建议

本轮完成后，下一阶段应先执行 C3.4 evidence path：

1. 如果没有 reviewed C3.3 TTM local evidence，则先运行或复核 C3.3 explicit local TTM evidence，再用 C3.4 本机证据复核入口给出 decision。
2. 如果 C3.4 仍 blocked，则修 TTM local evidence gap。
3. 只有 C3.4 ready 后，才进入 C3.5 second forecasting candidate design；C3.5 继续 single-candidate-only，优先 design，不默认执行。
