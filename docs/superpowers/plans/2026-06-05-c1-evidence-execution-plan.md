# C1 Evidence Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the C1 evidence execution framework, run E1-E3 through a unified C-stage report path, and document the project-level transition toward open-source model evaluation, dataset organization, and conditional self-developed model preparation.

**Architecture:** Add a narrow C1 execution layer under `b08_model_core.experiments` that reads the existing C0 contract plus a new C1 execution config, creates evidence specs, runs E1/E2/E3 with small task-specific functions, records structured model/evidence statuses, and renders one Markdown report. Keep this as a bounded evidence framework, not a generic experiment platform. Update `README.md` and `details.md` so future work does not drift: C1 is the front-half evaluation system preparation; C2 is systematic open-source model evaluation plus open dataset organization; B remains conditional self-developed model preparation.

**Tech Stack:** Python 3.11, pandas, numpy, PyYAML, pytest, existing `b08_model_core` modules, Markdown docs.

---

## Scope Guard

This plan implements the approved spec:

`docs/superpowers/specs/2026-06-05-c1-evidence-execution-design.md`

It must not implement public dataset downloads, production alarms, RUL claims, automatic maintenance recommendations, or B-stage self-developed model training. It must not expand the document system beyond one implementation plan and the required README/details updates.

Spec review notes to carry into implementation:

- Define evidence-level statuses explicitly.
- Preserve C0 `data_label_audit` in the C1 result/report path.

## File Structure

Create:

- `configs/c_stage_c1_execution.yaml`
  - C1 execution defaults. References C0 contract, FU13 dataset/config paths, E1-E3 enabled evidence, model switches, output path, strictness, and no-download policy.

- `src/b08_model_core/experiments/c1_evidence.py`
  - C1 config loader, registry, evidence/result dataclasses, status enums, runner functions, E2/E3 helper functions, report renderer.
  - Keep implementation in one focused module for C1. Split later only if it grows beyond this stage.

- `tests/test_c1_evidence.py`
  - TDD tests for config inheritance, registry validation, result/report schema, E2 input-exclusion note, E3 deterministic mask, candidate model failure states, and runner/report behavior.

Modify:

- `src/b08_model_core/cli.py`
  - Add `uv run b08-model-core experiment c-stage-c1 --config ... --output ...`.

- `README.md`
  - Add a short C1/C2/B transition note and command entry. Keep existing default workflow intact.

- `details.md`
  - Add a 2026-06-05 stage ledger row and update current-stage/next-work wording so future work is anchored around C1 evidence preparation, C2 open-source model evaluation, open dataset organization, and conditional B-stage self-developed model preparation.

Do not modify:

- `docs/index.html`
- `docs/research/**`
- Historical archive docs
- `data/**`
- `hf_cache/**`

## Evidence-Level Statuses

C1 evidence results use:

| status | meaning |
| --- | --- |
| `passed` | Evidence ran and has usable baseline or candidate metrics for the configured task. |
| `failed` | Evidence could not produce its required baseline/result path. |
| `needs_review` | Evidence ran but interpretation, class balance, mask policy, split, or candidate result needs human review. |
| `planned_not_executed` | Evidence exists in C0 but is intentionally not executed in C1, e.g. E4/E5. |

Model results use the model statuses from the spec:

`available_and_ran`, `missing_dependency`, `missing_or_blocked_weights`, `unsupported_task`, `unsupported_window_shape`, `runtime_failed`, `skipped_by_config`, `planned_not_executed`.

## Task 1: Create C1 Config And Registry Tests

**Files:**

- Create: `tests/test_c1_evidence.py`
- Create later: `configs/c_stage_c1_execution.yaml`
- Create later: `src/b08_model_core/experiments/c1_evidence.py`

- [ ] **Step 1: Write failing tests for config loading and registry inheritance**

Add tests that import these future APIs:

```python
from pathlib import Path

import pytest

from b08_model_core.experiments.c1_evidence import (
    C1EvidenceConfigError,
    EvidenceStatus,
    load_c1_execution_config,
    build_c1_registry,
)


def test_c1_execution_config_references_c0_contract():
    config = load_c1_execution_config("configs/c_stage_c1_execution.yaml")
    assert config.stage == "C1_evidence_execution"
    assert config.contract_path == Path("configs/c_stage_minimum_evidence.yaml")
    assert config.enabled_evidence == [
        "E1_forecasting_residual",
        "E2_representation",
        "E3_imputation",
    ]
    assert config.allow_download is False


def test_c1_registry_inherits_contract_fields_and_preserves_e4_e5():
    config = load_c1_execution_config("configs/c_stage_c1_execution.yaml")
    registry = build_c1_registry(config)
    e1 = registry.by_evidence_id["E1_forecasting_residual"]
    assert e1.experiment_id == "c0_fu13_forecast_residual_v1"
    assert e1.data_label_audit["source_status"]
    assert e1.invalid_claims
    assert registry.execution_status["E4_open_data_pm"] == EvidenceStatus.PLANNED_NOT_EXECUTED
    assert registry.execution_status["E5_patent_effect"] == EvidenceStatus.PLANNED_NOT_EXECUTED


def test_c1_registry_rejects_unknown_enabled_evidence(tmp_path):
    config = load_c1_execution_config("configs/c_stage_c1_execution.yaml")
    config.enabled_evidence = ["E99_unknown"]
    with pytest.raises(C1EvidenceConfigError, match="unknown enabled evidence"):
        build_c1_registry(config)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c1_evidence.py -q
```

Expected: FAIL because `b08_model_core.experiments.c1_evidence` does not exist.

- [ ] **Step 3: Create minimal C1 config and registry implementation**

Create `configs/c_stage_c1_execution.yaml` with relative paths only:

```yaml
stage: C1_evidence_execution
contract_path: configs/c_stage_minimum_evidence.yaml
dataset:
  fu13_observations: data/processed/fu13_real_observations.parquet
  fu13_config: configs/fu13_real_data_schema.yaml
  boundary: internal_fu13_no_raw_data_committed
enabled_evidence:
  - E1_forecasting_residual
  - E2_representation
  - E3_imputation
window:
  window_mode: cross-stage
  context_length: 90
  prediction_length: 16
  max_windows: 40
models:
  baseline:
    enabled: true
  ttm:
    enabled: true
    model_cache_dir: hf_cache
    allow_download: false
  moment:
    enabled: true
  units:
    enabled: true
outputs:
  report: reports/c_stage_c1_evidence_report.md
execution_policy:
  strict_model_success: false
  no_network_by_default: true
  record_failure: true
  do_not_over_claim: true
```

Create `src/b08_model_core/experiments/c1_evidence.py` with:

- `EvidenceStatus` enum.
- `ModelExecutionStatus` enum.
- `C1ExecutionConfig` dataclass.
- `C1EvidenceSpec` dataclass.
- `C1EvidenceRegistry` dataclass.
- `load_c1_execution_config(path)`.
- `build_c1_registry(config)`.

Use `load_and_validate_c_stage_contract` from `c_stage_contract.py`.

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
uv run python -m pytest tests/test_c1_evidence.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add configs/c_stage_c1_execution.yaml src/b08_model_core/experiments/c1_evidence.py tests/test_c1_evidence.py
git commit -m "feat: add c1 evidence registry"
```

## Task 2: Add Result Schema, Report Renderer, And Status Coverage

**Files:**

- Modify: `src/b08_model_core/experiments/c1_evidence.py`
- Modify: `tests/test_c1_evidence.py`

- [ ] **Step 1: Write failing tests for result schema and report renderer**

Add tests:

```python
from b08_model_core.experiments.c1_evidence import (
    C1EvidenceResult,
    C1ModelResult,
    EvidenceStatus,
    ModelExecutionStatus,
    render_c1_evidence_report,
)


