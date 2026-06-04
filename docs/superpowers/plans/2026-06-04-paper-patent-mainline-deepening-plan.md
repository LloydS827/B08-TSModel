# Paper Patent Mainline Deepening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 B08 A 阶段深化为“论文框架优先、专利与实验需求反推”的知识成果包，同时用严格文档预算避免调研资料让项目重新臃肿。

**Architecture:** 本计划采用少量主资产承接大量外部调研：`paper-patent-directions.md` 承接论文/专利主线，`source-registry.md` 承接外部来源证据，其他矩阵只在必要时小范围更新。调研由 subagent 核对 primary sources，主线程只整合被 claim/evidence 引用的证据。

**Tech Stack:** Markdown 文档、primary-source web research、subagent review、`rg` 静态一致性检查。无代码实现、无模型训练、无测试套件变更。

---

## Scope and Guardrails

本计划对应 spec：`docs/superpowers/specs/2026-06-04-paper-patent-mainline-deepening-design.md`。

硬约束：

- 固定现有 5 个专利候选：新增专利候选必须先请用户确认。
- 第一轮 source registry 最多登记 18 条 `accepted`/`candidate` 来源；`rejected`/`needs-review` 审计行最多额外保留 4 条。
- 默认只新增 1 个文档：`docs/research/source-registry.md`。
- 禁止新增 `docs/research/papers/`、`docs/research/models/`、`docs/research/patents/`、临时 HTML、散落 Markdown。
- 每条外部来源必须填写 `supports_claim_id`、`patent_id` 或 `evidence_id` 中至少一个；专利 prior-art 来源可以只挂 `patent_id`。
- 不启动 C 阶段实验实现，不启动 B 阶段自研训练。
- 不声称生产告警、RUL 精确估计、自动维修建议、专利授权或自研基础模型训练成功。
- Git 提交只在用户明确要求收尾时执行；执行计划本身不要求自动 commit。

## File Budget

| 文件 | 动作 | 责任边界 |
| --- | --- | --- |
| `docs/research/source-registry.md` | Create | 唯一外部来源登记表，记录 primary source、claim/evidence 映射和最小证据。 |
| `docs/research/paper-patent-directions.md` | Modify | 主承接文档，深化论文框架、贡献点、专利候选、证据需求和 C 阶段反推。 |
| `docs/research/index.md` | Modify if needed | 仅在新增 `source-registry.md` 后加入一行入口，不展开内容。 |
| `docs/research/open-source-model-paper-matrix.md` | Modify only if needed | 仅当外部核对改变模型候选、来源状态或缺口表述时更新。 |
| `docs/research/task-metric-matrix.md` | Modify only if needed | 仅当 C 阶段证据接口需要补充 task_id/gate 字段时更新。 |
| `docs/research/predictive-maintenance-dataset-matrix.md` | Modify only if needed | 仅当数据来源/授权/任务映射被 primary source 核对改变时更新。 |
| `details.md` | Modify at end only if user wants stage log | 只写阶段摘要，不写流水账。 |

## Claim and Evidence IDs

执行前固定以下 ID，所有来源必须挂接到其中至少一个。

### Paper claim IDs

| claim_id | 含义 |
| --- | --- |
| `C1_problem_definition` | B08 是小样本工业物联设备健康管理问题，不是普通 forecasting。 |
| `C2_related_work_map` | 时序基础模型、预测性维护、工业异常检测、弱标签学习的相关工作分层。 |
| `C3_industrial_gap` | 现有模型在工业 metadata、多传感器物理域、弱标签、多任务健康管理上的缺口。 |
| `C4_framework_design` | B08 的数据、任务、模型、评测和 workflow 框架。 |
| `C5_validation_path` | FU13 + 开源预测性维护数据的分层验证路径。 |
| `C6_boundary_claims` | 不能过度承诺生产告警、RUL、自动维修或专利授权。 |

### Patent claim IDs

| patent_id | 含义 |
| --- | --- |
| `P1_stage_sensor_encoding` | 工艺阶段与传感器物理域联合编码方法。 |
| `P2_small_sample_pretraining` | 工业设备小样本预测性维护的基础时序模型预训练方法。 |
| `P3_weak_label_anomaly_signal` | 无故障标签条件下的设备异常候选信号生成方法。 |
| `P4_real_open_data_fusion` | 真机数据与开源设备健康数据融合的设备时序基础模型训练方法。 |
| `P5_multitask_health_evaluation` | 多任务设备状态表征、预测残差和退化趋势联合评估方法。 |

### Evidence IDs

