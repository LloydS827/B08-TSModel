from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable
import warnings

import numpy as np
import pandas as pd
import yaml

from b08_model_core.adapters.base import dependency_available
from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.experiments.c1_evidence import (
    apply_deterministic_mask,
    reconstruction_metrics,
    simple_statistical_embedding,
)
from b08_model_core.tasks.window_builder import build_model_windows


CORE_MODEL_IDS = ("ttm", "moment", "chronos", "timesfm", "moirai_uni2ts", "units")
INVALID_C2_CLAIMS = [
    "不得解释为生产告警",
    "不得解释为 FU13 RUL",
    "不得解释为自动维修建议",
    "不得解释为模型选型终局",
    "不得解释为自研训练 Go 结论",
]


class C2OpenModelConfigError(ValueError):
    """Raised when the C2 open model evaluation config cannot be used."""


class C2TaskId(StrEnum):
    FORECASTING = "forecasting"
    REPRESENTATION = "representation"
    IMPUTATION = "imputation"


class C2AuditStatus(StrEnum):
    AUDIT_PASSED = "audit_passed"
    NEEDS_LICENSE_REVIEW = "needs_license_review"
    NEEDS_DEPENDENCY_REVIEW = "needs_dependency_review"
    NEEDS_INTERFACE_REVIEW = "needs_interface_review"
    AUDIT_FAILED = "audit_failed"


class C2ModelTaskStatus(StrEnum):
    AVAILABLE_AND_RAN = "available_and_ran"
    MISSING_DEPENDENCY = "missing_dependency"
    MISSING_OR_BLOCKED_WEIGHTS = "missing_or_blocked_weights"
    UNSUPPORTED_TASK = "unsupported_task"
    UNSUPPORTED_WINDOW_SHAPE = "unsupported_window_shape"
    RUNTIME_FAILED = "runtime_failed"
    LICENSE_OR_INTERFACE_NEEDS_REVIEW = "license_or_interface_needs_review"
    SKIPPED_BY_CONFIG = "skipped_by_config"


@dataclass
class C2ModelSpec:
    model_id: str
    display_name: str
    source_kind: str
    source_ref: str
    model_card_ref: str
    license_note: str
    dependency_modules: list[str]
    primary_tasks: list[C2TaskId]
    supported_tasks: list[C2TaskId]
    force_missing_dependency: bool = False
    force_unsupported_task: bool = False


@dataclass
class C2ModelAuditRecord:
    model_id: str
    display_name: str
    source_kind: str
    source_ref: str
    model_card_ref: str
    license_note: str
    dependency_status: str
    weights_status: str
    supported_tasks: list[str]
    input_constraints: str
    offline_feasibility: str
    audit_status: C2AuditStatus


@dataclass
class C2ExecutionConfig:
    stage: str
    upstream_c1_config: Path
    dataset_path: Path
    fu13_config_path: Path
    dataset_boundary: str
    window_mode: str
    context_length: int
    prediction_length: int
    max_windows: int
    mask_ratio: float
    seed: int
    core_models: list[C2ModelSpec]
    task_policy: dict[C2TaskId, list[str]]
    allow_download: bool
    model_cache_dir: str | None
    strict_model_success: bool
    no_network_by_default: bool
    record_failure: bool
    do_not_over_claim: bool
    report_path: Path

    @property
    def by_model_id(self) -> dict[str, C2ModelSpec]:
        return {model.model_id: model for model in self.core_models}


@dataclass
class C2ModelTaskAttempt:
    model_id: str
    task_id: C2TaskId
    status: C2ModelTaskStatus = C2ModelTaskStatus.SKIPPED_BY_CONFIG


@dataclass
class C2ModelTaskResult:
    model_id: str
    display_name: str
    task_id: C2TaskId
    status: C2ModelTaskStatus
    dataset_boundary: str
    window_policy: str
    metrics: dict[str, Any]
    baseline_reference: str
    baseline_metrics: dict[str, Any]
    failure_reason: str | None
    error_detail: str | None
    artifact_outputs: dict[str, Any]
    invalid_claims: list[str]
    decision_notes: list[str]


