# C3.2 Explicit Local Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit local C3.2 baseline execution for C-MAPSS RUL and FU13-like forecasting while preserving the default contract-only safety path.

**Architecture:** Keep the current C3.2 contract runner as the default path, and extend it with an opt-in `local_execution` section. Reuse existing simulation, window, baseline, and metric primitives; extract only the minimal public C-MAPSS local RUL loader needed to avoid duplicating parser logic.

**Tech Stack:** Python dataclasses, YAML config, NumPy/Pandas, existing C3.1 C-MAPSS parser, existing forecasting baselines, pytest, Markdown reports.

---

## File Structure

- Modify `src/b08_model_core/evaluation/metrics.py`
  - Add `rul_regression_metrics`, `nasa_rul_score`, and `forecasting_residual_ranking`.
- Modify `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
  - Add public helper dataclasses/functions for loading local C-MAPSS RUL baseline records from an explicit `raw_dir` and selected subsets.
  - Keep existing C3.1 behavior unchanged.
- Modify `src/b08_model_core/experiments/c32_open_model_cross_dataset_evaluation.py`
  - Add optional local execution config dataclasses.
  - Validate explicit opt-in safety flags.
  - Run C-MAPSS RUL baseline and FU13-like forecasting reference only when local execution is enabled.
  - Extend report sections without changing the default no-touch path.
- Create `configs/local/c_stage_c32_explicit_local_execution.example.yaml`
  - Full classic opt-in example with all four C-MAPSS subsets.
- Modify `src/b08_model_core/cli.py`
  - Keep `experiment c-stage-c32 --config --output` unchanged; behavior comes from config.
- Modify `tests/test_c32_open_model_cross_dataset_evaluation.py`
  - Add local execution config, safety, CLI, report, and no-adapter tests.
- Create `tests/test_c32_local_execution.py`
  - Add focused metric and local fixture tests.
- Modify `tests/test_experiment_scaffold.py`
  - Add docs regression assertions for explicit local execution.
- Modify `README.md`
  - Document local execution command and separated metrics.
- Modify `details.md`
  - Update current stage, daily row, and next plan.

---

## Task 1: Metrics And C-MAPSS Local RUL Helper

**Files:**
- Modify: `src/b08_model_core/evaluation/metrics.py`
- Modify: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
- Test: `tests/test_c32_local_execution.py`

- [ ] **Step 1: Write failing metric tests**

Create `tests/test_c32_local_execution.py` with tests for:

```python
import math
from pathlib import Path

import numpy as np
import pytest

from b08_model_core.evaluation.metrics import (
    forecasting_residual_ranking,
    nasa_rul_score,
    rul_regression_metrics,
)


def test_rul_regression_metrics_include_nasa_score():
    truth = np.array([10.0, 20.0, 30.0])
    prediction = np.array([12.0, 18.0, 30.0])

    metrics = rul_regression_metrics(prediction, truth)

    assert metrics["mae"] == 4.0 / 3.0
    assert metrics["rmse"] == math.sqrt(8.0 / 3.0)
    assert metrics["nasa_score"] == nasa_rul_score(prediction, truth)
    assert metrics["count"] == 3


