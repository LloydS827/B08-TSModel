# C Stage Post-C3.4 Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write the post-C3.4 C-stage roadmap into README/details with tests that preserve the C3.4/C3.5 gate, multi-task evidence direction, and C -> B decision boundary.

**Architecture:** This is a documentation-oriented change. `README.md` becomes the stable project-entry roadmap, `details.md` remains the current status and next-step ledger, and `tests/test_experiment_scaffold.py` protects the key roadmap claims from regression. No experiment behavior, CLI, adapter, config, dependency, data, cache, or generated report changes are allowed.

**Tech Stack:** Markdown, pytest, existing `uv` workflow.

---

## File Structure

- Modify: `tests/test_experiment_scaffold.py`
  - Add focused documentation tests for the new README roadmap and details ledger.
  - Keep tests string-based, consistent with existing scaffold documentation tests.
- Modify: `README.md`
  - Add a concise “后续发展路线” section after “当前可复现资产” and before “快速开始”.
  - Add a link to the new spec in the C3.4/C3.5 route text or documentation references.
- Modify: `details.md`
  - Update date, current stage, daily update, and next-step plan.
  - Preserve the existing three main sections: current stage, daily updates, next plan.
- Existing spec: `docs/superpowers/specs/2026-06-26-c-stage-post-c34-roadmap-design.md`
  - Already committed; do not rewrite unless implementation reveals a spec mismatch.

## Task 1: Add Roadmap Documentation Tests

**Files:**
- Modify: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Add README roadmap test**

Add a new test near the existing documentation tests:

```python
def test_readme_documents_post_c34_c_stage_roadmap():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "## 后续发展路线" in readme
    roadmap = readme.split("## 后续发展路线", 1)[1].split("\n## 快速开始", 1)[0]

    assert "论文/专利证据优先" in roadmap
    assert "工程样板承接" in roadmap
    assert "C3.4" in roadmap
    assert "C3.5" in roadmap
    assert "candidate_expansion_design_ready" in roadmap
    assert "single second forecasting candidate design" in roadmap
    assert "E2 representation" in roadmap
    assert "E3 imputation/reconstruction" in roadmap
    assert "weak-label" in roadmap
    assert "E5 patent effect" in roadmap
    assert "C -> B" in roadmap
    assert "go_to_b_minimal_prototype" in roadmap
    assert "stay_in_c_adaptation" in roadmap
    assert "knowledge_only_consolidation" in roadmap
    assert "no_go_hold" in roadmap
    assert "不生成 leaderboard" in roadmap
    assert "不直接训练自研基础模型" in roadmap
    assert "docs/superpowers/specs/2026-06-26-c-stage-post-c34-roadmap-design.md" in roadmap
```

- [ ] **Step 2: Run README test to verify it fails**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_readme_documents_post_c34_c_stage_roadmap -q
```

Expected: the test fails because README has not yet been updated.

- [ ] **Step 3: Keep failing test uncommitted until README is updated**

Do not commit the intentionally failing test by itself. The project must remain usable at every committed state. Leave the test in the working tree and continue to Task 2 so the next commit includes both the README test and the README implementation that makes it pass.

## Task 2: Update README Roadmap

**Files:**
- Modify: `README.md`
- Test: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Insert `## 后续发展路线` section**

Place after the FU13 canonical observations fact table and before `## 快速开始`.

Use this content, preserving existing README tone and avoiding excessive detail:

```markdown
## 后续发展路线

B08 后续默认按“论文/专利证据优先，工程样板承接，模型原型 gate 后置”的路线推进。C 阶段后续不是继续堆开源模型数量，也不是直接训练自研基础模型，而是把已经完成的 FU13、C-MAPSS、baseline、TTM 和 C3.4 decision review 收束成可审查证据链。

短期重点是 C3.4 / C3.5 gate。若 C3.4 仍为 `hold_candidate_expansion_pending_ttm_local_evidence`，下一步先运行或复核 C3.3 explicit local TTM evidence；若 C3.4 记录 `blocked_candidate_expansion_due_to_ttm_evidence_gap`，下一步先修 TTM dependency/cache/shape/runtime blocker；只有当 C3.4 达到 `candidate_expansion_design_ready` 后，才进入 C3.5 `single second forecasting candidate design`。C3.5 仍然只设计一个 forecasting 候选，不执行多模型竞赛，不生成 leaderboard。

中期重点从 forecasting-only 转向多任务证据：补齐 `E2 representation`、`E3 imputation/reconstruction`、weak-label candidate signal review 和 `E5 patent effect`。这些任务用于判断模型是否支持设备状态理解、候选异常信号和论文/专利技术效果样例，不能写成生产告警、RUL 精确估计或自动维修建议。

后期形成 C -> B decision review。只有当开源模型和工程 baseline 在 representation / imputation / weak-label 任务上存在稳定缺口，并且结构感知输入、阶段编码、多任务头或弱标签目标有明确实验必要性时，才进入 `go_to_b_minimal_prototype`；否则默认选择 `stay_in_c_adaptation`、`knowledge_only_consolidation` 或 `no_go_hold`。

本路线的设计记录见 [C Stage Post-C3.4 Roadmap Design](docs/superpowers/specs/2026-06-26-c-stage-post-c34-roadmap-design.md)。无论进入哪个后续阶段，都继续保持 C-MAPSS RUL baseline-only、RUL 与 forecasting 指标分开解释、不直接训练自研基础模型、不提交 raw / zip / parquet / cache / generated report。
```

