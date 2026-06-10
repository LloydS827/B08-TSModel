# C3.1 Default Preflight Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the C3.1 default preflight report and project docs decision-grade after the NASA PCoE #6 source/license review, while keeping local raw mapping and C3.2 blocked.

**Architecture:** Keep the existing C3.1 runner and CLI shape. Add source/license snapshots to the run result so the report can render config evidence without network access, add a tracked source/license review doc, and update README/details to reflect the reviewed but still blocked state.

**Tech Stack:** Python 3.11+, dataclasses, YAML config, existing C3.1 experiment module, pytest, uv, Markdown docs.

---

## File Structure

- Modify: `configs/c_stage_c31_cmapss_minimal_ingestion.yaml`
  - Set `source.source_status` to `verified` after official PCoE source and S3 target calibration.
  - `verified` means source identity and download-target identity only; it does not approve license, redistribution, local raw use, training, or evaluation.
  - Keep all license review fields as `needs_review`.
  - Keep all safety flags false.

- Modify: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
  - Add `source` and `license_review` snapshots to `C31CmapssRunResult`.
  - Populate those snapshots in every return path.
  - Render source URL, download target, citation, license status, redistribution status, training-use status, and local raw opt-in decision.

- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`
  - Add failing tests for source verified / license blocked config state.
  - Add failing tests for decision-grade report content.
  - Update existing tests that expected default `blocked_by_source_review`.

- Modify: `tests/test_experiment_scaffold.py`
  - Add README/details regression checks for the source/license review doc and local raw blocked conclusion.

- Create: `docs/reviews/2026-06-10-c31-cmapss-source-license-review.md`
  - Record official source, download target HEAD result, citation, calibration source caveat, and decision.

- Modify: `README.md`
  - Link the source/license review doc from the C3.1 section.
  - Record that source/download target are calibrated but local raw opt-in and C3.2 remain blocked.

- Modify: `details.md`
  - Update current stage, daily ledger, and next plan.

---

## Task 1: TDD For Reviewed Source/License State

**Files:**
- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`
- Modify: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Add failing config and report tests**

In `tests/test_c31_cmapss_minimal_ingestion.py`, update `test_c31_default_config_is_offline_and_lists_classic_cmapss_files`:

```python
assert config.source.source_status == "verified"
assert config.license_review.license_status == "needs_review"
assert config.license_review.redistribution_status == "needs_review"
assert config.license_review.training_use_status == "needs_review"
```

Add a focused report test:

```python
def test_c31_report_renders_source_license_decision_details():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)
    result = run_c31_cmapss_minimal_ingestion(config, config_path=_DEFAULT_CONFIG)

    text = render_c31_cmapss_report(result)

    assert "NASA PCoE #6 Turbofan Engine Degradation Simulation Data Set" in text
    assert "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/" in text
    assert "https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip" in text
    assert "Saxena, A., Goebel, K., Simon, D., and Eklund, N." in text
    assert "| license_decision | needs_review |" in text
    assert "| redistribution_status | needs_review |" in text
    assert "| training_use_status | needs_review |" in text
    assert "Local raw opt-in: blocked until license, redistribution, and training-use review are resolved." in text
```

Update `test_c31_source_license_block_does_not_inspect_raw_dir_when_local_raw_enabled` so it only expects `blocked_by_license_review`, not `blocked_by_source_review`.

Update any test that specifically exercises unapproved source behavior, including `test_c31_blocks_unapproved_source_even_when_license_is_schema_approved`, so the modified config explicitly sets:

```python
data["source"]["source_status"] = "needs_review"
```

Do not rely on the default config for unapproved source scenarios after this plan changes the default source state to `verified`.

- [ ] **Step 2: Add failing docs regression tests**

In `tests/test_experiment_scaffold.py`, extend `test_c31_cmapss_minimal_ingestion_workflow_is_documented`:

```python
assert "docs/reviews/2026-06-10-c31-cmapss-source-license-review.md" in c31_section
assert "local raw opt-in" in c31_section
assert "blocked" in c31_section
assert "source/license review" in details
assert "C3.2" in details
```

- [ ] **Step 3: Run targeted tests and confirm RED**

Run:

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py::test_c31_default_config_is_offline_and_lists_classic_cmapss_files tests/test_c31_cmapss_minimal_ingestion.py::test_c31_report_renders_source_license_decision_details tests/test_experiment_scaffold.py::test_c31_cmapss_minimal_ingestion_workflow_is_documented -q
```

Expected: FAIL because config/report/docs do not yet contain the reviewed decision details.

---

## Task 2: Implement Report And Config Minimal Change

**Files:**
- Modify: `configs/c_stage_c31_cmapss_minimal_ingestion.yaml`
- Modify: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`

- [ ] **Step 1: Update default config**

Change:

```yaml
source_status: needs_review
```

to:

```yaml
source_status: verified
```

Do not change any safety flag or license review field.

