from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

import yaml


class C33ConfigError(ValueError):
    """Raised when the C3.3 single-candidate evaluation config is invalid."""


@dataclass(frozen=True)
class C33SafetyPolicy:
    allow_network: bool
    allow_download: bool
    allow_model_cache: bool
    allow_local_execution: bool
    allow_training: bool
    allow_write_processed: bool


@dataclass(frozen=True)
class C33Prerequisites:
    c32_design_doc: Path
    c32_local_status: str


@dataclass(frozen=True)
class C33Candidate:
    model_id: str
    model_ref: str
    task_id: str
    dataset_view: str


@dataclass(frozen=True)
class C33MetricContract:
    forecasting_metrics: tuple[str, ...]
    adapter_status_fields: tuple[str, ...]
    leaderboard_allowed: bool


@dataclass(frozen=True)
class C33LocalFu13LikeConfig:
    days: int
    seed: int
    context_length: int
    prediction_length: int
    max_windows: int
    residual_top_k: int


@dataclass(frozen=True)
class C33LocalExecutionConfig:
    enabled: bool
    model_cache_dir: Path
    fu13_like: C33LocalFu13LikeConfig


@dataclass(frozen=True)
class C33Outputs:
    report: Path


@dataclass(frozen=True)
class C33Config:
    stage: str
    safety_policy: C33SafetyPolicy
    prerequisites: C33Prerequisites
    candidate: C33Candidate
    metric_contract: C33MetricContract
    local_execution: C33LocalExecutionConfig | None
    outputs: C33Outputs


@dataclass(frozen=True)
class C33ForecastingBaselineResult:
    model_name: str
    metrics: dict[str, float | int | None]
    residual_ranking: tuple[dict[str, float | int | str], ...]


@dataclass(frozen=True)
class C33ForecastingReferenceResult:
    days: int
    seed: int
    context_length: int
    prediction_length: int
    max_windows: int
    train_window_count: int
    test_window_count: int
    baseline_metrics: dict[str, dict[str, float | int | None]]
    baseline_results: tuple[C33ForecastingBaselineResult, ...]


@dataclass(frozen=True)
class C33AdapterExecutionResult:
    model_id: str
    task_id: str
    status: Any
    adapter_status: Any
    metrics: dict[str, Any]
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
    download_allowed_not_verified: bool


@dataclass(frozen=True)
class C33RunResult:
    config_path: Path
    stage: str
    status: str
    go_no_go_decision: str
    safety_policy: C33SafetyPolicy
    prerequisites: C33Prerequisites
    candidate: C33Candidate
    metric_contract: C33MetricContract
    invalid_claims: tuple[str, ...]
    baseline_reference_result: C33ForecastingReferenceResult | None = None
    adapter_result: C33AdapterExecutionResult | None = None
    adapter_failure: C33AdapterExecutionResult | None = None
    ttm_metrics: dict[str, float | int | None] | None = None
    ttm_residual_ranking: tuple[dict[str, float | int | str], ...] | None = None
    local_execution_blocked_reason: str = ""


_EXPECTED_STAGE = "C3_3_single_candidate_open_model_local_evaluation"
_EXPECTED_C32_LOCAL_STATUS = "local_execution_baseline_reference_ready"
_EXPECTED_CANDIDATE = {
    "model_id": "ttm",
    "task_id": "forecasting_residual",
    "dataset_view": "fu13_like_simulated_forecasting",
}
_CONTRACT_READY_STATUS = "contract_ready_single_candidate_local_execution_blocked"
_TTM_READY_STATUS = "local_execution_ttm_forecasting_ready"
_TTM_MISSING_DEPENDENCY_STATUS = "local_execution_ttm_missing_dependency"
_TTM_MISSING_OR_BLOCKED_WEIGHTS_STATUS = (
    "local_execution_ttm_missing_or_blocked_weights"
)
_TTM_UNSUPPORTED_WINDOW_SHAPE_STATUS = (
    "local_execution_ttm_unsupported_window_shape"
)
_TTM_RUNTIME_FAILED_STATUS = "local_execution_ttm_runtime_failed"
_INSUFFICIENT_FU13_LIKE_WINDOWS_STATUS = "blocked_insufficient_fu13_like_windows"
_GO_DECISION = "Go for C3.3 explicit local TTM cache-first evaluation"
_INVALID_CLAIMS = (
    "no production RUL",
    "no production alarms",
    "no maintenance recommendations",
    "no candidate leaderboard",
    "no self-developed model superiority",
)
_SAFETY_FLAGS = (
    "allow_network",
    "allow_download",
    "allow_model_cache",
    "allow_local_execution",
    "allow_training",
    "allow_write_processed",
)


def load_c33_config(path: str | Path) -> C33Config:
    config_path = Path(path)
    raw = _load_yaml_mapping(config_path)
    stage = _required_string(raw, "stage")
    if stage != _EXPECTED_STAGE:
        raise C33ConfigError(f"stage must be {_EXPECTED_STAGE}")

    local_execution_enabled = _local_execution_enabled(raw)
    safety_policy = _load_safety_policy(
        raw,
        local_execution_enabled=local_execution_enabled,
    )
    prerequisites = _load_prerequisites(raw)
    candidate = _load_candidate(raw)
    metric_contract = _load_metric_contract(raw)
    local_execution = _load_local_execution(
        raw,
        safety_policy=safety_policy,
        config_root=_project_root_for_config(config_path),
    )
    outputs = _load_outputs(raw)

    return C33Config(
        stage=stage,
        safety_policy=safety_policy,
        prerequisites=prerequisites,
        candidate=candidate,
        metric_contract=metric_contract,
        local_execution=local_execution,
        outputs=outputs,
    )


