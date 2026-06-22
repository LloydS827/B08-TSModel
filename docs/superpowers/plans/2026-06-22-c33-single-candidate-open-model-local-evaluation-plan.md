# C3.3 Single-Candidate Open Model Local Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add C3.3 as a default-safe, single-candidate open model local evaluation stage that validates TTM adapter/cache/dependency evidence on FU13-like forecasting only.

**Architecture:** Add a new C-stage experiment module instead of changing C3.2 semantics. The default C3.3 config renders a contract-only report without importing adapters or touching cache; the explicit local config reruns FU13-like baseline reference and invokes one injectable TTM adapter path, mapping adapter outcomes to structured C3.3 statuses.

**Tech Stack:** Python dataclasses, YAML config, existing FU13-like simulation/window/baseline/metric helpers, existing open model adapter dataclasses, pytest, Markdown reports, existing CLI experiment scaffold.

---

## File Structure

- Create `configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml`
  - Default contract-only config for C3.3.
- Create `configs/local/c_stage_c33_ttm_fu13_like_local_evaluation.example.yaml`
  - Explicit local opt-in example for TTM on FU13-like forecasting.
- Create `src/b08_model_core/experiments/c33_single_candidate_open_model_local_evaluation.py`
  - Config loader, validation, runner, status mapping, report renderer.
- Modify `src/b08_model_core/cli.py`
  - Add `experiment c-stage-c33`.
- Create `tests/test_c33_single_candidate_open_model_local_evaluation.py`
  - Config, runner, fake adapter, report, and CLI tests.
- Modify `tests/test_experiment_scaffold.py`
  - Add C3.3 docs/CLI scaffold assertions if the file already checks staged commands.
- Modify `README.md`
  - Add C3.3 command, local opt-in command, and safety boundary.
- Modify `details.md`
  - Update current stage, daily update, and next plan.

---

## Task 1: C3.3 Config Contract And Report

**Files:**
- Create: `configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml`
- Create: `configs/local/c_stage_c33_ttm_fu13_like_local_evaluation.example.yaml`
- Create: `src/b08_model_core/experiments/c33_single_candidate_open_model_local_evaluation.py`
- Test: `tests/test_c33_single_candidate_open_model_local_evaluation.py`

- [ ] **Step 1: Write failing config tests**

Create `tests/test_c33_single_candidate_open_model_local_evaluation.py` with tests that import:

```python
from pathlib import Path

import pytest
import yaml

from b08_model_core.experiments.c33_single_candidate_open_model_local_evaluation import (
    C33ConfigError,
    load_c33_config,
    render_c33_report,
    run_c33_single_candidate_open_model_local_evaluation,
)
```

Add constants:

```python
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG = _REPO_ROOT / "configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml"
_LOCAL_CONFIG = _REPO_ROOT / "configs/local/c_stage_c33_ttm_fu13_like_local_evaluation.example.yaml"
```

Add tests:

```python
def test_c33_default_config_is_contract_only_and_offline_safe():
    config = load_c33_config(_DEFAULT_CONFIG)

    assert config.stage == "C3_3_single_candidate_open_model_local_evaluation"
    assert config.safety_policy.allow_network is False
    assert config.safety_policy.allow_download is False
    assert config.safety_policy.allow_model_cache is False
    assert config.safety_policy.allow_local_execution is False
    assert config.safety_policy.allow_training is False
    assert config.safety_policy.allow_write_processed is False
    assert config.candidate.model_id == "ttm"
    assert config.candidate.task_id == "forecasting_residual"
    assert config.candidate.dataset_view == "fu13_like_simulated_forecasting"
    assert config.metric_contract.leaderboard_allowed is False
    assert config.local_execution is None


def test_c33_local_config_is_explicit_opt_in_cache_first():
    config = load_c33_config(_LOCAL_CONFIG)

    assert config.safety_policy.allow_local_execution is True
    assert config.safety_policy.allow_model_cache is True
    assert config.safety_policy.allow_network is False
    assert config.safety_policy.allow_download is False
    assert config.safety_policy.allow_training is False
    assert config.safety_policy.allow_write_processed is False
    assert config.local_execution is not None
    assert config.local_execution.enabled is True
    assert config.local_execution.model_cache_dir == _REPO_ROOT / "hf_cache"
    assert config.local_execution.fu13_like.context_length == 32
    assert config.local_execution.fu13_like.prediction_length == 8
    assert config.local_execution.fu13_like.max_windows == 60
```