| evidence_id | 含义 |
| --- | --- |
| `E1_forecasting_residual` | forecasting 是强基线但不足以直接推出维护能力。 |
| `E2_representation` | 工业设备需要状态表征和弱标签 probe。 |
| `E3_imputation` | 多传感器缺失与重建是基础任务。 |
| `E4_open_data_pm` | 第三层任务需要 run-to-failure 或故障数据。 |
| `E5_patent_effect` | 专利技术效果需要实验样例、对照或专家复核支撑。 |

---

### Task 1: Preflight and Document Budget Lock

**Files:**
- Read: `docs/superpowers/specs/2026-06-04-paper-patent-mainline-deepening-design.md`
- Read: `docs/research/index.md`
- Read: `docs/research/paper-patent-directions.md`
- Read: `docs/research/open-source-model-paper-matrix.md`
- Read: `docs/research/task-metric-matrix.md`
- Read: `docs/research/predictive-maintenance-dataset-matrix.md`

- [ ] **Step 1: Confirm current workspace state**

Run:

```bash
git status --short --branch
```

Expected: identify any uncommitted files before editing. Do not overwrite unrelated user changes.

- [ ] **Step 2: Confirm no forbidden research subdirectories exist**

Run:

```bash
find docs/research -maxdepth 2 -type d | sort
```

Expected: no `docs/research/papers`, `docs/research/models`, or `docs/research/patents` directories.

- [ ] **Step 3: Record document budget in worker handoff**

Write in the task handoff, not as a new file:

```text
Allowed create: docs/research/source-registry.md only.
Allowed default modify: docs/research/paper-patent-directions.md and docs/research/index.md.
Conditional modify: model/task/dataset matrices only if primary-source evidence changes an existing claim.
Forbidden: per-paper/model/patent notes, temporary HTML, scattered Markdown.
```

- [ ] **Step 4: Stop if scope pressure appears**

If a worker proposes more than one new document or more than 18 first-round sources, stop and ask the main thread/user to approve expansion.

---

### Task 2: Create Source Registry Skeleton

**Files:**
- Create: `docs/research/source-registry.md`
- Modify: `docs/research/index.md`

- [ ] **Step 1: Create registry header and rules**

Create `docs/research/source-registry.md` with this structure:

```markdown
# B08 论文/专利主线来源登记表

## 定位

本文件只登记支撑 B08 论文/专利主线的外部 primary sources，不写长篇读书笔记，不替代论文综述正文。

每条来源必须挂接至少一个 `supports_claim_id`、`patent_id` 或 `evidence_id`。不能挂接的资料不进入本表。

## 文档预算

- 第一轮最多登记 18 条 accepted/candidate 来源。
- rejected/needs-review 审计行最多额外保留 4 条，且必须解释重要排除原因。
- 不为单篇论文、单个模型、单个数据集或单个专利创建独立文档。
- 原始 PDF、模型权重、数据下载包不得放入 `docs/`。
- 二手博客、排行榜和新闻稿只能作为线索，不能作为主要证据。

## ID 字典

### supports_claim_id

| id | 含义 |
| --- | --- |
| C1_problem_definition | 小样本工业物联设备健康管理问题定义 |
| C2_related_work_map | 相关工作分层 |
| C3_industrial_gap | 工业 metadata / 弱标签 / 多任务缺口 |
| C4_framework_design | 数据-任务-模型-评测框架 |
| C5_validation_path | FU13 + 开源数据验证路径 |
| C6_boundary_claims | 边界和禁止过度承诺 |

### patent_id

| id | 含义 |
| --- | --- |
| P1_stage_sensor_encoding | 工艺阶段与传感器物理域联合编码 |
| P2_small_sample_pretraining | 小样本工业设备基础模型预训练 |
| P3_weak_label_anomaly_signal | 无故障标签异常候选信号生成 |
| P4_real_open_data_fusion | 真机与开源设备健康数据融合训练 |
| P5_multitask_health_evaluation | 多任务设备状态与退化趋势评估 |

### evidence_id

| id | 含义 |
| --- | --- |
| E1_forecasting_residual | forecasting residual 证据 |
| E2_representation | representation / probe 证据 |
| E3_imputation | imputation / reconstruction 证据 |
| E4_open_data_pm | run-to-failure / fault / RUL 开源数据证据 |
| E5_patent_effect | 专利技术效果证据 |

## 来源登记表

| source_id | type | title | url_or_doi | primary_source | supports_claim_id | patent_id | evidence_id | relevance | key_claim | checked_at | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

- [ ] **Step 2: Add initial empty status note**

Append:

```markdown
## 使用规则