def run_c33_single_candidate_open_model_local_evaluation(
    config: C33Config,
    config_path: str | Path,
    *,
    adapter_factory: Callable[[], object] | None = None,
) -> C33RunResult:
    if config.local_execution is None:
        return C33RunResult(
            config_path=Path(config_path),
            stage=config.stage,
            status=_CONTRACT_READY_STATUS,
            go_no_go_decision=_GO_DECISION,
            safety_policy=config.safety_policy,
            prerequisites=config.prerequisites,
            candidate=config.candidate,
            metric_contract=config.metric_contract,
            invalid_claims=_INVALID_CLAIMS,
            local_execution_blocked_reason=(
                "default C3.3 config disables local execution, model cache, "
                "network, and downloads"
            ),
        )

    reference_attempt = _run_fu13_like_forecasting_reference(
        config.local_execution.fu13_like,
    )
    if reference_attempt is None:
        return C33RunResult(
            config_path=Path(config_path),
            stage=config.stage,
            status=_INSUFFICIENT_FU13_LIKE_WINDOWS_STATUS,
            go_no_go_decision=_GO_DECISION,
            safety_policy=config.safety_policy,
            prerequisites=config.prerequisites,
            candidate=config.candidate,
            metric_contract=config.metric_contract,
            invalid_claims=_INVALID_CLAIMS,
            local_execution_blocked_reason="insufficient FU13-like windows",
        )

    forecasting_reference, _train_windows, test_windows = reference_attempt
    context = _build_adapter_execution_context(config)
    try:
        adapter = _build_ttm_adapter(adapter_factory)
    except Exception as exc:
        adapter_evidence = _c33_result_from_exception(
            exc,
            context,
            test_windows,
            failure_stage="construct",
        )
        return _local_run_result(
            config=config,
            config_path=config_path,
            forecasting_reference=forecasting_reference,
            adapter_evidence=adapter_evidence,
            ttm_metrics=None,
            ttm_ranking=None,
        )

    raw_adapter_result = _run_ttm_adapter(
        adapter,
        test_windows,
        context,
        inspect_and_load=adapter_factory is None,
    )
    adapter_evidence = _adapter_result_to_c33_result(raw_adapter_result, context)
    ttm_metrics = None
    ttm_ranking = None
    if _is_successful_adapter_result(adapter_evidence):
        try:
            ttm_metrics, ttm_ranking = _ttm_forecasting_evidence(
                raw_adapter_result,
                test_windows,
                config.local_execution.fu13_like.residual_top_k,
            )
        except Exception as exc:
            adapter_evidence = _c33_result_from_exception(
                exc,
                context,
                test_windows,
                failure_stage="metrics",
                status=_metric_exception_status(exc),
                raw_result=raw_adapter_result,
            )
    return _local_run_result(
        config=config,
        config_path=config_path,
        forecasting_reference=forecasting_reference,
        adapter_evidence=adapter_evidence,
        ttm_metrics=ttm_metrics,
        ttm_ranking=ttm_ranking,
    )


def _local_run_result(
    *,
    config: C33Config,
    config_path: str | Path,
    forecasting_reference: C33ForecastingReferenceResult,
    adapter_evidence: C33AdapterExecutionResult,
    ttm_metrics: dict[str, float | int | None] | None,
    ttm_ranking: tuple[dict[str, float | int | str], ...] | None,
) -> C33RunResult:
    adapter_result = (
        adapter_evidence
        if _is_successful_adapter_result(adapter_evidence)
        else None
    )
    adapter_failure = None if adapter_result is not None else adapter_evidence
    return C33RunResult(
        config_path=Path(config_path),
        stage=config.stage,
        status=_c33_status_for_adapter_result(adapter_evidence),
        go_no_go_decision=_GO_DECISION,
        safety_policy=config.safety_policy,
        prerequisites=config.prerequisites,
        candidate=config.candidate,
        metric_contract=config.metric_contract,
        invalid_claims=_INVALID_CLAIMS,
        baseline_reference_result=forecasting_reference,
        adapter_result=adapter_result,
        adapter_failure=adapter_failure,
        ttm_metrics=ttm_metrics,
        ttm_residual_ranking=ttm_ranking,
    )


