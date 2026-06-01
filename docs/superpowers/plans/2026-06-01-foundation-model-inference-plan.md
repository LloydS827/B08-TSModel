# Foundation Model Inference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run at least one real open-source time-series foundation model on simulated FU13 windows, compare it against existing baselines, and produce a route-decision report without binding the project to one model ecosystem.

**Architecture:** Add a small model-agnostic foundation forecasting boundary around the existing `ModelWindow` contract. TTM is the first concrete adapter, but all TTM-specific imports, weight loading, and shape conversion stay inside the adapter so TimesFM, Chronos, Moirai, or FlowState can be added later without changing canonical schema or window construction. Baseline-only workflows must continue to run without external model dependencies or downloaded weights.

**Tech Stack:** Python 3.11+, numpy, pandas, pyarrow, pydantic, pytest, uv, optional `granite-tsfm` / `torch` / `transformers` / `huggingface_hub` for first TTM inference, existing `b08_model_core` CLI.

---

## Authoritative Inputs

- Design spec: `docs/superpowers/specs/2026-06-01-foundation-model-inference-design.md`
- Chinese readable design: `docs/foundation-model-inference-design.html`
- Existing experiment scaffold: `src/b08_model_core/experiments/forecasting.py`
- Existing model adapters: `src/b08_model_core/adapters/`
- Existing CLI: `src/b08_model_core/cli.py`
- Existing tests: `tests/test_experiment_scaffold.py`, `tests/test_baselines.py`, `tests/test_window_builder.py`
- Current official dependency evidence checked on 2026-06-01:
  - PyPI package `granite-tsfm` exists, current observed version `0.3.6`, Python `>=3.11,<3.14`.
  - Hugging Face checkpoint `ibm-granite/granite-timeseries-ttm-r2` exists and is tagged for `granite-tsfm`, TinyTimeMixer, forecasting, Apache-2.0.
  - Granite TSFM notebook imports `TimeSeriesPreprocessor`, `get_datasets`, and `get_model` from `tsfm_public`, then predicts with `transformers.Trainer`.

## Scope Guard

Implement only the first real foundation-model inference path and the reusable boundary around it.

Do not implement TimesFM, Chronos, Moirai, FlowState, MOMENT, TSPulse, or UniTS in this plan. The report may recommend them as fallbacks.

Do not add production alarms, dashboards, work orders, or a training platform.

Do not commit model weights, Hugging Face caches, generated parquet data, or transient experiment reports.

## Proposed File Structure

Create:

- `src/b08_model_core/foundation/__init__.py`
  - Exports foundation forecasting contracts and runner.
- `src/b08_model_core/foundation/results.py`
  - Defines `FoundationModelStatus`, `FoundationForecastResult`, route recommendation helpers, and metric comparison helpers.
- `src/b08_model_core/foundation/runner.py`
  - Defines `FoundationForecastRunner`, builds train/test windows, runs baselines, runs the selected foundation adapter, combines metrics, and returns an experiment result object. Also exposes a thin `run_foundation_forecasting()` convenience function for existing functional call style.
- `src/b08_model_core/foundation/reporting.py`
  - Renders Markdown reports with dataset summary, baseline metrics, baseline comparison deltas, selected model status, local dependency/weight/cache status, failure reasons, IO coverage, and route recommendation.
- `tests/test_foundation_results.py`
  - Unit tests for status, metric comparison, and route recommendation.
- `tests/test_foundation_runner.py`
  - Unit tests using fake adapters so no external weights are required.
- `tests/test_ttm_adapter.py`
  - Unit tests for TTM dependency handling and input conversion with lazy imports.

Modify:

- `src/b08_model_core/adapters/base.py`
  - Keep existing compatibility, or add thin protocol-compatible helpers if useful.
- `src/b08_model_core/adapters/ttm_adapter.py`
  - Replace prototype boundary with a lazy-import TTM forecasting adapter.
- `src/b08_model_core/evaluation/metrics.py`
  - Add RMSE and point-metric behavior for models that do not produce intervals.
- `src/b08_model_core/experiments/forecasting.py`
  - Delegate to the foundation runner/reporting path while preserving default baseline-only behavior.
- `src/b08_model_core/cli.py`
  - Add CLI options and exit-code behavior.
- `tests/test_experiment_scaffold.py`
  - Update current scaffold tests and add missing-dependency behavior.
- `.gitignore`
  - Ignore local model/cache directories.
- `pyproject.toml`
  - Add optional `foundation-ttm` dependencies.
- `uv.lock`
  - Update after optional dependency changes.
- `README.md`
  - Document install/download/cache/run/report interpretation.
- `details.md`
  - Record completion of the implementation plan and update after implementation progress.

## Command Conventions

Use project-standard uv commands:

```bash
uv sync --extra dev
uv run pytest -q
```

When optional TTM dependencies are needed:

```bash
uv sync --extra dev --extra foundation-ttm
```

If `uv` is unavailable in the local shell, install or expose `uv` before implementation. Do not replace project documentation with non-uv commands.

## Task 1: Foundation Result and Metric Contract

**Files:**
- Create: `src/b08_model_core/foundation/__init__.py`
- Create: `src/b08_model_core/foundation/results.py`
- Modify: `src/b08_model_core/evaluation/metrics.py`
- Test: `tests/test_foundation_results.py`
- Test: `tests/test_baselines.py`

- [ ] **Step 1: Write failing tests for point and interval metrics**

Add to `tests/test_foundation_results.py`:

```python
import numpy as np

from b08_model_core.evaluation.metrics import forecasting_metrics


class Window:
    def __init__(self, y):
        self.y = np.asarray(y, dtype=float)


def test_forecasting_metrics_include_rmse_for_point_predictions():
    windows = [Window([[1.0, 3.0], [2.0, 4.0]])]
    preds = {"y_hat": np.array([[[2.0, 1.0], [2.0, 5.0]]])}

    metrics = forecasting_metrics(preds, windows)

    assert metrics["mae"] == 1.0
    assert round(metrics["rmse"], 6) == round(np.sqrt(1.5), 6)
    assert metrics["interval_coverage"] is None


def test_forecasting_metrics_keep_interval_coverage_when_quantiles_exist():
    windows = [Window([[1.0], [2.0]])]
    preds = {
        "y_hat": np.array([[[1.0], [2.5]]]),
        "q_low": np.array([[[0.5], [2.0]]]),
        "q_high": np.array([[[1.5], [3.0]]]),
    }

    metrics = forecasting_metrics(preds, windows)

    assert metrics["mae"] == 0.25
    assert metrics["interval_coverage"] == 1.0
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_foundation_results.py::test_forecasting_metrics_include_rmse_for_point_predictions tests/test_foundation_results.py::test_forecasting_metrics_keep_interval_coverage_when_quantiles_exist -v
```

Expected: FAIL because `tests/test_foundation_results.py` or RMSE support does not exist.

- [ ] **Step 3: Implement metric behavior**

Modify `src/b08_model_core/evaluation/metrics.py`:

```python
from __future__ import annotations

import numpy as np


def forecasting_metrics(predictions: dict[str, np.ndarray], windows: list[object]) -> dict[str, float | None]:
    truth = np.stack([window.y for window in windows], axis=0)
    y_hat = predictions["y_hat"]
    error = y_hat - truth
    mae = float(np.mean(np.abs(error)))
    rmse = float(np.sqrt(np.mean(error**2)))
    if "q_low" in predictions and "q_high" in predictions:
        coverage = float(np.mean((truth >= predictions["q_low"]) & (truth <= predictions["q_high"])))
    else:
        coverage = None
    return {"mae": mae, "rmse": rmse, "interval_coverage": coverage}
```

- [ ] **Step 4: Write failing tests for foundation result statuses**

Add to `tests/test_foundation_results.py`:

```python
from b08_model_core.foundation.results import (
    FoundationForecastResult,
    FoundationModelStatus,
    recommend_route,
)


def test_foundation_result_marks_success_only_when_model_ran():
    success = FoundationForecastResult(
        model_name="FakeModel",
        adapter_name="fake",
        status=FoundationModelStatus.AVAILABLE_AND_RAN,
    )
    failure = FoundationForecastResult(
        model_name="TTM",
        adapter_name="ttm",
        status=FoundationModelStatus.MISSING_DEPENDENCY,
        reason="optional dependency missing",
    )

    assert success.succeeded is True
    assert failure.succeeded is False


def test_route_recommendation_uses_baseline_comparison_and_status():
    assert recommend_route(
        FoundationForecastResult(
            model_name="TTM",
            adapter_name="ttm",
            status=FoundationModelStatus.MISSING_DEPENDENCY,
            reason="optional dependency missing",
        ),
        baseline_mae=9.0,
    ) == "no_go_missing_dependency"

    assert recommend_route(
        FoundationForecastResult(
            model_name="TTM",
            adapter_name="ttm",
            status=FoundationModelStatus.AVAILABLE_AND_RAN,
            metrics={"mae": 8.0},
        ),
        baseline_mae=9.0,
    ) == "direct_reuse_candidate"
```

- [ ] **Step 5: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_foundation_results.py -v
```

Expected: FAIL because `b08_model_core.foundation.results` does not exist.

- [ ] **Step 6: Implement result contracts**

Create `src/b08_model_core/foundation/results.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np


class FoundationModelStatus(StrEnum):
    AVAILABLE_AND_RAN = "available_and_ran"
    MISSING_DEPENDENCY = "missing_dependency"
    MISSING_OR_BLOCKED_WEIGHTS = "missing_or_blocked_weights"
    UNSUPPORTED_WINDOW_SHAPE = "unsupported_window_shape"
    RUNTIME_FAILED = "runtime_failed"
    SKIPPED_BY_USER = "skipped_by_user"


@dataclass
class FoundationForecastResult:
    model_name: str
    adapter_name: str
    status: FoundationModelStatus
    y_hat: np.ndarray | None = None
    q_low: np.ndarray | None = None
    q_high: np.ndarray | None = None
    metrics: dict[str, float | None] = field(default_factory=dict)
    reason: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    io_coverage: dict[str, bool] = field(default_factory=dict)
    dependency_status: str = "unknown"
    weight_status: str = "unknown"
    cache_dir: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == FoundationModelStatus.AVAILABLE_AND_RAN

    def predictions(self) -> dict[str, np.ndarray]:
        if self.y_hat is None:
            return {}
        payload = {"y_hat": self.y_hat}
        if self.q_low is not None and self.q_high is not None:
            payload["q_low"] = self.q_low
            payload["q_high"] = self.q_high
        return payload


def recommend_route(result: FoundationForecastResult, baseline_mae: float | None) -> str:
    if result.status == FoundationModelStatus.MISSING_DEPENDENCY:
        return "no_go_missing_dependency"
    if result.status == FoundationModelStatus.MISSING_OR_BLOCKED_WEIGHTS:
        return "no_go_missing_or_blocked_weights"
    if result.status == FoundationModelStatus.UNSUPPORTED_WINDOW_SHAPE:
        return "no_go_unsupported_window_shape"
    if result.status == FoundationModelStatus.RUNTIME_FAILED:
        return "no_go_runtime_failed"
    if not result.succeeded:
        return "skipped"
    model_mae = result.metrics.get("mae")
    if model_mae is None or baseline_mae is None:
        return "ran_needs_review"
    if model_mae < baseline_mae * 0.98:
        return "direct_reuse_candidate"
    if model_mae <= baseline_mae * 1.10:
        return "few_shot_candidate"
    return "fallback_comparator"
```

Create `src/b08_model_core/foundation/__init__.py`:

```python
from b08_model_core.foundation.results import (
    FoundationForecastResult,
    FoundationModelStatus,
    recommend_route,
)

__all__ = ["FoundationForecastResult", "FoundationModelStatus", "recommend_route"]
```

- [ ] **Step 7: Run tests**

Run:

```bash
uv run pytest tests/test_foundation_results.py tests/test_baselines.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/b08_model_core/foundation/__init__.py src/b08_model_core/foundation/results.py src/b08_model_core/evaluation/metrics.py tests/test_foundation_results.py tests/test_baselines.py
git commit -m "feat: add foundation forecast result contract"
```

## Task 2: Markdown Report Renderer

**Files:**
- Create: `src/b08_model_core/foundation/reporting.py`
- Modify: `src/b08_model_core/foundation/__init__.py`
- Test: `tests/test_foundation_results.py`

- [ ] **Step 1: Write failing report-rendering test**

Add to `tests/test_foundation_results.py`:

```python
from b08_model_core.foundation.reporting import render_foundation_forecasting_report


def test_foundation_report_contains_status_metrics_and_fallback_recommendation():
    result = FoundationForecastResult(
        model_name="TTM",
        adapter_name="ttm",
        status=FoundationModelStatus.MISSING_DEPENDENCY,
        reason="optional dependency missing",
        metadata={"checkpoint": "ibm-granite/granite-timeseries-ttm-r2"},
        io_coverage={"numeric_values": True, "stage_token": False, "domain_token": False},
        dependency_status="missing_dependency",
        weight_status="not_attempted",
        cache_dir="hf_cache",
    )

    text = render_foundation_forecasting_report(
        dataset_path="data/simulated/fu13.parquet",
        train_count=10,
        test_count=4,
        context_length=512,
        prediction_length=96,
        sensor_count=16,
        baseline_metrics={
            "RobustStageForecaster": {"mae": 9.0, "rmse": 12.0, "interval_coverage": 0.92},
            "StageSeasonalNaiveForecaster": {"mae": 18.0, "rmse": 20.0, "interval_coverage": 0.0},
        },
        foundation_result=result,
        route_recommendation="no_go_missing_dependency",
        fallback_candidates=["FlowState", "TimesFM", "Chronos", "Moirai"],
    )

    assert "# Forecasting Foundation Model Experiment" in text
    assert "TTM" in text
    assert "missing_dependency" in text
    assert "optional dependency missing" in text
    assert "RobustStageForecaster" in text
    assert "Baseline Comparison" in text
    assert "Local Model Environment" in text
    assert "dependency_status" in text
    assert "weight_status" in text
    assert "cache_dir" in text
    assert "FlowState" in text
    assert "stage_token" in text
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest tests/test_foundation_results.py::test_foundation_report_contains_status_metrics_and_fallback_recommendation -v
```

Expected: FAIL because `b08_model_core.foundation.reporting` does not exist.

- [ ] **Step 3: Implement report renderer**

Create `src/b08_model_core/foundation/reporting.py`:

```python
from __future__ import annotations