- `key_claim` 只记录与 B08 直接相关的最小证据。
- `status=accepted` 表示该来源已被主线文档引用。
- `status=candidate` 表示可用于后续核对，但尚未进入主线论证。
- `status=rejected` 表示核对后不采用，并需简述原因。
- `status=needs-review` 表示来源可靠性、许可证、接口或适用性仍需复核。
```

- [ ] **Step 3: Update research index minimally**

Modify `docs/research/index.md` in the research asset list with one row:

```markdown
| [source-registry.md](source-registry.md) | 计划创建 / A 阶段论文专利深化使用 | 统一登记外部论文、仓库、模型卡、数据集和专利来源，要求每条来源挂接 claim/evidence/patent ID，避免碎片化文档。 |
```

Also add it near `paper-patent-directions.md` in the reading order as optional evidence registry.

- [ ] **Step 4: Verify no accidental extra docs were created**

Run:

```bash
find docs/research -maxdepth 2 -type f | sort
```

Expected: at most one new file beyond existing research assets: `docs/research/source-registry.md`.

---

### Task 3: Primary Source Research Batch A - Time-Series Foundation Models

**Files:**
- Modify: `docs/research/source-registry.md`
- Conditional modify: `docs/research/open-source-model-paper-matrix.md`

- [ ] **Step 1: Dispatch model research subagent**

Use one subagent. Ask it to browse and verify primary sources only for first-round core models:

```text
TTM / TinyTimeMixer, MOMENT, Chronos, TimesFM, Moirai / Uni2TS, UniTS.
Optional only if time remains: TSPulse as extension candidate.
Do not create files. Return source rows only.
Each row must include source_id, type, title, URL/DOI, primary_source, supports_claim_id, patent_id if relevant, evidence_id, relevance, key_claim, checked_at, status.
Maximum rows: 7.
```

- [ ] **Step 2: Main thread filters rows**

Accept only rows that meet all conditions:

```text
- primary source is paper, official repository, official model card, or official documentation
- row supports C2, C3, C4, E1, E2, or E3
- key_claim is specific to B08 and not a generic model advertisement
- source is not already represented with enough detail in existing matrix unless it adds needed support
```

- [ ] **Step 3: Append accepted rows to source registry**

Update only the table in `docs/research/source-registry.md`.

Use source IDs:

```text
S001_TTM_2024
S002_MOMENT_2024
S003_CHRONOS_2024
S004_TIMESFM_2023
S005_MOIRAI_2024
S006_UNITS_2024
S007_TSPULSE_EXTENSION
```

- [ ] **Step 4: Decide whether model matrix update is needed**

Only modify `docs/research/open-source-model-paper-matrix.md` if the primary-source check changes one of these:

```text
- open-source availability
- task coverage
- adaptation support
- license or model-card status
- core vs extension candidate status
```

If no change is needed, do not edit the matrix.

- [ ] **Step 5: Document rejected/needs-review rows only in registry**

If a source is unreliable or not primary, add it only if useful as `status=rejected` or `status=needs-review`; otherwise omit it entirely.

---

### Task 4: Primary Source Research Batch B - Predictive Maintenance, Industrial Time Series, and Prior Art

**Files:**
- Modify: `docs/research/source-registry.md`
- Conditional modify: `docs/research/predictive-maintenance-dataset-matrix.md`
- Conditional modify: `docs/research/task-metric-matrix.md`

- [ ] **Step 1: Dispatch PM/dataset research subagent**

Use one subagent. Ask it to verify primary or canonical sources for:

```text
C-MAPSS, IMS Bearing, PRONOSTIA / FEMTO-ST, Tennessee Eastman Process, industrial anomaly/process monitoring review, predictive maintenance/RUL review.
Maximum rows: 6.
```

Required mapping:

```text
- C1_problem_definition or C2_related_work_map for reviews
- C5_validation_path and E4_open_data_pm for datasets
- C6_boundary_claims if a source clarifies RUL/maintenance limits
```

- [ ] **Step 2: Dispatch patent/prior-art search subagent**

Use one subagent. Ask it to perform a first-pass prior-art search for the fixed 5 patent IDs only.

Limits:

```text
- Maximum rows: 5.
- Do not propose new patent candidates.
- Use patent/publication databases or official patent pages when available.
- Return keywords and closest prior-art themes, not legal conclusions.
```

- [ ] **Step 3: Main thread filters rows against source cap**

Total `accepted`/`candidate` registry rows after Task 4 must be <= 18. `rejected`/`needs-review` rows may be kept only when they explain an important exclusion, with a maximum of 4 extra audit rows.

Priority order if too many rows:

```text
1. Sources directly needed for C1-C5 paper frame
2. Sources needed for P1-P5 prior-art framing
3. Sources needed for E1-E5 experiment evidence
4. Extension model or speculative sources
```

- [ ] **Step 4: Append accepted rows to source registry**

Use source IDs:

```text
S008_CMAPSS
S009_IMS_BEARING
S010_PRONOSTIA
S011_TEP
S012_PM_RUL_REVIEW
S013_INDUSTRIAL_ANOMALY_REVIEW
S014_PRIOR_ART_P1
S015_PRIOR_ART_P2
S016_PRIOR_ART_P3
S017_PRIOR_ART_P4
S018_PRIOR_ART_P5
```

- [ ] **Step 5: Conditional matrix updates**

Only update dataset/task matrices if primary-source evidence changes an existing field or adds a missing boundary.

Allowed examples:

```text
- Mark a dataset as candidate / needs license review.
- Clarify RUL support vs fault classification support.
- Clarify that open data evidence does not prove FU13 production capability.
```

Do not expand matrices into full literature reviews.

---

### Task 5: Deepen Paper Mainline in Main Document

**Files:**
- Modify: `docs/research/paper-patent-directions.md`

- [ ] **Step 1: Add paper mainline blueprint section**

Add a section titled:

```markdown
## 论文主线蓝图
```

It must include:

```markdown
- 论文暂定题目
- 核心问题
- 3-5 个贡献点
- 相关工作分层
- 验证路径
- 禁止过度解释
```

- [ ] **Step 2: Use this tentative title**

```markdown
面向小样本工业物联设备健康管理的时序基础模型框架与验证
```

- [ ] **Step 3: Define one core question**

Use this wording unless research evidence forces refinement:

```markdown
在真实故障标签稀缺、工况阶段强结构、多传感器物理域耦合且跨设备泛化需求存在的工业物联场景下，如何构建设备时序基础模型的任务体系、数据组织、模型适配和验证路径，使其能够在小样本条件下服务预测性维护相关候选任务？
```

- [ ] **Step 4: Draft 4 contribution candidates**

Use concise bullets:

```markdown
1. 提出面向小样本工业设备健康管理的时序基础模型问题定义。
2. 建立 forecasting、imputation、representation、weak-label proxy 和预测性维护目标任务的分层验证框架。
3. 将 FU13 真机数据与开源预测性维护数据放入统一 schema / task / metric 证据路径。
4. 提出从开源模型适配到条件性自研训练的 A -> C -> B 决策门。
```

- [ ] **Step 5: Link each contribution to source IDs and evidence IDs**

Add a small table:

```markdown
| contribution_id | supports_claim_id | evidence_id | source_ids | current_gap |
| --- | --- | --- | --- | --- |
```

Each row must reference source IDs from `source-registry.md`.

---

### Task 6: Structure the Fixed Five Patent Candidates

**Files:**
- Modify: `docs/research/paper-patent-directions.md`

- [ ] **Step 1: Add patent candidate table**

Add or replace a section titled:

```markdown
## 专利候选结构化拆解
```

- [ ] **Step 2: Add exactly five patent rows**

Rows must use these IDs only:

```text
P1_stage_sensor_encoding
P2_small_sample_pretraining
P3_weak_label_anomaly_signal
P4_real_open_data_fusion
P5_multitask_health_evaluation
```

- [ ] **Step 3: Use required columns**

Use this table header:

```markdown
| patent_id | technical_problem | proposed_solution | key_steps | inputs_outputs | alternatives | evidence_needed | prior_art_keywords | source_ids | current_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

