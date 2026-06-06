from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import math
from pathlib import Path
import signal
import time
from typing import Any
import warnings

import numpy as np
import pandas as pd
import yaml

from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.experiments.c1_evidence import (
    apply_deterministic_mask,
    reconstruction_metrics,
    simple_statistical_embedding,
)
from b08_model_core.tasks.window_builder import build_model_windows


class C21ConfigError(ValueError):
    """Raised when the C2.1 executable evaluation config cannot be used."""


class C21TaskId(StrEnum):
    FORECASTING = "forecasting"
    REPRESENTATION = "representation"
    IMPUTATION = "imputation"


REQUIRED_C21_TASKS: dict[str, tuple[C21TaskId, ...]] = {
    "ttm": (C21TaskId.FORECASTING,),
    "chronos": (C21TaskId.FORECASTING,),
    "timesfm": (C21TaskId.FORECASTING,),
    "moirai_uni2ts": (C21TaskId.FORECASTING,),
    "moment": (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION),
    "units": (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION),
}


@dataclass
class C21ExecutionConfig:
    stage: str
    upstream_c2_config: Path
    dataset_path: Path
    fu13_config_path: Path
    dataset_boundary: str
    window_mode: str
    context_length: int
    prediction_length: int
    max_windows: int
    mask_ratio: float
    seed: int
    allow_network: bool
    allow_download: bool
    strict_model_success: bool
    record_failure: bool
    do_not_over_claim: bool
    continue_on_model_failure: bool
    timeout_seconds_per_model: float
    cache_dir: Path
    reuse_existing_cache: bool
    write_cache_manifest: bool
    report_path: Path
    cache_manifest_path: Path


@dataclass
class C21ModelTaskAttempt:
    model_id: str
    task_id: C21TaskId


@dataclass
class C21ModelTaskResult:
    model_id: str
    display_name: str
    task_id: C21TaskId
    status: Any
    metrics: dict[str, Any]
    baseline_metrics: dict[str, Any]
    failure_stage: str
    failure_reason: str
    error_type: str
    error_detail: str
    dependency_status: str
    weight_status: str
    input_shape: dict[str, Any]
    output_shape: dict[str, Any]
    runtime_seconds: float | None
    adapter_name: str
    model_ref: str | None
    cache_dir: str | Path | None
    actual_network_used: bool | str | None


@dataclass
class C21RunResult:
    run_id: str
    config_path: str | Path
    upstream_c2_config: str | Path
    dataset_boundary: str
    config_allows_network: bool
    config_allows_download: bool
    cache_dir: str | Path
    tested_windows: int
    task_results: list[C21ModelTaskResult]
    invalid_claims: list[str]
    c3_handoff_notes: list[str] = field(
        default_factory=lambda: [
            "C2.1 records executable adapter status and failure evidence only.",
            "C3 must re-check dependencies, weights, licenses, and interfaces before promotion.",
        ]
    )
    b_decision_notes: list[str] = field(
        default_factory=lambda: [
            "C2.1 results are not a B-stage self-training Go decision.",
            "Offline executable checks must not be interpreted as production alert readiness.",
        ]
    )

    @property
    def has_required_attempt_failure(self) -> bool:
        from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus

        by_attempt = {
            (task_result.model_id, task_result.task_id): task_result
            for task_result in self.task_results
        }
        for model_id, task_ids in REQUIRED_C21_TASKS.items():
            for task_id in task_ids:
                task_result = by_attempt.get((model_id, task_id))
                if task_result is None:
                    return True
                if task_result.status != OpenModelAdapterStatus.AVAILABLE_AND_RAN:
                    return True
        return False


