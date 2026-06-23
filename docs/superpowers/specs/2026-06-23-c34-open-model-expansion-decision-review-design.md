# C3.4 Open Model Expansion Decision Review Design

Date: 2026-06-23

## 项目理解

B08 当前已经从“设备时序模型工作台”收束为公司时空智能在能源设备时序方向的核心样板项目。C 阶段的价值不是生成开源模型排行榜，而是把 FU13 observations、cycle / window、baseline、开源时序基础模型 adapter/cache evidence、候选信号和报告边界组织成可复核证据链。

截至 C3.3，项目已经完成：

- C3.1：NASA C-MAPSS classic 的本机 raw mapping review、schema、RUL metadata 和 split/leakage guard。
- C3.2：默认 cross-dataset contract，以及 explicit local 下的 C-MAPSS RUL baseline evaluation 和 FU13-like forecasting baseline reference。
- C3.3：默认 single-candidate contract-only 报告，以及 explicit local opt-in 下的 TTM on FU13-like forecasting adapter/cache/dependency evidence 路径。
- C2.2：Chronos、TimesFM、Moirai / Uni2TS、MOMENT、UniTS 和 frontier watchlist 的 versioned target / audit 口径。

C3.4 的合理位置不是“马上扩第二个模型”，而是把 C3.3 的 TTM 本机证据变成下一步是否扩候选的决策门。这个门必须保持默认离线、安全、可审计，并继续禁止 leaderboard、RUL/forecasting 指标混合、自研训练和生产能力宣称。

## 问题

C3.3 已经把单个候选 TTM 的本机执行链路做成可审计状态，但项目还缺少一个稳定的阶段结论：

- 如果 TTM 只到 `contract_ready_single_candidate_local_execution_blocked`、`local_execution_ttm_missing_dependency`、`local_execution_ttm_missing_or_blocked_weights`、`local_execution_ttm_unsupported_window_shape`、`local_execution_ttm_runtime_failed` 或 `blocked_insufficient_fu13_like_windows`，下一步不应盲目扩到 Chronos / TimesFM / Moirai。
- 如果 TTM local evidence 真的达到 `local_execution_ttm_forecasting_ready`，也不能直接开始多模型竞赛，而应先选择一个最小第二候选，并确认它的 package、license、cache、shape、resource 和 FU13-like forecasting fit。
- C2.2 watchlist 与 C3.3 local evidence 目前分散在不同阶段报告中，缺少一个简洁的 C3.4 Go / No-Go 报告把它们合并为“扩候选是否值得”的判断。

如果本轮直接新增 Chronos/TimesFM/Moirai 真实执行，会同时引入依赖、权重、资源、接口、指标解释和测试稳定性风险。更稳妥的推进是先让 C3.4 形成一个默认安全的 decision review stage。

## 目标

- 新增 C3.4 阶段设计，用于 review C3.3 TTM evidence 并给出 open model candidate expansion decision。
- 默认配置只读取结构化配置，不读取本机 model cache、不运行 adapter、不下载权重、不联网、不训练、不写 processed data。
- C3.4 报告必须明确 C3.3 TTM evidence gate：只有 `local_execution_ttm_forecasting_ready` 且 adapter evidence 字段完整时，才允许进入第二候选设计。
- C3.4 报告必须引用 C2.2 priority / watchlist 候选，但不把任何候选提升为真实执行。
- 默认决策应保守：在仓库默认证据只到 C3.3 contract-only 的情况下，结论为 `hold_candidate_expansion_pending_ttm_local_evidence`。
- 显式本机证据可通过配置录入 C3.3 local evidence status 和 adapter fields；录入仍不触发 adapter 执行。
- 保持 C-MAPSS RUL baseline-only，RUL metrics 与 forecasting metrics 继续分开解释。
- 更新 README 与 `details.md`，记录 C3.4 阶段入口、边界和下一步。

## 非目标

- 不新增 Chronos、TimesFM、Moirai 或其他 open model 的真实本机执行。
- 不新增 RUL open model adapter，不在 C-MAPSS RUL 上运行 open model。
- 不训练、微调或自研基础模型。
- 不读取本机 raw files、FU13 real data、C-MAPSS raw、model cache 或 generated reports。
- 不下载公开数据或模型权重。
- 不生成跨模型、跨任务或跨数据集 leaderboard。
- 不宣称生产 RUL、故障概率、维修建议、生产告警或自研模型优越性。

## 关键假设