- [ ] **Step 4: Keep status conservative**

Allowed `current_status` values in this stage:

```text
candidate
evidence-needed
needs-prior-art-review
```

Do not use `ready-for-disclosure` unless the user explicitly asks for a patent handoff package.

- [ ] **Step 5: Add patent boundary note**

Add this note below the table:

```markdown
以上方向是技术交底候选，不构成新颖性、创造性、可授权性或侵权风险判断；后续需要专利检索、代理人审查和实验/样例证据支撑。
```

---

### Task 7: Reverse C-Stage Evidence Needs from Paper and Patent Claims

**Files:**
- Modify: `docs/research/paper-patent-directions.md`
- Conditional modify: `docs/research/task-metric-matrix.md`

- [ ] **Step 1: Add evidence backlog section**

Add a section titled:

```markdown
## C 阶段证据需求反推
```

- [ ] **Step 2: Add evidence backlog table**

Use this header:

```markdown
| evidence_id | supports | required_experiment | required_data | primary_metric | expected_artifact | invalid_claims |
| --- | --- | --- | --- | --- | --- | --- |
```

- [ ] **Step 3: Fill E1-E5 only**

Use exactly these rows:

```text
E1_forecasting_residual
E2_representation
E3_imputation
E4_open_data_pm
E5_patent_effect
```