@dataclass
class C2OpenModelEvaluationResult:
    run_id: str
    upstream_c1_config: str
    execution_time_utc: str
    dataset_boundary: str
    environment_boundary: str
    audit_records: list[C2ModelAuditRecord]
    task_results: list[C2ModelTaskResult]
    failure_taxonomy: dict[str, list[dict[str, str]]]
    c3_handoff_notes: list[str]
    b_decision_notes: list[str]
    invalid_claims: list[str]


@dataclass
class C2ModelRegistry:
    by_model_id: dict[str, C2ModelSpec]
    attempts: list[C2ModelTaskAttempt]
    allow_download: bool = False
    no_network_by_default: bool = True


def load_c2_open_model_config(path: str | Path) -> C2ExecutionConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise C2OpenModelConfigError("C2 open model config must be a mapping")

    dataset = _load_optional_mapping(raw, "dataset")
    window = _load_optional_mapping(raw, "window")
    cache_policy = _load_optional_mapping(raw, "model_cache_policy")
    execution_policy = _load_optional_mapping(raw, "execution_policy")
    outputs = _load_optional_mapping(raw, "outputs")
    core_models = _load_optional_list(raw, "core_models")
    task_policy = _load_optional_mapping(raw, "task_policy")
    stage = _load_required_string(raw, "stage")
    if stage != "C2_open_model_evaluation":
        raise C2OpenModelConfigError("C2 stage must be C2_open_model_evaluation")

    return C2ExecutionConfig(
        stage=stage,
        upstream_c1_config=Path(_load_required_string(raw, "upstream_c1_config")),
        dataset_path=Path(_load_required_string(dataset, "fu13_observations")),
        fu13_config_path=Path(_load_required_string(dataset, "fu13_config")),
        dataset_boundary=_load_required_string(dataset, "boundary"),
        window_mode=_load_window_mode(window),
        context_length=_load_positive_int(window, "context_length"),
        prediction_length=_load_positive_int(window, "prediction_length"),
        max_windows=_load_min_int(window, "max_windows", minimum=2),
        mask_ratio=_load_mask_ratio(window, "mask_ratio"),
        seed=_load_nonnegative_int(window, "seed"),
        core_models=[_load_model_spec(item) for item in core_models],
        task_policy=_load_task_policy(task_policy),
        allow_download=_load_bool(cache_policy, "allow_download", False),
        model_cache_dir=cache_policy.get("cache_dir"),
        strict_model_success=_load_bool(execution_policy, "strict_model_success", False),
        no_network_by_default=_load_bool(execution_policy, "no_network_by_default", True),
        record_failure=_load_bool(execution_policy, "record_failure", True),
        do_not_over_claim=_load_bool(execution_policy, "do_not_over_claim", True),
        report_path=Path(_load_required_string(outputs, "report")),
    )