- C3.3 的 default status `contract_ready_single_candidate_local_execution_blocked` 本身不是失败，但不足以支撑第二候选扩展。
- C3.3 的 `local_execution_ttm_missing_dependency`、`local_execution_ttm_missing_or_blocked_weights`、`local_execution_ttm_unsupported_window_shape`、`local_execution_ttm_runtime_failed` 和 `blocked_insufficient_fu13_like_windows` 都是有效证据；它们说明当前应先修 TTM 链路、窗口参数或记录 blocker，而不是扩模型。
- C3.4 不应自动解析未提交的 local report，因为 generated report、cache 和本机路径都保持 ignored；更可靠的默认方式是用显式配置录入已审查的 evidence status。
- C2.2 中 Chronos、TimesFM、Moirai / Uni2TS 是 forecasting 扩展的最自然候选，但都需要 package、license、cache、resource、shape 和 FU13-like adapter path 进一步设计。
- 如果 C3.3 TTM evidence gate 未通过，C3.4 的下一步应是 TTM local evidence remediation 或保持阶段性 No-Go，而不是推进 C3.5 第二候选执行。

## 方案比较

### 方案 A：只更新文档，人工记录 C3.4 判断

风险最低，但不可验证。README/details 可以写出 C3.4 判断，但没有 CLI、config 和测试来防止后续把“决策评审”误写成“第二候选实跑”或 leaderboard。

### 方案 B：新增 C3.4 decision review stage，默认离线生成 Go / No-Go 报告

新增 `c-stage-c34` 配置、runner、CLI 和报告。默认配置只包含 C3.3 evidence summary、C2.2 candidate references、gate policy 和 invalid claims；默认状态为 `hold_candidate_expansion_pending_ttm_local_evidence`。如果显式配置录入 `local_execution_ttm_forecasting_ready` 且必要 adapter fields 完整，则状态变为 `candidate_expansion_design_ready`，并推荐下一阶段只设计一个第二 forecasting 候选。其他 C3.3 状态映射为 `hold_candidate_expansion_pending_ttm_local_evidence` 或 `blocked_candidate_expansion_due_to_ttm_evidence_gap`。

这是推荐方案。它规模适中，能把项目路线中的 C3.4 变成可运行、可测试、可审计的阶段，同时不引入新模型执行风险。

### 方案 C：直接新增第二候选 open model local evaluation

短期看推进更快，但违背 C3.3 的下一阶段建议。Chronos、TimesFM、Moirai 的依赖、权重、资源和 API 都未完成 C3.4 决策门审查；直接实跑容易扩大成多模型竞赛，也会让默认测试和本机环境更不稳定。

## 推荐设计

### 阶段入口

新增默认入口：

```bash
uv run b08-model-core experiment c-stage-c34 \
  --config configs/c_stage_c34_open_model_expansion_decision_review.yaml \
  --output reports/c_stage_c34_open_model_expansion_decision_review.md
```

默认报告状态：

```text
hold_candidate_expansion_pending_ttm_local_evidence
```

该状态表示：C3.4 decision review 可运行，但默认仓库证据只证明 C3.3 contract 和 safety boundary，不足以扩第二候选。

可选本机证据录入样例：

```bash
uv run b08-model-core experiment c-stage-c34 \
  --config configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml \
  --output reports/c_stage_c34_review_c33_local_ttm_evidence.md
```

该配置只录入人工已审查的 C3.3 local evidence status 和 adapter fields，不读取 C3.3 generated report，不检查 cache，不运行 adapter。

### 配置

新增默认配置 `configs/c_stage_c34_open_model_expansion_decision_review.yaml`：

- `stage`: `C3_4_open_model_expansion_decision_review`
- `safety_policy`: 默认 `allow_network: false`、`allow_download: false`、`allow_model_cache: false`、`allow_local_execution: false`、`allow_training: false`、`allow_write_processed: false`
- `prerequisites`:
  - C3.3 design doc
  - C3.3 default status
  - C3.2 local status anchor
  - C2.2 watchlist audit source
- `c33_evidence`:
  - `source`: `default_contract`
  - `status`: `contract_ready_single_candidate_local_execution_blocked`
  - `candidate`: `ttm`
  - `task`: `fu13_like_forecasting`
  - `adapter_evidence`: 使用显式 sentinel `not_applicable_default_contract`，表示默认 contract-only 未运行 adapter；此时不要求 dependency/runtime/shape 字段。