from b08_model_core.foundation.results import FoundationForecastResult


def _fmt_metric(value: float | None) -> str:
    return "not_available" if value is None else f"{value:.6f}"


def _fmt_delta(model_value: float | None, baseline_value: float | None) -> tuple[str, str]:
    if model_value is None or baseline_value is None:
        return "not_available", "not_available"
    delta = model_value - baseline_value
    percent = (delta / baseline_value * 100.0) if baseline_value else 0.0
    return f"{delta:.6f}", f"{percent:.2f}%"


def render_foundation_forecasting_report(
    dataset_path: str,
    train_count: int,
    test_count: int,
    context_length: int,
    prediction_length: int,
    sensor_count: int,
    baseline_metrics: dict[str, dict[str, float | None]],
    foundation_result: FoundationForecastResult,
    route_recommendation: str,
    fallback_candidates: list[str],
) -> str:
    lines = [
        "# Forecasting Foundation Model Experiment",
        "",
        f"Dataset: {dataset_path}",
        f"Windows: train={train_count}, test={test_count}",
        f"Context length: {context_length}",
        f"Prediction length: {prediction_length}",
        f"Sensor count: {sensor_count}",
        "",
        "## Baseline Metrics",
        "",
        "| model | mae | rmse | interval_coverage |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, metrics in baseline_metrics.items():
        lines.append(
            f"| {name} | {_fmt_metric(metrics.get('mae'))} | "
            f"{_fmt_metric(metrics.get('rmse'))} | {_fmt_metric(metrics.get('interval_coverage'))} |"
        )

    robust_metrics = baseline_metrics.get("RobustStageForecaster", {})
    mae_delta, mae_delta_pct = _fmt_delta(foundation_result.metrics.get("mae"), robust_metrics.get("mae"))
    rmse_delta, rmse_delta_pct = _fmt_delta(foundation_result.metrics.get("rmse"), robust_metrics.get("rmse"))
    lines.extend(
        [
            "",
            "## Baseline Comparison",
            "",
            "| metric | model_minus_robust_baseline | percent_delta |",
            "| --- | ---: | ---: |",
            f"| mae | {mae_delta} | {mae_delta_pct} |",
            f"| rmse | {rmse_delta} | {rmse_delta_pct} |",
        ]
    )

    lines.extend(
        [
            "",
            "## Foundation Model Status",
            "",
            f"- model: {foundation_result.model_name}",
            f"- adapter: {foundation_result.adapter_name}",
            f"- status: {foundation_result.status.value}",
            f"- reason: {foundation_result.reason or 'none'}",
        ]
    )
    for key, value in sorted(foundation_result.metadata.items()):
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Local Model Environment",
            "",
            f"- dependency_status: {foundation_result.dependency_status}",
            f"- weight_status: {foundation_result.weight_status}",
            f"- cache_dir: {foundation_result.cache_dir or 'default'}",
        ]
    )

    lines.extend(["", "## Foundation Model Metrics", "", "| mae | rmse | interval_coverage |", "| ---: | ---: | ---: |"])
    lines.append(
        f"| {_fmt_metric(foundation_result.metrics.get('mae'))} | "
        f"{_fmt_metric(foundation_result.metrics.get('rmse'))} | "
        f"{_fmt_metric(foundation_result.metrics.get('interval_coverage'))} |"
    )

    lines.extend(["", "## IO Coverage", "", "| input | used |", "| --- | --- |"])
    for key, value in sorted(foundation_result.io_coverage.items()):
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## Route Recommendation",
            "",
            f"Recommendation: {route_recommendation}",
            "",
            "Fallback candidates if this model is blocked or weak: " + ", ".join(fallback_candidates),
        ]
    )
    return "\n".join(lines) + "\n"
```

Optionally export it from `src/b08_model_core/foundation/__init__.py`.

- [ ] **Step 4: Run test**

Run:

```bash
uv run pytest tests/test_foundation_results.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/b08_model_core/foundation/reporting.py src/b08_model_core/foundation/__init__.py tests/test_foundation_results.py
git commit -m "feat: render foundation forecast reports"
```

## Task 3: TTM Adapter Dependency and Input Conversion

**Files:**
- Modify: `src/b08_model_core/adapters/ttm_adapter.py`
- Test: `tests/test_ttm_adapter.py`

- [ ] **Step 1: Write failing tests for dependency status and input conversion**

Create `tests/test_ttm_adapter.py`:

```python
from dataclasses import dataclass

import numpy as np

from b08_model_core.adapters.ttm_adapter import TTMForecastAdapter
from b08_model_core.foundation.results import FoundationModelStatus


@dataclass
class Window:
    X: np.ndarray
    mask: np.ndarray
    y: np.ndarray
    stage_token: np.ndarray
    sensor_token: list[str]
    domain_token: list[str]


def _window(value: float = 1.0) -> Window:
    x = np.full((8, 3), value, dtype=float)
    y = np.full((4, 3), value + 1, dtype=float)
    return Window(
        X=x,
        mask=np.ones_like(x, dtype=bool),
        y=y,
        stage_token=np.array(["抽真空"] * 8, dtype=object),
        sensor_token=["s1", "s2", "s3"],
        domain_token=["mechanical", "thermal", "fluid"],
    )


def test_ttm_adapter_reports_missing_dependency_without_importing_weights(monkeypatch):
    adapter = TTMForecastAdapter(dependency_checker=lambda name: False)

    result = adapter.predict([_window()], context_length=8, prediction_length=4, allow_download=False)

    assert result.status == FoundationModelStatus.MISSING_DEPENDENCY
    assert result.model_name == "TTM"
    assert "dependency" in result.reason


def test_ttm_adapter_conversion_preserves_shape_and_sensor_order():
    adapter = TTMForecastAdapter(dependency_checker=lambda name: True)
    prepared = adapter.prepare_windows([_window(), _window(2.0)], context_length=8, prediction_length=4)

    assert prepared.past_values.shape == (2, 8, 3)
    assert prepared.future_values.shape == (2, 4, 3)
    assert prepared.past_observed_mask.shape == (2, 8, 3)
    assert prepared.sensor_token == ["s1", "s2", "s3"]
    assert prepared.channel_center.shape == (2, 1, 3)
    assert prepared.channel_scale.shape == (2, 1, 3)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_ttm_adapter.py -v
```

Expected: FAIL because `TTMForecastAdapter` does not exist.

- [ ] **Step 3: Implement TTM adapter dataclass and dependency path**

Modify `src/b08_model_core/adapters/ttm_adapter.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Callable

import numpy as np

from b08_model_core.adapters.base import TimeSeriesFoundationAdapter
from b08_model_core.foundation.results import FoundationForecastResult, FoundationModelStatus