def build_c2_model_registry(config: C2ExecutionConfig) -> C2ModelRegistry:
    configured_ids = [model.model_id for model in config.core_models]
    configured_id_set = set(configured_ids)
    core_id_set = set(CORE_MODEL_IDS)
    missing = sorted(core_id_set - configured_id_set)
    extra = sorted(configured_id_set - core_id_set)
    duplicates = sorted({model_id for model_id in configured_ids if configured_ids.count(model_id) > 1})
    if missing:
        raise C2OpenModelConfigError(f"missing core models: {missing}")
    if extra:
        raise C2OpenModelConfigError(f"extra core models: {extra}")
    if duplicates:
        raise C2OpenModelConfigError(f"duplicate core models: {duplicates}")
    if configured_ids != list(CORE_MODEL_IDS):
        raise C2OpenModelConfigError(
            f"core model order must be {list(CORE_MODEL_IDS)}, got {configured_ids}"
        )

    by_model_id = config.by_model_id
    attempts: list[C2ModelTaskAttempt] = []
    covered_pairs: set[tuple[str, C2TaskId]] = set()
    for task_id, model_ids in config.task_policy.items():
        for model_id in model_ids:
            if model_id not in by_model_id:
                raise C2OpenModelConfigError(f"task policy references unknown core model: {model_id}")
            pair = (model_id, task_id)
            if pair not in covered_pairs:
                attempts.append(C2ModelTaskAttempt(model_id=model_id, task_id=task_id))
                covered_pairs.add(pair)

    for model in config.core_models:
        if not model.primary_tasks:
            raise C2OpenModelConfigError(f"{model.model_id} must declare at least one primary task")
        for task_id in model.primary_tasks:
            pair = (model.model_id, task_id)
            if pair not in covered_pairs:
                attempts.append(C2ModelTaskAttempt(model_id=model.model_id, task_id=task_id))
                covered_pairs.add(pair)

    return C2ModelRegistry(
        by_model_id=by_model_id,
        attempts=attempts,
        allow_download=config.allow_download,
        no_network_by_default=config.no_network_by_default,
    )


def run_c2_model_audit(
    registry: C2ModelRegistry,
    dependency_checker: Callable[[str], bool] = dependency_available,
) -> list[C2ModelAuditRecord]:
    records: list[C2ModelAuditRecord] = []
    for model in registry.by_model_id.values():
        missing_dependencies = [
            module_name
            for module_name in model.dependency_modules
            if not dependency_checker(module_name)
        ]
        dependency_status = _format_dependency_status(model, missing_dependencies)
        audit_status = _audit_status_for_model(model, missing_dependencies)
        records.append(
            C2ModelAuditRecord(
                model_id=model.model_id,
                display_name=model.display_name,
                source_kind=model.source_kind,
                source_ref=model.source_ref,
                model_card_ref=model.model_card_ref,
                license_note=model.license_note,
                dependency_status=dependency_status,
                weights_status=_weights_status_for_model(model, registry.allow_download),
                supported_tasks=[task_id.value for task_id in model.supported_tasks],
                input_constraints=_input_constraints_for_model(model),
                offline_feasibility=_offline_feasibility(registry.no_network_by_default),
                audit_status=audit_status,
            )
        )
    return records