def render_c33_report(result: C33RunResult) -> str:
    lines = [
        "# C3.3 Single-Candidate Open Model Local Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Stage: {result.stage}",
        f"- Config: {result.config_path}",
        f"- Status: {result.status}",
        f"- Decision: {result.go_no_go_decision}",
        "- Default path validates the contract only; it does not instantiate adapters or inspect model cache.",
        "- Forecasting residual evidence is separated from RUL claims and model leaderboard claims.",
        "",
        "## Safety Policy",
        "",
    ]
    for flag in _SAFETY_FLAGS:
        lines.append(f"- {flag}: {getattr(result.safety_policy, flag)}")
    lines.extend(
        [
            "",
            "## C3.2 Anchor",
            "",
            f"- Design doc: {result.prerequisites.c32_design_doc}",
            f"- Required local status: {result.prerequisites.c32_local_status}",
            "- C3.2 remains the baseline reference anchor; C3.3 only adds a single TTM forecasting adapter contract.",
            "",
            "## Candidate Contract",
            "",
            f"- Candidate: {result.candidate.model_id}",
            f"- Model ref: {result.candidate.model_ref}",
            f"- Task: {result.candidate.task_id}",
            f"- Dataset view: {result.candidate.dataset_view}",
            _adapter_execution_report_line(result),
            "",
            "## Metric Contract",
            "",
            f"- Forecasting metrics: {', '.join(result.metric_contract.forecasting_metrics)}",
            f"- Adapter status fields: {', '.join(result.metric_contract.adapter_status_fields)}",
            f"- Leaderboard allowed: {result.metric_contract.leaderboard_allowed}",
            "- Residual ranking may be used only for sensor-level forecasting error explanation.",
            "",
        ]
    )
    if result.local_execution_blocked_reason:
        lines.extend(
            [
                "## Local Execution Blocked",
                "",
                f"- Status: {result.status}",
                f"- Reason: {result.local_execution_blocked_reason}",
                "",
            ]
        )
    if result.baseline_reference_result is not None:
        lines.extend(
            _render_forecasting_reference_section(
                result.baseline_reference_result,
            )
        )
    adapter_evidence = result.adapter_result or result.adapter_failure
    if adapter_evidence is not None:
        lines.extend(_render_ttm_adapter_execution_section(adapter_evidence))
    if result.ttm_metrics is not None:
        lines.extend(
            _render_ttm_metrics_section(
                result.ttm_metrics,
                result.ttm_residual_ranking or (),
            )
        )
    if (
        result.baseline_reference_result is not None
        or adapter_evidence is not None
        or result.status == _INSUFFICIENT_FU13_LIKE_WINDOWS_STATUS
    ):
        lines.extend(_render_separated_metric_interpretation_section())
    lines.extend(
        [
            "## Go / No-Go",
            "",
            f"- Go: {result.go_no_go_decision}.",
            "- No-Go: local model execution by default, cache inspection by default, downloads without network permission, training, processed-data writes, production claims, or leaderboard claims.",
            "",
            "## Invalid Claims",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in result.invalid_claims)
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            _next_step_report_line(result),
            "",
        ]
    )
    return "\n".join(lines)


def _run_fu13_like_forecasting_reference(
    config: C33LocalFu13LikeConfig,
) -> tuple[C33ForecastingReferenceResult, list[object], list[object]] | None:
    import numpy as np

    from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
    from b08_model_core.baselines.seasonal_naive import StageSeasonalNaiveForecaster
    from b08_model_core.evaluation.metrics import (
        forecasting_metrics,
        forecasting_residual_ranking,
    )
    from b08_model_core.simulation.export_dataset import simulate_dataset
    from b08_model_core.tasks.window_builder import build_model_windows

    observations = simulate_dataset(days=config.days, seed=config.seed)
    windows = build_model_windows(
        observations,
        context_length=config.context_length,
        prediction_length=config.prediction_length,
        stride=config.prediction_length,
        allow_cross_stage=True,
    )[: config.max_windows]
    if len(windows) < 2:
        return None

    split = max(1, int(len(windows) * 0.7))
    if split == len(windows):
        split -= 1
    train = windows[:split]
    test = windows[split:]
    truth = np.stack([window.y for window in test], axis=0)
    sensor_ids = tuple(test[0].sensor_token)

    baseline_results: list[C33ForecastingBaselineResult] = []
    for model_name, model in (
        ("RobustStageForecaster", RobustStageForecaster()),
        ("StageSeasonalNaiveForecaster", StageSeasonalNaiveForecaster()),
    ):
        predictions = model.fit(train).predict(test)
        metrics = forecasting_metrics(predictions, test)
        ranking = forecasting_residual_ranking(
            predictions,
            truth,
            sensor_ids,
            top_k=config.residual_top_k,
        )
        baseline_results.append(
            C33ForecastingBaselineResult(
                model_name=model_name,
                metrics=metrics,
                residual_ranking=ranking,
            )
        )

    return (
        C33ForecastingReferenceResult(
            days=config.days,
            seed=config.seed,
            context_length=config.context_length,
            prediction_length=config.prediction_length,
            max_windows=config.max_windows,
            train_window_count=len(train),
            test_window_count=len(test),
            baseline_metrics={
                item.model_name: item.metrics for item in baseline_results
            },
            baseline_results=tuple(baseline_results),
        ),
        train,
        test,
    )


def _build_adapter_execution_context(config: C33Config) -> Any:
    from b08_model_core.adapters.open_models.base import AdapterExecutionContext

    local_execution = config.local_execution
    if local_execution is None:
        raise C33ConfigError("local_execution is required for adapter execution")
    return AdapterExecutionContext(
        allow_network=config.safety_policy.allow_network,
        allow_download=config.safety_policy.allow_download,
        cache_dir=local_execution.model_cache_dir,
        timeout_seconds_per_model=300.0,
        metadata={"stage": config.stage, "candidate": config.candidate.model_id},
    )


