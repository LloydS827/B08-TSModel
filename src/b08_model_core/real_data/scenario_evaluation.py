from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from b08_model_core.adapters.ttm_adapter import TTMForecastAdapter
from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.baselines.rolling import RollingSensorForecaster
from b08_model_core.baselines.seasonal_naive import StageSeasonalNaiveForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.experiments.forecasting import BaselineOnlyAdapter
from b08_model_core.foundation import FoundationForecastResult, FoundationModelStatus
from b08_model_core.real_data.fu13_config import FU13RealDataConfig
from b08_model_core.tasks.window_builder import build_model_windows


QUALITY_MODES = {"all", "good_only", "drop_invalid", "drop_unassigned_cycle"}
STAGE_SCOPES = {"related", "with_waiting"}
SUPPORTED_SCENARIO_EVALUATION_MODELS = {"baseline", "ttm"}


@dataclass
class ScenarioSelectionSummary:
    scenario: str
    sensor_ids: list[str]
    related_stages: list[str]
    waiting_stages: list[str]
    stage_scope: str
    quality_mode: str
    input_rows: int
    selected_rows: int
    waiting_rows: int
    quality_counts: dict[str, int]


@dataclass
class ScenarioRunResult:
    quality_mode: str
    stage_scope: str
    selection: ScenarioSelectionSummary
    train_windows: int
    test_windows: int
    metrics: dict[str, dict[str, float | int | None]]
    foundation_result: FoundationForecastResult
    candidate_signal: dict[str, object]


@dataclass
class ScenarioEvaluationResult:
    scenario: str
    model: str
    context_length: int
    prediction_length: int
    max_windows: int
    rolling_window_size: int
    runs: list[ScenarioRunResult]


def select_scenario_observations(
    df: pd.DataFrame,
    cfg: FU13RealDataConfig,
    *,
    scenario: str,
    quality_mode: str,
    stage_scope: str,
) -> tuple[pd.DataFrame, ScenarioSelectionSummary]:
    if quality_mode not in QUALITY_MODES:
        raise ValueError(f"unsupported quality_mode: {quality_mode}")
    if stage_scope not in STAGE_SCOPES:
        raise ValueError(f"unsupported stage_scope: {stage_scope}")

    sensors = [sensor for sensor in cfg.sensors if sensor.scenario == scenario]
    if not sensors:
        raise ValueError(f"unknown scenario: {scenario}")

    sensor_ids = [sensor.sensor_id for sensor in sensors]
    related_stages = _ordered_unique(stage for sensor in sensors for stage in sensor.related_stages)
    waiting_stages = list(cfg.cycle_rules.waiting_stages)
    allowed_stages = related_stages if stage_scope == "related" else _ordered_unique([*related_stages, *waiting_stages])

    mask = (
        (df["device_id"] == cfg.device_id)
        & df["sensor_id"].isin(sensor_ids)
        & df["stage"].isin(allowed_stages)
    )
    selected = df[mask].copy()
    selected = _apply_quality_mode(selected, quality_mode)
    waiting_rows = int(selected["stage"].isin(waiting_stages).sum())
    summary = ScenarioSelectionSummary(
        scenario=scenario,
        sensor_ids=sensor_ids,
        related_stages=related_stages,
        waiting_stages=waiting_stages,
        stage_scope=stage_scope,
        quality_mode=quality_mode,
        input_rows=int(len(df)),
        selected_rows=int(len(selected)),
        waiting_rows=waiting_rows,
        quality_counts={str(k): int(v) for k, v in selected["quality_flag"].value_counts().items()},
    )
    return selected, summary