DEFAULT_TTM_CHECKPOINT = "ibm-granite/granite-timeseries-ttm-r2"


@dataclass
class PreparedTTMWindows:
    past_values: np.ndarray
    past_observed_mask: np.ndarray
    future_values: np.ndarray
    sensor_token: list[str]
    channel_center: np.ndarray
    channel_scale: np.ndarray


class TTMForecastAdapter:
    name = "TTM"
    adapter_name = "ttm"

    def __init__(
        self,
        checkpoint: str = DEFAULT_TTM_CHECKPOINT,
        dependency_checker: Callable[[str], bool] | None = None,
    ) -> None:
        self.checkpoint = checkpoint
        self.dependency_checker = dependency_checker or (lambda name: find_spec(name) is not None)

    def available(self) -> bool:
        return self.dependency_checker("tsfm_public") and self.dependency_checker("transformers")

    def prepare_windows(
        self,
        windows: list[object],
        context_length: int,
        prediction_length: int,
    ) -> PreparedTTMWindows:
        if not windows:
            raise ValueError("at least one window is required")
        past = np.stack([window.X for window in windows], axis=0).astype(float)
        future = np.stack([window.y for window in windows], axis=0).astype(float)
        if past.shape[1] != context_length or future.shape[1] != prediction_length:
            raise ValueError(
                f"window shape mismatch: past={past.shape}, future={future.shape}, "
                f"context_length={context_length}, prediction_length={prediction_length}"
            )
        mask = np.stack([window.mask for window in windows], axis=0).astype(bool)
        center = np.nanmean(np.where(mask, past, np.nan), axis=1, keepdims=True)
        scale = np.nanstd(np.where(mask, past, np.nan), axis=1, keepdims=True)
        center = np.nan_to_num(center, nan=0.0)
        scale = np.maximum(np.nan_to_num(scale, nan=1.0), 1e-6)
        scaled_past = (np.nan_to_num(past, nan=center) - center) / scale
        scaled_future = (future - center) / scale
        return PreparedTTMWindows(
            past_values=scaled_past,
            past_observed_mask=mask,
            future_values=scaled_future,
            sensor_token=list(windows[0].sensor_token),
            channel_center=center,
            channel_scale=scale,
        )

    def predict(
        self,
        windows: list[object],
        context_length: int,
        prediction_length: int,
        allow_download: bool = False,
        model_cache_dir: str | Path | None = None,
    ) -> FoundationForecastResult:
        if not self.available():
            return FoundationForecastResult(
                model_name=self.name,
                adapter_name=self.adapter_name,
                status=FoundationModelStatus.MISSING_DEPENDENCY,
                reason="optional TTM dependency is not installed; run `uv sync --extra dev --extra foundation-ttm`",
                metadata={"checkpoint": self.checkpoint},
                io_coverage={"numeric_values": True, "stage_token": False, "domain_token": False, "sensor_token": False},
                dependency_status="missing_dependency",
                weight_status="not_attempted",
                cache_dir=str(model_cache_dir) if model_cache_dir else None,
            )
        return self._predict_with_ttm(windows, context_length, prediction_length, allow_download, model_cache_dir)

    def _predict_with_ttm(self, windows, context_length, prediction_length, allow_download, model_cache_dir):
        raise NotImplementedError("implemented in Task 4")


def build_adapter() -> TimeSeriesFoundationAdapter:
    adapter = TTMForecastAdapter()
    available = adapter.available()
    return TimeSeriesFoundationAdapter("TTM", {"forecasting"}, available, "" if available else "optional TTM dependency is not installed")
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_ttm_adapter.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/b08_model_core/adapters/ttm_adapter.py tests/test_ttm_adapter.py
git commit -m "feat: add ttm adapter input contract"
```

## Task 4: TTM Lazy Real-Inference Boundary

**Files:**
- Modify: `src/b08_model_core/adapters/ttm_adapter.py`
- Test: `tests/test_ttm_adapter.py`

- [ ] **Step 1: Write failing tests with fake TTM runtime**

Add to `tests/test_ttm_adapter.py`:

```python
from types import SimpleNamespace


def test_ttm_adapter_predicts_with_injected_runtime_and_unscales_output():
    class FakeRuntime:
        def predict(self, prepared, checkpoint, prediction_length, allow_download, model_cache_dir):
            assert checkpoint == "fake/checkpoint"
            assert prediction_length == 4
            return np.zeros((len(prepared.past_values), prediction_length, prepared.past_values.shape[-1]))

    adapter = TTMForecastAdapter(
        checkpoint="fake/checkpoint",
        dependency_checker=lambda name: True,
        runtime_factory=lambda: FakeRuntime(),
    )

    result = adapter.predict([_window(5.0)], context_length=8, prediction_length=4, allow_download=False)

    assert result.status == FoundationModelStatus.AVAILABLE_AND_RAN
    assert result.y_hat.shape == (1, 4, 3)
    assert np.allclose(result.y_hat, 5.0)
    assert result.metadata["checkpoint"] == "fake/checkpoint"


def test_ttm_adapter_converts_runtime_errors_to_reportable_status():
    class BrokenRuntime:
        def predict(self, prepared, checkpoint, prediction_length, allow_download, model_cache_dir):
            raise RuntimeError("boom")

    adapter = TTMForecastAdapter(dependency_checker=lambda name: True, runtime_factory=lambda: BrokenRuntime())

    result = adapter.predict([_window()], context_length=8, prediction_length=4, allow_download=False)

    assert result.status == FoundationModelStatus.RUNTIME_FAILED
    assert "boom" in result.reason
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_ttm_adapter.py::test_ttm_adapter_predicts_with_injected_runtime_and_unscales_output tests/test_ttm_adapter.py::test_ttm_adapter_converts_runtime_errors_to_reportable_status -v
```

Expected: FAIL because `runtime_factory` and `_predict_with_ttm` behavior do not exist.

- [ ] **Step 3: Implement runtime injection and lazy imports**

Modify `src/b08_model_core/adapters/ttm_adapter.py`.

Add a runtime class that imports heavy dependencies only inside `predict`:

```python
class TTMRuntime:
    def predict(self, prepared: PreparedTTMWindows, checkpoint: str, prediction_length: int, allow_download: bool, model_cache_dir: str | Path | None) -> np.ndarray:
        import tempfile

        import torch
        from torch.utils.data import Dataset
        from transformers import Trainer, TrainingArguments
        from tsfm_public.toolkit.get_model import get_model

        class WindowDataset(Dataset):
            def __len__(self):
                return len(prepared.past_values)

            def __getitem__(self, index):
                return {
                    "past_values": torch.as_tensor(prepared.past_values[index], dtype=torch.float32),
                    "past_observed_mask": torch.as_tensor(prepared.past_observed_mask[index], dtype=torch.bool),
                    "future_values": torch.as_tensor(prepared.future_values[index], dtype=torch.float32),
                }

        if model_cache_dir is not None:
            import os

            os.environ.setdefault("HF_HOME", str(model_cache_dir))
        if not allow_download:
            import os

            os.environ.setdefault("HF_HUB_OFFLINE", "1")

        model = get_model(
            checkpoint,
            context_length=prepared.past_values.shape[1],
            prediction_length=prediction_length,
            freq_prefix_tuning=False,
            freq=None,
            prefer_l1_loss=False,
            prefer_longer_context=True,
        )
        trainer = Trainer(
            model=model,
            args=TrainingArguments(
                output_dir=tempfile.mkdtemp(prefix="b08-ttm-"),
                per_device_eval_batch_size=min(16, max(1, len(prepared.past_values))),
                report_to="none",
            ),
        )
        output = trainer.predict(WindowDataset())
        predictions = output.predictions[0] if isinstance(output.predictions, (tuple, list)) else output.predictions
        return np.asarray(predictions, dtype=float)