def _build_ttm_adapter(adapter_factory: Callable[[], object] | None) -> object:
    if adapter_factory is not None:
        return adapter_factory()

    from b08_model_core.adapters.open_models.ttm import TTMOpenModelAdapter

    return TTMOpenModelAdapter()


def _run_ttm_adapter(
    adapter: object,
    windows: list[object],
    context: Any,
    *,
    inspect_and_load: bool,
) -> Any:
    from b08_model_core.adapters.open_models.base import (
        AdapterFailure,
        AdapterReadiness,
        OpenModelAdapterStatus,
    )

    started = time.monotonic()
    try:
        if not inspect_and_load:
            return adapter.run_forecasting(windows, context)  # type: ignore[attr-defined]

        inspected = adapter.inspect_environment(context)  # type: ignore[attr-defined]
        if isinstance(inspected, AdapterFailure):
            return inspected
        if (
            isinstance(inspected, AdapterReadiness)
            and inspected.adapter_status != OpenModelAdapterStatus.READY
        ):
            return _readiness_to_failure(inspected)

        loaded = adapter.load(context)  # type: ignore[attr-defined]
        if isinstance(loaded, AdapterFailure):
            return loaded
        return loaded.run_forecasting(windows, context)  # type: ignore[attr-defined]
    except Exception as exc:
        return _exception_to_adapter_failure(
            exc,
            context,
            windows,
            runtime_seconds=time.monotonic() - started,
        )


def _readiness_to_failure(readiness: Any) -> Any:
    from b08_model_core.adapters.open_models.base import AdapterFailure
    from b08_model_core.experiments.c21_executable_open_model_evaluation import (
        C21TaskId,
    )

    limitations = ", ".join(readiness.known_limitations)
    return AdapterFailure(
        model_id=readiness.model_id or "ttm",
        task_id=C21TaskId.FORECASTING,
        status=readiness.adapter_status,
        failure_stage="inspect",
        failure_reason=limitations or "TTM adapter is not ready",
        error_type="AdapterReadiness",
        error_detail=_value(readiness.metadata),
        dependency_status=readiness.dependency_status,
        weight_status=readiness.weight_status,
        adapter_name=readiness.adapter_name,
        model_ref=readiness.model_ref,
        cache_dir=readiness.cache_dir,
        actual_network_used=readiness.actual_network_used,
    )


def _c33_result_from_exception(
    exc: Exception,
    context: Any,
    windows: list[object],
    *,
    failure_stage: str,
    status: Any | None = None,
    raw_result: Any | None = None,
) -> C33AdapterExecutionResult:
    from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus

    actual_network_used = getattr(raw_result, "actual_network_used", None)
    return C33AdapterExecutionResult(
        model_id=getattr(raw_result, "model_id", "") or "ttm",
        task_id=_task_value(getattr(raw_result, "task_id", "forecasting")),
        status=status or OpenModelAdapterStatus.RUNTIME_FAILED,
        adapter_status=status or OpenModelAdapterStatus.RUNTIME_FAILED,
        metrics={},
        failure_stage=failure_stage,
        failure_reason=str(exc),
        error_type=type(exc).__name__,
        error_detail=str(exc),
        dependency_status=getattr(raw_result, "dependency_status", "unknown"),
        weight_status=_weight_status(raw_result),
        input_shape=_forecasting_input_shape(windows),
        output_shape=dict(getattr(raw_result, "output_shape", {}) or {}),
        runtime_seconds=_runtime_seconds(raw_result),
        adapter_name=getattr(raw_result, "adapter_name", ""),
        model_ref=getattr(raw_result, "model_ref", None),
        cache_dir=getattr(raw_result, "cache_dir", None) or context.cache_dir,
        actual_network_used=_network_usage_value(actual_network_used, context),
        download_allowed_not_verified=_download_allowed_not_verified(
            actual_network_used,
            context,
        ),
    )


def _metric_exception_status(exc: Exception) -> Any:
    from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus

    detail = str(exc).lower()
    if any(
        token in detail
        for token in (
            "shape",
            "matching",
            "broadcast",
            "sensor_ids length",
            "prediction and truth",
        )
    ):
        return OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE
    return OpenModelAdapterStatus.RUNTIME_FAILED


def _exception_to_adapter_failure(
    exc: Exception,
    context: Any,
    windows: list[object],
    *,
    runtime_seconds: float,
) -> Any:
    from b08_model_core.adapters.open_models.base import (
        AdapterFailure,
        OpenModelAdapterStatus,
    )
    from b08_model_core.experiments.c21_executable_open_model_evaluation import (
        C21TaskId,
    )

    return AdapterFailure(
        model_id="ttm",
        task_id=C21TaskId.FORECASTING,
        status=OpenModelAdapterStatus.RUNTIME_FAILED,
        failure_stage="execute",
        failure_reason=str(exc),
        error_type=type(exc).__name__,
        error_detail=str(exc),
        dependency_status="unknown",
        weight_status="unknown",
        input_shape=_forecasting_input_shape(windows),
        adapter_name="",
        runtime_seconds=runtime_seconds,
        cache_dir=context.cache_dir,
        actual_network_used=_network_usage_value(None, context),
    )


