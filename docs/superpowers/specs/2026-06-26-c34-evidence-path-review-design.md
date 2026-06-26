# C3.4 Evidence Path Review Design

Date: 2026-06-26

## 项目理解

B08 当前已经完成 post-C3.4 C-stage roadmap 的入口级规划。下一阶段建议明确要求先执行 C3.4 evidence path：如果尚未 reviewed C3.3 TTM local evidence，则先补齐或复核 C3.3 explicit local TTM evidence，再用 C3.4 复核；只有 C3.4 达到 `candidate_expansion_design_ready` 后，才进入 C3.5 single second forecasting candidate design。

仓库默认路径仍必须保持可复现和安全：不联网、不下载、不检查本机 cache、不提交 generated reports、不读取 raw/parquet、不训练、不生成 leaderboard。C3.4 已经实现为 decision review stage，可以从结构化配置中读取 C3.3 evidence summary 并输出 hold、blocked 或 ready 决策。因此本轮合理目标不是新增模型执行，而是把 C3.4 evidence path 的当前复核结论沉淀为 tracked review 文档，并把 README/details 指向这份证据路径记录。

## 问题

当前 README/details 已经说明“先 C3.4 evidence path，再 C3.5”，但还缺少一份阶段 review 文档回答三个实际问题：

- 当前仓库默认 C3.4 evidence path 到底走到哪一步。
- 是否已经有 reviewed C3.3 TTM local evidence 足以进入 `candidate_expansion_design_ready`。
- 如果没有，下一步到底是运行 C3.3 explicit local TTM、修 blocker，还是进入 C3.5。

如果继续只写路线，会显得空泛；如果直接执行第二候选设计，会绕过 C3.4 gate；如果在没有本机 ready evidence 的情况下声称 ready，会制造伪证据。

## 目标

- 新增 tracked review 文档 `docs/reviews/2026-06-26-c34-evidence-path-review.md`。
- 明确记录默认 C3.4 evidence path 结论：仓库默认 C3.3 contract evidence 只能得到 `hold_candidate_expansion_pending_ttm_local_evidence`。
- 明确记录本机 C3.4 review example 当前是 blocker 示例，不是 ready 证据：`blocked_candidate_expansion_due_to_ttm_evidence_gap`。
- 明确记录缺口：尚未在 tracked review 中确认 reviewed C3.3 TTM local evidence 达到 `local_execution_ttm_forecasting_ready` 且 adapter evidence 字段完整。
- 更新 README 和 details，把“下一步先执行 C3.4 evidence path”从路线口号升级为可点击的 review 记录。
- 新增文档测试，保护 review 文档、README/details 入口和 C3.5 gate 不被后续改松。

## 非目标

- 不运行 TTM 权重下载或真实模型执行。
- 不新增 C3.5 CLI、adapter、配置或候选选择实现。
- 不读取或提交 `reports/c_stage_c33_*.md`、`reports/c_stage_c34_*.md` 等 generated reports。
- 不读取 FU13 real parquet、C-MAPSS raw、model cache 或 ignored local data。
- 不改变 C3.4 runner 的决策逻辑。
- 不把 Chronos、TimesFM、Moirai 或其他模型提升为可执行候选。
- 不生成 leaderboard，不混合 RUL 与 forecasting 指标。

## 关键假设

- 目前仓库内没有可追踪的 C3.3 explicit local TTM ready report；本轮不能假设用户本机 cache 已经具备 ready evidence。
- `configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml` 是 blocker review example，不能被解释为 C3.5 ready。
- 本轮可以运行默认安全的 C3.4 CLI smoke 到临时目录进行验证，但不提交生成报告。
- review 文档是 C3.4 evidence path 的 tracked 结论；真正的本机 ready evidence 仍需后续用 explicit local opt-in 生成并人工录入复核。

## 方案比较

### 方案 A：只更新 details 的下一步文字