- [ ] **Step 2: Add source/license snapshots to run result**

In `C31CmapssRunResult`, add:

```python
source: C31Source | None = None
license_review: C31LicenseReview | None = None
```

In every `C31CmapssRunResult(...)` return inside `run_c31_cmapss_minimal_ingestion`, pass:

```python
source=config.source,
license_review=config.license_review,
```

- [ ] **Step 3: Render source/license detail in report**

Inside `render_c31_cmapss_report`, after `## Source And License Preflight`, add a table that includes source and license details when available:

```python
source = result.source
license_review = result.license_review
```

Render rows for:

- `primary_source`
- `primary_source_url`
- `download_target_url`
- `source_status`
- `citation_required`
- `citation`
- `license_decision`
- `license_status`
- `redistribution_status`
- `training_use_status`

Then add:

```markdown
Local raw opt-in: blocked until license, redistribution, and training-use review are resolved.
```

Keep the existing blocked flag table or adapt it without removing the section names tested by existing tests.

- [ ] **Step 4: Run targeted tests and confirm GREEN**

Run:

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py tests/test_experiment_scaffold.py::test_c31_cmapss_minimal_ingestion_workflow_is_documented -q
```

Expected: PASS.

---

## Task 3: Source/License Review Doc And Project Docs

**Files:**
- Create: `docs/reviews/2026-06-10-c31-cmapss-source-license-review.md`
- Modify: `README.md`
- Modify: `details.md`

- [ ] **Step 1: Create the review doc**

Create `docs/reviews/2026-06-10-c31-cmapss-source-license-review.md` with these sections:

```markdown
# C3.1 C-MAPSS Source And License Review

## Review Scope

## Official Source Calibration

## License And Use Boundary

## Local Raw Opt-In Decision

## C3.2 Decision

## Next Options
```

Required conclusions:

- NASA PCoE #6 source and download target are calibrated.
- S3 target returned `200 OK`, `Content-Type: application/zip`, and content length `12429152` during manual review. This is recorded review evidence only; the C3.1 CLI must not perform runtime network checks in the default path.
- NASA Open Data Portal C-MAPSS page is calibration only and reports `License not specified` plus unavailable / non-public signals.
- Redistribution and research training/evaluation use remain unresolved.
- Do not allow local raw opt-in yet.
- C3.2 remains No-Go.

- [ ] **Step 2: Update README C3.1 section**

Add one short paragraph after the default safety flags:

```markdown
2026-06-10 source/license review 见 [C3.1 C-MAPSS Source And License Review](docs/reviews/2026-06-10-c31-cmapss-source-license-review.md)。当前结论是 NASA PCoE #6 source 和 download target 已完成校准，但 license / redistribution / research training-evaluation use 仍未明确；local raw opt-in 和 C3.2 继续 blocked。
```

- [ ] **Step 3: Update details ledger and next plan**

In `details.md`:

- Update current stage to say default preflight review has been executed and local raw remains blocked.
- Add or update the 2026-06-10 daily row with the preflight review and report enhancement.
- Update next plan so the first next action is not “run default preflight” anymore; it should be either get explicit C-MAPSS use authorization or choose the next C3 registry dataset.

- [ ] **Step 4: Run docs regression tests**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c31_cmapss_minimal_ingestion_workflow_is_documented -q
```

Expected: PASS.

---

## Task 4: Verification And Local Report Review

**Files:**
- No additional source files unless verification reveals a scoped issue.
- Generated report remains ignored: `reports/c_stage_c31_cmapss_minimal_ingestion.md`

- [ ] **Step 1: Run full test suite**

Run:

```bash
uv run python -m pytest -q
```

Expected: `390 passed, 1 skipped` or equivalent with no failures.

- [ ] **Step 2: Regenerate default C3.1 report**

Run:

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output reports/c_stage_c31_cmapss_minimal_ingestion.md
```

Expected: exit code 0. Report includes `Status: blocked`, source/license detail rows, and local raw opt-in blocked decision.

- [ ] **Step 3: Inspect git status for forbidden artifacts**

Run:

```bash
git status --short
git check-ignore -v reports/c_stage_c31_cmapss_minimal_ingestion.md data/public/cmapss/raw data/processed/cmapss hf_cache
```

Expected: only intended tracked docs/source/test/config changes are shown. Generated report and data/cache paths remain ignored.

- [ ] **Step 4: Commit**

Run:

```bash
git add configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py \
  tests/test_c31_cmapss_minimal_ingestion.py \
  tests/test_experiment_scaffold.py \
  docs/reviews/2026-06-10-c31-cmapss-source-license-review.md \
  docs/superpowers/specs/2026-06-10-c31-preflight-review-design.md \
  docs/superpowers/plans/2026-06-10-c31-preflight-review-plan.md \
  README.md details.md
git commit -m "docs: record c31 preflight review decision"
```

Expected: commit succeeds on `codex/c31-preflight-review`.