def test_c1_report_contains_audit_invalid_claims_failures_and_decision_gate():
    result = C1EvidenceResult(
        evidence_id="E2_representation",
        experiment_id="c0_fu13_representation_probe_v1",
        task_id="fu13_representation_probe_v1",
        status=EvidenceStatus.NEEDS_REVIEW,
        dataset_boundary="internal_fu13_no_raw_data_committed",
        split_policy="time_batch_or_run_split_to_define",
        data_label_audit={"source_status": "internal_source_record_required"},
        model_results=[
            C1ModelResult(
                model_name="MOMENT",
                status=ModelExecutionStatus.MISSING_DEPENDENCY,
                reason="optional MOMENT dependency is not installed",
            )
        ],
        primary_metrics={"macro_F1": None},
        failure_reasons=["candidate model unavailable"],
        artifact_outputs=["representation_probe_report"],
        invalid_claims=["不得解释为生产告警"],
        decision_gate_notes=["needs MOMENT/UniTS verification"],
    )
    text = render_c1_evidence_report([result], planned_not_executed=["E4_open_data_pm"])
    assert "E2_representation" in text
    assert "missing_dependency" in text
    assert "data_label_audit" in text
    assert "不得解释为生产告警" in text
    assert "CT4 Decision Gate Draft" in text
    assert "E4_open_data_pm" in text
    assert "planned_not_executed" in text
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run python -m pytest tests/test_c1_evidence.py::test_c1_report_contains_audit_invalid_claims_failures_and_decision_gate -q
```

Expected: FAIL because result/report APIs do not exist.

- [ ] **Step 3: Implement result dataclasses and renderer**

Add:

- `C1ModelResult`
- `C1EvidenceResult`
- `render_c1_evidence_report(results, planned_not_executed=())`

The report must include metadata-like sections, status table, per-evidence sections, `data_label_audit`, failure reasons, invalid claims, and CT4 draft notes.

- [ ] **Step 4: Run targeted and existing C1 tests**

Run:

```bash
uv run python -m pytest tests/test_c1_evidence.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/b08_model_core/experiments/c1_evidence.py tests/test_c1_evidence.py
git commit -m "feat: add c1 evidence report schema"
```

## Task 3: Add E2/E3 Baseline Helpers

**Files:**

- Modify: `src/b08_model_core/experiments/c1_evidence.py`
- Modify: `tests/test_c1_evidence.py`

- [ ] **Step 1: Write failing tests for deterministic mask and statistical embedding**

Add tests using tiny synthetic `ModelWindow` objects:

```python
import numpy as np

from b08_model_core.experiments.c1_evidence import (
    apply_deterministic_mask,
    simple_statistical_embedding,
    reconstruction_metrics,
)


def test_deterministic_mask_is_reproducible():
    values = np.arange(24, dtype=float).reshape(6, 4)
    masked_a, mask_a = apply_deterministic_mask(values, mask_ratio=0.25, seed=7)
    masked_b, mask_b = apply_deterministic_mask(values, mask_ratio=0.25, seed=7)
    assert np.array_equal(mask_a, mask_b)
    assert np.array_equal(masked_a, masked_b)
    assert mask_a.sum() == 6


def test_statistical_embedding_summarizes_window_shape():
    values = np.array([[1.0, 2.0], [3.0, 6.0]])
    embedding = simple_statistical_embedding(values)
    assert embedding["mean_sensor_0"] == 2.0
    assert embedding["std_sensor_1"] == 2.0


def test_reconstruction_metrics_reports_masked_error_only():
    truth = np.array([[1.0, 2.0], [3.0, 4.0]])
    reconstructed = np.array([[1.0, 0.0], [0.0, 4.0]])
    mask = np.array([[False, True], [True, False]])
    metrics = reconstruction_metrics(truth, reconstructed, mask)
    assert metrics["mae"] == 2.5
    assert metrics["count"] == 2
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c1_evidence.py::test_deterministic_mask_is_reproducible tests/test_c1_evidence.py::test_statistical_embedding_summarizes_window_shape tests/test_c1_evidence.py::test_reconstruction_metrics_reports_masked_error_only -q
```

Expected: FAIL because helpers do not exist.

- [ ] **Step 3: Implement minimal helpers**

Implement:

- `apply_deterministic_mask(values, mask_ratio, seed)`
- `simple_statistical_embedding(values)`
- `reconstruction_metrics(truth, reconstructed, mask)`

Keep these simple and deterministic; no model dependency.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run python -m pytest tests/test_c1_evidence.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/b08_model_core/experiments/c1_evidence.py tests/test_c1_evidence.py
git commit -m "feat: add c1 representation and reconstruction helpers"
```

## Task 4: Add C1 Runner

**Files:**

- Modify: `src/b08_model_core/experiments/c1_evidence.py`
- Modify: `tests/test_c1_evidence.py`

- [ ] **Step 1: Write failing tests for runner output and E1 residual traceability**

Add fixture-building tests with a tiny parquet dataset. Test that:

- `run_c1_evidence(config)` returns E1, E2, E3 plus planned-not-executed E4/E5.
- E1 baseline result has forecasting metrics, residual summary, and top-k candidate examples.
- E1 top-k examples include `sensor_id`, `timestamp`, `stage`, `quality_policy`, `absolute_residual`, and `model_name`.
- E2 includes a statistical embedding baseline and input-exclusion note.
- E3 includes deterministic mask metrics.
- MOMENT/UniTS unavailable paths are recorded as `missing_dependency` or `unsupported_task`.