```

Update `TTMForecastAdapter.__init__`:

```python
    def __init__(
        self,
        checkpoint: str = DEFAULT_TTM_CHECKPOINT,
        dependency_checker: Callable[[str], bool] | None = None,
        runtime_factory: Callable[[], object] | None = None,
    ) -> None:
        self.checkpoint = checkpoint
        self.dependency_checker = dependency_checker or (lambda name: find_spec(name) is not None)
        self.runtime_factory = runtime_factory or TTMRuntime
```

Implement `_predict_with_ttm`:

```python
    def _predict_with_ttm(self, windows, context_length, prediction_length, allow_download, model_cache_dir):
        try:
            prepared = self.prepare_windows(windows, context_length, prediction_length)
            scaled = self.runtime_factory().predict(prepared, self.checkpoint, prediction_length, allow_download, model_cache_dir)
            if scaled.shape != prepared.future_values.shape:
                return FoundationForecastResult(
                    model_name=self.name,
                    adapter_name=self.adapter_name,
                    status=FoundationModelStatus.UNSUPPORTED_WINDOW_SHAPE,
                    reason=f"TTM prediction shape {scaled.shape} does not match expected {prepared.future_values.shape}",
                    metadata={"checkpoint": self.checkpoint},
                    io_coverage={"numeric_values": True, "stage_token": False, "domain_token": False, "sensor_token": False},
                    dependency_status="available",
                    weight_status="loaded",
                    cache_dir=str(model_cache_dir) if model_cache_dir else None,
                )
            y_hat = scaled * prepared.channel_scale + prepared.channel_center
            return FoundationForecastResult(
                model_name=self.name,
                adapter_name=self.adapter_name,
                status=FoundationModelStatus.AVAILABLE_AND_RAN,
                y_hat=y_hat,
                metadata={"checkpoint": self.checkpoint},
                io_coverage={"numeric_values": True, "stage_token": False, "domain_token": False, "sensor_token": False},
                dependency_status="available",
                weight_status="loaded",
                cache_dir=str(model_cache_dir) if model_cache_dir else None,
            )
        except Exception as exc:
            message = str(exc)
            status = FoundationModelStatus.MISSING_OR_BLOCKED_WEIGHTS if "offline" in message.lower() or "download" in message.lower() else FoundationModelStatus.RUNTIME_FAILED
            return FoundationForecastResult(
                model_name=self.name,
                adapter_name=self.adapter_name,
                status=status,
                reason=message,
                metadata={"checkpoint": self.checkpoint},
                io_coverage={"numeric_values": True, "stage_token": False, "domain_token": False, "sensor_token": False},
                dependency_status="available",
                weight_status="blocked_or_unknown" if status == FoundationModelStatus.MISSING_OR_BLOCKED_WEIGHTS else "unknown",
                cache_dir=str(model_cache_dir) if model_cache_dir else None,
            )
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_ttm_adapter.py -v
```

Expected: PASS without installing TTM dependencies.

- [ ] **Step 5: Commit**

```bash
git add src/b08_model_core/adapters/ttm_adapter.py tests/test_ttm_adapter.py
git commit -m "feat: add lazy ttm inference boundary"
```

## Task 5: Foundation Runner and Baseline Comparison

**Files:**
- Create: `src/b08_model_core/foundation/runner.py`
- Modify: `src/b08_model_core/foundation/__init__.py`
- Test: `tests/test_foundation_runner.py`

- [ ] **Step 1: Write failing runner tests with fake adapters**

Create `tests/test_foundation_runner.py`:

```python
import numpy as np

from b08_model_core.foundation.results import FoundationForecastResult, FoundationModelStatus
from b08_model_core.foundation.runner import FoundationForecastRunner, run_foundation_forecasting
from b08_model_core.simulation.export_dataset import simulate_dataset


class FakeSuccessfulAdapter:
    name = "FakeModel"
    adapter_name = "fake"

    def predict(self, windows, context_length, prediction_length, allow_download=False, model_cache_dir=None):
        truth = np.stack([window.y for window in windows], axis=0)
        return FoundationForecastResult(
            model_name=self.name,
            adapter_name=self.adapter_name,
            status=FoundationModelStatus.AVAILABLE_AND_RAN,
            y_hat=truth.copy(),
            metadata={"checkpoint": "fake"},
            io_coverage={"numeric_values": True},
            dependency_status="available",
            weight_status="loaded",
            cache_dir="fake-cache",
        )


class FakeMissingAdapter:
    name = "TTM"
    adapter_name = "ttm"

    def predict(self, windows, context_length, prediction_length, allow_download=False, model_cache_dir=None):
        return FoundationForecastResult(
            model_name=self.name,
            adapter_name=self.adapter_name,
            status=FoundationModelStatus.MISSING_DEPENDENCY,
            reason="missing",
            metadata={"checkpoint": "fake"},
            io_coverage={"numeric_values": True},
            dependency_status="missing_dependency",
            weight_status="not_attempted",
            cache_dir="fake-cache",
        )