def run_scenario_evaluation(
    dataset_path: str | Path,
    cfg: FU13RealDataConfig,
    *,
    scenario: str,
    model: str,
    quality_modes: Sequence[str],
    stage_scopes: Sequence[str],
    context_length: int,
    prediction_length: int,
    max_windows: int,
    rolling_window_size: int,
    allow_download: bool,
    model_cache_dir: str | None,
) -> ScenarioEvaluationResult:
    if model not in SUPPORTED_SCENARIO_EVALUATION_MODELS:
        raise ValueError(f"unsupported scenario evaluation model: {model}")
    if context_length <= 0:
        raise ValueError("context_length must be greater than 0")
    if prediction_length <= 0:
        raise ValueError("prediction_length must be greater than 0")
    if max_windows <= 0:
        raise ValueError("max_windows must be greater than 0")

    df = pd.read_parquet(dataset_path)
    runs: list[ScenarioRunResult] = []
    for quality_mode in quality_modes:
        for stage_scope in stage_scopes:
            selected, selection = select_scenario_observations(
                df,
                cfg,
                scenario=scenario,
                quality_mode=quality_mode,
                stage_scope=stage_scope,
            )
            windows = build_model_windows(
                selected,
                context_length=context_length,
                prediction_length=prediction_length,
                stride=prediction_length,
                allow_cross_stage=True,
            )[:max_windows]
            if len(windows) < 2:
                runs.append(_not_enough_windows_run(quality_mode, stage_scope, selection, train_windows=len(windows)))
                continue

            split = max(1, int(len(windows) * 0.7))
            train = windows[:split]
            test = windows[split:]
            if not test:
                runs.append(_not_enough_windows_run(quality_mode, stage_scope, selection, train_windows=len(train)))
                continue

            robust_predictions = RobustStageForecaster().fit(train).predict(test)
            seasonal_predictions = StageSeasonalNaiveForecaster().fit(train).predict(test)
            rolling_predictions = RollingSensorForecaster(window_size=rolling_window_size).fit(train).predict(test)
            metrics: dict[str, dict[str, float | int | None]] = {
                "RobustStageForecaster": forecasting_metrics(robust_predictions, test),
                "StageSeasonalNaiveForecaster": forecasting_metrics(seasonal_predictions, test),
                "RollingSensorForecaster": forecasting_metrics(rolling_predictions, test),
            }

            adapter = _adapter_for_model(model)
            foundation_result = adapter.predict(
                test,
                context_length=context_length,
                prediction_length=prediction_length,
                allow_download=allow_download,
                model_cache_dir=model_cache_dir,
            )
            candidate_predictions = rolling_predictions
            if foundation_result.succeeded and foundation_result.predictions():
                foundation_metrics = forecasting_metrics(foundation_result.predictions(), test)
                foundation_result.metrics = foundation_metrics
                metrics[foundation_result.model_name] = foundation_metrics
                candidate_predictions = foundation_result.predictions()

            runs.append(
                ScenarioRunResult(
                    quality_mode=quality_mode,
                    stage_scope=stage_scope,
                    selection=selection,
                    train_windows=len(train),
                    test_windows=len(test),
                    metrics=metrics,
                    foundation_result=foundation_result,
                    candidate_signal=_candidate_signal_summary(candidate_predictions, test),
                )
            )

    return ScenarioEvaluationResult(
        scenario=scenario,
        model=_scenario_model_name(model),
        context_length=context_length,
        prediction_length=prediction_length,
        max_windows=max_windows,
        rolling_window_size=rolling_window_size,
        runs=runs,
    )


def render_scenario_evaluation_report(result: ScenarioEvaluationResult) -> str:
    lines = [
        "# Leak Current Scenario Evaluation",
        "",
        (
            "This report evaluates forecasting residuals as candidate residual signals, not a failure prediction, "
            "RUL, maintenance recommendation, or production alarm."
        ),
        "本报告仅评估预测残差作为候选异常信号，不是故障预测、RUL、维护建议或生产报警。",
        "",
        "## Summary",
        f"- scenario: {_format_value(result.scenario)}",
        f"- model: {_format_value(result.model)}",
        f"- context_length: {result.context_length}",
        f"- prediction_length: {result.prediction_length}",
        f"- max_windows: {result.max_windows}",
        f"- rolling_window_size: {result.rolling_window_size}",
    ]
    for run in result.runs:
        lines.extend(
            [
                "",
                f"## Run: quality={_format_value(run.quality_mode)}, stage_scope={_format_value(run.stage_scope)}",
                "",
                "### Selection",
                f"- input_rows: {run.selection.input_rows}",
                f"- selected_rows: {run.selection.selected_rows}",
                f"- waiting_rows: {run.selection.waiting_rows}",
                f"- related_stages: {_format_value(', '.join(run.selection.related_stages))}",
                f"- train_windows: {run.train_windows}",
                f"- test_windows: {run.test_windows}",
                "",
                "### Metrics",
            ]
        )
        lines.extend(_metric_table(run.metrics, label_name="model"))
        if run.foundation_result.metrics:
            lines.extend(["", "### Foundation Metrics"])
            lines.extend(_metric_table({run.foundation_result.model_name: run.foundation_result.metrics}, label_name="model"))
        lines.extend(
            [
                "",
                "### Candidate Residual Signals",
                "candidate residual signal only.",
            ]
        )
        lines.extend(_candidate_signal_table(run.candidate_signal))
        lines.extend(["", "### Top Residual Windows"])
        lines.extend(_top_windows_table(run.candidate_signal.get("top_windows")))
        lines.extend(["", "Boundary note: candidate residual signal only."])
    return "\n".join(lines) + "\n"


def _apply_quality_mode(df: pd.DataFrame, quality_mode: str) -> pd.DataFrame:
    if quality_mode == "all":
        return df
    if quality_mode == "good_only":
        return df[df["quality_flag"] == "good"].copy()
    if quality_mode == "drop_invalid":
        return df[df["quality_flag"] != "invalid"].copy()
    if quality_mode == "drop_unassigned_cycle":
        return df[df["quality_flag"] != "unassigned_cycle"].copy()
    raise ValueError(f"unsupported quality_mode: {quality_mode}")