Add a test shaped like:

```python
def test_c1_runner_e1_outputs_residual_summary_and_traceable_topk(tmp_path):
    config = _write_c1_fixture_config(tmp_path, candidate_model_failures=True)
    results = run_c1_evidence(load_c1_execution_config(config))
    e1 = _result_by_id(results, "E1_forecasting_residual")
    assert e1.status == EvidenceStatus.PASSED
    assert e1.primary_metrics["mae"] is not None
    assert e1.artifact_outputs["residual_summary"]["abs_residual_p95"] is not None
    top_example = e1.artifact_outputs["top_k_candidate_examples"][0]
    assert {
        "sensor_id",
        "timestamp",
        "stage",
        "quality_policy",
        "absolute_residual",
        "model_name",
    }.issubset(top_example)
```

- [ ] **Step 2: Run runner tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c1_evidence.py -q
```

Expected: FAIL because `run_c1_evidence` does not exist.

- [ ] **Step 3: Implement runner**

Implement:

- `run_c1_evidence(config: C1ExecutionConfig) -> list[C1EvidenceResult]`
- Internal `_run_e1_forecasting`, `_run_e2_representation`, `_run_e3_imputation`
- Candidate model status checks for MOMENT and UniTS via their adapter builders or dependency checks.

Use existing `run_real_data_forecasting` for E1 baseline/TTM where feasible. For E2/E3, build windows via `build_model_windows`; use simple baselines first.

E1 residual output requirements:

- Use the selected baseline or candidate predictions to compute absolute residuals.
- Summarize residuals with at least mean, p95, max, and count.
- Emit top-k examples sorted by absolute residual.
- Each top-k row must include sensor id, target timestamp if available, stage if available, quality policy, model name, observed value, predicted value, and absolute residual.
- If timestamp/stage cannot be recovered from a window, write `not_available` rather than omitting the field.

- [ ] **Step 4: Run C1 tests**

Run:

```bash
uv run python -m pytest tests/test_c1_evidence.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add src/b08_model_core/experiments/c1_evidence.py tests/test_c1_evidence.py
git commit -m "feat: add c1 evidence runner"
```

## Task 5: Add CLI Command

**Files:**

- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_c1_evidence.py` or create `tests/test_cli_c1_evidence.py`

- [ ] **Step 1: Write failing CLI tests for report writing and exit-code contract**

Add tests that call:

```python
from b08_model_core.cli import main


def test_cli_c_stage_c1_writes_report(tmp_path):
    config = tmp_path / "c1.yaml"
    output = tmp_path / "report.md"
    # Write a minimal config pointing at a tiny parquet fixture.
    result = main(["experiment", "c-stage-c1", "--config", str(config), "--output", str(output)])
    assert result == 0
    assert output.exists()
    assert "C1 Evidence Report" in output.read_text(encoding="utf-8")


def test_cli_c_stage_c1_returns_nonzero_for_missing_config(tmp_path):
    result = main([
        "experiment",
        "c-stage-c1",
        "--config",
        str(tmp_path / "missing.yaml"),
        "--output",
        str(tmp_path / "report.md"),
    ])
    assert result == 1


def test_cli_c_stage_c1_returns_nonzero_for_missing_dataset(tmp_path):
    config = _write_c1_config_with_missing_dataset(tmp_path)
    result = main(["experiment", "c-stage-c1", "--config", str(config), "--output", str(tmp_path / "report.md")])
    assert result == 1


def test_cli_c_stage_c1_candidate_failure_is_reported_without_default_failure(tmp_path):
    config = _write_c1_fixture_config(tmp_path, candidate_model_failures=True, strict_model_success=False)
    output = tmp_path / "report.md"
    result = main(["experiment", "c-stage-c1", "--config", str(config), "--output", str(output)])
    assert result == 0
    text = output.read_text(encoding="utf-8")
    assert "missing_dependency" in text or "unsupported_task" in text
    assert "E1_forecasting_residual" in text
```

