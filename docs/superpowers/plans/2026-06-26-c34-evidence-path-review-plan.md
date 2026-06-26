# C3.4 Evidence Path Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tracked C3.4 evidence path review that records the current hold/blocker state, keeps C3.5 gated behind `candidate_expansion_design_ready`, and links the review from README/details.

**Architecture:** This is a documentation-and-test change. `docs/reviews/2026-06-26-c34-evidence-path-review.md` becomes the tracked evidence path record; `README.md` exposes it from the roadmap and document index; `details.md` updates the current ledger; `tests/test_experiment_scaffold.py` protects the evidence path wording. Existing C3.4 experiment code remains unchanged.

**Tech Stack:** Markdown, pytest, existing `uv` workflow.

---

## File Structure

- Create: `docs/reviews/2026-06-26-c34-evidence-path-review.md`
  - Records the reviewed C3.4 evidence path state.
  - Must state default hold, local example blocked, ready evidence absent, C3.5 blocked until ready.
- Modify: `README.md`
  - Add a route sentence/link in `## 后续发展路线`.
  - Add review link in `## 文档入口`.
- Modify: `details.md`
  - Update current stage, daily update, and next-step item 1.
  - Preserve exactly three top-level `##` sections.
- Modify: `tests/test_experiment_scaffold.py`
  - Add one focused doc test for the new review and README/details links.
- Verify: `tests/test_c34_open_model_expansion_decision_review.py`
  - Run existing C3.4 tests to confirm decision logic remains unchanged.

## Task 1: Evidence Path Review Test And Document

**Files:**
- Create: `docs/reviews/2026-06-26-c34-evidence-path-review.md`
- Modify: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Add failing documentation test**

Add this test near the existing C3.4/post-C3.4 documentation tests:

```python
def test_c34_evidence_path_review_is_documented_and_gated():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")
    review_path = REPO_ROOT / "docs/reviews/2026-06-26-c34-evidence-path-review.md"

    assert review_path.exists()
    review = review_path.read_text(encoding="utf-8")

    assert "C3.4 Evidence Path Review" in review
    assert "hold_candidate_expansion_pending_ttm_local_evidence" in review
    assert "blocked_candidate_expansion_due_to_ttm_evidence_gap" in review
    assert "local_execution_ttm_forecasting_ready" in review
    assert "candidate_expansion_design_ready" in review
    assert "C3.5 blocked" in review
    assert "single second forecasting candidate design" in review
    assert "不生成 leaderboard" in review
    assert "不运行第二候选 open model" in review
    assert "不提交 generated reports" in review
    assert "docs/reviews/2026-06-26-c34-evidence-path-review.md" in readme
    assert "docs/reviews/2026-06-26-c34-evidence-path-review.md" in details
    assert details.count("\n## ") == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c34_evidence_path_review_is_documented_and_gated -q
```

Expected: FAIL because the review document and links do not exist yet.

- [ ] **Step 3: Create review document**

Create `docs/reviews/2026-06-26-c34-evidence-path-review.md`:

```markdown
# C3.4 Evidence Path Review

Date: 2026-06-26

## Scope

This review records the current C3.4 evidence path status. It is review-only: it does not run TTM, does not inspect model cache, does not read raw/parquet data, does not run a second open model, does not train, and does not submit generated reports.

## Inputs Reviewed

- C3.3 default contract: `contract_ready_single_candidate_local_execution_blocked`
- C3.4 default config: `configs/c_stage_c34_open_model_expansion_decision_review.yaml`
- C3.4 local review example: `configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml`
- Post-C3.4 roadmap: `docs/superpowers/specs/2026-06-26-c-stage-post-c34-roadmap-design.md`

## Current Decision

| Path | Reviewed status | C3.4 decision | Meaning |
| --- | --- | --- | --- |
| Default repository evidence | `contract_ready_single_candidate_local_execution_blocked` | `hold_candidate_expansion_pending_ttm_local_evidence` | C3.4 is runnable, but C3.3 local TTM evidence has not been reviewed as ready. |
| Local review example | `local_execution_ttm_missing_or_blocked_weights` | `blocked_candidate_expansion_due_to_ttm_evidence_gap` | The example documents a cache/weight blocker, not C3.5 readiness. |

Current tracked conclusion: there is no reviewed C3.3 TTM local evidence in the repository that reaches `local_execution_ttm_forecasting_ready` with complete adapter evidence. Therefore C3.5 blocked until C3.4 reaches `candidate_expansion_design_ready`.

## Evidence Gap

To enter C3.5, a reviewed C3.3 explicit local TTM run must provide:

- `dependency_status`
- `weight_status`
- `adapter_status`
- `runtime_seconds`
- `input_shape`
- `output_shape`
- `actual_network_used`
- `download_allowed_not_verified`

The fields must be internally consistent with `local_execution_ttm_forecasting_ready`.

## Next Step

1. Run or review C3.3 explicit local TTM evidence only through the documented opt-in command.
2. Record the reviewed adapter evidence in a local C3.4 review config.
3. Run C3.4 review again.
4. Proceed to C3.5 `single second forecasting candidate design` only if the C3.4 decision is `candidate_expansion_design_ready`.

## Invalid Claims

- 不运行第二候选 open model。
- 不生成 leaderboard。
- 不把 C-MAPSS RUL 写成 open-model readiness。
- 不宣称生产告警、故障概率、RUL 精确估计或维修建议。
- 不提交 generated reports、raw、zip、parquet、cache 或模型权重。
```