def _adapter_result_to_c33_result(raw_result: Any, context: Any) -> C33AdapterExecutionResult:
    status = getattr(raw_result, "status", "")
    if _status_value(status) == "available_and_ran" and hasattr(raw_result, "predictions"):
        metadata = dict(getattr(raw_result, "metadata", {}) or {})
        return C33AdapterExecutionResult(
            model_id=getattr(raw_result, "model_id", "") or "ttm",
            task_id=_task_value(getattr(raw_result, "task_id", "")),
            status=status,
            adapter_status=status,
            metrics=dict(getattr(raw_result, "metrics", {}) or {}),
            failure_stage="",
            failure_reason="",
            error_type="",
            error_detail="",
            dependency_status=metadata.get("dependency_status", "available"),
            weight_status=metadata.get("weight_status", "not_checked"),
            input_shape=dict(getattr(raw_result, "input_shape", {}) or {}),
            output_shape=dict(getattr(raw_result, "output_shape", {}) or {}),
            runtime_seconds=_runtime_seconds(raw_result),
            adapter_name=getattr(raw_result, "adapter_name", ""),
            model_ref=getattr(raw_result, "model_ref", None),
            cache_dir=getattr(raw_result, "cache_dir", None) or context.cache_dir,
            actual_network_used=_network_usage_value(
                getattr(raw_result, "actual_network_used", None),
                context,
            ),
            download_allowed_not_verified=_download_allowed_not_verified(
                getattr(raw_result, "actual_network_used", None),
                context,
            ),
        )
    if hasattr(raw_result, "status"):
        return C33AdapterExecutionResult(
            model_id=getattr(raw_result, "model_id", "") or "ttm",
            task_id=_task_value(getattr(raw_result, "task_id", "")),
            status=status,
            adapter_status=status,
            metrics={},
            failure_stage=getattr(raw_result, "failure_stage", ""),
            failure_reason=getattr(raw_result, "failure_reason", ""),
            error_type=getattr(raw_result, "error_type", ""),
            error_detail=getattr(raw_result, "error_detail", ""),
            dependency_status=getattr(raw_result, "dependency_status", "unknown"),
            weight_status=getattr(raw_result, "weight_status", "unknown"),
            input_shape=dict(getattr(raw_result, "input_shape", {}) or {}),
            output_shape={},
            runtime_seconds=getattr(raw_result, "runtime_seconds", None),
            adapter_name=getattr(raw_result, "adapter_name", ""),
            model_ref=getattr(raw_result, "model_ref", None),
            cache_dir=getattr(raw_result, "cache_dir", None) or context.cache_dir,
            actual_network_used=_network_usage_value(
                getattr(raw_result, "actual_network_used", None),
                context,
            ),
            download_allowed_not_verified=_download_allowed_not_verified(
                getattr(raw_result, "actual_network_used", None),
                context,
            ),
        )
    return _adapter_result_to_c33_result(
        _exception_to_adapter_failure(
            TypeError(
                f"adapter returned unsupported result type: {type(raw_result).__name__}"
            ),
            context,
            [],
            runtime_seconds=0.0,
        ),
        context,
    )


def _c33_result_from_exception(
    exc: Exception,
    context: Any,
    windows: list[object],
    *,
    failure_stage: str,
    status: object | None = None,
    raw_result: Any | None = None,
) -> C33AdapterExecutionResult:
    from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus

    adapter_status = status or OpenModelAdapterStatus.RUNTIME_FAILED
    return C33AdapterExecutionResult(
        model_id=getattr(raw_result, "model_id", "") or "ttm",
        task_id=_task_value(getattr(raw_result, "task_id", "")) or "forecasting",
        status=adapter_status,
        adapter_status=adapter_status,
        metrics={},
        failure_stage=failure_stage,
        failure_reason=str(exc),
        error_type=type(exc).__name__,
        error_detail=str(exc),
        dependency_status=getattr(raw_result, "dependency_status", "unknown"),
        weight_status=getattr(raw_result, "weight_status", "unknown"),
        input_shape=dict(
            getattr(raw_result, "input_shape", None)
            or _forecasting_input_shape(windows)
        ),
        output_shape=dict(getattr(raw_result, "output_shape", None) or {}),
        runtime_seconds=getattr(raw_result, "runtime_seconds", None),
        adapter_name=getattr(raw_result, "adapter_name", ""),
        model_ref=getattr(raw_result, "model_ref", None),
        cache_dir=getattr(raw_result, "cache_dir", None) or context.cache_dir,
        actual_network_used=_network_usage_value(
            getattr(raw_result, "actual_network_used", None),
            context,
        ),
        download_allowed_not_verified=_download_allowed_not_verified(
            getattr(raw_result, "actual_network_used", None),
            context,
        ),
    )