def test_forecasting_residual_ranking_groups_by_sensor():
    truth = np.zeros((2, 2, 3))
    prediction = np.array(
        [
            [[1.0, 0.0, 3.0], [1.0, 0.0, 3.0]],
            [[2.0, 0.0, 1.0], [2.0, 0.0, 1.0]],
        ]
    )

    ranking = forecasting_residual_ranking(
        {"y_hat": prediction},
        truth,
        ["s1", "s2", "s3"],
        top_k=2,
    )

    assert ranking == (
        {"rank": 1, "sensor_id": "s3", "mean_abs_residual": 2.0},
        {"rank": 2, "sensor_id": "s1", "mean_abs_residual": 1.5},
    )
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run python -m pytest tests/test_c32_local_execution.py -q
```

Expected: FAIL because the new metric helpers do not exist.

- [ ] **Step 3: Implement metric helpers**

In `src/b08_model_core/evaluation/metrics.py` add:

- `nasa_rul_score(prediction, truth) -> float`
  - Convert to NumPy arrays.
  - `error = prediction - truth`.
  - Use `np.where(error < 0, np.exp(-error / 13.0) - 1.0, np.exp(error / 10.0) - 1.0)`.
  - Return sum as float.
- `rul_regression_metrics(prediction, truth) -> dict[str, float | int]`
  - Return `mae`, `rmse`, `nasa_score`, `count`.
  - Reject empty arrays or shape mismatch with `ValueError`.
- `forecasting_residual_ranking(predictions, truth, sensor_ids, top_k=5)`
  - Use `predictions["y_hat"] - truth`.
  - Mean absolute residual over window and horizon axes.
  - Sort descending by residual, then ascending sensor id for ties.
  - Return tuple of dict rows.

- [ ] **Step 4: Write failing C-MAPSS helper test**

Add to `tests/test_c32_local_execution.py`:

```python
import yaml

from b08_model_core.experiments.c31_cmapss_minimal_ingestion import (
    C31RawSchemaMismatch,
    load_cmapss_rul_baseline_dataset,
)


def _write_fd001_fixture(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True)
    train_rows = [
        "1 1 0 0 0 " + " ".join(["1"] * 21),
        "1 2 0 0 0 " + " ".join(["1"] * 21),
        "1 3 0 0 0 " + " ".join(["1"] * 21),
        "2 1 0 0 0 " + " ".join(["2"] * 21),
        "2 2 0 0 0 " + " ".join(["2"] * 21),
    ]
    test_rows = [
        "1 1 0 0 0 " + " ".join(["3"] * 21),
        "1 2 0 0 0 " + " ".join(["3"] * 21),
        "2 1 0 0 0 " + " ".join(["4"] * 21),
    ]
    (raw_dir / "train_FD001.txt").write_text("\\n".join(train_rows) + "\\n", encoding="utf-8")
    (raw_dir / "test_FD001.txt").write_text("\\n".join(test_rows) + "\\n", encoding="utf-8")
    (raw_dir / "RUL_FD001.txt").write_text("7\\n5\\n", encoding="utf-8")


def test_load_cmapss_rul_baseline_dataset_from_local_raw(tmp_path):
    raw_dir = tmp_path / "data/public/cmapss/raw"
    _write_fd001_fixture(raw_dir)

    dataset = load_cmapss_rul_baseline_dataset(raw_dir, subsets=("FD001",))

    assert dataset.subsets == ("FD001",)
    assert len(dataset.train_records) == 5
    assert len(dataset.test_final_records) == 2
    assert dataset.test_final_records[0].rul == 7
    assert dataset.test_final_records[1].rul == 5


def test_load_cmapss_rul_baseline_dataset_reports_schema_mismatch(tmp_path):
    raw_dir = tmp_path / "data/public/cmapss/raw"
    _write_fd001_fixture(raw_dir)
    (raw_dir / "train_FD001.txt").write_text("1 1 0\n", encoding="utf-8")

    with pytest.raises(C31RawSchemaMismatch, match="expected 26 columns"):
        load_cmapss_rul_baseline_dataset(raw_dir, subsets=("FD001",))
```

- [ ] **Step 5: Implement C-MAPSS helper**

In `c31_cmapss_minimal_ingestion.py` add public dataclasses:

- `CmapssRulCycleRecord`
  - `subset`, `file_role`, `unit_id`, `cycle_index`, `rul`.
- `CmapssRulBaselineDataset`
  - `subsets`, `train_records`, `test_final_records`.

Add `load_cmapss_rul_baseline_dataset(raw_dir, subsets)`:

- For each subset, use existing private parser functions internally.
- Build train RUL records from `_train_rul_targets`.
- Build test final records only from the final cycle per test unit using `_test_rul_targets`.
- Preserve raw 1-based `cycle_index`.
- Do not write processed files.

Also expose a public schema mismatch alias:

```python
C31RawSchemaMismatch = _C31RawSchemaMismatch
```

This lets C3.2 catch schema mismatch without importing private names.

- [ ] **Step 6: Run Task 1 tests**

Run:

```bash
uv run python -m pytest tests/test_c32_local_execution.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```bash
git add src/b08_model_core/evaluation/metrics.py \
  src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py \
  tests/test_c32_local_execution.py
git commit -m "feat: add c32 baseline metric helpers"
```