def test_foundation_runner_scores_successful_adapter(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    simulate_dataset(days=3, seed=31, output_path=dataset)

    result = run_foundation_forecasting(
        dataset_path=dataset,
        model_name="fake",
        adapter=FakeSuccessfulAdapter(),
        context_length=64,
        prediction_length=16,
        max_windows=20,
        allow_download=False,
    )

    assert result.foundation_result.status == FoundationModelStatus.AVAILABLE_AND_RAN
    assert result.foundation_result.metrics["mae"] == 0.0
    assert "RobustStageForecaster" in result.baseline_metrics
    assert result.route_recommendation == "direct_reuse_candidate"


def test_foundation_forecast_runner_class_matches_functional_entrypoint(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    simulate_dataset(days=3, seed=33, output_path=dataset)

    runner = FoundationForecastRunner()
    result = runner.run(
        dataset_path=dataset,
        model_name="fake",
        adapter=FakeSuccessfulAdapter(),
        context_length=64,
        prediction_length=16,
        max_windows=20,
        allow_download=False,
    )

    assert result.foundation_result.status == FoundationModelStatus.AVAILABLE_AND_RAN
    assert result.foundation_result.metrics["mae"] == 0.0


def test_foundation_runner_preserves_missing_dependency_status(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    simulate_dataset(days=3, seed=32, output_path=dataset)

    result = run_foundation_forecasting(
        dataset_path=dataset,
        model_name="ttm",
        adapter=FakeMissingAdapter(),
        context_length=64,
        prediction_length=16,
        max_windows=20,
        allow_download=False,
    )

    assert result.foundation_result.status == FoundationModelStatus.MISSING_DEPENDENCY
    assert result.route_recommendation == "no_go_missing_dependency"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_foundation_runner.py -v
```

Expected: FAIL because `b08_model_core.foundation.runner` does not exist.

- [ ] **Step 3: Implement runner**

Create `src/b08_model_core/foundation/runner.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.baselines.seasonal_naive import StageSeasonalNaiveForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.foundation.results import FoundationForecastResult, recommend_route
from b08_model_core.tasks.window_builder import build_model_windows


@dataclass
class FoundationExperimentResult:
    dataset_path: str
    train_count: int
    test_count: int
    context_length: int
    prediction_length: int
    sensor_count: int
    baseline_metrics: dict[str, dict[str, float | None]]
    foundation_result: FoundationForecastResult
    route_recommendation: str
    fallback_candidates: list[str]


def _split_windows(windows: list[object]) -> tuple[list[object], list[object]]:
    split = max(1, int(len(windows) * 0.7))
    return windows[:split], windows[split:] or windows[-1:]


class FoundationForecastRunner:
    def run(
        self,
        dataset_path: str | Path,
        model_name: str,
        adapter: object,
        context_length: int,
        prediction_length: int,
        max_windows: int,
        allow_download: bool,
        model_cache_dir: str | Path | None = None,
    ) -> FoundationExperimentResult:
        df = pd.read_parquet(dataset_path)
        windows = build_model_windows(
            df,
            context_length=context_length,
            prediction_length=prediction_length,
            stride=prediction_length,
        )[:max_windows]
        if len(windows) < 2:
            raise ValueError(f"at least two windows are required; got {len(windows)}")
        train, test = _split_windows(windows)

        robust_preds = RobustStageForecaster().fit(train).predict(test)
        robust_metrics = forecasting_metrics(robust_preds, test)
        seasonal_preds = StageSeasonalNaiveForecaster().fit(train).predict(test)
        seasonal_metrics = forecasting_metrics(seasonal_preds, test)

        foundation_result = adapter.predict(
            test,
            context_length=context_length,
            prediction_length=prediction_length,
            allow_download=allow_download,
            model_cache_dir=model_cache_dir,
        )
        if foundation_result.succeeded and foundation_result.predictions():
            foundation_result.metrics = forecasting_metrics(foundation_result.predictions(), test)

        baseline_metrics = {
            "RobustStageForecaster": robust_metrics,
            "StageSeasonalNaiveForecaster": seasonal_metrics,
        }
        route = recommend_route(foundation_result, baseline_mae=robust_metrics.get("mae"))
        return FoundationExperimentResult(
            dataset_path=str(dataset_path),
            train_count=len(train),
            test_count=len(test),
            context_length=context_length,
            prediction_length=prediction_length,
            sensor_count=len(test[0].sensor_token),
            baseline_metrics=baseline_metrics,
            foundation_result=foundation_result,
            route_recommendation=route,
            fallback_candidates=["FlowState", "TimesFM", "Chronos", "Moirai"],
        )


def run_foundation_forecasting(**kwargs) -> FoundationExperimentResult:
    return FoundationForecastRunner().run(**kwargs)
```

Export from `src/b08_model_core/foundation/__init__.py`.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_foundation_runner.py tests/test_foundation_results.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/b08_model_core/foundation/runner.py src/b08_model_core/foundation/__init__.py tests/test_foundation_runner.py
git commit -m "feat: run foundation forecasting comparisons"
```

## Task 6: Experiment Entry Point and CLI Options

**Files:**
- Modify: `src/b08_model_core/experiments/forecasting.py`
- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Write failing test for baseline mode preserving existing behavior**

Update `tests/test_experiment_scaffold.py::test_forecasting_experiment_scaffold_runs_without_external_weights` to assert the updated report content but keep return code `0`:

```python
assert "Forecasting Foundation Model Experiment" in text
assert "baseline" in text or "skipped_by_user" in text
assert "RobustStageForecaster" in text
assert "StageSeasonalNaiveForecaster" in text
assert "Route Recommendation" in text
```

- [ ] **Step 2: Write failing test for TTM missing dependency exit code**

Add to `tests/test_experiment_scaffold.py`:

```python
def test_forecasting_experiment_ttm_missing_dependency_returns_one_but_writes_report(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "forecasting_ttm.md"
    simulate_dataset(days=3, seed=24, output_path=dataset)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "experiment",
            "forecasting",
            "--dataset",
            str(dataset),
            "--output",
            str(report),
            "--model",
            "ttm",
            "--context-length",
            "64",
            "--prediction-length",
            "16",
            "--max-windows",
            "20",
            "--no-download",
        ],
        text=True,
        capture_output=True,
    )

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "TTM" in text
    assert "Foundation Model Status" in text
    failed_statuses = ["missing_dependency", "missing_or_blocked_weights", "unsupported_window_shape", "runtime_failed"]
    if "available_and_ran" in text:
        assert result.returncode == 0
    else:
        assert result.returncode == 1
        assert any(status in text for status in failed_statuses)
```

This accepts CI environments with optional dependencies installed, but it still enforces the exit-code contract: only `available_and_ran` returns `0`; reportable model failures return `1`.

- [ ] **Step 3: Write failing CLI validation test for new positive lengths**

Add to `tests/test_experiment_scaffold.py`:

```python
def test_forecasting_experiment_rejects_non_positive_context_length(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "forecasting_experiment.md"
    simulate_dataset(days=3, seed=25, output_path=dataset)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "experiment",
            "forecasting",
            "--dataset",
            str(dataset),
            "--output",
            str(report),
            "--context-length",
            "0",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "must be greater than 0" in result.stderr
```

- [ ] **Step 4: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_experiment_scaffold.py -v
```

Expected: FAIL because CLI options and report path do not exist yet.

- [ ] **Step 5: Implement experiment entry point**

Modify `src/b08_model_core/experiments/forecasting.py` to accept model and cache options.

Key behavior:

```python
from b08_model_core.adapters.ttm_adapter import TTMForecastAdapter
from b08_model_core.foundation.reporting import render_foundation_forecasting_report
from b08_model_core.foundation.results import FoundationForecastResult, FoundationModelStatus
from b08_model_core.foundation.runner import run_foundation_forecasting


def _adapter_for(model: str):
    if model == "ttm":
        return TTMForecastAdapter()
    raise ValueError(f"unsupported foundation model: {model}")


def run_forecasting_experiment(
    dataset_path: str | Path,
    output_path: str | Path,
    context_length: int = 128,
    prediction_length: int = 32,
    max_windows: int = 120,
    model: str = "baseline",
    allow_download: bool = False,
    model_cache_dir: str | Path | None = None,
) -> tuple[Path, int]:
    if model == "baseline":
        adapter = _SkippedAdapter()
    else:
        adapter = _adapter_for(model)
    result = run_foundation_forecasting(
        dataset_path=dataset_path,
        model_name=model,
        adapter=adapter,
        context_length=context_length,
        prediction_length=prediction_length,
        max_windows=max_windows,
        allow_download=allow_download,
        model_cache_dir=model_cache_dir,
    )
    text = render_foundation_forecasting_report(
        dataset_path=result.dataset_path,
        train_count=result.train_count,
        test_count=result.test_count,
        context_length=result.context_length,
        prediction_length=result.prediction_length,
        sensor_count=result.sensor_count,
        baseline_metrics=result.baseline_metrics,
        foundation_result=result.foundation_result,
        route_recommendation=result.route_recommendation,
        fallback_candidates=result.fallback_candidates,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    exit_code = 0 if model == "baseline" or result.foundation_result.succeeded else 1
    return output, exit_code
```

Implement `_SkippedAdapter` locally:

```python
class _SkippedAdapter:
    name = "baseline"
    adapter_name = "baseline"

    def predict(self, windows, context_length, prediction_length, allow_download=False, model_cache_dir=None):
        return FoundationForecastResult(
            model_name="baseline",
            adapter_name="baseline",
            status=FoundationModelStatus.SKIPPED_BY_USER,
            reason="baseline-only mode selected",
            io_coverage={"numeric_values": False, "stage_token": False, "domain_token": False, "sensor_token": False},
            dependency_status="not_required",
            weight_status="not_required",
            cache_dir=str(model_cache_dir) if model_cache_dir else None,
        )
```

Keep `candidate_matrix()` status table only if needed; otherwise the new report replaces it.

- [ ] **Step 6: Implement CLI options and exit code behavior**

Modify `src/b08_model_core/cli.py`:

```python
forecasting.add_argument("--model", choices=["baseline", "ttm"], default="baseline")
forecasting.add_argument("--context-length", type=_positive_int, default=128)
forecasting.add_argument("--prediction-length", type=_positive_int, default=32)
forecasting.add_argument("--model-cache-dir")
download = forecasting.add_mutually_exclusive_group()
download.add_argument("--allow-download", action="store_true", default=False)
download.add_argument("--no-download", action="store_false", dest="allow_download")
```

Update dispatch:

```python
if args.command == "experiment" and args.experiment_command == "forecasting":
    _, exit_code = run_forecasting_experiment(
        args.dataset,
        args.output,
        context_length=args.context_length,
        prediction_length=args.prediction_length,
        max_windows=args.max_windows,
        model=args.model,
        allow_download=args.allow_download,
        model_cache_dir=args.model_cache_dir,
    )
    return exit_code
```

- [ ] **Step 7: Run tests**

Run:

```bash
uv run pytest tests/test_experiment_scaffold.py tests/test_foundation_runner.py tests/test_ttm_adapter.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/b08_model_core/experiments/forecasting.py src/b08_model_core/cli.py tests/test_experiment_scaffold.py
git commit -m "feat: add foundation forecasting cli"
```

## Task 7: Optional Dependencies, Cache Ignore Rules, and Lockfile

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `.gitignore`
- Test: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Write failing static test for ignore rules and extras**

Add to `tests/test_experiment_scaffold.py`:

```python
from pathlib import Path
import tomllib


def test_foundation_ttm_extra_and_local_model_caches_are_documented():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = pyproject["project"]["optional-dependencies"]
    assert "foundation-ttm" in extras
    assert any(dep.startswith("granite-tsfm") for dep in extras["foundation-ttm"])

    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "models/" in gitignore
    assert "hf_cache/" in gitignore
    assert ".cache/" in gitignore
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest tests/test_experiment_scaffold.py::test_foundation_ttm_extra_and_local_model_caches_are_documented -v
```

Expected: FAIL because extra and ignore rules are missing.

- [ ] **Step 3: Update pyproject optional dependencies**

Modify `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = ["pytest>=7"]
foundation-ttm = [
  "granite-tsfm>=0.3.6",
  "torch>=2",
  "transformers>=4.40",
  "huggingface_hub>=0.20",
]
```

If implementation-time official docs show a newer required minimum, update the lower bound and mention the source in README.

- [ ] **Step 4: Update ignore rules**

Modify `.gitignore`:

```gitignore
models/
hf_cache/
.cache/
ttm_finetuned_models/
```

Keep existing ignored generated parquet and report rules.

- [ ] **Step 5: Update uv lockfile**

Run:

```bash
uv lock
```

Expected: `uv.lock` updates to include the optional extra resolution.

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/test_experiment_scaffold.py::test_foundation_ttm_extra_and_local_model_caches_are_documented -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock .gitignore tests/test_experiment_scaffold.py
git commit -m "chore: add optional ttm foundation dependencies"
```

## Task 8: README and Progress Ledger

**Files:**
- Modify: `README.md`
- Modify: `details.md`
- Test: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Write failing static documentation test**

Add to `tests/test_experiment_scaffold.py`:

```python
def test_readme_documents_foundation_model_local_weight_workflow():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "foundation-ttm" in text
    assert "--model ttm" in text
    assert "HF_HOME" in text or "model-cache-dir" in text
    assert "模型权重" in text
    assert "不要提交" in text or "不上传 GitHub" in text
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest tests/test_experiment_scaffold.py::test_readme_documents_foundation_model_local_weight_workflow -v
```

Expected: FAIL because README does not yet document the workflow.

- [ ] **Step 3: Update README**

Add a new section after the first forecasting experiment scaffold command:

```markdown
## 真实基础模型推理实验

默认测试和 baseline 不需要下载模型权重。需要运行 TTM 等真实基础模型时，再安装可选依赖：

```bash
uv sync --extra dev --extra foundation-ttm
```

模型权重默认下载到本机 Hugging Face 缓存。也可以指定本仓库外或被 `.gitignore` 忽略的缓存目录：

```bash
HF_HOME=hf_cache uv run b08-model-core experiment forecasting \
  --dataset data/simulated/furnace_fu13_45d.parquet \
  --output reports/forecasting_ttm_experiment.md \
  --model ttm \
  --context-length 512 \
  --prediction-length 96 \
  --max-windows 40 \
  --model-cache-dir hf_cache \
  --allow-download
```

模型权重、`hf_cache/`、`models/`、生成的 parquet 和临时实验报告只保存在本机，不要提交或上传 GitHub。

报告中的判断口径：

- TTM 明显优于 baseline：进入直接引用候选。
- TTM 接近 baseline 且运行稳定：进入 few-shot 或轻量适配候选。
- TTM 较弱但成本低：保留为对照，继续测试 FlowState、TimesFM、Chronos 或 Moirai。
- TTM 无法安装、下载或适配窗口：记录失败原因，转测备用模型。
```

- [ ] **Step 4: Update details.md**

Add a recent update row:

```markdown
| 2026-06-01 | 完成真实基础模型推理实施计划，明确先跑 TTM 等轻量模型，同时保留 FlowState、TimesFM、Chronos、Moirai 等备用路线；要求模型权重只保存在本机。 |
```

After actual implementation later, update `details.md` again with whether inference succeeded or failed.

- [ ] **Step 5: Run docs test**

Run:

```bash
uv run pytest tests/test_experiment_scaffold.py::test_readme_documents_foundation_model_local_weight_workflow -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md details.md tests/test_experiment_scaffold.py
git commit -m "docs: document foundation model inference workflow"
```

## Task 9: Manual TTM Local Verification

**Files:**
- No committed generated files.
- Generated local artifacts must remain ignored:
  - `data/simulated/furnace_fu13_45d.parquet`
  - `reports/forecasting_ttm_experiment.md`
  - `hf_cache/` or standard Hugging Face cache

- [ ] **Step 1: Install optional dependencies locally**

Run:

```bash
uv sync --extra dev --extra foundation-ttm
```

Expected: command completes. If it fails, capture the exact package-resolution error in the implementation notes and do not change core dependencies to force heavyweight packages into base install.

- [ ] **Step 2: Generate simulated data**

Run:

```bash
uv run b08-model-core simulate \
  --days 45 \
  --seed 42 \
  --output data/simulated/furnace_fu13_45d.parquet
```

Expected: ignored parquet file exists under `data/simulated/`.

- [ ] **Step 3: Run baseline-only experiment**

Run:

```bash
uv run b08-model-core experiment forecasting \
  --dataset data/simulated/furnace_fu13_45d.parquet \
  --output reports/forecasting_baseline_experiment.md \
  --model baseline \
  --context-length 128 \
  --prediction-length 32 \
  --max-windows 40
```

Expected: exit code `0`; report contains `skipped_by_user`, `RobustStageForecaster`, and `StageSeasonalNaiveForecaster`.

- [ ] **Step 4: Run TTM experiment with local cache**

Run:

```bash
HF_HOME=hf_cache uv run b08-model-core experiment forecasting \
  --dataset data/simulated/furnace_fu13_45d.parquet \
  --output reports/forecasting_ttm_experiment.md \
  --model ttm \
  --context-length 512 \
  --prediction-length 96 \
  --max-windows 40 \
  --model-cache-dir hf_cache \
  --allow-download
```

Expected:

- Exit code `0`.
- Report contains `available_and_ran`, TTM MAE/RMSE, baseline MAE/RMSE, baseline comparison deltas, local dependency/weight/cache status, IO coverage, and route recommendation.
- If exit code is `1`, the implementation is not complete. Stop the completion path, keep the diagnostic report, and surface the blocker to the user. The report must still exist and contain one of:
  - `missing_dependency`
  - `missing_or_blocked_weights`
  - `unsupported_window_shape`
  - `runtime_failed`

Do not treat a failed TTM run as successful completion of this plan. The stage goal is to run at least one real open-source foundation model locally on simulated FU13 windows. If TTM is blocked, either fix the environment/model integration or write a follow-up plan for the next fallback adapter after user approval.

- [ ] **Step 5: Confirm generated artifacts are ignored**

Run:

```bash
git status --short --ignored
```

Expected: model caches, generated parquet, and transient reports are ignored and not staged.

- [ ] **Step 6: Record manual verification result in details.md**

If TTM runs:

```markdown
| 2026-06-01 | 在 FU13 模拟数据上完成 TTM 本机 zero-shot 推理，报告已能和 baseline 同口径比较，下一步判断是否进入轻量适配或测试备用模型。 |
```

If TTM fails, record it as a blocked attempt, not a completed inference stage:

```markdown
| 2026-06-01 | 尝试在 FU13 模拟数据上运行 TTM，但尚未完成真实基础模型推理闭环；本机报告已记录依赖、权重或运行失败原因，下一步需要修正环境或另行规划备用模型 adapter。 |
```

- [ ] **Step 7: Commit only source/docs changes**

Do not commit generated parquet, ignored reports, or model cache.

```bash
git add details.md
git commit -m "docs: record foundation inference verification"
```

Only run this commit if `details.md` changed after manual verification. If TTM failed, do not continue to the final completion gate until the blocker is resolved or the user approves a fallback-adapter plan.

## Task 10: Final Verification Gate

**Files:**
- No new files expected unless prior tasks changed source/docs.

Do not enter this final gate unless Task 9 produced a TTM report with `available_and_ran` and command exit code `0`. If Task 9 produced a reportable failure, the implementation is blocked rather than complete.

- [ ] **Step 1: Run targeted tests**

Run:

```bash
uv run pytest tests/test_foundation_results.py tests/test_foundation_runner.py tests/test_ttm_adapter.py tests/test_experiment_scaffold.py -v
```

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run:

```bash
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run baseline CLI smoke test**

Run:

```bash
uv run b08-model-core simulate \
  --days 3 \
  --seed 42 \
  --output data/simulated/furnace_fu13_smoke.parquet
uv run b08-model-core experiment forecasting \
  --dataset data/simulated/furnace_fu13_smoke.parquet \
  --output reports/forecasting_baseline_smoke.md \
  --model baseline \
  --max-windows 20
```

Expected: both commands return `0`; report exists and is ignored by git unless intentionally whitelisted.

- [ ] **Step 4: Run whitespace check**

Run:

```bash
git diff --check
```

Expected: no output, exit code `0`.

- [ ] **Step 5: Confirm TTM success evidence is present**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
report = Path("reports/forecasting_ttm_experiment.md")
text = report.read_text(encoding="utf-8")
required = [
    "available_and_ran",
    "Baseline Comparison",
    "Local Model Environment",
    "TTM",
    "Route Recommendation",
]
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit(f"TTM success evidence missing: {missing}")
print("TTM success evidence present")
PY
```

Expected: `TTM success evidence present`. If this fails, do not claim completion.

- [ ] **Step 6: Confirm no large local artifacts are staged**

Run:

```bash
git status --short
```

Expected: only intended source, tests, docs, `pyproject.toml`, and `uv.lock` changes are staged or unstaged. No model weights, `hf_cache/`, `models/`, generated parquet, or transient reports appear as tracked changes.

- [ ] **Step 7: Final commit if needed**

If any source/docs changes remain uncommitted:

```bash
git add <intended-files>
git commit -m "chore: verify foundation inference workflow"
```

- [ ] **Step 8: Final implementation summary**

Report:

- Which model path was implemented first.
- Confirmation that TTM local inference ran with status `available_and_ran`.
- Baseline metrics and foundation model metrics.
- Baseline comparison deltas and route recommendation.
- Report path for local experiment.
- Tests run and pass/fail status.
- Any uncommitted or ignored artifacts left intentionally.

## Implementation Notes

- Use `superpowers:test-driven-development` before implementation work.
- Use `superpowers:verification-before-completion` before claiming task completion.
- Use `superpowers:subagent-driven-development` for task-by-task execution if choosing the recommended execution path.
- Preserve user changes. Do not revert unrelated edits.
- Keep heavyweight model imports inside `TTMRuntime` or another lazy adapter runtime.
- Keep fallback models as route recommendations in this plan. Do not implement multiple model ecosystems until the first TTM path is proven or fails with a documented reason.
- If actual `granite-tsfm` runtime API differs from the plan snippets, adapt only inside `TTMRuntime` and keep all tests for dependency handling, report status, CLI behavior, and artifact ignoring intact.
