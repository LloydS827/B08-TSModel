import numpy as np

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
    assert metrics["rmse"] == 0.3535533905932738
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