---

## Task 2: C3.2 Local Execution Config And Runner

**Files:**
- Create: `configs/local/c_stage_c32_explicit_local_execution.example.yaml`
- Modify: `src/b08_model_core/experiments/c32_open_model_cross_dataset_evaluation.py`
- Test: `tests/test_c32_open_model_cross_dataset_evaluation.py`
- Test: `tests/test_c32_local_execution.py`

- [ ] **Step 1: Write failing config and safety tests**

Extend `tests/test_c32_open_model_cross_dataset_evaluation.py`:

```python
_LOCAL_EXECUTION_CONFIG = (
    _REPO_ROOT / "configs/local/c_stage_c32_explicit_local_execution.example.yaml"
)


def test_c32_local_execution_example_is_explicit_opt_in():
    config = load_c32_config(_LOCAL_EXECUTION_CONFIG)

    assert config.safety_policy.allow_local_execution is True
    assert config.safety_policy.allow_local_raw_data is True
    assert config.safety_policy.allow_network is False
    assert config.safety_policy.allow_download is False
    assert config.safety_policy.allow_model_cache is False
    assert config.safety_policy.allow_training is False
    assert config.safety_policy.allow_write_processed is False
    assert config.local_execution is not None
    assert config.local_execution.enabled is True
    assert config.local_execution.cmapss.subsets == ("FD001", "FD002", "FD003", "FD004")
    assert config.local_execution.fu13_like.context_length == 32
    assert config.local_execution.fu13_like.prediction_length == 8
    assert config.local_execution.fu13_like.max_windows == 60


def test_c32_rejects_local_execution_without_required_flags(tmp_path):
    data = yaml.safe_load(_LOCAL_EXECUTION_CONFIG.read_text(encoding="utf-8"))
    data["safety_policy"]["allow_local_raw_data"] = False
    broken = _write_yaml(tmp_path / "broken_local.yaml", data)

    with pytest.raises(C32ConfigError, match="allow_local_raw_data"):
        load_c32_config(broken)


def test_c32_rejects_local_execution_with_training_enabled(tmp_path):
    data = yaml.safe_load(_LOCAL_EXECUTION_CONFIG.read_text(encoding="utf-8"))
    data["safety_policy"]["allow_training"] = True
    broken = _write_yaml(tmp_path / "broken_training.yaml", data)

    with pytest.raises(C32ConfigError, match="allow_training"):
        load_c32_config(broken)
```

- [ ] **Step 2: Add local execution example config**

Create `configs/local/c_stage_c32_explicit_local_execution.example.yaml` by copying the default C3.2 contract and adding:

```yaml
safety_policy:
  allow_network: false
  allow_download: false
  allow_local_raw_data: true
  allow_local_execution: true
  allow_model_cache: false
  allow_training: false
  allow_write_processed: false
local_execution:
  enabled: true
  cmapss:
    raw_dir: data/public/cmapss/raw
    subsets: [FD001, FD002, FD003, FD004]
    progress_bucket_count: 20
  fu13_like:
    days: 3
    seed: 42
    context_length: 32
    prediction_length: 8
    max_windows: 60
    residual_top_k: 5
```

Keep model cache disabled and leaderboard false.

- [ ] **Step 3: Implement local config dataclasses and validation**

In `c32_open_model_cross_dataset_evaluation.py`:

- Extend `C32SafetyPolicy` with `allow_local_execution: bool = False`.
- Add `C32LocalCmapssConfig`, `C32LocalFu13LikeConfig`, `C32LocalExecutionConfig`.
- Add `local_execution: C32LocalExecutionConfig | None` to `C32Config`.
- Default config should still load when `allow_local_execution` is absent; treat absent as false.
- If `local_execution.enabled` true:
  - require `allow_local_execution` and `allow_local_raw_data` true.
  - require network/download/model_cache/training/write_processed false.
  - validate subsets are non-empty and only classic subset ids.
  - validate `progress_bucket_count`, `days`, `context_length`, `prediction_length`, `max_windows`, `residual_top_k` are positive.

- [ ] **Step 4: Write failing runner tests**

Add to `tests/test_c32_local_execution.py` helper to build local C3.2 config from the example and FD001 fixture:

```python
from b08_model_core.experiments.c32_open_model_cross_dataset_evaluation import (
    load_c32_config,
    render_c32_report,
    run_c32_open_model_cross_dataset_evaluation,
)


def _c32_fd001_local_config(tmp_path: Path) -> Path:
    source = Path("configs/local/c_stage_c32_explicit_local_execution.example.yaml")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    raw_dir = tmp_path / "data/public/cmapss/raw"
    data["local_execution"]["cmapss"]["raw_dir"] = str(raw_dir)
    data["local_execution"]["cmapss"]["subsets"] = ["FD001"]
    path = tmp_path / "c32_fd001.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    _write_fd001_fixture(raw_dir)
    return path


def test_c32_local_execution_runs_rul_and_forecasting_reference(tmp_path):
    config_path = _c32_fd001_local_config(tmp_path)
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(config, config_path=config_path)

    assert result.status == "local_execution_baseline_reference_ready"
    assert result.rul_baseline_result is not None
    assert result.rul_baseline_result.overall_metrics["subset_count"] == 1
    assert result.rul_baseline_result.overall_metrics["count"] == 2
    assert result.forecasting_reference_result is not None
    assert set(result.forecasting_reference_result.baseline_metrics) == {
        "RobustStageForecaster",
        "StageSeasonalNaiveForecaster",
    }
    text = render_c32_report(result)
    assert "C-MAPSS RUL Baseline Evaluation" in text
    assert "FU13-like Forecasting Reference" in text
    assert "Separated Metric Interpretation" in text
    assert "Leaderboard allowed: False" in text
```

Add exact-value RUL baseline test for the FD001 fixture:

```python
def test_c32_local_execution_rul_baseline_uses_deterministic_progress_profile(tmp_path):
    config_path = _c32_fd001_local_config(tmp_path)
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(config, config_path=config_path)

    assert result.rul_baseline_result is not None
    subset = result.rul_baseline_result.subset_metrics[0]
    assert subset.subset == "FD001"
    assert subset.predictions == (1.0, 2.0)
    assert subset.truth == (7.0, 5.0)
    assert subset.metrics["mae"] == 4.5
    assert subset.metrics["rmse"] == math.sqrt(22.5)
    expected_nasa = (math.exp(6.0 / 13.0) - 1.0) + (math.exp(3.0 / 13.0) - 1.0)
    assert subset.metrics["nasa_score"] == pytest.approx(expected_nasa)
    assert result.rul_baseline_result.overall_metrics["mae"] == 4.5
    assert result.rul_baseline_result.overall_metrics["rmse"] == math.sqrt(22.5)
    assert result.rul_baseline_result.overall_metrics["nasa_score"] == pytest.approx(expected_nasa)
```

This fixture intentionally exercises:

- per-unit train progress (`cycle_index / unit_max_cycle`)
- subset train max-cycle median reference (`median(3, 2) = 2.5`)
- nearest non-empty bucket fallback
- lower-bucket tie handling
- overall aggregation matching per-subset metrics for a single selected subset

Add blocked missing raw test:

```python
def test_c32_local_execution_blocks_when_raw_missing(tmp_path):
    config_path = _c32_fd001_local_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    missing_dir = tmp_path / "data/public/cmapss/missing"
    data["local_execution"]["cmapss"]["raw_dir"] = str(missing_dir)
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(config, config_path=config_path)

    assert result.status == "blocked_missing_cmapss_raw"
    assert result.rul_baseline_result is None
```

Add schema mismatch and insufficient FU13-like windows tests:

```python
def test_c32_local_execution_blocks_on_raw_schema_mismatch(tmp_path):
    config_path = _c32_fd001_local_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw_dir = Path(data["local_execution"]["cmapss"]["raw_dir"])
    (raw_dir / "train_FD001.txt").write_text("1 1 0\n", encoding="utf-8")
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(config, config_path=config_path)

    assert result.status == "blocked_cmapss_raw_schema_mismatch"
    assert "expected 26 columns" in result.local_execution_blocked_reason
    assert result.rul_baseline_result is None


def test_c32_local_execution_blocks_when_fu13_like_windows_are_insufficient(tmp_path):
    config_path = _c32_fd001_local_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["local_execution"]["fu13_like"]["days"] = 1
    data["local_execution"]["fu13_like"]["context_length"] = 100000
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(config, config_path=config_path)

    assert result.status == "blocked_insufficient_fu13_like_windows"
    assert result.forecasting_reference_result is None
```

Add local execution no-adapter guard:

```python
def test_c32_local_execution_does_not_import_open_model_adapters(tmp_path, monkeypatch):
    import builtins
    import importlib

    forbidden = (
        "b08_model_core.adapters.open_models",
        "b08_model_core.adapters.ttm_adapter",
    )
    original_import = builtins.__import__
    original_import_module = importlib.import_module

    def guarded_import(name, *args, **kwargs):
        if name.startswith(forbidden):
            raise AssertionError(f"C3.2 local execution imported adapters: {name}")
        return original_import(name, *args, **kwargs)

    def guarded_import_module(name, *args, **kwargs):
        if name.startswith(forbidden):
            raise AssertionError(f"C3.2 local execution imported adapter module: {name}")
        return original_import_module(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(importlib, "import_module", guarded_import_module)
    config_path = _c32_fd001_local_config(tmp_path)
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(config, config_path=config_path)

    assert result.status == "local_execution_baseline_reference_ready"
```

- [ ] **Step 5: Implement local runner**

In `c32_open_model_cross_dataset_evaluation.py`:

- Add result dataclasses:
  - `C32RulSubsetMetrics`
  - `C32RulBaselineResult`
  - `C32ForecastingBaselineResult`
  - `C32ForecastingReferenceResult`
- Add `rul_baseline_result` and `forecasting_reference_result` to `C32RunResult`.
- Add `local_execution_blocked_reason: str = ""` to `C32RunResult`.
- In `run_c32_open_model_cross_dataset_evaluation`:
  - If local execution absent/disabled, return exactly the current contract-only result.
  - If local enabled, first check required raw files using configured raw dir and selected subsets.
  - On missing raw, return status `blocked_missing_cmapss_raw`.
  - Build C-MAPSS RUL dataset via `load_cmapss_rul_baseline_dataset(config.local_execution.cmapss.raw_dir, subsets=...)`.
  - Build per-subset profiles and predictions.
  - Keep `predictions` and `truth` tuples on `C32RulSubsetMetrics` so deterministic RUL tests and reports can audit the baseline behavior.
  - Compute per-subset and overall metrics with `rul_regression_metrics`.
  - Catch `C31RawSchemaMismatch` and return status `blocked_cmapss_raw_schema_mismatch` with the mismatch text in `local_execution_blocked_reason`.
  - Generate FU13-like observations with `simulate_dataset(days, seed)`.
  - Build windows with `allow_cross_stage=True`, `stride=prediction_length`, truncate to max windows.
  - If fewer than 2 windows are available, return status `blocked_insufficient_fu13_like_windows` with a clear blocked reason.
  - Split using `split = max(1, int(len(windows) * 0.7)); if split == len(windows): split -= 1`.
  - Fit robust and seasonal baselines on train windows and evaluate test windows.
  - Compute `forecasting_metrics` and `forecasting_residual_ranking`.
  - Return status `local_execution_baseline_reference_ready`.
  - Do not import open model adapters.

