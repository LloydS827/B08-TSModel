from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from b08_model_core.adapters.ttm_adapter import TTMForecastAdapter
from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.baselines.seasonal_naive import StageSeasonalNaiveForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.experiments.forecasting import BaselineOnlyAdapter
from b08_model_core.foundation.results import FoundationForecastResult
from b08_model_core.tasks.window_builder import build_model_windows


SUPPORTED_REAL_DATA_FORECAST_MODELS = {"baseline", "ttm"}
SUPPORTED_WINDOW_MODES = {"stage-local", "cross-stage"}


@dataclass
class RealForecastingResult:
    model: str
    window_mode: str
    train_windows: int
    test_windows: int
    baseline_metrics: dict[str, dict[str, float | None]]
    foundation_result: FoundationForecastResult
    grouped_metrics_source: str
    sensor_metrics: dict[str, dict[str, float | int | None]]
    scenario_metrics: dict[str, dict[str, float | int | None]]


def run_real_data_forecasting(
    dataset_path: str | Path,
    *,
    model: str,
    window_mode: str,
    context_length: int,
    prediction_length: int,
    max_windows: int,
    allow_download: bool,
    model_cache_dir: str | None,
    dependency_checker: Callable[[str], bool] | None = None,
    sensor_scenario: Mapping[str, str] | None = None,
) -> RealForecastingResult:
    if model not in SUPPORTED_REAL_DATA_FORECAST_MODELS:
        raise ValueError(f"unsupported real data forecasting model: {model}")
    if window_mode not in SUPPORTED_WINDOW_MODES:
        raise ValueError(f"unsupported real data forecasting window_mode: {window_mode}")
    if context_length <= 0:
        raise ValueError("context_length must be greater than 0")
    if prediction_length <= 0:
        raise ValueError("prediction_length must be greater than 0")
    if max_windows <= 0:
        raise ValueError("max_windows must be greater than 0")

    df = pd.read_parquet(dataset_path)
    windows = build_model_windows(
        df,
        context_length=context_length,
        prediction_length=prediction_length,
        stride=prediction_length,
        allow_cross_stage=(window_mode == "cross-stage"),
    )[:max_windows]
    if len(windows) < 2:
        raise ValueError(f"not enough windows for real data forecasting: need at least 2, got {len(windows)}")

    split = max(1, int(len(windows) * 0.7))
    train = windows[:split]
    test = windows[split:]
    if not test:
        raise ValueError("not enough windows for real data forecasting test split")

    robust_predictions = RobustStageForecaster().fit(train).predict(test)
    seasonal_predictions = StageSeasonalNaiveForecaster().fit(train).predict(test)
    baseline_metrics = {
        "RobustStageForecaster": forecasting_metrics(robust_predictions, test),
        "StageSeasonalNaiveForecaster": forecasting_metrics(seasonal_predictions, test),
    }

    adapter = _adapter_for_model(model, dependency_checker)
    foundation_result = adapter.predict(
        test,
        context_length=context_length,
        prediction_length=prediction_length,
        allow_download=allow_download,
        model_cache_dir=model_cache_dir,
    )
    if foundation_result.succeeded and foundation_result.predictions():
        foundation_result.metrics = forecasting_metrics(foundation_result.predictions(), test)

    metrics_predictions = foundation_result.predictions() if foundation_result.succeeded else {}
    grouped_metrics_source = "foundation_model" if metrics_predictions else "RobustStageForecaster fallback"
    if not metrics_predictions:
        metrics_predictions = robust_predictions
    domain_by_sensor = df.drop_duplicates("sensor_id").set_index("sensor_id")["domain"].to_dict()

    return RealForecastingResult(
        model=foundation_result.model_name,
        window_mode=window_mode,
        train_windows=len(train),
        test_windows=len(test),
        baseline_metrics=baseline_metrics,
        foundation_result=foundation_result,
        grouped_metrics_source=grouped_metrics_source,
        sensor_metrics=_metrics_by_sensor(metrics_predictions, test),
        scenario_metrics=_metrics_by_scenario(
            metrics_predictions,
            test,
            sensor_scenario=sensor_scenario or {},
            domain_by_sensor=domain_by_sensor,
        ),
    )