Add helper:

```python
def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
```

Add validation tests:

```python
def test_c33_rejects_wrong_stage(tmp_path):
    data = yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
    data["stage"] = "wrong"
    with pytest.raises(C33ConfigError, match="stage"):
        load_c33_config(_write_yaml(tmp_path / "broken.yaml", data))


def test_c33_rejects_non_ttm_candidate(tmp_path):
    data = yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
    data["candidate"]["model_id"] = "chronos"
    with pytest.raises(C33ConfigError, match="candidate.model_id"):
        load_c33_config(_write_yaml(tmp_path / "broken.yaml", data))


def test_c33_rejects_download_without_network(tmp_path):
    data = yaml.safe_load(_LOCAL_CONFIG.read_text(encoding="utf-8"))
    data["safety_policy"]["allow_download"] = True
    data["safety_policy"]["allow_network"] = False
    with pytest.raises(C33ConfigError, match="allow_network"):
        load_c33_config(_write_yaml(tmp_path / "broken.yaml", data))


def test_c33_rejects_local_execution_without_model_cache(tmp_path):
    data = yaml.safe_load(_LOCAL_CONFIG.read_text(encoding="utf-8"))
    data["safety_policy"]["allow_model_cache"] = False
    with pytest.raises(C33ConfigError, match="allow_model_cache"):
        load_c33_config(_write_yaml(tmp_path / "broken.yaml", data))
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run python -m pytest tests/test_c33_single_candidate_open_model_local_evaluation.py -q
```

Expected: FAIL because the C3.3 module/configs do not exist.

- [ ] **Step 3: Add configs**

Create default config:

```yaml
stage: C3_3_single_candidate_open_model_local_evaluation
safety_policy:
  allow_network: false
  allow_download: false
  allow_model_cache: false
  allow_local_execution: false
  allow_training: false
  allow_write_processed: false
prerequisites:
  c32_design_doc: docs/superpowers/specs/2026-06-16-c32-explicit-local-execution-design.md
  c32_local_status: local_execution_baseline_reference_ready
candidate:
  model_id: ttm
  model_ref: ibm-granite/granite-timeseries-ttm-r2
  task_id: forecasting_residual
  dataset_view: fu13_like_simulated_forecasting
metric_contract:
  forecasting_metrics: [forecasting_mae, forecasting_rmse, residual_ranking]
  adapter_status_fields:
    - dependency_status
    - weight_status
    - adapter_status
    - runtime_seconds
    - input_shape
    - output_shape
    - actual_network_used
    - download_allowed_not_verified
  leaderboard_allowed: false
outputs:
  report: reports/c_stage_c33_single_candidate_open_model_local_evaluation.md
```

Create local config with the same base sections plus:

```yaml
safety_policy:
  allow_network: false
  allow_download: false
  allow_model_cache: true
  allow_local_execution: true
  allow_training: false
  allow_write_processed: false
local_execution:
  enabled: true
  model_cache_dir: hf_cache
  fu13_like:
    days: 3
    seed: 42
    context_length: 32
    prediction_length: 8
    max_windows: 60
    residual_top_k: 5
outputs:
  report: reports/c_stage_c33_ttm_fu13_like_local_evaluation.md
```

- [ ] **Step 4: Implement config dataclasses and validation**

In `src/b08_model_core/experiments/c33_single_candidate_open_model_local_evaluation.py` define:

- `C33ConfigError(ValueError)`
- `C33SafetyPolicy`
- `C33Prerequisites`
- `C33Candidate`
- `C33MetricContract`
- `C33LocalFu13LikeConfig`
- `C33LocalExecutionConfig`
- `C33Outputs`
- `C33Config`
- `C33RunResult`

Implement `load_c33_config(path)` with these rules:

- `stage` must be `C3_3_single_candidate_open_model_local_evaluation`.
- Default config requires all safety flags false.
- Local execution requires `allow_local_execution: true` and `allow_model_cache: true`.
- `allow_training` and `allow_write_processed` must always be false.
- `allow_download: true` requires `allow_network: true`.
- Candidate must be exactly:
  - `model_id: ttm`
  - `task_id: forecasting_residual`
  - `dataset_view: fu13_like_simulated_forecasting`
- `leaderboard_allowed` must be false.
- Relative `model_cache_dir` resolves from repository root, using the same project-root search pattern as C3.2.

- [ ] **Step 5: Implement contract runner and report**

Implement:

```python
def run_c33_single_candidate_open_model_local_evaluation(
    config: C33Config,
    config_path: str | Path,
    *,
    adapter_factory: Callable[[], object] | None = None,
) -> C33RunResult:
```

For Task 1, only contract path is required:

- If `config.local_execution is None`, return status `contract_ready_single_candidate_local_execution_blocked`.
- Do not import open model adapters in this path.

Implement `render_c33_report(result)` with sections:

- Summary
- Safety Policy
- C3.2 Anchor
- Candidate Contract
- Metric Contract
- Go / No-Go
- Invalid Claims
- Next Step

Report must not present a model/candidate leaderboard table or ranking. It may include forecasting residual ranking for sensor-level error explanation, the explicit guard line `Leaderboard allowed: False`, and the candidate `ttm`.

- [ ] **Step 6: Add contract report test**

Add:

```python
def test_c33_contract_runner_renders_default_report():
    config = load_c33_config(_DEFAULT_CONFIG)
    result = run_c33_single_candidate_open_model_local_evaluation(config, config_path=_DEFAULT_CONFIG)
    text = render_c33_report(result)

    assert result.status == "contract_ready_single_candidate_local_execution_blocked"
    assert "C3.2 Anchor" in text
    assert "Candidate Contract" in text
    assert "ttm" in text
    assert "Leaderboard allowed: False" in text
    assert "No-Go" in text
```

Add a default no-adapter-touch test:

```python
def test_c33_contract_runner_does_not_call_adapter_factory():
    config = load_c33_config(_DEFAULT_CONFIG)

    def forbidden_factory():
        raise AssertionError("default C3.3 contract path touched adapter factory")

    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_DEFAULT_CONFIG,
        adapter_factory=forbidden_factory,
    )

    assert result.status == "contract_ready_single_candidate_local_execution_blocked"
```

- [ ] **Step 7: Run Task 1 tests**

Run:

```bash
uv run python -m pytest tests/test_c33_single_candidate_open_model_local_evaluation.py -q
```

Expected: PASS for Task 1 tests.

- [ ] **Step 8: Commit Task 1**

```bash
git add configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml \
  configs/local/c_stage_c33_ttm_fu13_like_local_evaluation.example.yaml \
  src/b08_model_core/experiments/c33_single_candidate_open_model_local_evaluation.py \
  tests/test_c33_single_candidate_open_model_local_evaluation.py
git commit -m "feat: add c33 single candidate contract"
```

---

## Task 2: Local FU13-like Baseline And TTM Adapter Evidence

**Files:**
- Modify: `src/b08_model_core/experiments/c33_single_candidate_open_model_local_evaluation.py`
- Test: `tests/test_c33_single_candidate_open_model_local_evaluation.py`

- [ ] **Step 1: Write fake adapter tests**

Extend the test file with fake adapter classes using existing adapter result dataclasses:

```python
import numpy as np

from b08_model_core.adapters.open_models.base import (
    AdapterFailure,
    AdapterTaskOutput,
    OpenModelAdapterStatus,
)
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId
```

Add:

```python
class FakeSuccessfulTTMAdapter:
    model_id = "ttm"
    model_ref = "fake-ttm"

    def run_forecasting(self, windows, context):
        windows = list(windows)
        truth = np.stack([window.y for window in windows], axis=0)
        prediction = truth + 1.0
        return AdapterTaskOutput(
            model_id="ttm",
            task_id=C21TaskId.FORECASTING,
            status=OpenModelAdapterStatus.AVAILABLE_AND_RAN,
            predictions=prediction,
            metrics={"runtime_seconds": 0.01},
            input_shape={"windows": len(windows)},
            output_shape={"predictions": list(prediction.shape)},
            runtime_seconds=0.01,
            adapter_name="FakeSuccessfulTTMAdapter",
            model_ref="fake-ttm",
            cache_dir=context.cache_dir,
            actual_network_used=False,
            metadata={"weight_status": "available"},
        )


class FakeMissingDependencyTTMAdapter:
    def run_forecasting(self, windows, context):
        return AdapterFailure(
            model_id="ttm",
            task_id=C21TaskId.FORECASTING,
            status=OpenModelAdapterStatus.MISSING_DEPENDENCY,
            failure_stage="execute",
            failure_reason="missing tsfm_public",
            dependency_status="missing:tsfm_public",
            weight_status="not_attempted",
            adapter_name="FakeMissingDependencyTTMAdapter",
            cache_dir=context.cache_dir,
            actual_network_used=False,
        )


class FakeMissingWeightsTTMAdapter:
    def run_forecasting(self, windows, context):
        return AdapterFailure(
            model_id="ttm",
            task_id=C21TaskId.FORECASTING,
            status=OpenModelAdapterStatus.MISSING_OR_BLOCKED_WEIGHTS,
            failure_stage="execute",
            failure_reason="offline cache miss",
            dependency_status="available",
            weight_status="blocked_or_unknown",
            adapter_name="FakeMissingWeightsTTMAdapter",
            cache_dir=context.cache_dir,
            actual_network_used=False,
        )


class FakeRuntimeErrorTTMAdapter:
    def run_forecasting(self, windows, context):
        raise RuntimeError("runtime exploded")
```

Add success test:

```python
def test_c33_local_execution_runs_baseline_and_successful_ttm():
    config = load_c33_config(_LOCAL_CONFIG)
    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_LOCAL_CONFIG,
        adapter_factory=FakeSuccessfulTTMAdapter,
    )
    text = render_c33_report(result)

    assert result.status == "local_execution_ttm_forecasting_ready"
    assert result.baseline_reference_result is not None
    assert result.adapter_result is not None
    assert result.ttm_metrics is not None
    assert result.ttm_metrics["mae"] == 1.0
    assert result.ttm_residual_ranking
    assert "TTM Adapter Execution" in text
    assert "TTM Forecasting Metrics" in text
    assert "Residual Ranking" in text
    assert "Separated Metric Interpretation" in text
```

Add failure evidence test:

```python
def test_c33_local_execution_records_missing_dependency_as_evidence():
    config = load_c33_config(_LOCAL_CONFIG)
    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_LOCAL_CONFIG,
        adapter_factory=FakeMissingDependencyTTMAdapter,
    )
    text = render_c33_report(result)

    assert result.status == "local_execution_ttm_missing_dependency"
    assert result.adapter_failure is not None
    assert result.ttm_metrics is None
    assert "missing tsfm_public" in text
```

Add missing weights and exception tests:

```python
def test_c33_local_execution_records_missing_weights_as_evidence():
    config = load_c33_config(_LOCAL_CONFIG)
    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_LOCAL_CONFIG,
        adapter_factory=FakeMissingWeightsTTMAdapter,
    )
    text = render_c33_report(result)

    assert result.status == "local_execution_ttm_missing_or_blocked_weights"
    assert result.adapter_failure is not None
    assert result.ttm_metrics is None
    assert "offline cache miss" in text


def test_c33_local_execution_records_adapter_exception_as_runtime_failed():
    config = load_c33_config(_LOCAL_CONFIG)
    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_LOCAL_CONFIG,
        adapter_factory=FakeRuntimeErrorTTMAdapter,
    )
    text = render_c33_report(result)

    assert result.status == "local_execution_ttm_runtime_failed"
    assert result.adapter_failure is not None
    assert "runtime exploded" in text
```

Add insufficient window test by copying local config to tmp and setting `days: 1`, `context_length: 100000`; expect `blocked_insufficient_fu13_like_windows`.

- [ ] **Step 2: Run failing Task 2 tests**

Run:

```bash
uv run python -m pytest tests/test_c33_single_candidate_open_model_local_evaluation.py -q
```

Expected: FAIL because local execution is not implemented.

- [ ] **Step 3: Implement local result dataclasses**

In the C3.3 module add:

- `C33ForecastingBaselineResult`
- `C33ForecastingReferenceResult`
- Optional fields on `C33RunResult`:
  - `baseline_reference_result`
  - `adapter_result`
  - `adapter_failure`
  - `ttm_metrics`
  - `ttm_residual_ranking`
  - `local_execution_blocked_reason`

Reuse C3.2 field names where reasonable, but keep C3.3 types local to the new module.

- [ ] **Step 4: Implement FU13-like baseline reference**

Add `_run_fu13_like_baseline_reference(config)` that:

- Uses `simulate_dataset(days=config.days, seed=config.seed)`.
- Builds windows with `build_model_windows(..., stride=prediction_length, allow_cross_stage=True)`.
- Truncates to `max_windows`.
- Requires at least 2 windows.
- Uses 70/30 time split with at least one test window, matching C3.2.
- Fits `RobustStageForecaster` and `StageSeasonalNaiveForecaster` on train windows.
- Computes `forecasting_metrics` and `forecasting_residual_ranking`.
- Returns test windows and a baseline reference result.

- [ ] **Step 5: Implement adapter execution and status mapping**

In the local execution path:

- If no `adapter_factory` is passed, import `TTMOpenModelAdapter` inside the local branch only.
- Build `AdapterExecutionContext` with:
  - `allow_network=config.safety_policy.allow_network`
  - `allow_download=config.safety_policy.allow_download`
  - `cache_dir=config.local_execution.model_cache_dir`
  - `timeout_seconds_per_model=300.0`
  - metadata containing `stage: c33` and `candidate: ttm`
- Call `adapter.run_forecasting(test_windows, context)`.
- Catch adapter exceptions and convert them to an `AdapterFailure` with:
  - `status=OpenModelAdapterStatus.RUNTIME_FAILED`
  - `failure_stage="execute"`
  - `failure_reason=str(exc)`
  - `error_type=type(exc).__name__`
  - `error_detail=str(exc)`
  - cache dir and network/download context recorded.
- If status is `AVAILABLE_AND_RAN`, compute `forecasting_metrics({"y_hat": predictions}, test_windows)` and `forecasting_residual_ranking`.
- Map failures:
  - `MISSING_DEPENDENCY` -> `local_execution_ttm_missing_dependency`
  - `MISSING_OR_BLOCKED_WEIGHTS` -> `local_execution_ttm_missing_or_blocked_weights`
  - `UNSUPPORTED_WINDOW_SHAPE` -> `local_execution_ttm_unsupported_window_shape`
- any other non-success -> `local_execution_ttm_runtime_failed`

Derive `download_allowed_not_verified` for reporting as:

- `True` when `context.allow_download` is true and the adapter result does not provide a stricter `actual_network_used` boolean.
- `False` otherwise.

- [ ] **Step 6: Extend report**

Add report sections when local execution ran:

- Baseline Forecasting Reference
- TTM Adapter Execution
- TTM Forecasting Metrics, only when available
- Separated Metric Interpretation

The adapter section must include:

- status
- dependency_status
- weight_status
- adapter_status
- runtime_seconds
- input_shape
- output_shape
- actual_network_used
- download_allowed_not_verified
- failure_reason if present

- [ ] **Step 7: Run Task 2 tests**

Run:

```bash
uv run python -m pytest tests/test_c33_single_candidate_open_model_local_evaluation.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 2**

```bash
git add src/b08_model_core/experiments/c33_single_candidate_open_model_local_evaluation.py \
  tests/test_c33_single_candidate_open_model_local_evaluation.py
git commit -m "feat: run c33 ttm local evidence"
```

---

## Task 3: CLI, Docs, And Stage Regression Coverage

**Files:**
- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_experiment_scaffold.py`
- Modify: `tests/test_c33_single_candidate_open_model_local_evaluation.py`
- Modify: `README.md`
- Modify: `details.md`

- [ ] **Step 1: Write failing CLI test**

Add to `tests/test_c33_single_candidate_open_model_local_evaluation.py`:

```python
from b08_model_core.cli import main


def test_c33_cli_writes_default_report(tmp_path):
    output = tmp_path / "c33_report.md"

    exit_code = main([
        "experiment",
        "c-stage-c33",
        "--config",
        str(_DEFAULT_CONFIG),
        "--output",
        str(output),
    ])

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "C3.3 Single-Candidate Open Model Local Evaluation Report" in text
    assert "contract_ready_single_candidate_local_execution_blocked" in text
```

Add config-error CLI test for `allow_download: true` and `allow_network: false` returning 1.

- [ ] **Step 2: Add scaffold/docs regression assertions**

Inspect `tests/test_experiment_scaffold.py`. If it contains README command assertions, add C3.3 command checks:

- `experiment c-stage-c33`
- `configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml`
- `configs/local/c_stage_c33_ttm_fu13_like_local_evaluation.example.yaml`

- [ ] **Step 3: Run failing CLI/scaffold tests**

Run:

```bash
uv run python -m pytest tests/test_c33_single_candidate_open_model_local_evaluation.py tests/test_experiment_scaffold.py -q
```

Expected: FAIL until CLI and docs are updated.

- [ ] **Step 4: Implement CLI**

In `src/b08_model_core/cli.py`:

- Import:
  - `load_c33_config`
  - `render_c33_report`
  - `run_c33_single_candidate_open_model_local_evaluation`
- Add parser:

```python
c_stage_c33 = experiment_sub.add_parser("c-stage-c33")
c_stage_c33.add_argument("--config", required=True)
c_stage_c33.add_argument("--output", required=True)
```

- Add handler near C3.2:

```python
if args.command == "experiment" and args.experiment_command == "c-stage-c33":
    try:
        config = load_c33_config(args.config)
        result = run_c33_single_candidate_open_model_local_evaluation(
            config,
            config_path=args.config,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_c33_report(result), encoding="utf-8")
    except (FileNotFoundError, ValueError, OSError, PermissionError):
        return 1
    return 0
```

Do not make structured adapter failure statuses return 1.

- [ ] **Step 5: Update README**

In README:

- Add C3.3 section after C3.2.
- Include default command and explicit local command.
- State:
  - default does not inspect cache or instantiate TTM
  - local opt-in runs only TTM on FU13-like forecasting
  - C-MAPSS RUL remains baseline-only
  - RUL and forecasting metrics remain separated
  - no leaderboard, no training, no raw/cache/report commits
- Add C3.3 spec/plan links in document entry list.

- [ ] **Step 6: Update details.md**

Update:

- Current stage: C3.3 single-candidate open model local evaluation implemented, next enters C3.4 decision review.
- Daily update row for 2026-06-22.
- Next plan:
  - Review C3.3 TTM local evidence.
  - Decide whether to expand to another forecasting open model.
  - Keep C-MAPSS RUL baseline-only unless a separate RUL adapter design is approved.

- [ ] **Step 7: Run Task 3 tests**

Run:

```bash
uv run python -m pytest tests/test_c33_single_candidate_open_model_local_evaluation.py tests/test_experiment_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 3**

```bash
git add src/b08_model_core/cli.py \
  tests/test_experiment_scaffold.py \
  tests/test_c33_single_candidate_open_model_local_evaluation.py \
  README.md details.md
git commit -m "docs: document c33 local evaluation workflow"
```

---

## Final Verification

- [ ] **Step 1: Run targeted C3.3 tests**

```bash
uv run python -m pytest tests/test_c33_single_candidate_open_model_local_evaluation.py -q
```

Expected: all C3.3 tests pass.

- [ ] **Step 2: Run C-stage nearby tests**

```bash
uv run python -m pytest tests/test_c32_local_execution.py tests/test_c32_open_model_cross_dataset_evaluation.py tests/test_experiment_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full suite**

```bash
uv run python -m pytest -q
```

Expected: PASS.

- [ ] **Step 4: Run default C3.3 CLI smoke**

```bash
uv run b08-model-core experiment c-stage-c33 \
  --config configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml \
  --output /tmp/c_stage_c33_single_candidate_open_model_local_evaluation.md
```

Expected: exit 0 and report status `contract_ready_single_candidate_local_execution_blocked`.

- [ ] **Step 5: Inspect git status**

```bash
git status --short
```

Expected: only intended tracked source/docs/config/test changes; no raw, zip, parquet, cache, or generated reports.