def render_c21_report(result: C21RunResult) -> str:
    lines = [
        "# C2.1 Executable Open Model Evaluation Report",
        "",
        "## Report Metadata",
        "",
        f"- run_id: {_value(result.run_id)}",
        f"- config_path: {_value(result.config_path)}",
        f"- upstream_c2_config: {_value(result.upstream_c2_config)}",
        f"- dataset_boundary: {_value(result.dataset_boundary)}",
        f"- tested_windows: {_value(result.tested_windows)}",
        f"- config_allows_network: {_value(result.config_allows_network)}",
        f"- config_allows_download: {_value(result.config_allows_download)}",
        f"- cache_dir: {_value(result.cache_dir)}",
        "",
        "## Executive Summary",
        "",
        f"- model_task_attempts: {len(result.task_results)}",
        "- scope: offline executable open model adapter attempts and report rendering.",
        "- boundary: no CLI, concrete adapter factory, external cache download, or real open model call is performed.",
        "",
        "## Adapter Readiness Table",
        "",
        (
            "| model_id | display_name | adapter_name | status | dependency_status | "
            "weight_status | model_ref | cache_dir | actual_network_used |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for task_result in _readiness_results(result.task_results):
        lines.append(
            (
                f"| {_cell(task_result.model_id)} | {_cell(task_result.display_name)} | "
                f"{_cell(task_result.adapter_name)} | {_cell(task_result.status)} | "
                f"{_cell(task_result.dependency_status)} | {_cell(task_result.weight_status)} | "
                f"{_cell(task_result.model_ref)} | {_cell(task_result.cache_dir)} | "
                f"{_cell(task_result.actual_network_used)} |"
            )
        )

    lines.extend(
        [
            "",
            "## Model-Task Result Matrix",
            "",
            (
                "| model_id | task_id | display_name | status | metrics | baseline_metrics | "
                "failure_stage | failure_reason | error_type | error_detail | input_shape | output_shape | "
                "runtime_seconds |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for task_result in result.task_results:
        lines.append(
            (
                f"| {_cell(task_result.model_id)} | {_cell(task_result.task_id)} | "
                f"{_cell(task_result.display_name)} | {_cell(task_result.status)} | "
                f"{_cell(task_result.metrics)} | {_cell(task_result.baseline_metrics)} | "
                f"{_cell(task_result.failure_stage)} | {_cell(task_result.failure_reason)} | "
                f"{_cell(task_result.error_type)} | {_cell(task_result.error_detail)} | "
                f"{_cell(task_result.input_shape)} | {_cell(task_result.output_shape)} | "
                f"{_cell(task_result.runtime_seconds)} |"
            )
        )

    lines.extend(
        [
            "",
            "## Forecasting Comparison",
            "",
            "| model_id | status | metrics | baseline_metrics | runtime_seconds | failure_reason |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for task_result in result.task_results:
        if task_result.task_id != C21TaskId.FORECASTING:
            continue
        lines.append(
            (
                f"| {_cell(task_result.model_id)} | {_cell(task_result.status)} | "
                f"{_cell(task_result.metrics)} | {_cell(task_result.baseline_metrics)} | "
                f"{_cell(task_result.runtime_seconds)} | {_cell(task_result.failure_reason)} |"
            )
        )

    lines.extend(
        [
            "",
            "## Representation And Imputation Results",
            "",
            "| model_id | task_id | status | metrics | baseline_metrics | runtime_seconds | failure_reason |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for task_result in result.task_results:
        if task_result.task_id not in {C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION}:
            continue
        lines.append(
            (
                f"| {_cell(task_result.model_id)} | {_cell(task_result.task_id)} | "
                f"{_cell(task_result.status)} | {_cell(task_result.metrics)} | "
                f"{_cell(task_result.baseline_metrics)} | {_cell(task_result.runtime_seconds)} | "
                f"{_cell(task_result.failure_reason)} |"
            )
        )

    lines.extend(
        [
            "",
            "## Failure Taxonomy",
            "",
            "| status | model_id | task_id | failure_stage | reason | detail |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    failure_results = [task_result for task_result in result.task_results if task_result.failure_reason]
    if failure_results:
        for task_result in failure_results:
            lines.append(
                (
                    f"| {_cell(task_result.status)} | {_cell(task_result.model_id)} | "
                    f"{_cell(task_result.task_id)} | {_cell(task_result.failure_stage)} | "
                    f"{_cell(task_result.failure_reason)} | {_cell(task_result.error_detail)} |"
                )
            )
    else:
        lines.append("| none | none | none | none | none | none |")

    lines.extend(["", "## Cache Manifest", ""])
    lines.extend(render_c21_cache_manifest(result).rstrip().splitlines())
    lines.extend(["", "## C2 -> C3 Handoff", ""])
    lines.extend(f"- {_value(note)}" for note in (result.c3_handoff_notes or ["none"]))
    lines.extend(["", "## C2 -> B Decision Notes", ""])
    lines.extend(f"- {_value(note)}" for note in (result.b_decision_notes or ["none"]))
    lines.extend(["", "## Invalid Claims", ""])
    lines.extend(f"- {_value(claim)}" for claim in (result.invalid_claims or ["none"]))
    return "\n".join(lines) + "\n"


def render_c21_cache_manifest(result: C21RunResult) -> str:
    lines = [
        "| key | value |",
        "| --- | --- |",
        f"| run_id | {_cell(result.run_id)} |",
        f"| cache_dir | {_cell(result.cache_dir)} |",
        f"| network_allowed | {_cell(result.config_allows_network)} |",
        f"| download_allowed | {_cell(result.config_allows_download)} |",
        f"| dataset_boundary | {_cell(result.dataset_boundary)} |",
        "",
        "| model_id | task_id | cache_dir | weight_status | actual_network_used | model_ref |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if result.task_results:
        for task_result in result.task_results:
            lines.append(
                (
                    f"| {_cell(task_result.model_id)} | {_cell(task_result.task_id)} | "
                    f"{_cell(task_result.cache_dir)} | {_cell(task_result.weight_status)} | "
                    f"{_cell(task_result.actual_network_used)} | {_cell(task_result.model_ref)} |"
                )
            )
    else:
        lines.append("| none | none | none | none | none | none |")
    return "\n".join(lines) + "\n"


def load_c21_executable_config(path: str | Path) -> C21ExecutionConfig:
    raw = _load_mapping(Path(path))
    dataset = _load_mapping(raw, "dataset")
    window = _load_mapping(raw, "window")
    execution_policy = _load_mapping(raw, "execution_policy")
    model_cache_policy = _load_mapping(raw, "model_cache_policy")
    outputs = _load_mapping(raw, "outputs")

    stage = _load_required_string(raw, "stage")
    if stage != "C2_1_executable_open_model_evaluation":
        raise C21ConfigError("C2.1 stage must be C2_1_executable_open_model_evaluation")

    return C21ExecutionConfig(
        stage=stage,
        upstream_c2_config=Path(_load_required_string(raw, "upstream_c2_config")),
        dataset_path=Path(_load_required_string(dataset, "fu13_observations")),
        fu13_config_path=Path(_load_required_string(dataset, "fu13_config")),
        dataset_boundary=_load_required_string(dataset, "boundary"),
        window_mode=_load_window_mode(window),
        context_length=_load_positive_int(window, "context_length"),
        prediction_length=_load_positive_int(window, "prediction_length"),
        max_windows=_load_positive_int(window, "max_windows"),
        mask_ratio=_load_mask_ratio(window, "mask_ratio"),
        seed=_load_nonnegative_int(window, "seed"),
        allow_network=_load_bool(execution_policy, "allow_network"),
        allow_download=_load_bool(execution_policy, "allow_download"),
        strict_model_success=_load_bool(execution_policy, "strict_model_success"),
        record_failure=_load_bool(execution_policy, "record_failure"),
        do_not_over_claim=_load_bool(execution_policy, "do_not_over_claim"),
        continue_on_model_failure=_load_bool(execution_policy, "continue_on_model_failure"),
        timeout_seconds_per_model=_load_positive_number(
            execution_policy,
            "timeout_seconds_per_model",
        ),
        cache_dir=Path(_load_required_string(model_cache_policy, "cache_dir")),
        reuse_existing_cache=_load_bool(model_cache_policy, "reuse_existing_cache"),
        write_cache_manifest=_load_bool(model_cache_policy, "write_cache_manifest"),
        report_path=Path(_load_required_string(outputs, "report")),
        cache_manifest_path=Path(_load_required_string(outputs, "cache_manifest")),
    )


def build_c21_attempts(config: C21ExecutionConfig) -> list[C21ModelTaskAttempt]:
    if config.stage != "C2_1_executable_open_model_evaluation":
        raise C21ConfigError("C2.1 attempts require a C2.1 executable config")

    return [
        C21ModelTaskAttempt(model_id=model_id, task_id=task_id)
        for model_id, task_ids in REQUIRED_C21_TASKS.items()
        for task_id in task_ids
    ]


def run_c21_executable_evaluation(
    config: C21ExecutionConfig | str | Path,
    adapter_factory: Any = None,
) -> C21RunResult:
    from b08_model_core.adapters.open_models.base import AdapterExecutionContext

    config_source: str | Path = "provided_config"
    if not isinstance(config, C21ExecutionConfig):
        config_source = config
        config = load_c21_executable_config(config)

    df = pd.read_parquet(config.dataset_path)
    windows = build_model_windows(
        df,
        context_length=config.context_length,
        prediction_length=config.prediction_length,
        stride=config.prediction_length,
        allow_cross_stage=(config.window_mode == "cross-stage"),
    )[: config.max_windows]
    if not windows:
        raise ValueError("not enough windows for C2.1 executable evaluation")

    baselines = {
        C21TaskId.FORECASTING: _safe_forecasting_baseline(windows),
        C21TaskId.REPRESENTATION: _safe_representation_baseline(windows),
        C21TaskId.IMPUTATION: _safe_imputation_baseline(config, windows),
    }
    task_results: list[C21ModelTaskResult] = []

    for attempt in build_c21_attempts(config):
        adapter = _adapter_for_attempt(adapter_factory, attempt.model_id)
        context = AdapterExecutionContext(
            allow_network=config.allow_network,
            allow_download=config.allow_download,
            cache_dir=config.cache_dir,
            timeout_seconds_per_model=config.timeout_seconds_per_model,
            metadata={
                "stage": config.stage,
                "dataset_boundary": config.dataset_boundary,
                "model_id": attempt.model_id,
                "task_id": attempt.task_id.value,
            },
        )
        baseline_metrics = baselines.get(attempt.task_id, {"baseline": "not_run"})
        started = time.monotonic()
        try:
            raw_result = _run_attempt_with_timeout(
                config.timeout_seconds_per_model,
                lambda: _run_adapter_attempt(attempt, adapter, windows, config, context),
            )
            task_results.append(
                _adapter_result_to_c21_result(
                    raw_result,
                    attempt,
                    adapter,
                    baseline_metrics,
                    context,
                )
            )
        except TimeoutError as exc:
            task_results.append(
                _failure_result(
                    attempt,
                    adapter,
                    baseline_metrics,
                    context,
                    status_name="TIMEOUT",
                    failure_stage="execute",
                    failure_reason=f"model-task attempt exceeded {config.timeout_seconds_per_model} seconds",
                    error_type=type(exc).__name__,
                    error_detail=str(exc),
                    runtime_seconds=time.monotonic() - started,
                )
            )
        except Exception as exc:
            task_results.append(
                _failure_result(
                    attempt,
                    adapter,
                    baseline_metrics,
                    context,
                    status_name="RUNTIME_FAILED",
                    failure_stage="execute",
                    failure_reason="model-task attempt raised an exception",
                    error_type=type(exc).__name__,
                    error_detail=str(exc),
                    runtime_seconds=time.monotonic() - started,
                )
            )

    execution_time_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return C21RunResult(
        run_id=f"c21-executable-{execution_time_utc}",
        config_path=config_source,
        upstream_c2_config=config.upstream_c2_config,
        dataset_boundary=config.dataset_boundary,
        config_allows_network=config.allow_network,
        config_allows_download=config.allow_download,
        cache_dir=config.cache_dir,
        tested_windows=len(windows),
        task_results=task_results,
        invalid_claims=[
            "不得解释为生产告警",
            "不得解释为生产能力",
            "不得解释为真实 open model 权重已下载或已验证",
            "不得解释为 C3 或 B 阶段 Go 决策",
        ],
    )


def _safe_forecasting_baseline(windows: list[object]) -> dict[str, Any]:
    try:
        split = max(1, int(len(windows) * 0.7))
        train = windows[:split]
        test = windows[split:] or windows[-1:]
        predictions = RobustStageForecaster().fit(train).predict(test)
        metrics = forecasting_metrics(predictions, test)
        return {
            "baseline": "RobustStageForecaster",
            **metrics,
            "train_windows": len(train),
            "test_windows": len(test),
        }
    except Exception as exc:
        return {"baseline": "not_run", "reason": str(exc)}


def _safe_representation_baseline(windows: list[object]) -> dict[str, Any]:
    try:
        embeddings = [simple_statistical_embedding(window.X) for window in windows]
        return {
            "baseline": "statistical_embedding",
            "embedding_windows": len(embeddings),
            "embedding_features": len(embeddings[0]) if embeddings else 0,
        }
    except Exception as exc:
        return {"baseline": "not_run", "reason": str(exc)}


def _safe_imputation_baseline(
    config: C21ExecutionConfig,
    windows: list[object],
) -> dict[str, Any]:
    try:
        metrics_by_window = []
        for index, window in enumerate(windows):
            masked, mask = apply_deterministic_mask(
                window.X,
                mask_ratio=config.mask_ratio,
                seed=config.seed + index,
            )
            median_source = np.asarray(window.X, dtype=float).copy()
            median_source[mask] = np.nan
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                medians = np.nanmedian(median_source, axis=0)
            fallback_medians = np.median(np.asarray(window.X, dtype=float), axis=0)
            medians = np.where(np.isnan(medians), fallback_medians, medians)
            medians = np.nan_to_num(medians, nan=0.0)
            reconstructed = masked.copy()
            reconstructed[mask] = np.take(medians, np.where(mask)[1])
            metrics_by_window.append(reconstruction_metrics(window.X, reconstructed, mask))

        mae_values = [metric["mae"] for metric in metrics_by_window if metric["mae"] is not None]
        rmse_values = [metric["rmse"] for metric in metrics_by_window if metric["rmse"] is not None]
        return {
            "baseline": "simple_reconstruction_baseline",
            "mae": float(np.mean(mae_values)) if mae_values else None,
            "rmse": float(np.mean(rmse_values)) if rmse_values else None,
            "count": int(sum(int(metric["count"]) for metric in metrics_by_window)),
        }
    except Exception as exc:
        return {"baseline": "not_run", "reason": str(exc)}


def _adapter_for_attempt(adapter_factory: Any, model_id: str) -> Any:
    if adapter_factory is None:
        return None
    if isinstance(adapter_factory, dict):
        return adapter_factory.get(model_id)
    if callable(adapter_factory):
        return adapter_factory(model_id)
    return None


def _run_adapter_attempt(
    attempt: C21ModelTaskAttempt,
    adapter: Any,
    windows: list[object],
    config: C21ExecutionConfig,
    context: Any,
) -> Any:
    from b08_model_core.adapters.open_models.base import AdapterFailure, OpenModelAdapterStatus

    if adapter is None:
        return AdapterFailure(
            model_id=attempt.model_id,
            task_id=attempt.task_id,
            status=OpenModelAdapterStatus.LICENSE_OR_INTERFACE_NEEDS_REVIEW,
            failure_stage="inspect",
            failure_reason="adapter not configured; real adapter factory pending",
            error_type="AdapterNotConfigured",
            error_detail=attempt.model_id,
            dependency_status="unknown",
            weight_status="not_checked",
            input_shape={"windows": len(windows)},
            cache_dir=context.cache_dir,
            actual_network_used=False,
        )

    inspected = adapter.inspect_environment(context)
    if isinstance(inspected, AdapterFailure):
        return inspected

    loaded = adapter.load(context)
    if attempt.task_id == C21TaskId.FORECASTING:
        return loaded.run_forecasting(windows, context)
    if attempt.task_id == C21TaskId.REPRESENTATION:
        return loaded.run_representation(windows, context)
    if attempt.task_id == C21TaskId.IMPUTATION:
        return loaded.run_imputation(
            windows,
            {"mask_ratio": config.mask_ratio, "seed": config.seed},
            context,
        )
    raise ValueError(f"unsupported C2.1 task_id: {attempt.task_id}")


def _adapter_result_to_c21_result(
    raw_result: Any,
    attempt: C21ModelTaskAttempt,
    adapter: Any,
    baseline_metrics: dict[str, Any],
    context: Any,
) -> C21ModelTaskResult:
    from b08_model_core.adapters.open_models.base import AdapterFailure, AdapterTaskOutput

    if isinstance(raw_result, AdapterTaskOutput):
        return C21ModelTaskResult(
            model_id=raw_result.model_id or attempt.model_id,
            display_name=_display_name(adapter, raw_result.model_id or attempt.model_id),
            task_id=raw_result.task_id,
            status=raw_result.status,
            metrics=dict(raw_result.metrics),
            baseline_metrics=dict(raw_result.baseline_metrics or baseline_metrics),
            failure_stage="",
            failure_reason="",
            error_type="",
            error_detail="",
            dependency_status="available",
            weight_status="not_checked",
            input_shape=dict(raw_result.input_shape),
            output_shape=dict(raw_result.output_shape),
            runtime_seconds=_runtime_seconds(raw_result),
            adapter_name=raw_result.adapter_name or _adapter_name(adapter),
            model_ref=raw_result.model_ref,
            cache_dir=raw_result.cache_dir or context.cache_dir,
            actual_network_used=raw_result.actual_network_used
            if raw_result.actual_network_used is not None
            else False,
        )
    if isinstance(raw_result, AdapterFailure):
        return C21ModelTaskResult(
            model_id=raw_result.model_id or attempt.model_id,
            display_name=_display_name(adapter, raw_result.model_id or attempt.model_id),
            task_id=attempt.task_id,
            status=raw_result.status,
            metrics={},
            baseline_metrics=dict(baseline_metrics),
            failure_stage=raw_result.failure_stage,
            failure_reason=raw_result.failure_reason,
            error_type=raw_result.error_type,
            error_detail=raw_result.error_detail,
            dependency_status=raw_result.dependency_status,
            weight_status=raw_result.weight_status,
            input_shape=dict(raw_result.input_shape),
            output_shape={},
            runtime_seconds=raw_result.runtime_seconds,
            adapter_name=raw_result.adapter_name or _adapter_name(adapter),
            model_ref=raw_result.model_ref,
            cache_dir=raw_result.cache_dir or context.cache_dir,
            actual_network_used=raw_result.actual_network_used
            if raw_result.actual_network_used is not None
            else False,
        )
    raise TypeError(f"adapter returned unsupported result type: {type(raw_result).__name__}")


def _failure_result(
    attempt: C21ModelTaskAttempt,
    adapter: Any,
    baseline_metrics: dict[str, Any],
    context: Any,
    *,
    status_name: str,
    failure_stage: str,
    failure_reason: str,
    error_type: str,
    error_detail: str,
    runtime_seconds: float,
) -> C21ModelTaskResult:
    from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus

    return C21ModelTaskResult(
        model_id=attempt.model_id,
        display_name=_display_name(adapter, attempt.model_id),
        task_id=attempt.task_id,
        status=getattr(OpenModelAdapterStatus, status_name),
        metrics={},
        baseline_metrics=dict(baseline_metrics),
        failure_stage=failure_stage,
        failure_reason=failure_reason,
        error_type=error_type,
        error_detail=error_detail,
        dependency_status="unknown",
        weight_status="not_checked",
        input_shape={},
        output_shape={},
        runtime_seconds=runtime_seconds,
        adapter_name=_adapter_name(adapter),
        model_ref=None,
        cache_dir=context.cache_dir,
        actual_network_used=False,
    )


def _runtime_seconds(raw_result: Any) -> float | None:
    if raw_result.runtime_seconds is not None:
        return raw_result.runtime_seconds
    value = raw_result.metrics.get("runtime_seconds")
    return float(value) if isinstance(value, int | float) else None


def _display_name(adapter: Any, fallback: str) -> str:
    if adapter is None:
        return fallback
    return str(getattr(adapter, "display_name", None) or fallback)


def _adapter_name(adapter: Any) -> str:
    return "" if adapter is None else adapter.__class__.__name__


class _AttemptTimeout(TimeoutError):
    pass


def _run_attempt_with_timeout(seconds: float, run: Any) -> Any:
    with _attempt_timeout(seconds):
        return run()


@contextmanager
def _attempt_timeout(seconds: float):
    old_handler = signal.getsignal(signal.SIGALRM)

    def _raise_timeout(signum: int, frame: Any) -> None:
        raise _AttemptTimeout(f"attempt timed out after {seconds} seconds")

    signal.signal(signal.SIGALRM, _raise_timeout)
    old_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, old_timer[0], old_timer[1])
        signal.signal(signal.SIGALRM, old_handler)


def _load_mapping(raw: dict[str, Any] | Path, key: str | None = None) -> dict[str, Any]:
    if isinstance(raw, Path):
        loaded = yaml.safe_load(raw.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise C21ConfigError("C2.1 executable config must be a mapping")
        return loaded

    value = raw.get(key)
    if not isinstance(value, dict):
        raise C21ConfigError(f"{key} must be a mapping")
    return value


def _load_required_string(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise C21ConfigError(f"{key} must be a non-empty string")
    return value


def _load_window_mode(raw: dict[str, Any]) -> str:
    value = _load_required_string(raw, "window_mode")
    if value not in {"stage-local", "cross-stage"}:
        raise C21ConfigError("window_mode must be stage-local or cross-stage")
    return value


def _load_positive_int(raw: dict[str, Any], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise C21ConfigError(f"{key} must be a positive integer")
    return value


def _load_nonnegative_int(raw: dict[str, Any], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise C21ConfigError(f"{key} must be a nonnegative integer")
    return value


def _load_positive_number(raw: dict[str, Any], key: str) -> float:
    value = raw.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise C21ConfigError(f"{key} must be a positive number")
    value = float(value)
    if not math.isfinite(value):
        raise C21ConfigError(f"{key} must be finite")
    return value


def _load_mask_ratio(raw: dict[str, Any], key: str) -> float:
    value = raw.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise C21ConfigError(f"{key} must be a number in (0, 1]")
    ratio = float(value)
    if not 0 < ratio <= 1:
        raise C21ConfigError(f"{key} must be in (0, 1]")
    return ratio


def _load_bool(raw: dict[str, Any], key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise C21ConfigError(f"{key} must be a boolean")
    return value


def _readiness_results(task_results: list[C21ModelTaskResult]) -> list[C21ModelTaskResult]:
    by_model_id: dict[str, C21ModelTaskResult] = {}
    for task_result in task_results:
        by_model_id.setdefault(task_result.model_id, task_result)
    return list(by_model_id.values())


def _value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if enum_value is not None:
        return _value(enum_value)
    if value is None or (isinstance(value, str) and value == ""):
        return "not_available"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, dict):
        if not value:
            return "not_available"
        return ", ".join(f"{key}={_value(item)}" for key, item in value.items())
    if isinstance(value, list | tuple):
        if not value:
            return "not_available"
        return ", ".join(_value(item) for item in value)
    return str(value)


def _cell(value: object) -> str:
    return _value(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("|", "\\|")