def _ttm_forecasting_evidence(
    raw_result: Any,
    windows: list[object],
    top_k: int,
) -> tuple[
    dict[str, float | int | None] | None,
    tuple[dict[str, float | int | str], ...] | None,
]:
    import numpy as np

    from b08_model_core.evaluation.metrics import (
        forecasting_metrics,
        forecasting_residual_ranking,
    )

    if _status_value(getattr(raw_result, "status", "")) != "available_and_ran":
        return None, None
    if not hasattr(raw_result, "predictions"):
        return None, None
    metrics = forecasting_metrics(
        {"y_hat": np.asarray(getattr(raw_result, "predictions"), dtype=float)},
        windows,
    )
    truth = np.stack([window.y for window in windows], axis=0)
    ranking = forecasting_residual_ranking(
        {"y_hat": np.asarray(getattr(raw_result, "predictions"), dtype=float)},
        truth,
        tuple(windows[0].sensor_token),
        top_k=top_k,
    )
    return metrics, ranking


def _metric_exception_status(exc: Exception) -> object:
    from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus

    message = str(exc).lower()
    if any(token in message for token in ("shape", "broadcast", "dimension", "axis")):
        return OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE
    return OpenModelAdapterStatus.RUNTIME_FAILED


def _c33_status_for_adapter_result(result: C33AdapterExecutionResult) -> str:
    status = _status_value(result.status)
    if status == "available_and_ran":
        return _TTM_READY_STATUS
    if status == "missing_dependency":
        return _TTM_MISSING_DEPENDENCY_STATUS
    if status == "missing_or_blocked_weights":
        return _TTM_MISSING_OR_BLOCKED_WEIGHTS_STATUS
    if status == "unsupported_window_shape":
        return _TTM_UNSUPPORTED_WINDOW_SHAPE_STATUS
    return _TTM_RUNTIME_FAILED_STATUS


def _is_successful_adapter_result(result: C33AdapterExecutionResult) -> bool:
    return _status_value(result.status) == "available_and_ran"


def _status_value(status: object) -> str:
    return str(getattr(status, "value", status))


def _adapter_execution_report_line(result: C33RunResult) -> str:
    if (
        result.baseline_reference_result is None
        and result.adapter_result is None
        and result.adapter_failure is None
    ):
        return "- Adapter execution: disabled in contract-only config"
    return "- Adapter execution: explicit local TTM run"


def _next_step_report_line(result: C33RunResult) -> str:
    if (
        result.baseline_reference_result is None
        and result.adapter_result is None
        and result.adapter_failure is None
    ):
        return "- Use an explicit local config to record TTM adapter/cache/dependency evidence."
    return "- Review C3.3 local TTM evidence before deciding whether another forecasting open model should be added."


def _render_forecasting_reference_section(
    result: C33ForecastingReferenceResult,
) -> list[str]:
    lines = [
        "## Baseline Forecasting Reference",
        "",
        f"- Simulation days: {result.days}",
        f"- Seed: {result.seed}",
        f"- Context length: {result.context_length}",
        f"- Prediction length: {result.prediction_length}",
        f"- Max windows: {result.max_windows}",
        f"- Train windows: {result.train_window_count}",
        f"- Test windows: {result.test_window_count}",
        "",
        "| Baseline | MAE | RMSE | Interval coverage | Count |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in result.baseline_results:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.model_name,
                    str(item.metrics["mae"]),
                    str(item.metrics["rmse"]),
                    str(item.metrics["interval_coverage"]),
                    str(item.metrics["count"]),
                ]
            )
            + " |"
        )
    for item in result.baseline_results:
        lines.extend(
            [
                "",
                f"### {item.model_name} Residual Ranking",
                "",
                "| Rank | Sensor | Mean absolute residual |",
                "| ---: | --- | ---: |",
            ]
        )
        for row in item.residual_ranking:
            lines.append(
                f"| {row['rank']} | {row['sensor_id']} | {row['mean_abs_residual']} |"
            )
    lines.append("")
    return lines


def _render_ttm_adapter_execution_section(
    result: C33AdapterExecutionResult,
) -> list[str]:
    return [
        "## TTM Adapter Execution",
        "",
        f"- status: {result.status}",
        f"- adapter_status: {result.adapter_status}",
        f"- dependency_status: {result.dependency_status}",
        f"- weight_status: {result.weight_status}",
        f"- runtime_seconds: {result.runtime_seconds}",
        f"- input_shape: {_value(result.input_shape)}",
        f"- output_shape: {_value(result.output_shape)}",
        f"- actual_network_used: {result.actual_network_used}",
        f"- download_allowed_not_verified: {result.download_allowed_not_verified}",
        f"- adapter_name: {result.adapter_name}",
        f"- model_ref: {result.model_ref}",
        f"- cache_dir: {result.cache_dir}",
        f"- failure_stage: {result.failure_stage}",
        f"- failure_reason: {result.failure_reason}",
        f"- error_type: {result.error_type}",
        f"- error_detail: {result.error_detail}",
        "",
    ]


def _render_ttm_metrics_section(
    metrics: dict[str, float | int | None],
    ranking: tuple[dict[str, float | int | str], ...],
) -> list[str]:
    lines = [
        "## TTM Forecasting Metrics",
        "",
        f"- MAE: {metrics['mae']}",
        f"- RMSE: {metrics['rmse']}",
        f"- Interval coverage: {metrics['interval_coverage']}",
        f"- Count: {metrics['count']}",
        "",
        "| Rank | Sensor | Mean absolute residual |",
        "| ---: | --- | ---: |",
    ]
    for row in ranking:
        lines.append(
            f"| {row['rank']} | {row['sensor_id']} | {row['mean_abs_residual']} |"
        )
    lines.append("")
    return lines