- `decision_policy`:
  - `require_ttm_status`: `local_execution_ttm_forecasting_ready`
  - `require_adapter_fields`: dependency_status、weight_status、adapter_status、runtime_seconds、input_shape、output_shape、actual_network_used、download_allowed_not_verified
  - `allow_second_candidate_execution`: false
  - `leaderboard_allowed`: false
  - `rul_open_model_allowed`: false
- `candidate_review`: C2.2-derived forecasting候选，只做 design readiness review。
- `outputs`: report path

新增本机证据录入样例 `configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml`：

- 与默认配置相同安全边界。
- `c33_evidence.source`: `explicit_local_reviewed`
- `c33_evidence.status`: 用户按已审查 C3.3 local report 录入。
- 如果 status 为 `local_execution_ttm_forecasting_ready`，必须同时录入 required adapter fields。
- 如果 status 是 `local_execution_ttm_missing_dependency`、`local_execution_ttm_missing_or_blocked_weights`、`local_execution_ttm_unsupported_window_shape` 或 `local_execution_ttm_runtime_failed`，必须录入 `failure_reason`、`dependency_status` 和 `weight_status`。
- 如果 status 是 `blocked_insufficient_fu13_like_windows`，必须录入 `failure_reason` 或 `blocked_reason`，但不要求 adapter evidence 字段，因为 adapter 尚未执行。

### 决策状态

- `hold_candidate_expansion_pending_ttm_local_evidence`: 默认状态；C3.3 TTM evidence 尚不足，不扩候选。
- `candidate_expansion_design_ready`: C3.3 TTM local evidence ready 且 required adapter fields 完整；下一阶段可设计一个第二 forecasting candidate。
- `blocked_candidate_expansion_due_to_ttm_evidence_gap`: 已录入 explicit local evidence，但 TTM 证据显示缺依赖、缺权重、shape 不兼容或 runtime failure；下一步先修 TTM evidence gap。
- `invalid_c34_decision_contract`: 配置试图允许 leaderboard、RUL open model、第二候选执行、network/download/cache/training/write processed，或缺少必要 evidence 字段。

CLI 退出码约定：

- `invalid_c34_decision_contract` 或配置错误返回 1。
- 其他决策状态返回 0，因为它们是 C3.4 要表达的审查结论。

### C3.3 Evidence Mapping

C3.4 只接受以下 C3.3 evidence status。任何其他 status 都是配置错误。

| C3.3 evidence status | C3.4 decision status | 必填 evidence 字段 | CLI exit |
| --- | --- | --- | --- |
| `contract_ready_single_candidate_local_execution_blocked` | `hold_candidate_expansion_pending_ttm_local_evidence` | `source`、`candidate`、`task`；`adapter_evidence: not_applicable_default_contract` | 0 |
| `local_execution_ttm_forecasting_ready` | `candidate_expansion_design_ready` | `dependency_status`、`weight_status`、`adapter_status`、`runtime_seconds`、`input_shape`、`output_shape`、`actual_network_used`、`download_allowed_not_verified` | 0 |
| `local_execution_ttm_missing_dependency` | `blocked_candidate_expansion_due_to_ttm_evidence_gap` | `failure_reason`、`dependency_status`、`weight_status` | 0 |
| `local_execution_ttm_missing_or_blocked_weights` | `blocked_candidate_expansion_due_to_ttm_evidence_gap` | `failure_reason`、`dependency_status`、`weight_status` | 0 |
| `local_execution_ttm_unsupported_window_shape` | `blocked_candidate_expansion_due_to_ttm_evidence_gap` | `failure_reason`、`dependency_status`、`weight_status`、`input_shape` 或 `output_shape` | 0 |
| `local_execution_ttm_runtime_failed` | `blocked_candidate_expansion_due_to_ttm_evidence_gap` | `failure_reason`、`dependency_status`、`weight_status` | 0 |
| `blocked_insufficient_fu13_like_windows` | `hold_candidate_expansion_pending_ttm_local_evidence` | `failure_reason` 或 `blocked_reason` | 0 |

Required adapter fields are mandatory only for `local_execution_ttm_forecasting_ready`. Blocker statuses require failure evidence instead. The default contract-only status intentionally does not populate adapter fields and must not fail validation for that reason.

### 候选评审口径

C3.4 不做候选实跑，只输出候选 readiness：

| candidate | 默认结论 | 理由 |
| --- | --- | --- |
| Chronos / Chronos-Bolt | `review_only_not_promoted` | 需要 package、license、cache、API shape、resource review |
| TimesFM | `review_only_not_promoted` | 需要 TimesFM 2.5 package、weights、license、resource、forecasting API review |
| Moirai / Uni2TS | `review_only_not_promoted` | 需要 Uni2TS dependency、checkpoint compatibility 和 probabilistic forecasting shape review |

