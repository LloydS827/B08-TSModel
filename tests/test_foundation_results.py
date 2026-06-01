import numpy as np
import pytest

from b08_model_core.foundation import render_foundation_report
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.foundation.results import (
    FoundationForecastResult,
    FoundationModelStatus,
    recommend_route,
)


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
    assert metrics["rmse"] == pytest.approx(0.3535533905932738)
    assert metrics["interval_coverage"] == 1.0


def test_foundation_model_status_values_are_stable_contract():
    assert [status.value for status in FoundationModelStatus] == [
        "available_and_ran",
        "missing_dependency",
        "missing_or_blocked_weights",
        "unsupported_window_shape",
        "runtime_failed",
        "skipped_by_user",
    ]


def test_foundation_result_marks_success_only_when_model_ran():
    success = FoundationForecastResult(
        model_name="FakeModel",
        adapter_name="fake",
        status=FoundationModelStatus.AVAILABLE_AND_RAN,
    )
    failures = [
        FoundationForecastResult(model_name="TTM", adapter_name="ttm", status=status)
        for status in FoundationModelStatus
        if status is not FoundationModelStatus.AVAILABLE_AND_RAN
    ]

    assert success.succeeded is True
    assert all(result.succeeded is False for result in failures)


def test_foundation_result_predictions_omit_missing_arrays():
    y_hat = np.array([[[1.0]]])
    q_low = np.array([[[0.5]]])
    q_high = np.array([[[1.5]]])

    point_result = FoundationForecastResult(
        model_name="FakeModel",
        adapter_name="fake",
        status=FoundationModelStatus.AVAILABLE_AND_RAN,
        y_hat=y_hat,
    )
    interval_result = FoundationForecastResult(
        model_name="FakeModel",
        adapter_name="fake",
        status=FoundationModelStatus.AVAILABLE_AND_RAN,
        y_hat=y_hat,
        q_low=q_low,
        q_high=q_high,
    )
    empty_result = FoundationForecastResult(
        model_name="FakeModel",
        adapter_name="fake",
        status=FoundationModelStatus.RUNTIME_FAILED,
    )

    point_predictions = point_result.predictions()
    interval_predictions = interval_result.predictions()

    assert set(point_predictions) == {"y_hat"}
    assert point_predictions["y_hat"] is y_hat
    assert set(interval_predictions) == {"y_hat", "q_low", "q_high"}
    assert interval_predictions["y_hat"] is y_hat
    assert interval_predictions["q_low"] is q_low
    assert interval_predictions["q_high"] is q_high
    assert empty_result.predictions() == {}


def test_route_recommendation_uses_status_before_metrics():
    routes = {
        FoundationModelStatus.MISSING_DEPENDENCY: "no_go_missing_dependency",
        FoundationModelStatus.MISSING_OR_BLOCKED_WEIGHTS: "no_go_missing_or_blocked_weights",
        FoundationModelStatus.UNSUPPORTED_WINDOW_SHAPE: "no_go_unsupported_window_shape",
        FoundationModelStatus.RUNTIME_FAILED: "no_go_runtime_failed",
        FoundationModelStatus.SKIPPED_BY_USER: "baseline_only",
    }

    for status, route in routes.items():
        assert (
            recommend_route(
                FoundationForecastResult(model_name="TTM", adapter_name="ttm", status=status, metrics={"mae": 1.0}),
                baseline_mae=9.0,
            )
            == route
        )


def test_route_recommendation_uses_baseline_comparison_when_successful():
    assert (
        recommend_route(
            FoundationForecastResult(
                model_name="TTM",
                adapter_name="ttm",
                status=FoundationModelStatus.AVAILABLE_AND_RAN,
                metrics={"mae": 8.0},
            ),
            baseline_mae=9.0,
        )
        == "direct_reuse_candidate"
    )
    assert (
        recommend_route(
            FoundationForecastResult(
                model_name="TTM",
                adapter_name="ttm",
                status=FoundationModelStatus.AVAILABLE_AND_RAN,
                metrics={"mae": 9.1},
            ),
            baseline_mae=9.0,
        )
        == "fine_tune_candidate"
    )
    assert (
        recommend_route(
            FoundationForecastResult(
                model_name="TTM",
                adapter_name="ttm",
                status=FoundationModelStatus.AVAILABLE_AND_RAN,
                metrics={"mae": 12.0},
            ),
            baseline_mae=9.0,
        )
        == "fallback_comparator"
    )
    assert (
        recommend_route(
            FoundationForecastResult(
                model_name="TTM",
                adapter_name="ttm",
                status=FoundationModelStatus.AVAILABLE_AND_RAN,
            ),
            baseline_mae=9.0,
        )
        == "fallback_comparator"
    )
    assert (
        recommend_route(
            FoundationForecastResult(
                model_name="TTM",
                adapter_name="ttm",
                status=FoundationModelStatus.AVAILABLE_AND_RAN,
                metrics={"mae": 8.0},
            ),
            baseline_mae=None,
        )
        == "fallback_comparator"
    )