- [ ] **Step 2: Run README roadmap test**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_readme_documents_post_c34_c_stage_roadmap -q
```

Expected: README roadmap test passes.

- [ ] **Step 3: Commit README update together with roadmap tests**

```bash
git add README.md tests/test_experiment_scaffold.py
git commit -m "docs: add post c34 roadmap to readme"
```

## Task 3: Update Details Ledger

**Files:**
- Modify: `details.md`
- Test: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Add details roadmap ledger test**

Add this test near `test_details_records_c34_completion_and_next_step`:

```python
def test_details_records_post_c34_roadmap_and_preserves_ledger_shape():
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "更新日期：2026-06-26" in details
    assert "post-C3.4 C-stage roadmap documented" in details
    assert "| 2026-06-26 |" in details
    assert "C3.4 / C3.5 gate" in details
    assert "single second forecasting candidate design" in details
    assert "E2 representation" in details
    assert "E3 imputation/reconstruction" in details
    assert "C -> B decision review" in details
    assert "go_to_b_minimal_prototype" in details
    assert "stay_in_c_adaptation" in details
    assert "knowledge_only_consolidation" in details
    assert "no_go_hold" in details
    assert details.count("\n## ") == 3
```

- [ ] **Step 2: Run details test to verify it fails**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_details_records_post_c34_roadmap_and_preserves_ledger_shape -q
```

Expected: the test fails because details has not yet been updated.

- [ ] **Step 3: Update date and current phase**

Change:

```markdown
更新日期：2026-06-23
```

to:

```markdown
更新日期：2026-06-26
```

Change the current phase sentence to include:

```markdown
项目当前处于 **C3.4 open model expansion decision review implemented; post-C3.4 C-stage roadmap documented** 阶段。
```

- [ ] **Step 4: Add daily update row**

Add a new first row under `## 2. 每日更新`:

```markdown
| 2026-06-26 | 完成 post-C3.4 C-stage roadmap documented：把后续路线写入 README，明确论文/专利证据优先、工程样板承接、模型原型 gate 后置；保持 C3.4 / C3.5 gate，只有 C3.4 达到 `candidate_expansion_design_ready` 后才进入 C3.5 `single second forecasting candidate design`；中期转向 `E2 representation`、`E3 imputation/reconstruction`、weak-label candidate signal review 和 `E5 patent effect`，后期形成 C -> B decision review，默认决策包括 `go_to_b_minimal_prototype`、`stay_in_c_adaptation`、`knowledge_only_consolidation` 和 `no_go_hold`。 |
```

- [ ] **Step 5: Replace next-step plan**

Replace `## 3. 下一步计划` content with a concise gate-based plan:

```markdown
下一步主线改为 post-C3.4 C-stage roadmap：先守住 C3.4 / C3.5 gate，再从 forecasting-only 转向多任务证据，最后形成 C -> B decision review。目标仍是补充可复核证据，不是扩大 open model 竞赛、直接训练自研模型或生成跨任务 leaderboard。

具体计划如下：

1. C3.4 evidence path：如果 C3.4 仍为 default / hold，则先运行或复核 C3.3 explicit local TTM evidence；如果 C3.4 记录 blocker，则先修 TTM dependency/cache/shape/runtime gap。
2. C3.5 single second forecasting candidate design：只有 C3.4 达到 `candidate_expansion_design_ready` 后才进入；仍然只设计一个 forecasting 候选，不做多模型竞赛，不生成 leaderboard。
3. E2 / E3 多任务证据：补齐 `E2 representation` 和 `E3 imputation/reconstruction`，明确 stage、quality_flag、failure_proxy、mask policy、输入排除和 split/leakage 边界。
4. Weak-label 与 E5 patent effect：把 residual、reconstruction error、trend/spike candidate 和专家复核入口连接起来，并沉淀 P1-P5 的最小技术效果样例。
5. C -> B decision review：根据证据选择 `go_to_b_minimal_prototype`、`stay_in_c_adaptation`、`knowledge_only_consolidation` 或 `no_go_hold`；只有在 representation / imputation / weak-label 任务上存在稳定缺口时，才进入 B minimal prototype。
6. 持续保留边界：C-MAPSS RUL baseline-only，RUL metrics 和 forecasting metrics separated；默认不下载公开数据、不提交 raw / zip / parquet / cache / report、不运行训练；任何 raw、权重、cache、联网执行都必须使用 explicit local opt-in 配置。
7. 继续维护文档分工：README 负责项目定位、快速开始、标准命令、安全边界和后续路线；`details.md` 只维护当前阶段、每日更新和下一步台账；阶段解释和执行细节优先写入对应 spec / plan / report。
```

- [ ] **Step 6: Run details test and scaffold docs tests**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_details_records_post_c34_roadmap_and_preserves_ledger_shape tests/test_experiment_scaffold.py::test_details_records_c34_completion_and_next_step tests/test_experiment_scaffold.py::test_c32_cross_dataset_evaluation_workflow_is_documented -q
```

Expected: selected details tests pass.

- [ ] **Step 7: Commit details update together with details test**

```bash
git add details.md tests/test_experiment_scaffold.py
git commit -m "docs: update post c34 roadmap ledger"
```

## Task 4: Final Verification and Branch Readiness

**Files:**
- Verify: all changed files

- [ ] **Step 1: Run documentation test module**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py -q
```

Expected: pass.

- [ ] **Step 2: Run full suite**

Run:

```bash
uv run python -m pytest -q
```

Expected: pass, with the existing skipped count acceptable.

- [ ] **Step 3: Check formatting and git status**

Run:

```bash
git diff --check
git status --short --branch
```

Expected: no whitespace errors; branch contains only intended committed changes.

- [ ] **Step 4: Prepare PR summary**

Summarize:

- Referenced existing post-C3.4 roadmap spec.
- Added README后续发展路线.
- Updated details ledger and next plan.
- Added documentation tests.
- Verification commands and results.