def _render_separated_metric_interpretation_section() -> list[str]:
    return [
        "## Separated Metric Interpretation",
        "",
        "- Baseline and TTM metrics are FU13-like forecasting evidence only.",
        "- Residual ranking explains sensor-level forecasting error; it is not a RUL metric.",
        "- This report does not create a candidate leaderboard or production readiness claim.",
        "",
    ]


def _task_value(task_id: Any) -> str:
    return str(getattr(task_id, "value", task_id))


def _runtime_seconds(raw_result: Any) -> float | None:
    if raw_result is None:
        return None
    runtime_seconds = getattr(raw_result, "runtime_seconds", None)
    if runtime_seconds is not None:
        return runtime_seconds
    value = (getattr(raw_result, "metrics", {}) or {}).get("runtime_seconds")
    return float(value) if isinstance(value, int | float) else None


def _status_value(status: Any) -> str:
    return str(getattr(status, "value", status))


def _weight_status(raw_result: Any | None) -> str:
    if raw_result is None:
        return "unknown"
    metadata = dict(getattr(raw_result, "metadata", {}) or {})
    return str(
        getattr(raw_result, "weight_status", None)
        or metadata.get("weight_status")
        or "unknown"
    )


def _network_usage_value(value: bool | str | None, context: Any) -> bool | str | None:
    return value


def _download_allowed_not_verified(value: bool | str | None, context: Any) -> bool:
    return bool(context.allow_download and not isinstance(value, bool))


def _forecasting_input_shape(windows: list[object]) -> dict[str, Any]:
    first = windows[0] if windows else None
    return {
        "windows": len(windows),
        "X": _array_shape(getattr(first, "X", None)),
        "y": _array_shape(getattr(first, "y", None)),
    }


def _array_shape(value: Any) -> list[int] | None:
    if value is None:
        return None
    try:
        return list(value.shape)
    except AttributeError:
        return None


def _value(value: object) -> str:
    return str(value)


def _adapter_execution_report_line(result: C33RunResult) -> str:
    if result.baseline_reference_result is None:
        return "- Adapter execution: disabled in contract-only config"
    return "- Adapter execution: explicit local TTM run"


def _next_step_report_line(result: C33RunResult) -> str:
    if result.baseline_reference_result is None:
        return "- Use an explicit local config to record TTM adapter/cache/dependency evidence."
    return "- Review the structured TTM adapter evidence before any broader C-stage promotion."


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise C33ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise C33ConfigError(f"{path} must contain a mapping")
    return loaded