def test_render_foundation_report_includes_successful_model_comparison():
    dataset_summary = {
        "dataset": "FU13 simulated 45d",
        "windows": 24,
        "horizon": 12,
        "sensors": 5,
    }
    baseline_metrics = {
        "RobustStageForecaster": {
            "mae": 2.5,
            "rmse": 3.0,
            "interval_coverage": None,
        }
    }
    foundation_result = FoundationForecastResult(
        model_name="TTM",
        adapter_name="ttm",
        status=FoundationModelStatus.AVAILABLE_AND_RAN,
        reason="ran on local simulated windows",
        metrics={"mae": 2.0, "rmse": 2.75, "interval_coverage": None},
        io_coverage={"point_forecast": True, "prediction_interval": False},
        dependency_status="installed",
        weight_status="cached",
        cache_dir="/private/tmp/b08-model-cache",
    )

    report = render_foundation_report(
        dataset_summary=dataset_summary,
        baseline_metrics=baseline_metrics,
        foundation_result=foundation_result,
        route_recommendation="direct_reuse_candidate",
        fallback_candidates=["FlowState", "TimesFM"],
    )

    assert "# Forecasting Foundation Model Experiment" in report
    for section in [
        "Dataset Summary",
        "Selected Foundation Model",
        "Foundation Model Status",
        "Baseline Comparison",
        "Local Model Environment",
        "IO Coverage",
        "Route Recommendation",
    ]:
        assert section in report
    assert "TTM" in report
    assert "available_and_ran" in report
    assert "RobustStageForecaster" in report
    assert "mae: 2.500000" in report
    assert "rmse: 3.000000" in report
    assert "foundation mae: 2.000000" in report
    assert "foundation rmse: 2.750000" in report
    assert "MAE delta: -0.500000" in report
    assert "RMSE delta: -0.250000" in report
    assert "interval_coverage: not_available" in report
    assert "cache_dir: /private/tmp/b08-model-cache" in report
    assert "dependency_status: installed" in report
    assert "weight_status: cached" in report
    assert "fallback candidates: FlowState, TimesFM" in report


def test_render_foundation_report_includes_missing_dependency_reason():
    foundation_result = FoundationForecastResult(
        model_name="TimesFM",
        adapter_name="timesfm",
        status=FoundationModelStatus.MISSING_DEPENDENCY,
        reason="timesfm package is not installed",
        dependency_status="missing: timesfm",
        weight_status="not_checked",
        cache_dir=None,
    )

    report = render_foundation_report(
        dataset_summary={"dataset": "FU13 simulated smoke"},
        baseline_metrics={"RobustStageForecaster": {"mae": 1.0, "rmse": None}},
        foundation_result=foundation_result,
        route_recommendation="no_go_missing_dependency",
        fallback_candidates=["TTM"],
    )

    assert "TimesFM" in report
    assert "missing_dependency" in report
    assert "reason: timesfm package is not installed" in report
    assert "cache_dir: not_available" in report
    assert "dependency_status: missing: timesfm" in report
    assert "weight_status: not_checked" in report
    assert "Route Recommendation" in report
    assert "no_go_missing_dependency" in report


def test_render_foundation_report_handles_empty_and_missing_sections():
    foundation_result = FoundationForecastResult(
        model_name="BaselineOnly",
        adapter_name="baseline",
        status=FoundationModelStatus.SKIPPED_BY_USER,
    )

    report = render_foundation_report(
        dataset_summary={},
        baseline_metrics={},
        foundation_result=foundation_result,
        route_recommendation="baseline_only",
        fallback_candidates=[],
    )

    assert "Dataset Summary\n- not_available" in report
    assert "Baseline Comparison\n- not_available" in report
    assert "MAE delta: not_available" in report
    assert "RMSE delta: not_available" in report
    assert "fallback candidates: not_available" in report
    assert "IO Coverage\n- not_available" in report


def test_render_foundation_report_handles_none_baseline_metrics():
    foundation_result = FoundationForecastResult(
        model_name="TTM",
        adapter_name="ttm",
        status=FoundationModelStatus.MISSING_OR_BLOCKED_WEIGHTS,
        reason="offline cache miss",
        dependency_status="installed",
        weight_status="blocked_or_unknown",
    )

    report = render_foundation_report(
        dataset_summary=None,
        baseline_metrics={"RobustStageForecaster": None},
        foundation_result=foundation_result,
        route_recommendation="no_go_missing_or_blocked_weights",
        fallback_candidates=[],
    )

    assert "Dataset Summary\n- not_available" in report
    assert "- RobustStageForecaster\n  - not_available" in report
    assert "missing_or_blocked_weights" in report
    assert "reason: offline cache miss" in report