改动最小，但没有独立证据记录。后续读者仍无法判断 C3.4 evidence path 是否已经执行过，也容易把“下一步 C3.5”误读成直接开始第二候选。

### 方案 B：新增 C3.4 evidence path review 文档并同步入口

这是推荐方案。它用一份 tracked review 文档记录当前 evidence path 的真实状态：default hold、local example blocked、ready evidence absent、C3.5 blocked until ready。README 只补链接和一句状态，details 更新当前阶段和下一步台账。实现只涉及文档和文档测试，不触碰模型依赖。

### 方案 C：直接运行 C3.3 explicit local TTM 并尝试达成 ready

如果用户本机已配置 optional dependency、cache 和权重，这会是最终需要做的动作；但它依赖本机环境和 ignored artifacts，不适合作为默认仓库提交。本轮可以把它列为下一步命令和验收口径，但不把其成功作为默认实现目标。

## 推荐设计

### Review 文档

新增 `docs/reviews/2026-06-26-c34-evidence-path-review.md`，包含：

- 范围：review-only，不运行模型，不提交 generated report。
- 输入：C3.3 默认配置状态、C3.4 默认配置、C3.4 local evidence review example、post-C3.4 roadmap。
- 当前结论：
  - default C3.4 status: `hold_candidate_expansion_pending_ttm_local_evidence`
  - local example C3.4 status: `blocked_candidate_expansion_due_to_ttm_evidence_gap`
  - no reviewed ready evidence: 未确认 `local_execution_ttm_forecasting_ready`
  - C3.5 decision: blocked until `candidate_expansion_design_ready`
- 缺口：dependency/cache/weight/shape/runtime evidence 尚未完整 ready。
- 下一步：先执行或复核 C3.3 explicit local TTM evidence；若 blocked，修 TTM evidence gap；只有 C3.4 ready 后写 C3.5 single second forecasting candidate design spec。
- 禁止宣称：第二候选可执行、leaderboard、RUL open-model readiness、生产告警、自研模型优越性。

### README 更新

在“后续发展路线”中补一段或一句，指向 C3.4 evidence path review，并明确当前 tracked 结论仍是 hold/blocker，不进入 C3.5。

在“文档入口”增加 review 链接。

### details 更新

更新当前阶段为 “post-C3.4 roadmap documented; C3.4 evidence path reviewed”。每日更新新增一行，记录 review 文档和当前 gate 结论。下一步计划第一项改为更具体的 “补齐 C3.3 explicit local TTM ready evidence 并用 C3.4 复核”，而不是泛泛的 “C3.4 evidence path”。

### 测试策略

- 新增文档测试检查 review 文档存在并包含 hold、blocked、ready evidence absent、C3.5 blocked、no leaderboard 等关键约束。
- 新增或更新 README/details 测试，确保链接到 C3.4 evidence path review，且 C3.5 仍以 `candidate_expansion_design_ready` 为前置条件。
- 运行 targeted documentation tests。
- 运行 C3.4 测试，确认既有 decision review 逻辑未被改变。
- 运行全量测试。

## 验收标准

- spec、plan、review 文档均在 `docs/superpowers/` 或 `docs/reviews/` 下可追踪。
- README 和 details 都能从项目入口指向 C3.4 evidence path review。
- review 文档明确当前不是 C3.5 ready。
- 测试保护文档中的 hold/blocker/ready gate。
- 默认实验行为、配置和模型执行逻辑不变。
- 不提交 raw、zip、parquet、cache 或 generated report。

## 下一阶段建议

本轮完成后，下一阶段应先补齐 reviewed C3.3 TTM local evidence：在具备本机 optional dependency 和 cache/weight 条件后运行 C3.3 explicit local TTM，人工复核 adapter evidence 字段，再把结果录入 C3.4 local review config。只有 C3.4 输出 `candidate_expansion_design_ready` 后，才进入 C3.5 single second forecasting candidate design。