如果 C3.3 evidence gate 通过，C3.4 可以在报告中推荐下一阶段优先候选，但仍不自动执行。推荐顺序应基于最少新增风险：

1. Chronos-Bolt fallback route：如果 package/cache/license 更清晰，优先作为第二候选设计对象。
2. TimesFM：仅在 package 与 PyTorch cache 路径清晰时进入下一阶段。
3. Moirai / Uni2TS：接口和 probabilistic output shape 更复杂，除非前两者不适合，否则暂不优先。

### 报告

报告包含：

- Summary：stage、status、decision、config、C3.3 evidence source。
- Safety Policy：所有 flags。
- C3.3 Evidence Gate：status、candidate、task、required fields completeness、failure reason。
- Decision Policy：require_ttm_status、required fields、leaderboard_allowed、rul_open_model_allowed、second_candidate_execution_allowed。
- Candidate Expansion Review：Chronos / TimesFM / Moirai 的 review-only readiness、promotion blockers 和 next design requirement。
- Metric Separation：C-MAPSS RUL baseline-only；FU13-like forecasting metrics only；不合成排名。
- Go / No-Go：是否进入 C3.5 second-candidate design。
- Invalid Claims：no production RUL、no alarms、no maintenance recommendation、no leaderboard、no self-developed superiority、no second-candidate execution in C3.4。
- Next Step：根据 status 生成下一阶段建议。

### 测试策略

- 默认 config offline safe：不允许 network/download/cache/local execution/training/write processed。
- 默认 runner 不触碰 adapter factory、model cache 或 C3.3 generated report。
- 默认状态为 `hold_candidate_expansion_pending_ttm_local_evidence`。
- 配置若允许 leaderboard、RUL open model、second candidate execution、network/download/cache/training/write processed，应报配置错误。
- `local_execution_ttm_forecasting_ready` 但缺 adapter field 时应报配置错误。
- `local_execution_ttm_forecasting_ready` 且 adapter fields 完整时状态为 `candidate_expansion_design_ready`，但报告仍声明 C3.4 不执行第二候选。
- `local_execution_ttm_missing_dependency`、`local_execution_ttm_missing_or_blocked_weights`、`local_execution_ttm_unsupported_window_shape`、`local_execution_ttm_runtime_failed` 映射到 `blocked_candidate_expansion_due_to_ttm_evidence_gap`，并要求 failure evidence。
- `blocked_insufficient_fu13_like_windows` 映射到 `hold_candidate_expansion_pending_ttm_local_evidence`，并要求 blocked reason，但不要求 adapter evidence。
- CLI 默认路径写报告且返回 0。
- README/details/scaffold 测试包含 C3.4 命令、文档入口和 safety boundary。
- 全量 `uv run python -m pytest -q` 通过。

## 验收标准

- C3.4 默认 CLI 可离线运行并生成 decision review report。
- C3.4 默认不读取 raw、本机 cache、C3.3 generated report，不实例化任何 open model adapter。
- C3.4 报告清楚说明：默认不扩候选，除非 C3.3 TTM local evidence ready 且 required adapter fields 完整。
- C3.4 可用显式配置录入 C3.3 本机证据，并将 ready / blocker 状态映射为不同决策。
- Chronos、TimesFM、Moirai 只作为 review-only 候选出现在 C3.4，不执行、不下载、不生成排行榜。
- C-MAPSS RUL baseline-only、RUL/forecasting 指标分离、安全边界和 invalid claims 均在报告和文档中保留。
- README 和 `details.md` 同步 C3.4 阶段入口、边界和下一步。
- 不提交 raw、zip、parquet、cache 或 generated report。

## 下一阶段建议

如果 C3.4 默认结论是 `hold_candidate_expansion_pending_ttm_local_evidence`，下一阶段应先运行或补齐 C3.3 explicit local TTM evidence，不进入第二候选。

如果 C3.4 结论是 `blocked_candidate_expansion_due_to_ttm_evidence_gap`，下一阶段应修复 TTM dependency/cache/shape/runtime blocker，仍不扩候选。

只有当 C3.4 结论是 `candidate_expansion_design_ready`，下一阶段才进入 C3.5 second forecasting candidate design。C3.5 仍应只选择一个候选，优先 Chronos-Bolt fallback route 或另一个最小风险 forecasting adapter；C-MAPSS RUL 继续 baseline-only，直到另行批准 RUL adapter design。