- [ ] **Step 6: Extend report renderer**

Add report sections only when corresponding results exist:

- `## C-MAPSS RUL Baseline Evaluation`
  - status, subsets, per-subset table, overall metrics.
- `## FU13-like Forecasting Reference`
  - simulation/window parameters, train/test windows, baseline metrics, residual ranking.
- `## Separated Metric Interpretation`
  - RUL metrics and forecasting metrics are not merged.
  - No leaderboard, no training, no open model execution.

For blocked local execution statuses, render status, blocked reason, and next action. This includes `blocked_missing_cmapss_raw`, `blocked_cmapss_raw_schema_mismatch`, and `blocked_insufficient_fu13_like_windows`.

- [ ] **Step 7: Run Task 2 tests**

Run:

```bash
uv run python -m pytest tests/test_c32_local_execution.py tests/test_c32_open_model_cross_dataset_evaluation.py -q
```

Expected: PASS, including existing default no-touch tests.

- [ ] **Step 8: Commit Task 2**

```bash
git add configs/local/c_stage_c32_explicit_local_execution.example.yaml \
  src/b08_model_core/experiments/c32_open_model_cross_dataset_evaluation.py \
  tests/test_c32_local_execution.py \
  tests/test_c32_open_model_cross_dataset_evaluation.py
git commit -m "feat: add c32 explicit local baseline execution"
```

---

## Task 3: CLI, README, Details, And Docs Tests

**Files:**
- Modify: `src/b08_model_core/cli.py`
- Modify: `README.md`
- Modify: `details.md`
- Modify: `tests/test_experiment_scaffold.py`
- Test: `tests/test_c32_local_execution.py`
- Test: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Write failing CLI smoke test**

Add to `tests/test_c32_local_execution.py`:

```python
from b08_model_core.cli import main


def test_cli_c_stage_c32_runs_explicit_local_execution(tmp_path):
    config_path = _c32_fd001_local_config(tmp_path)
    output = tmp_path / "c32_local.md"

    exit_code = main(
        [
            "experiment",
            "c-stage-c32",
            "--config",
            str(config_path),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "local_execution_baseline_reference_ready" in text
    assert "C-MAPSS RUL Baseline Evaluation" in text
    assert "FU13-like Forecasting Reference" in text
```

If CLI already works through config-only behavior, this may pass after Task 2. Keep the test as regression coverage.

- [ ] **Step 2: Write failing docs regression test**

Extend `tests/test_experiment_scaffold.py`:

```python
def test_c32_explicit_local_execution_workflow_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "configs/local/c_stage_c32_explicit_local_execution.example.yaml" in readme
    assert "local_execution_baseline_reference_ready" in readme
    assert "C-MAPSS RUL baseline evaluation" in readme
    assert "FU13-like forecasting reference" in readme
    assert "不生成 leaderboard" in readme
    assert "不运行 open model adapter" in readme
    assert "explicit local execution" in details
    assert "C-MAPSS RUL baseline" in details
    assert "FU13-like forecasting reference" in details
```

- [ ] **Step 3: Update README**

In the C3.2 section:

- Keep default contract command unchanged.
- Add explicit local execution example:

```bash
uv run b08-model-core experiment c-stage-c32 \
  --config configs/local/c_stage_c32_explicit_local_execution.example.yaml \
  --output reports/c_stage_c32_explicit_local_execution.md
```

Explain:

- Requires local ignored C-MAPSS raw files under `data/public/cmapss/raw`.
- Runs only C-MAPSS RUL baseline evaluation and FU13-like forecasting reference.
- Does not download, write processed data, inspect cache, instantiate open model adapters, train, or generate leaderboard.
- RUL and forecasting metrics are separated.