def _ordered_unique(values) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _adapter_for_model(model: str) -> object:
    if model == "baseline":
        return BaselineOnlyAdapter()
    if model == "ttm":
        return TTMForecastAdapter()
    raise ValueError(f"unsupported scenario evaluation model: {model}")


def _scenario_model_name(model: str) -> str:
    if model == "baseline":
        return BaselineOnlyAdapter.name
    if model == "ttm":
        return TTMForecastAdapter.name
    raise ValueError(f"unsupported scenario evaluation model: {model}")


def _not_enough_windows_run(
    quality_mode: str,
    stage_scope: str,
    selection: ScenarioSelectionSummary,
    *,
    train_windows: int,
) -> ScenarioRunResult:
    foundation_result = FoundationForecastResult(
        model_name="not_available",
        adapter_name="scenario_evaluation",
        status=FoundationModelStatus.SKIPPED_BY_USER,
        reason="not enough windows for scenario evaluation",
        dependency_status="not_required",
        weight_status="not_attempted",
    )
    return ScenarioRunResult(
        quality_mode=quality_mode,
        stage_scope=stage_scope,
        selection=selection,
        train_windows=train_windows,
        test_windows=0,
        metrics={},
        foundation_result=foundation_result,
        candidate_signal={"status": "not_enough_windows"},
    )


def _candidate_signal_summary(predictions: Mapping[str, np.ndarray], windows: list[object]) -> dict[str, object]:
    truth = np.stack([window.y for window in windows], axis=0)
    y_hat = np.asarray(predictions["y_hat"], dtype=float)
    residual = y_hat - truth
    abs_residual = np.abs(residual)
    p50, p90, p95, p99 = np.percentile(abs_residual, [50, 90, 95, 99])
    window_scores = []
    for index, window_abs_residual in enumerate(abs_residual):
        window_scores.append(
            {
                "window_index": index,
                "max_abs_residual": float(np.max(window_abs_residual)),
                "mean_abs_residual": float(np.mean(window_abs_residual)),
                "top_window_stage_summary": _stage_summary(windows[index]),
            }
        )
    window_scores.sort(key=lambda item: item["max_abs_residual"], reverse=True)
    return {
        "status": "available",
        "residual_mae": float(np.mean(abs_residual)),
        "residual_rmse": float(np.sqrt(np.mean(residual**2))),
        "abs_residual_p50": float(p50),
        "abs_residual_p90": float(p90),
        "abs_residual_p95": float(p95),
        "abs_residual_p99": float(p99),
        "points_above_p95": int(np.sum(abs_residual > p95)),
        "points_above_p99": int(np.sum(abs_residual > p99)),
        "top_windows": window_scores[:3],
    }


def _stage_summary(window: object) -> str:
    stages = np.asarray(getattr(window, "stage_token"), dtype=object)
    values, counts = np.unique(stages.astype(str), return_counts=True)
    return ", ".join(f"{value}:{int(count)}" for value, count in zip(values, counts, strict=True))


def _candidate_signal_table(candidate_signal: Mapping[str, object]) -> list[str]:
    keys = [
        "status",
        "residual_mae",
        "residual_rmse",
        "abs_residual_p50",
        "abs_residual_p90",
        "abs_residual_p95",
        "abs_residual_p99",
        "points_above_p95",
        "points_above_p99",
    ]
    rows = ["| signal | value |", "| --- | --- |"]
    for key in keys:
        rows.append(
            "| "
            + " | ".join(
                [
                    _format_markdown_cell(key),
                    _format_metric_or_value(candidate_signal.get(key)),
                ]
            )
            + " |"
        )
    return rows


def _top_windows_table(top_windows: object) -> list[str]:
    if not top_windows:
        return ["- not_available"]
    rows = [
        "| window_index | max_abs_residual | mean_abs_residual | top_window_stage_summary |",
        "| --- | --- | --- | --- |",
    ]
    for item in top_windows:
        if not isinstance(item, Mapping):
            continue
        rows.append(
            "| "
            + " | ".join(
                [
                    _format_metric_or_value(item.get("window_index")),
                    _format_metric_or_value(item.get("max_abs_residual")),
                    _format_metric_or_value(item.get("mean_abs_residual")),
                    _format_markdown_cell(item.get("top_window_stage_summary", "")),
                ]
            )
            + " |"
        )
    return rows


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


def _format_metric_or_value(value: object) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_metric(value)
    return _format_markdown_cell(_format_value(value))


def _format_markdown_cell(value: object) -> str:
    return str(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("|", "\\|")


def _format_value(value: object) -> str:
    if value is None or value == "":
        return "not_available"
    return str(value)