def run_c2_open_model_evaluation(config: C2ExecutionConfig) -> C2OpenModelEvaluationResult:
    registry = build_c2_model_registry(config)
    audit_records = run_c2_model_audit(registry)
    audit_by_model_id = {record.model_id: record for record in audit_records}

    df = pd.read_parquet(config.dataset_path)
    windows = build_model_windows(
        df,
        context_length=config.context_length,
        prediction_length=config.prediction_length,
        stride=config.prediction_length,
        allow_cross_stage=(config.window_mode == "cross-stage"),
    )[: config.max_windows]
    if len(windows) < 2:
        raise ValueError(f"not enough windows for C2 evaluation: need at least 2, got {len(windows)}")

    baselines = {
        C2TaskId.FORECASTING: _forecasting_baseline(windows),
        C2TaskId.REPRESENTATION: _representation_baseline(windows),
        C2TaskId.IMPUTATION: _imputation_baseline(config, windows),
    }
    window_policy = _window_policy(config, len(windows))
    task_results: list[C2ModelTaskResult] = []
    failure_taxonomy: dict[str, list[dict[str, str]]] = {}

    for attempt in registry.attempts:
        model = registry.by_model_id[attempt.model_id]
        audit_record = audit_by_model_id[attempt.model_id]
        status, failure_reason, error_detail = _model_task_status(model, attempt.task_id, audit_record)
        baseline_reference, baseline_metrics, baseline_artifacts = baselines[attempt.task_id]
        result = C2ModelTaskResult(
            model_id=model.model_id,
            display_name=model.display_name,
            task_id=attempt.task_id,
            status=status,
            dataset_boundary=config.dataset_boundary,
            window_policy=window_policy,
            metrics={},
            baseline_reference=baseline_reference,
            baseline_metrics=baseline_metrics,
            failure_reason=failure_reason,
            error_detail=error_detail,
            artifact_outputs=baseline_artifacts,
            invalid_claims=list(INVALID_C2_CLAIMS),
            decision_notes=_decision_notes(status, baseline_reference),
        )
        task_results.append(result)
        if failure_reason:
            failure_taxonomy.setdefault(status.value, []).append(
                {
                    "model_id": model.model_id,
                    "task_id": attempt.task_id.value,
                    "reason": failure_reason,
                    "detail": error_detail or "",
                }
            )

    execution_time_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return C2OpenModelEvaluationResult(
        run_id=_run_id(config, execution_time_utc),
        upstream_c1_config=str(config.upstream_c1_config),
        execution_time_utc=execution_time_utc,
        dataset_boundary=config.dataset_boundary,
        environment_boundary=_environment_boundary(config),
        audit_records=audit_records,
        task_results=task_results,
        failure_taxonomy=failure_taxonomy,
        c3_handoff_notes=[
            "C2 records baseline metrics and model-task readiness only.",
            "C3 must re-check licenses, interfaces, and dependencies before any external model execution.",
        ],
        b_decision_notes=[
            "C2 results are not a B-stage self-training Go decision.",
            "No open model candidate is marked available_and_ran in this status-only task.",
        ],
        invalid_claims=list(INVALID_C2_CLAIMS),
    )