- [ ] **Step 2: Run CLI tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c1_evidence.py::test_cli_c_stage_c1_writes_report tests/test_c1_evidence.py::test_cli_c_stage_c1_returns_nonzero_for_missing_config tests/test_c1_evidence.py::test_cli_c_stage_c1_returns_nonzero_for_missing_dataset tests/test_c1_evidence.py::test_cli_c_stage_c1_candidate_failure_is_reported_without_default_failure -q
```

Expected: FAIL because CLI command is missing.

- [ ] **Step 3: Implement CLI command**

Add `experiment c-stage-c1` with:

- `--config`
- `--output`

Load config, override output path, run C1 evidence, render report, write output. Return nonzero for config/data/report failure; return zero when baseline path succeeds and candidate model failures are reportable.

Exit-code contract:

| Scenario | Exit |
| --- | --- |
| Missing/invalid config | `1` |
| Missing dataset or E1 baseline cannot run | `1` |
| E1 baseline succeeds and candidate model fails with `strict_model_success: false` | `0` |
| E1 baseline succeeds and candidate model fails with `strict_model_success: true` | `1` |
| E1/E2/E3 report generated with reportable candidate failures | Depends on `strict_model_success`, default `0` |

- [ ] **Step 4: Run CLI and C1 tests**

Run:

```bash
uv run python -m pytest tests/test_c1_evidence.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```bash
git add src/b08_model_core/cli.py tests/test_c1_evidence.py
git commit -m "feat: add c1 evidence cli"
```

## Task 6: Update README And details Stage Roadmap

**Files:**

- Modify: `README.md`
- Modify: `details.md`

- [ ] **Step 1: Update README**

Add a concise C1 section near “下一阶段研发路线”:

- C1 is the current front-half evaluation system preparation stage.
- C1 command and report path.
- C1 completes E1-E3 evidence execution and keeps E4/E5 as follow-up.
- After C1, C2 focuses on systematic open-source model evaluation.
- A key side branch is open ecosystem dataset organization and schema mapping.
- B remains conditional self-developed model preparation after C1/C2 evidence.

- [ ] **Step 2: Update details**

Add a 2026-06-05 ledger row and update current conclusion:

- C1 spec and execution plan are accepted.
- Stage goal is to finish the evaluation framework and evidence preparation.
- Next substantial work is open-source model evaluation, open dataset organization, and conditional self-developed model preparation.
- This is not a prompt to keep debating roadmap; it is a concrete task track.

- [ ] **Step 3: Check wording does not over-claim**

Run:

```bash
rg -n "生产告警|RUL|自研|开源模型|数据集|C1|C2" README.md details.md
```

Expected: C1/C2/B language is explicit and does not claim production capability or self-developed training success.

- [ ] **Step 4: Commit Task 6**

```bash
git add README.md details.md
git commit -m "docs: clarify c1 roadmap and next work"
```

## Task 7: Full Verification

**Files:**

- Read/check only unless fixes are needed.

- [ ] **Step 1: Run full tests**

```bash
uv run python -m pytest -q
```

Expected: PASS.

- [ ] **Step 2: Run default C1 CLI smoke if fixture data exists**

If `data/processed/fu13_real_observations.parquet` exists locally, run:

```bash
uv run b08-model-core experiment c-stage-c1 \
  --config configs/c_stage_c1_execution.yaml \
  --output reports/c_stage_c1_evidence_report.md
```

Expected: report written. If TTM/MOMENT/UniTS are unavailable, report structured statuses; do not treat that as failure unless E1 baseline fails.

If the local FU13 parquet does not exist, record that smoke was skipped because private data is absent.

- [ ] **Step 3: Inspect report terms**

If report exists:

```bash
rg -n "C1 Evidence Report|E1_forecasting_residual|E2_representation|E3_imputation|planned_not_executed|data_label_audit|CT4|不得解释" reports/c_stage_c1_evidence_report.md
```

Expected: all required terms are present.

- [ ] **Step 4: Inspect git status**

```bash
git status --short
```

Expected: clean, except ignored local reports if generated.

- [ ] **Step 5: Final commit if verification fixes were required**

Only if Task 7 required fixes:

```bash
git add <changed-files>
git commit -m "fix: complete c1 evidence verification"
```

## Completion Criteria

- Plan document exists and has been reviewed.
- `configs/c_stage_c1_execution.yaml` exists.
- `src/b08_model_core/experiments/c1_evidence.py` implements C1 registry, statuses, result schema, helper baselines, runner, and report renderer.
- CLI command `experiment c-stage-c1` writes a C1 Markdown report.
- README/details clearly state C1, C2, open dataset organization, and conditional B-stage self-developed model preparation.
- Full tests pass.
- Worktree is clean after commits, aside from ignored local artifacts.