def render_real_data_forecasting_report(result: RealForecastingResult) -> str:
    lines = [
        "# Real FU13 Forecasting",
        "",
        "## Dataset Summary",
        f"- model: {result.model}",
        f"- window_mode: {result.window_mode}",
        f"- train_windows: {result.train_windows}",
        f"- test_windows: {result.test_windows}",
        "",
        "## Foundation Model Status",
        f"- status: {result.foundation_result.status.value}",
        f"- status_reason: {_format_value(result.foundation_result.reason)}",
        f"- dependency_status: {_format_value(result.foundation_result.dependency_status)}",
        f"- weight_status: {_format_value(result.foundation_result.weight_status)}",
        f"- cache_dir: {_format_value(result.foundation_result.cache_dir)}",
        "",
        "## Baseline Comparison",
    ]
    lines.extend(_metric_table(result.baseline_metrics, label_name="model"))
    if result.foundation_result.metrics:
        lines.extend(["", "## Foundation Metrics"])
        lines.extend(_metric_table({"foundation": result.foundation_result.metrics}, label_name="model"))
    lines.extend(["", "## Sensor Metrics", f"- grouped_metrics_source: {result.grouped_metrics_source}", ""])
    lines.extend(_metric_table(result.sensor_metrics, label_name="sensor"))
    lines.extend(["", "## Scenario Metrics", f"- grouped_metrics_source: {result.grouped_metrics_source}", ""])
    lines.extend(_metric_table(result.scenario_metrics, label_name="scenario"))
    return "\n".join(lines) + "\n"


def _adapter_for_model(model: str, dependency_checker: Callable[[str], bool] | None) -> object:
    if model == "baseline":
        return BaselineOnlyAdapter()
    if model == "ttm":
        if dependency_checker is None:
            return TTMForecastAdapter()
        return TTMForecastAdapter(dependency_checker=dependency_checker)
    raise ValueError(f"unsupported real data forecasting model: {model}")


def _metrics_by_sensor(
    predictions: Mapping[str, np.ndarray],
    windows: list[object],
) -> dict[str, dict[str, float | int | None]]:
    truth = np.stack([window.y for window in windows], axis=0)
    y_hat = np.asarray(predictions["y_hat"], dtype=float)
    sensors = list(getattr(windows[0], "sensor_token"))
    metrics: dict[str, dict[str, float | int | None]] = {}
    for index, sensor in enumerate(sensors):
        error = y_hat[:, :, index] - truth[:, :, index]
        metrics[str(sensor)] = _error_metrics(error, count=int(error.size))
    return metrics


def _metrics_by_scenario(
    predictions: Mapping[str, np.ndarray],
    windows: list[object],
    *,
    sensor_scenario: Mapping[str, str],
    domain_by_sensor: Mapping[str, str],
) -> dict[str, dict[str, float | int | None]]:
    truth = np.stack([window.y for window in windows], axis=0)
    y_hat = np.asarray(predictions["y_hat"], dtype=float)
    sensors = list(getattr(windows[0], "sensor_token"))
    grouped: dict[str, list[int]] = {}
    for index, sensor in enumerate(sensors):
        sensor_id = str(sensor)
        scenario = sensor_scenario.get(sensor_id) or domain_by_sensor.get(sensor_id) or "unmapped_sensor"
        grouped.setdefault(str(scenario), []).append(index)

    metrics: dict[str, dict[str, float | int | None]] = {}
    for scenario, indices in grouped.items():
        error = y_hat[:, :, indices] - truth[:, :, indices]
        metrics[scenario] = _error_metrics(error, count=int(error.size))
    return metrics


def _error_metrics(error: np.ndarray, *, count: int) -> dict[str, float | int | None]:
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "count": count,
    }


def _metric_table(metrics: Mapping[str, Mapping[str, float | int | None] | None], *, label_name: str) -> list[str]:
    if not metrics:
        return ["- not_available"]
    headers = [_format_markdown_cell(value) for value in [label_name, "mae", "rmse", "interval_coverage", "count"]]
    rows = ["| " + " | ".join(headers) + " |", "| --- | --- | --- | --- | --- |"]
    for label, values in metrics.items():
        if not values:
            rows.append(
                "| "
                + " | ".join(
                    [
                        _format_markdown_cell(label),
                        "not_available",
                        "not_available",
                        "not_available",
                        "not_available",
                    ]
                )
                + " |"
            )
            continue
        rows.append(
            "| "
            + " | ".join(
                [
                    _format_markdown_cell(label),
                    _format_metric(values.get("mae")),
                    _format_metric(values.get("rmse")),
                    _format_metric(values.get("interval_coverage")),
                    _format_metric(values.get("count")),
                ]
            )
            + " |"
        )
    return rows


def _format_metric(value: float | int | None) -> str:
    if value is None:
        return "not_available"
    if isinstance(value, int):
        return str(value)
    return f"{value:.6f}"


def _format_markdown_cell(value: object) -> str:
    return str(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("|", "\\|")


def _format_value(value: object) -> str:
    if value is None or value == "":
        return "not_available"
    return str(value)