- [ ] **Step 4: Keep experiments as future needs**

Each `required_experiment` must be written as future C-stage evidence, not as completed work.

- [ ] **Step 5: Conditional task matrix update**

Only update `docs/research/task-metric-matrix.md` if the evidence backlog reveals a missing field needed for future task tracking.

If updated, add no more than one short subsection named:

```markdown
## 论文/专利证据接口
```

The subsection should point back to `paper-patent-directions.md` and avoid duplicating the full evidence backlog.

---

### Task 8: Anti-Bloat and Consistency Review

**Files:**
- Read: `docs/research/source-registry.md`
- Read: `docs/research/paper-patent-directions.md`
- Read: `docs/research/index.md`
- Read conditionally modified matrices

- [ ] **Step 1: Run forbidden file check**

Run:

```bash
find docs/research -maxdepth 3 -type f | sort
```

Expected: no per-paper/model/patent note files and no temporary HTML reports.

- [ ] **Step 2: Run source row count check**

Run:

```bash
awk -F '|' '/^\| S[0-9]/ && ($0 ~ /accepted/ || $0 ~ /candidate/) {count++} END {print count+0}' docs/research/source-registry.md
```

Expected: `<= 18` for `accepted`/`candidate` rows. Then manually confirm `rejected`/`needs-review` rows are `<= 4` and explain important exclusions.

- [ ] **Step 3: Run claim/patent/evidence mapping check**

Run:

```bash
rg -n "\| S[0-9].*\|.*\|.*\|.*\|.*\|\s*\|" docs/research/source-registry.md
```

Expected: no accepted/candidate row with empty `supports_claim_id`, `patent_id`, and `evidence_id` simultaneously. Patent prior-art rows may use only `patent_id`. If the command is too coarse, inspect the table manually.

- [ ] **Step 4: Run overclaim check**

Run:

```bash
rg -n "生产告警|RUL 精确|自动维修|专利授权|已经完成自研|大规模训练成功" docs/research/paper-patent-directions.md docs/research/source-registry.md docs/research/index.md
```

Expected: matches only appear in boundary/forbidden-claim contexts.

- [ ] **Step 5: Dispatch consistency review subagent**

Ask one reviewer to check:

```text
- Does paper-patent-directions.md satisfy the spec?
- Does source-registry.md prevent document bloat?
- Are all source rows tied to claim/evidence/patent IDs?
- Are the five patent candidates fixed and conservative?
- Does the plan avoid premature C/B implementation claims?
```

Reviewer output must be `APPROVED` or `ISSUES_FOUND`.

- [ ] **Step 6: Fix only blocking issues**

If reviewer finds issues, fix only the named files and re-run one review. Do not expand scope.

---

### Task 9: Stage Handoff

**Files:**
- Modify if appropriate: `details.md`
- Read: `docs/research/index.md`
- Read: `docs/research/paper-patent-directions.md`
- Read: `docs/research/source-registry.md`

- [ ] **Step 1: Decide whether details.md needs a stage note**

If the implementation materially changes research stage status, append one concise stage summary to `details.md`.

Do not write a same-day action log.

- [ ] **Step 2: Prepare final handoff summary**

Report:

```text
- Files changed
- Source count
- Paper mainline title and core question
- Five fixed patent candidates
- C-stage evidence IDs
- Review result
- Known residual risks
- Tests/verification run: docs-only checks and subagent review, no code tests unless user requested
```

- [ ] **Step 3: Ask before Git/PR if not already requested**

If the user has not explicitly requested Git submission for this stage, stop after handoff and ask whether to commit/PR.

---

## Execution Notes for Subagents

Subagents must not create files unless specifically assigned. Research subagents return source rows only; they do not edit documents. Writer subagents may edit only assigned files. Reviewer subagents are read-only.

Use current-date checks when browsing external sources. Time-series foundation model repositories, model cards, licenses and paper versions can change; primary sources must be checked during execution, not assumed from memory.

## Verification Summary

This is a documentation/research plan. Verification is therefore:

- static document budget checks,
- source row count checks,
- claim/evidence mapping checks,
- overclaim checks,
- subagent document review.

No Python/unit test suite is required unless later execution touches code.