def render_c2_open_model_report(
    result: C2OpenModelEvaluationResult,
    *,
    config_path: str | None = None,
) -> str:
    lines = [
        "# C2 Open Model Evaluation Report",
        "",
        "## Report Metadata",
        "",
        f"- config_path: {_value(config_path)}",
        f"- run_id: {_value(result.run_id)}",
        f"- upstream_c1_config: {_value(result.upstream_c1_config)}",
        f"- execution_time_utc: {_value(result.execution_time_utc)}",
        f"- dataset_boundary: {_value(result.dataset_boundary)}",
        f"- environment_boundary: {_value(result.environment_boundary)}",
        f"- audit_records: {len(result.audit_records)}",
        f"- task_results: {len(result.task_results)}",
        "",
        "## C2 Scope",
        "",
        f"- core_model_ids: {_value(list(CORE_MODEL_IDS))}",
        "- scope: open model audit and status-only model-task evaluation",
        "- boundary: C2 does not approve B-stage self-training or C3 execution readiness.",
        "",
        "## Model Audit Table",
        "",
        (
            "| model_id | display_name | source_kind | source_ref | model_card_ref | "
            "license_note | dependency_status | weights_status | supported_tasks | "
            "input_constraints | offline_feasibility | audit_status |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in result.audit_records:
        lines.append(
            (
                f"| {_cell(record.model_id)} | {_cell(record.display_name)} | {_cell(record.source_kind)} | "
                f"{_cell(record.source_ref)} | {_cell(record.model_card_ref)} | {_cell(record.license_note)} | "
                f"{_cell(record.dependency_status)} | {_cell(record.weights_status)} | "
                f"{_cell(record.supported_tasks)} | {_cell(record.input_constraints)} | "
                f"{_cell(record.offline_feasibility)} | {_cell(record.audit_status.value)} |"
            )
        )

    lines.extend(
        [
            "",
            "## Model-Task Result Matrix",
            "",
            (
                "| model_id | display_name | task_id | status | dataset_boundary | window_policy | "
                "failure_reason | error_detail | decision_notes |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for task_result in result.task_results:
        lines.append(
            (
                f"| {_cell(task_result.model_id)} | {_cell(task_result.display_name)} | "
                f"{_cell(task_result.task_id.value)} | {_cell(task_result.status.value)} | "
                f"{_cell(task_result.dataset_boundary)} | {_cell(task_result.window_policy)} | "
                f"{_cell(task_result.failure_reason)} | {_cell(task_result.error_detail)} | "
                f"{_cell(task_result.decision_notes)} |"
            )
        )

    lines.extend(
        [
            "",
            "## Forecasting Results",
            "",
            "| model_id | status | baseline_reference | metrics | baseline_metrics | artifact_outputs |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for task_result in result.task_results:
        if task_result.task_id != C2TaskId.FORECASTING:
            continue
        lines.append(_task_result_metric_row(task_result))

    lines.extend(
        [
            "",
            "## Representation And Imputation Results",
            "",
            "| model_id | task_id | status | baseline_reference | metrics | baseline_metrics | artifact_outputs |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for task_result in result.task_results:
        if task_result.task_id not in {C2TaskId.REPRESENTATION, C2TaskId.IMPUTATION}:
            continue
        lines.append(
            (
                f"| {_cell(task_result.model_id)} | {_cell(task_result.task_id.value)} | "
                f"{_cell(task_result.status.value)} | {_cell(task_result.baseline_reference)} | "
                f"{_cell(task_result.metrics)} | {_cell(task_result.baseline_metrics)} | "
                f"{_cell(task_result.artifact_outputs)} |"
            )
        )

    lines.extend(
        [
            "",
            "## Baseline Comparison",
            "",
            "| task_id | model_id | baseline_reference | baseline_metrics |",
            "| --- | --- | --- | --- |",
        ]
    )
    for task_result in result.task_results:
        lines.append(
            (
                f"| {_cell(task_result.task_id.value)} | {_cell(task_result.model_id)} | "
                f"{_cell(task_result.baseline_reference)} | {_cell(task_result.baseline_metrics)} |"
            )
        )

    lines.extend(
        [
            "",
            "## Failure Taxonomy",
            "",
            "| status | model_id | task_id | reason | detail |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    failure_rows = [
        (status, item)
        for status, items in result.failure_taxonomy.items()
        for item in items
    ]
    if failure_rows:
        for status, item in failure_rows:
            lines.append(
                (
                    f"| {_cell(status)} | {_cell(item.get('model_id'))} | {_cell(item.get('task_id'))} | "
                    f"{_cell(item.get('reason'))} | {_cell(item.get('detail'))} |"
                )
            )
    else:
        lines.append("| none | none | none | none | none |")

    lines.extend(["", "## C2 -> C3 Handoff", ""])
    lines.extend(f"- {_value(note)}" for note in result.c3_handoff_notes)
    lines.extend(["", "## C2 -> B Decision Notes", ""])
    lines.extend(f"- {_value(note)}" for note in result.b_decision_notes)
    lines.extend(["", "## Invalid Claims", ""])
    lines.extend(f"- {claim}" for claim in result.invalid_claims)
    return "\n".join(lines) + "\n"


def _task_result_metric_row(task_result: C2ModelTaskResult) -> str:
    return (
        f"| {_cell(task_result.model_id)} | {_cell(task_result.status.value)} | "
        f"{_cell(task_result.baseline_reference)} | {_cell(task_result.metrics)} | "
        f"{_cell(task_result.baseline_metrics)} | {_cell(task_result.artifact_outputs)} |"
    )


def _forecasting_baseline(windows: list[object]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    split = max(1, int(len(windows) * 0.7))
    train = windows[:split]
    test = windows[split:]
    if not test:
        raise ValueError("not enough windows for C2 forecasting test split")
    predictions = RobustStageForecaster().fit(train).predict(test)
    metrics = forecasting_metrics(predictions, test)
    return (
        "RobustStageForecaster",
        metrics,
        {
            "split_policy": "ordered_70_30",
            "train_windows": len(train),
            "test_windows": len(test),
        },
    )


def _representation_baseline(windows: list[object]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    embeddings = [simple_statistical_embedding(window.X) for window in windows]
    feature_count = len(embeddings[0]) if embeddings else 0
    return (
        "statistical_embedding",
        {
            "embedding_windows": len(embeddings),
            "embedding_features": feature_count,
        },
        {
            "statistical_embedding_example": embeddings[0] if embeddings else {},
        },
    )


def _imputation_baseline(
    config: C2ExecutionConfig,
    windows: list[object],
) -> tuple[str, dict[str, Any], dict[str, Any]]:
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
    metrics = {
        "mae": float(np.mean(mae_values)) if mae_values else None,
        "rmse": float(np.mean(rmse_values)) if rmse_values else None,
        "count": int(sum(int(metric["count"]) for metric in metrics_by_window)),
    }
    return (
        "simple_reconstruction_baseline",
        metrics,
        {
            "mask_policy": {
                "mask_ratio": config.mask_ratio,
                "seed": config.seed,
                "applied_windows": len(windows),
            },
        },
    )


def _model_task_status(
    model: C2ModelSpec,
    task_id: C2TaskId,
    audit_record: C2ModelAuditRecord,
) -> tuple[C2ModelTaskStatus, str | None, str | None]:
    if model.force_missing_dependency:
        return (
            C2ModelTaskStatus.MISSING_DEPENDENCY,
            "forced missing dependency status from C2 config",
            "force_missing_dependency:true",
        )
    if model.force_unsupported_task:
        return (
            C2ModelTaskStatus.UNSUPPORTED_TASK,
            "forced unsupported task status from C2 config",
            "force_unsupported_task:true",
        )
    if audit_record.dependency_status.startswith("missing:"):
        return (
            C2ModelTaskStatus.MISSING_DEPENDENCY,
            "dependency modules are unavailable",
            audit_record.dependency_status,
        )
    if task_id not in model.supported_tasks:
        return (
            C2ModelTaskStatus.UNSUPPORTED_TASK,
            f"{task_id.value} is not listed in supported_tasks",
            ",".join(task.value for task in model.supported_tasks),
        )
    if audit_record.weights_status == "download_disabled":
        return (
            C2ModelTaskStatus.MISSING_OR_BLOCKED_WEIGHTS,
            "model weights are unavailable because downloads are disabled",
            audit_record.weights_status,
        )
    if audit_record.audit_status in {
        C2AuditStatus.NEEDS_LICENSE_REVIEW,
        C2AuditStatus.NEEDS_INTERFACE_REVIEW,
    }:
        return (
            C2ModelTaskStatus.LICENSE_OR_INTERFACE_NEEDS_REVIEW,
            "license or interface review prevents external model execution",
            audit_record.audit_status.value,
        )
    return (
        C2ModelTaskStatus.LICENSE_OR_INTERFACE_NEEDS_REVIEW,
        "external model runtime is not implemented in C2 Task 3",
        "status_only_runner",
    )


def _window_policy(config: C2ExecutionConfig, window_count: int) -> str:
    return (
        f"mode:{config.window_mode};context:{config.context_length};"
        f"prediction:{config.prediction_length};max_windows:{config.max_windows};"
        f"used_windows:{window_count}"
    )


def _run_id(config: C2ExecutionConfig, execution_time_utc: str) -> str:
    compact_time = (
        execution_time_utc.replace("-", "")
        .replace(":", "")
        .replace("+0000", "Z")
        .replace("+00:00", "Z")
    )
    return f"{config.stage}:{compact_time}:cfg{_config_signature(config)}"


def _config_signature(config: C2ExecutionConfig) -> str:
    payload = {
        "stage": config.stage,
        "upstream_c1_config": str(config.upstream_c1_config),
        "dataset_path": str(config.dataset_path),
        "fu13_config_path": str(config.fu13_config_path),
        "dataset_boundary": config.dataset_boundary,
        "window_mode": config.window_mode,
        "context_length": config.context_length,
        "prediction_length": config.prediction_length,
        "max_windows": config.max_windows,
        "mask_ratio": config.mask_ratio,
        "seed": config.seed,
        "task_policy": {
            task_id.value: model_ids for task_id, model_ids in config.task_policy.items()
        },
        "allow_download": config.allow_download,
        "model_cache_dir": config.model_cache_dir,
        "strict_model_success": config.strict_model_success,
        "no_network_by_default": config.no_network_by_default,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:12]


def _environment_boundary(config: C2ExecutionConfig) -> str:
    return (
        f"no_network_by_default:{str(config.no_network_by_default).lower()};"
        f"allow_download:{str(config.allow_download).lower()};"
        f"model_cache_dir:{_value(config.model_cache_dir)}"
    )


def _decision_notes(status: C2ModelTaskStatus, baseline_reference: str) -> list[str]:
    return [
        f"candidate_status:{status.value}",
        f"baseline_reference:{baseline_reference}",
        "candidate external runtime was not executed in C2 Task 3.",
    ]


def _format_dependency_status(
    model: C2ModelSpec,
    missing_dependencies: list[str],
) -> str:
    if missing_dependencies:
        return f"missing:{','.join(missing_dependencies)}"
    if model.dependency_modules:
        return "available"
    return "not_required"


def _audit_status_for_model(
    model: C2ModelSpec,
    missing_dependencies: list[str],
) -> C2AuditStatus:
    if missing_dependencies:
        return C2AuditStatus.NEEDS_DEPENDENCY_REVIEW
    if model.license_note == "needs_review":
        return C2AuditStatus.NEEDS_LICENSE_REVIEW
    if not model.source_ref or not model.model_card_ref or not model.supported_tasks:
        return C2AuditStatus.NEEDS_INTERFACE_REVIEW
    return C2AuditStatus.AUDIT_PASSED


def _weights_status_for_model(model: C2ModelSpec, allow_download: bool) -> str:
    if not model.model_card_ref or model.model_card_ref == "not_required":
        return "not_required_for_status_check"
    if allow_download:
        return "download_allowed"
    return "download_disabled"


def _input_constraints_for_model(model: C2ModelSpec) -> str:
    supported_tasks = ",".join(task_id.value for task_id in model.supported_tasks)
    return f"supported_tasks:{supported_tasks}" if supported_tasks else "supported_tasks:missing"


def _offline_feasibility(no_network_by_default: bool) -> str:
    return f"no_network_by_default:{str(no_network_by_default).lower()}"


def _load_model_spec(raw: Any) -> C2ModelSpec:
    if not isinstance(raw, dict):
        raise C2OpenModelConfigError("each C2 core model entry must be a mapping")
    return C2ModelSpec(
        model_id=str(raw.get("model_id", "")),
        display_name=str(raw.get("display_name", "")),
        source_kind=str(raw.get("source_kind", "")),
        source_ref=str(raw.get("source_ref", "")),
        model_card_ref=str(raw.get("model_card_ref", "")),
        license_note=str(raw.get("license_note", "")),
        dependency_modules=_load_string_list(raw, "dependency_modules"),
        primary_tasks=_load_task_ids(_load_optional_list(raw, "primary_tasks")),
        supported_tasks=_load_task_ids(_load_optional_list(raw, "supported_tasks")),
        force_missing_dependency=_load_bool(raw, "force_missing_dependency", False),
        force_unsupported_task=_load_bool(raw, "force_unsupported_task", False),
    )


def _load_task_policy(raw: Any) -> dict[C2TaskId, list[str]]:
    if not isinstance(raw, dict):
        raise C2OpenModelConfigError("C2 task policy must be a mapping")
    policy: dict[C2TaskId, list[str]] = {}
    for task_id, model_ids in raw.items():
        if not isinstance(model_ids, list):
            raise C2OpenModelConfigError("C2 task policy values must be lists")
        policy[_load_task_id(task_id)] = [str(model_id) for model_id in model_ids]
    return policy


def _load_task_ids(raw: Any) -> list[C2TaskId]:
    return [_load_task_id(task_id) for task_id in raw]


def _load_task_id(raw: Any) -> C2TaskId:
    try:
        return C2TaskId(str(raw))
    except ValueError as exc:
        raise C2OpenModelConfigError(f"unknown C2 task id: {raw}") from exc


def _load_optional_mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    if key not in raw:
        return {}
    value = raw[key]
    if not isinstance(value, dict):
        raise C2OpenModelConfigError(f"C2 {key} must be a mapping")
    return value


def _load_optional_list(raw: dict[str, Any], key: str) -> list[Any]:
    if key not in raw:
        return []
    value = raw[key]
    if not isinstance(value, list):
        raise C2OpenModelConfigError(f"C2 {key} must be a list")
    return value


def _load_string_list(raw: dict[str, Any], key: str) -> list[str]:
    return [str(item) for item in _load_optional_list(raw, key)]


def _load_bool(raw: dict[str, Any], key: str, default: bool) -> bool:
    if key not in raw:
        return default
    value = raw[key]
    if not isinstance(value, bool):
        raise C2OpenModelConfigError(f"C2 {key} must be a boolean")
    return value


def _load_required_string(raw: dict[str, Any], key: str) -> str:
    if key not in raw:
        raise C2OpenModelConfigError(f"C2 {key} is required")
    value = raw[key]
    if not isinstance(value, str) or not value.strip():
        raise C2OpenModelConfigError(f"C2 {key} must be a non-empty string")
    return value


def _load_window_mode(raw: dict[str, Any]) -> str:
    value = _load_required_string(raw, "window_mode")
    if value not in {"cross-stage", "stage-local"}:
        raise C2OpenModelConfigError("C2 window_mode must be cross-stage or stage-local")
    return value


def _load_positive_int(raw: dict[str, Any], key: str) -> int:
    value = _load_int(raw, key)
    if value <= 0:
        raise C2OpenModelConfigError(f"C2 {key} must be a positive integer")
    return value


def _load_min_int(raw: dict[str, Any], key: str, *, minimum: int) -> int:
    value = _load_int(raw, key)
    if value < minimum:
        raise C2OpenModelConfigError(f"C2 {key} must be >= {minimum}")
    return value


def _load_nonnegative_int(raw: dict[str, Any], key: str) -> int:
    value = _load_int(raw, key)
    if value < 0:
        raise C2OpenModelConfigError(f"C2 {key} must be a non-negative integer")
    return value


def _load_int(raw: dict[str, Any], key: str) -> int:
    if key not in raw:
        raise C2OpenModelConfigError(f"C2 {key} is required")
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise C2OpenModelConfigError(f"C2 {key} must be an integer")
    return value


def _load_mask_ratio(raw: dict[str, Any], key: str) -> float:
    if key not in raw:
        raise C2OpenModelConfigError(f"C2 {key} is required")
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise C2OpenModelConfigError(f"C2 {key} must be a number")
    ratio = float(value)
    if not math.isfinite(ratio):
        raise C2OpenModelConfigError(f"C2 {key} must be finite")
    if ratio <= 0 or ratio > 1:
        raise C2OpenModelConfigError(f"C2 {key} must be > 0 and <= 1")
    return ratio


def _value(value: object) -> str:
    if value is None or (isinstance(value, str) and value == ""):
        return "not_available"
    if isinstance(value, dict):
        if not value:
            return "not_available"
        return ", ".join(f"{key}={_value(item)}" for key, item in value.items())
    if isinstance(value, list):
        if not value:
            return "not_available"
        return ", ".join(_value(item) for item in value)
    return str(value)


def _cell(value: object) -> str:
    return _value(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("|", "\\|")
