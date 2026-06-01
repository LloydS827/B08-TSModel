from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from b08_model_core.foundation import (
    FoundationForecastResult,
    FoundationForecastRunner,
    FoundationModelStatus,
    run_foundation_forecasting,
)


def _write_dataset(path, points: int = 12) -> None:
    timestamps = pd.date_range("2026-01-01", periods=points, freq="min")
    rows = []
    for index, timestamp in enumerate(timestamps):
        for sensor_id, offset, domain in [
            ("pressure", 0.0, "atmosphere"),
            ("temperature", 100.0, "thermal"),
        ]:
            rows.append(
                {
                    "timestamp": timestamp,
                    "device_id": "FU13",
                    "batch_id": "batch-001",
                    "stage": "melting",
                    "sensor_id": sensor_id,
                    "value": float(index + offset),
                    "unit": "arb",
                    "domain": domain,
                    "quality_flag": "good",
                    "degradation_label": "normal",
                    "failure_proxy": False,
                }
            )
    pd.DataFrame(rows).to_parquet(path)


class TruthAdapter:
    def __init__(self) -> None:
        self.calls = []

    def predict(self, windows, *, context_length, prediction_length, allow_download, model_cache_dir):
        self.calls.append(
            {
                "windows": windows,
                "context_length": context_length,
                "prediction_length": prediction_length,
                "allow_download": allow_download,
                "model_cache_dir": model_cache_dir,
            }
        )
        return FoundationForecastResult(
            model_name="FakeTruth",
            adapter_name="fake_truth",
            status=FoundationModelStatus.AVAILABLE_AND_RAN,
            y_hat=np.stack([window.y for window in windows], axis=0),
        )


class MissingDependencyAdapter:
    def predict(self, windows, *, context_length, prediction_length, allow_download, model_cache_dir):
        return FoundationForecastResult(
            model_name="FakeMissing",
            adapter_name="fake_missing",
            status=FoundationModelStatus.MISSING_DEPENDENCY,
            reason="optional package is missing",
        )


def test_successful_adapter_gets_foundation_metrics_and_direct_reuse_route(tmp_path):
    dataset_path = tmp_path / "fu13.parquet"
    _write_dataset(dataset_path)
    adapter = TruthAdapter()

    result = run_foundation_forecasting(
        dataset_path=dataset_path,
        model_name="FakeTruth",
        adapter=adapter,
        context_length=3,
        prediction_length=2,
        max_windows=4,
        allow_download=False,
        model_cache_dir="/private/tmp/b08-model-cache",
    )

    assert result.dataset_path == str(dataset_path)
    assert result.model_name == "FakeTruth"
    assert result.train_count == 2
    assert result.test_count == 2
    assert result.context_length == 3
    assert result.prediction_length == 2
    assert result.sensor_count == 2
    assert result.foundation_result.metrics["mae"] == 0.0
    assert result.route_recommendation == "direct_reuse_candidate"
    assert result.fallback_candidates == ["FlowState", "TimesFM", "Chronos", "Moirai"]
    assert set(result.baseline_metrics) == {"RobustStageForecaster", "StageSeasonalNaiveForecaster"}
    assert result.baseline_metrics["RobustStageForecaster"]["mae"] > 0.0
    assert adapter.calls[0]["allow_download"] is False
    assert adapter.calls[0]["model_cache_dir"] == "/private/tmp/b08-model-cache"


def test_runner_class_matches_convenience_function(tmp_path):
    dataset_path = tmp_path / "fu13.parquet"
    _write_dataset(dataset_path)

    class_result = FoundationForecastRunner().run(
        dataset_path=dataset_path,
        model_name="FakeTruth",
        adapter=TruthAdapter(),
        context_length=3,
        prediction_length=2,
        max_windows=4,
        allow_download=False,
    )
    function_result = run_foundation_forecasting(
        dataset_path=dataset_path,
        model_name="FakeTruth",
        adapter=TruthAdapter(),
        context_length=3,
        prediction_length=2,
        max_windows=4,
        allow_download=False,
    )

    assert class_result.train_count == function_result.train_count
    assert class_result.test_count == function_result.test_count
    assert class_result.baseline_metrics == function_result.baseline_metrics
    assert class_result.foundation_result.metrics == function_result.foundation_result.metrics
    assert class_result.route_recommendation == function_result.route_recommendation


def test_missing_dependency_preserves_status_route_and_baseline_metrics(tmp_path):
    dataset_path = tmp_path / "fu13.parquet"
    _write_dataset(dataset_path)

    result = run_foundation_forecasting(
        dataset_path=dataset_path,
        model_name="FakeMissing",
        adapter=MissingDependencyAdapter(),
        context_length=3,
        prediction_length=2,
        max_windows=4,
        allow_download=False,
    )

    assert result.foundation_result.status == FoundationModelStatus.MISSING_DEPENDENCY
    assert result.foundation_result.metrics == {}
    assert result.route_recommendation == "no_go_missing_dependency"
    assert result.baseline_metrics["RobustStageForecaster"]["mae"] > 0.0
    assert result.baseline_metrics["StageSeasonalNaiveForecaster"]["mae"] > 0.0


def test_runner_raises_value_error_when_dataset_has_too_few_windows(tmp_path):
    dataset_path = tmp_path / "too_short.parquet"
    _write_dataset(dataset_path, points=4)

    with pytest.raises(ValueError, match="not enough windows"):
        run_foundation_forecasting(
            dataset_path=dataset_path,
            model_name="FakeTruth",
            adapter=TruthAdapter(),
            context_length=3,
            prediction_length=2,
            max_windows=4,
            allow_download=False,
        )


def test_runner_rejects_non_positive_max_windows(tmp_path):
    dataset_path = tmp_path / "fu13.parquet"
    _write_dataset(dataset_path)

    with pytest.raises(ValueError, match="max_windows"):
        run_foundation_forecasting(
            dataset_path=dataset_path,
            model_name="FakeTruth",
            adapter=TruthAdapter(),
            context_length=3,
            prediction_length=2,
            max_windows=0,
            allow_download=False,
        )