def _project_root_for_config(path: Path) -> Path:
    resolved = path.resolve()
    for candidate in (resolved.parent, *resolved.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return Path.cwd()


def _local_execution_enabled(raw: dict[str, Any]) -> bool:
    local_execution = raw.get("local_execution")
    if local_execution is None:
        return False
    if not isinstance(local_execution, dict):
        raise C33ConfigError("local_execution must be a mapping")
    return _optional_bool(local_execution, "enabled", "local_execution", False)


def _load_safety_policy(
    raw: dict[str, Any],
    *,
    local_execution_enabled: bool,
) -> C33SafetyPolicy:
    policy = _required_mapping(raw, "safety_policy")
    values = {
        flag: _required_bool(policy, flag, "safety_policy")
        for flag in _SAFETY_FLAGS
    }

    if values["allow_training"] is not False:
        raise C33ConfigError("safety_policy.allow_training must always be false")
    if values["allow_write_processed"] is not False:
        raise C33ConfigError(
            "safety_policy.allow_write_processed must always be false"
        )
    if values["allow_download"] and not values["allow_network"]:
        raise C33ConfigError(
            "safety_policy.allow_network must be true when allow_download is true"
        )

    if local_execution_enabled:
        if values["allow_local_execution"] is not True:
            raise C33ConfigError(
                "safety_policy.allow_local_execution must be true when "
                "local_execution.enabled is true"
            )
        if values["allow_model_cache"] is not True:
            raise C33ConfigError(
                "safety_policy.allow_model_cache must be true when "
                "local_execution.enabled is true"
            )
    else:
        for flag in _SAFETY_FLAGS:
            if values[flag] is not False:
                raise C33ConfigError(
                    f"safety_policy.{flag} must be false for default "
                    "contract-only C3.3 config"
                )

    return C33SafetyPolicy(**values)


def _load_prerequisites(raw: dict[str, Any]) -> C33Prerequisites:
    prerequisites = _required_mapping(raw, "prerequisites")
    c32_local_status = _required_string(
        prerequisites, "c32_local_status", "prerequisites"
    )
    if c32_local_status != _EXPECTED_C32_LOCAL_STATUS:
        raise C33ConfigError(
            f"prerequisites.c32_local_status must be {_EXPECTED_C32_LOCAL_STATUS}"
        )
    return C33Prerequisites(
        c32_design_doc=Path(
            _required_string(prerequisites, "c32_design_doc", "prerequisites")
        ),
        c32_local_status=c32_local_status,
    )


def _load_candidate(raw: dict[str, Any]) -> C33Candidate:
    candidate = _required_mapping(raw, "candidate")
    for field, expected in _EXPECTED_CANDIDATE.items():
        value = _required_string(candidate, field, "candidate")
        if value != expected:
            raise C33ConfigError(f"candidate.{field} must be {expected}")
    return C33Candidate(
        model_id=_EXPECTED_CANDIDATE["model_id"],
        model_ref=_required_string(candidate, "model_ref", "candidate"),
        task_id=_EXPECTED_CANDIDATE["task_id"],
        dataset_view=_EXPECTED_CANDIDATE["dataset_view"],
    )


def _load_metric_contract(raw: dict[str, Any]) -> C33MetricContract:
    metric_contract = _required_mapping(raw, "metric_contract")
    leaderboard_allowed = _required_bool(
        metric_contract,
        "leaderboard_allowed",
        "metric_contract",
    )
    if leaderboard_allowed is not False:
        raise C33ConfigError("metric_contract.leaderboard_allowed must be false")
    return C33MetricContract(
        forecasting_metrics=_required_string_list(
            metric_contract,
            "forecasting_metrics",
            "metric_contract",
        ),
        adapter_status_fields=_required_string_list(
            metric_contract,
            "adapter_status_fields",
            "metric_contract",
        ),
        leaderboard_allowed=leaderboard_allowed,
    )


def _load_local_execution(
    raw: dict[str, Any],
    *,
    safety_policy: C33SafetyPolicy,
    config_root: Path,
) -> C33LocalExecutionConfig | None:
    local_execution = raw.get("local_execution")
    if local_execution is None:
        return None
    if not isinstance(local_execution, dict):
        raise C33ConfigError("local_execution must be a mapping")
    enabled = _optional_bool(local_execution, "enabled", "local_execution", False)
    if not enabled:
        return None
    if not safety_policy.allow_local_execution:
        raise C33ConfigError(
            "safety_policy.allow_local_execution must be true when "
            "local_execution.enabled is true"
        )
    if not safety_policy.allow_model_cache:
        raise C33ConfigError(
            "safety_policy.allow_model_cache must be true when "
            "local_execution.enabled is true"
        )

    model_cache_dir = Path(
        _required_string(local_execution, "model_cache_dir", "local_execution")
    )
    if not model_cache_dir.is_absolute():
        model_cache_dir = config_root / model_cache_dir
    fu13_like = _load_local_fu13_like(local_execution)
    return C33LocalExecutionConfig(
        enabled=enabled,
        model_cache_dir=model_cache_dir,
        fu13_like=fu13_like,
    )


def _load_local_fu13_like(raw: dict[str, Any]) -> C33LocalFu13LikeConfig:
    fu13_like = _required_mapping(raw, "fu13_like")
    config = C33LocalFu13LikeConfig(
        days=_required_int(fu13_like, "days", "local_execution.fu13_like"),
        seed=_required_int(fu13_like, "seed", "local_execution.fu13_like"),
        context_length=_required_int(
            fu13_like,
            "context_length",
            "local_execution.fu13_like",
        ),
        prediction_length=_required_int(
            fu13_like,
            "prediction_length",
            "local_execution.fu13_like",
        ),
        max_windows=_required_int(
            fu13_like,
            "max_windows",
            "local_execution.fu13_like",
        ),
        residual_top_k=_required_int(
            fu13_like,
            "residual_top_k",
            "local_execution.fu13_like",
        ),
    )
    for field in (
        "days",
        "context_length",
        "prediction_length",
        "max_windows",
        "residual_top_k",
    ):
        if getattr(config, field) <= 0:
            raise C33ConfigError(f"local_execution.fu13_like.{field} must be positive")
    if config.seed < 0:
        raise C33ConfigError("local_execution.fu13_like.seed must be non-negative")
    return config


def _load_outputs(raw: dict[str, Any]) -> C33Outputs:
    outputs = _required_mapping(raw, "outputs")
    return C33Outputs(
        report=Path(_required_string(outputs, "report", "outputs")),
    )


def _required_mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise C33ConfigError(f"{key} must be a mapping")
    return value


def _required_string(
    raw: dict[str, Any],
    key: str,
    context: str = "config",
) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise C33ConfigError(f"{context}.{key} must be a non-empty string")
    return value


def _required_string_list(
    raw: dict[str, Any],
    key: str,
    context: str,
) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise C33ConfigError(f"{context}.{key} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise C33ConfigError(f"{context}.{key} must contain non-empty strings")
    return tuple(value)


def _required_bool(raw: dict[str, Any], key: str, context: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise C33ConfigError(f"{context}.{key} must be a boolean")
    return value


def _optional_bool(
    raw: dict[str, Any],
    key: str,
    context: str,
    default: bool,
) -> bool:
    value = raw.get(key, default)
    if not isinstance(value, bool):
        raise C33ConfigError(f"{context}.{key} must be a boolean")
    return value


def _required_int(raw: dict[str, Any], key: str, context: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise C33ConfigError(f"{context}.{key} must be an integer")
    return value