- [ ] **Step 4: Run documentation test**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c34_evidence_path_review_is_documented_and_gated -q
```

Expected: FAIL only because README/details links are still missing.

## Task 2: README And Details Evidence Path Links

**Files:**
- Modify: `README.md`
- Modify: `details.md`
- Modify: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Update README roadmap**

In `## 后续发展路线`, after the paragraph that starts `短期重点是 C3.4 / C3.5 gate`, add:

```markdown
当前 C3.4 evidence path 的 tracked review 见 [C3.4 Evidence Path Review](docs/reviews/2026-06-26-c34-evidence-path-review.md)：默认仓库证据仍是 hold，本机 review example 是 blocker 示例，尚未进入 C3.5 ready。
```

- [ ] **Step 2: Update README document entry list**

In `## 文档入口`, add a bullet after the C3.4 spec/plan links:

```markdown
- [C3.4 evidence path review](docs/reviews/2026-06-26-c34-evidence-path-review.md)
```

- [ ] **Step 3: Update details current stage**

Change the current stage sentence to:

```markdown
项目当前处于 **C3.4 open model expansion decision review implemented; post-C3.4 C-stage roadmap documented; C3.4 evidence path reviewed** 阶段。
```

- [ ] **Step 4: Update details daily update**

Add a new first row for 2026-06-26. If an existing 2026-06-26 row already exists, replace it with this combined row rather than creating a duplicate:

```markdown
| 2026-06-26 | 完成 post-C3.4 C-stage roadmap documented，并补充 [C3.4 evidence path review](docs/reviews/2026-06-26-c34-evidence-path-review.md)：把后续路线写入 README，明确论文/专利证据优先、工程样板承接、模型原型 gate 后置；保持 C3.4 / C3.5 gate，当前 tracked review 结论是默认仓库证据仍为 `hold_candidate_expansion_pending_ttm_local_evidence`，本机 review example 为 `blocked_candidate_expansion_due_to_ttm_evidence_gap`，尚未达到 `candidate_expansion_design_ready`；中期转向 `E2 representation`、`E3 imputation/reconstruction`、weak-label candidate signal review 和 `E5 patent effect`，后期形成 C -> B decision review。 |
```

- [ ] **Step 5: Update details next-step item 1**

Replace item 1 in `## 3. 下一步计划` with:

```markdown
1. 补齐 C3.3 TTM local evidence / C3.4 evidence path：当前 tracked review 见 [C3.4 evidence path review](docs/reviews/2026-06-26-c34-evidence-path-review.md)，默认仓库证据仍为 hold，本机 review example 是 blocker；下一步先运行或复核 C3.3 explicit local TTM evidence，并用 C3.4 本机证据复核入口确认是否达到 `candidate_expansion_design_ready`。
```

- [ ] **Step 6: Run focused documentation tests**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c34_evidence_path_review_is_documented_and_gated tests/test_experiment_scaffold.py::test_readme_documents_post_c34_c_stage_roadmap tests/test_experiment_scaffold.py::test_details_records_post_c34_roadmap_and_preserves_ledger_shape -q
```

Expected: all selected tests pass. If an existing test expects the previous current-stage exact substring, update it conservatively so it still checks the previous phrase plus the new evidence path phrase.

## Task 3: Verification And Final Readiness

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run C3.4 tests**

Run:

```bash
uv run python -m pytest tests/test_c34_open_model_expansion_decision_review.py -q
```

Expected: pass. This confirms C3.4 decision logic was not changed.

- [ ] **Step 2: Run documentation scaffold tests**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py -q
```

Expected: pass.

- [ ] **Step 3: Run default C3.4 CLI smoke to a temporary output**

Run:

```bash
tmp_report="$(mktemp -t c34-review-XXXXXX.md)"
uv run b08-model-core experiment c-stage-c34 \
  --config configs/c_stage_c34_open_model_expansion_decision_review.yaml \
  --output "$tmp_report"
rg -n "hold_candidate_expansion_pending_ttm_local_evidence|No leaderboard" "$tmp_report"
rm -f "$tmp_report"
```

Expected: command exits 0, `rg` finds the hold status and no-leaderboard text, and no generated report remains in the repository. The tracked review document, not the default generated report, carries the explicit C3.5 blocked wording.

- [ ] **Step 4: Run full suite**

Run:

```bash
uv run python -m pytest -q
```

Expected: pass, with existing skipped count acceptable.

- [ ] **Step 5: Check whitespace and git status**

Run:

```bash
git diff --check
git status --short --branch
```

Expected: no whitespace errors; only intended files are changed.

- [ ] **Step 6: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-06-26-c34-evidence-path-review-design.md \
  docs/superpowers/plans/2026-06-26-c34-evidence-path-review-plan.md \
  docs/reviews/2026-06-26-c34-evidence-path-review.md \
  README.md details.md tests/test_experiment_scaffold.py
git commit -m "docs: add c34 evidence path review"
```

Expected: commit succeeds on branch `codex/c34-evidence-path`.