- [ ] **Step 4: Update details.md**

Update:

- Date to `2026-06-16`.
- Current stage: C3.2 explicit local execution implemented or in progress.
- Daily row: spec/plan/local baseline execution.
- Next plan: C3.3 single-candidate open model local evaluation design, likely TTM on FU13-like forecasting first, C-MAPSS RUL remains baseline-only.

- [ ] **Step 5: Run Task 3 tests**

Run:

```bash
uv run python -m pytest tests/test_c32_local_execution.py tests/test_experiment_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add src/b08_model_core/cli.py README.md details.md \
  tests/test_c32_local_execution.py tests/test_experiment_scaffold.py
git commit -m "docs: document c32 explicit local execution"
```

---

## Task 4: Final Verification, Review, PR, Merge, Cleanup

**Files:**
- No source edits expected unless verification or review finds a bug.

- [ ] **Step 1: Run targeted tests**

```bash
uv run python -m pytest tests/test_c32_local_execution.py -q
uv run python -m pytest tests/test_c32_open_model_cross_dataset_evaluation.py -q
uv run python -m pytest tests/test_experiment_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full suite**

```bash
uv run python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run default C3.2 contract CLI**

```bash
uv run b08-model-core experiment c-stage-c32 \
  --config configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml \
  --output /tmp/c32_contract_report.md
rg -n "contract_ready_local_execution_blocked|No model training|Leaderboard allowed: False" /tmp/c32_contract_report.md
```

Expected: default contract path still reports blocked local execution and no leaderboard.

- [ ] **Step 4: Run local execution CLI with test fixture config**

Use the pytest CLI coverage as the primary verification because the repository must not depend on real local raw data. Do not commit generated reports.

- [ ] **Step 5: Safety audit**

```bash
git diff --check HEAD
git status --short
git ls-files data/public data/processed reports/c_stage_c32_explicit_local_execution.md hf_cache
```

Expected:

- no whitespace errors
- no uncommitted source changes after commits
- no tracked raw/processed/report/cache artifacts

- [ ] **Step 6: Subagent implementation review**

Dispatch final code review subagent with:

- Spec path: `docs/superpowers/specs/2026-06-16-c32-explicit-local-execution-design.md`
- Plan path: `docs/superpowers/plans/2026-06-16-c32-explicit-local-execution.md`
- Checks:
  - default C3.2 no-touch path preserved
  - local execution requires explicit opt-in
  - RUL and forecasting metrics separated
  - no open model adapter import in C3.2 local baseline
  - docs match implementation

Fix blocking findings, re-run relevant tests, and commit fixes.

- [ ] **Step 7: Push, open PR, merge remotely, cleanup local branch**

This step assumes implementation is on branch `codex/c32-explicit-local-execution`. Verify before pushing:

```bash
git branch --show-current
```

Expected: `codex/c32-explicit-local-execution`.

```bash
git push -u origin codex/c32-explicit-local-execution
cat > /tmp/c32_explicit_pr_body.md <<'PR_BODY'
## Summary
- Add C3.2 explicit local baseline execution for C-MAPSS RUL and FU13-like forecasting reference.
- Preserve the default C3.2 contract-only safety path.
- Keep RUL and forecasting metrics separated, with no leaderboard, training, or open model adapter execution.

## Verification
- `uv run python -m pytest -q`
- `uv run b08-model-core experiment c-stage-c32 --config configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml --output /tmp/c32_contract_report.md`
- `git ls-files data/public data/processed reports/c_stage_c32_explicit_local_execution.md hf_cache`
PR_BODY
gh pr create --base main --head codex/c32-explicit-local-execution \
  --title "Add C3.2 explicit local baseline execution" \
  --body-file /tmp/c32_explicit_pr_body.md
gh pr merge --squash --delete-branch
git switch main
git pull --ff-only
git branch -d codex/c32-explicit-local-execution
```

Expected: PR created and merged remotely; local branch removed after `main` is updated.
