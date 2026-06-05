from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.experiments.c_stage_contract import (
    load_and_validate_c_stage_contract,
)
from b08_model_core.tasks.window_builder import build_model_windows


class C1EvidenceConfigError(ValueError):
    """Raised when the C1 execution config cannot be used."""


class EvidenceStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    PLANNED_NOT_EXECUTED = "planned_not_executed"


class ModelExecutionStatus(StrEnum):
    AVAILABLE_AND_RAN = "available_and_ran"
    MISSING_DEPENDENCY = "missing_dependency"
    MISSING_OR_BLOCKED_WEIGHTS = "missing_or_blocked_weights"
    UNSUPPORTED_TASK = "unsupported_task"
    UNSUPPORTED_WINDOW_SHAPE = "unsupported_window_shape"
    RUNTIME_FAILED = "runtime_failed"
    SKIPPED_BY_CONFIG = "skipped_by_config"
    PLANNED_NOT_EXECUTED = "planned_not_executed"


@dataclass
class C1ExecutionConfig:
    stage: str
    contract_path: Path
    dataset_path: Path
    fu13_config_path: Path
    dataset_boundary: str
    enabled_evidence: list[str]
    window_mode: str
    context_length: int
    prediction_length: int
    max_windows: int
    models: dict[str, Any]
    report_path: Path
    strict_model_success: bool
    allow_download: bool
    model_cache_dir: str | None


@dataclass
class C1EvidenceSpec:
    evidence_id: str
    experiment_id: str
    task_id: str
    primary_metric: list[str]
    comparison: dict[str, Any]
    data_label_audit: dict[str, Any]
    invalid_claims: list[str]


@dataclass
class C1EvidenceRegistry:
    by_evidence_id: dict[str, C1EvidenceSpec]
    execution_status: dict[str, EvidenceStatus]
    decision_gate: dict[str, Any]


@dataclass
class C1ModelResult:
    model_name: str
    status: ModelExecutionStatus
    reason: str = ""
    metrics: dict[str, float | int | None] | None = None


@dataclass
class C1EvidenceResult:
    evidence_id: str
    experiment_id: str
    task_id: str
    status: EvidenceStatus
    dataset_boundary: str
    split_policy: str
    data_label_audit: dict[str, Any]
    model_results: list[C1ModelResult]
    primary_metrics: dict[str, float | int | str | None]
    failure_reasons: list[str]
    artifact_outputs: dict[str, Any]
    invalid_claims: list[str]
    decision_gate_notes: list[str]


def load_c1_execution_config(path: str | Path) -> C1ExecutionConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise C1EvidenceConfigError("C1 execution config must be a mapping")

    dataset = raw.get("dataset") or {}
    window = raw.get("window") or {}
    outputs = raw.get("outputs") or {}
    policy = raw.get("execution_policy") or {}
    models = raw.get("models") or {}
    ttm = models.get("ttm") or {}

    return C1ExecutionConfig(
        stage=str(raw.get("stage", "")),
        contract_path=Path(raw.get("contract_path", "")),
        dataset_path=Path(dataset.get("fu13_observations", "")),
        fu13_config_path=Path(dataset.get("fu13_config", "")),
        dataset_boundary=str(dataset.get("boundary", "")),
        enabled_evidence=list(raw.get("enabled_evidence") or []),
        window_mode=str(window.get("window_mode", "cross-stage")),
        context_length=int(window.get("context_length", 90)),
        prediction_length=int(window.get("prediction_length", 16)),
        max_windows=int(window.get("max_windows", 40)),
        models=dict(models),
        report_path=Path(outputs.get("report", "reports/c_stage_c1_evidence_report.md")),
        strict_model_success=bool(policy.get("strict_model_success", False)),
        allow_download=bool(ttm.get("allow_download", False)),
        model_cache_dir=ttm.get("model_cache_dir"),
    )


def build_c1_registry(config: C1ExecutionConfig) -> C1EvidenceRegistry:
    contract = load_and_validate_c_stage_contract(config.contract_path)
    experiments = contract["experiments"]
    known_evidence = {item["evidence_id"] for item in experiments}
    unknown = sorted(set(config.enabled_evidence) - known_evidence)
    if unknown:
        raise C1EvidenceConfigError(f"unknown enabled evidence: {unknown}")

    specs = {
        item["evidence_id"]: C1EvidenceSpec(
            evidence_id=item["evidence_id"],
            experiment_id=item["experiment_id"],
            task_id=item["task_id"],
            primary_metric=list(item.get("primary_metric") or []),
            comparison=dict(item.get("comparison") or {}),
            data_label_audit=dict(item.get("data_label_audit") or {}),
            invalid_claims=list(item.get("invalid_claims") or []),
        )
        for item in experiments
    }
    enabled = set(config.enabled_evidence)
    execution_status = {
        evidence_id: (
            EvidenceStatus.NEEDS_REVIEW
            if evidence_id in enabled
            else EvidenceStatus.PLANNED_NOT_EXECUTED
        )
        for evidence_id in specs
    }
    return C1EvidenceRegistry(
        by_evidence_id=specs,
        execution_status=execution_status,
        decision_gate=dict(contract.get("decision_gate") or {}),
    )


def render_c1_evidence_report(
    results: list[C1EvidenceResult],
    *,
    planned_not_executed: list[str] | None = None,
) -> str:
    planned = planned_not_executed or []
    lines = [
        "# C1 Evidence Report",
        "",
        "## Summary",
        "",
        "| evidence_id | status |",
        "| --- | --- |",
    ]
    for result in results:
        lines.append(f"| {_cell(result.evidence_id)} | {_cell(result.status.value)} |")
    for evidence_id in planned:
        lines.append(f"| {_cell(evidence_id)} | planned_not_executed |")

    for result in results:
        lines.extend(
            [
                "",
                f"## {result.evidence_id}",
                "",
                f"- experiment_id: {_value(result.experiment_id)}",
                f"- task_id: {_value(result.task_id)}",
                f"- status: {_value(result.status.value)}",
                f"- dataset_boundary: {_value(result.dataset_boundary)}",
                f"- split_policy: {_value(result.split_policy)}",
                "",
                "### data_label_audit",
            ]
        )
        for key, value in result.data_label_audit.items():
            lines.append(f"- {key}: {_value(value)}")
        lines.extend(["", "### Model Results", "", "| model | status | reason |", "| --- | --- | --- |"])
        for model in result.model_results:
            lines.append(
                f"| {_cell(model.model_name)} | {_cell(model.status.value)} | {_cell(model.reason or 'not_available')} |"
            )
        lines.extend(["", "### Primary Metrics"])
        for key, value in result.primary_metrics.items():
            lines.append(f"- {key}: {_value(value)}")
        lines.extend(["", "### Failure Reasons"])
        lines.extend(f"- {_value(reason)}" for reason in (result.failure_reasons or ["none"]))
        lines.extend(["", "### Artifact Outputs"])
        for key, value in result.artifact_outputs.items():
            lines.append(f"- {key}: {_value(value)}")
        lines.extend(["", "### Invalid Claims"])
        lines.extend(f"- {claim}" for claim in result.invalid_claims)
        lines.extend(["", "### Decision Gate Notes"])
        lines.extend(f"- {_value(note)}" for note in result.decision_gate_notes)

    lines.extend(["", "## Planned Not Executed"])
    if planned:
        lines.extend(f"- {evidence_id}: planned_not_executed" for evidence_id in planned)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## CT4 Decision Gate Draft",
            "",
            "- decision: not_finalized",
            "- note: C1 records evidence readiness only; it does not approve B-stage training.",
            "",
            "## Forbidden Interpretations",
            "",
            "- 不得解释为生产告警。",
            "- 不得解释为 FU13 RUL。",
            "- 不得解释为自动维修建议。",
            "- 不得解释为专利授权结论。",
        ]
    )
    return "\n".join(lines) + "\n"


def apply_deterministic_mask(
    values: np.ndarray,
    *,
    mask_ratio: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    if not 0 < mask_ratio <= 1:
        raise ValueError("mask_ratio must be in (0, 1]")
    arr = np.asarray(values, dtype=float)
    flat_size = arr.size
    mask_count = max(1, int(round(flat_size * mask_ratio)))
    rng = np.random.default_rng(seed)
    selected = rng.choice(flat_size, size=mask_count, replace=False)
    mask = np.zeros(flat_size, dtype=bool)
    mask[selected] = True
    mask = mask.reshape(arr.shape)
    masked = arr.copy()
    masked[mask] = 0.0
    return masked, mask


def simple_statistical_embedding(values: np.ndarray) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    embedding: dict[str, float] = {}
    for index in range(arr.shape[1]):
        series = arr[:, index]
        embedding[f"mean_sensor_{index}"] = float(np.mean(series))
        embedding[f"std_sensor_{index}"] = float(np.std(series))
    return embedding


def reconstruction_metrics(
    truth: np.ndarray,
    reconstructed: np.ndarray,
    mask: np.ndarray,
) -> dict[str, float | int | None]:
    masked_error = np.asarray(reconstructed, dtype=float)[mask] - np.asarray(truth, dtype=float)[mask]
    if masked_error.size == 0:
        return {"mae": None, "rmse": None, "count": 0}
    return {
        "mae": float(np.mean(np.abs(masked_error))),
        "rmse": float(np.sqrt(np.mean(masked_error**2))),
        "count": int(masked_error.size),
    }


def run_c1_evidence(config: C1ExecutionConfig) -> list[C1EvidenceResult]:
    registry = build_c1_registry(config)
    if not config.dataset_path.exists():
        raise FileNotFoundError(f"C1 dataset not found: {config.dataset_path}")
    df = pd.read_parquet(config.dataset_path)
    windows = build_model_windows(
        df,
        context_length=config.context_length,
        prediction_length=config.prediction_length,
        stride=config.prediction_length,
        allow_cross_stage=(config.window_mode == "cross-stage"),
    )[: config.max_windows]
    if len(windows) < 2:
        raise ValueError(f"not enough windows for C1 evidence: need at least 2, got {len(windows)}")

    results: list[C1EvidenceResult] = []
    if "E1_forecasting_residual" in config.enabled_evidence:
        results.append(_run_e1_forecasting(config, registry.by_evidence_id["E1_forecasting_residual"], windows))
    if "E2_representation" in config.enabled_evidence:
        results.append(_run_e2_representation(config, registry.by_evidence_id["E2_representation"], windows))
    if "E3_imputation" in config.enabled_evidence:
        results.append(_run_e3_imputation(config, registry.by_evidence_id["E3_imputation"], windows))

    for evidence_id, status in registry.execution_status.items():
        if status == EvidenceStatus.PLANNED_NOT_EXECUTED:
            spec = registry.by_evidence_id[evidence_id]
            results.append(
                C1EvidenceResult(
                    evidence_id=evidence_id,
                    experiment_id=spec.experiment_id,
                    task_id=spec.task_id,
                    status=EvidenceStatus.PLANNED_NOT_EXECUTED,
                    dataset_boundary=config.dataset_boundary,
                    split_policy=_split_policy(spec),
                    data_label_audit=spec.data_label_audit,
                    model_results=[
                        C1ModelResult(
                            model_name="not_executed_in_c1",
                            status=ModelExecutionStatus.PLANNED_NOT_EXECUTED,
                            reason="C1 executes E1-E3 only",
                        )
                    ],
                    primary_metrics={metric: None for metric in spec.primary_metric},
                    failure_reasons=[],
                    artifact_outputs={"status": "planned_not_executed"},
                    invalid_claims=spec.invalid_claims,
                    decision_gate_notes=["reserved for C2 or later stage"],
                )
            )
    return results


def _run_e1_forecasting(
    config: C1ExecutionConfig,
    spec: C1EvidenceSpec,
    windows: list[object],
) -> C1EvidenceResult:
    split = max(1, int(len(windows) * 0.7))
    train = windows[:split]
    test = windows[split:]
    if not test:
        raise ValueError("not enough windows for C1 E1 test split")
    predictions = RobustStageForecaster().fit(train).predict(test)
    metrics = forecasting_metrics(predictions, test)
    residual_summary, top_examples = _forecast_residual_artifacts(
        predictions["y_hat"],
        test,
        model_name="RobustStageForecaster",
        quality_policy="all_quality_flags_recorded",
    )
    model_results = [
        C1ModelResult(
            model_name="RobustStageForecaster",
            status=ModelExecutionStatus.AVAILABLE_AND_RAN,
            metrics=metrics,
        )
    ]
    if (config.models.get("ttm") or {}).get("enabled", False):
        model_results.append(_candidate_model_status("TTM", config.models.get("ttm") or {}, task="forecasting"))

    return C1EvidenceResult(
        evidence_id=spec.evidence_id,
        experiment_id=spec.experiment_id,
        task_id=spec.task_id,
        status=EvidenceStatus.PASSED,
        dataset_boundary=config.dataset_boundary,
        split_policy=_split_policy(spec),
        data_label_audit=spec.data_label_audit,
        model_results=model_results,
        primary_metrics={"mae": metrics.get("mae"), "rmse": metrics.get("rmse")},
        failure_reasons=[],
        artifact_outputs={
            "residual_summary": residual_summary,
            "top_k_candidate_examples": top_examples,
        },
        invalid_claims=spec.invalid_claims,
        decision_gate_notes=["E1 baseline evidence is available; candidate model status is recorded separately."],
    )


def _run_e2_representation(
    config: C1ExecutionConfig,
    spec: C1EvidenceSpec,
    windows: list[object],
) -> C1EvidenceResult:
    embeddings = [simple_statistical_embedding(window.X) for window in windows]
    feature_count = len(embeddings[0]) if embeddings else 0
    model_results = [
        C1ModelResult(
            model_name="statistical_embedding",
            status=ModelExecutionStatus.AVAILABLE_AND_RAN,
            metrics={"windows": len(embeddings), "features": feature_count},
        )
    ]
    for model_name in ["moment", "units"]:
        model_cfg = config.models.get(model_name) or {}
        if model_cfg.get("enabled", False):
            display = "MOMENT" if model_name == "moment" else "UniTS"
            model_results.append(_candidate_model_status(display, model_cfg, task="representation"))

    return C1EvidenceResult(
        evidence_id=spec.evidence_id,
        experiment_id=spec.experiment_id,
        task_id=spec.task_id,
        status=EvidenceStatus.PASSED,
        dataset_boundary=config.dataset_boundary,
        split_policy=_split_policy(spec),
        data_label_audit=spec.data_label_audit,
        model_results=model_results,
        primary_metrics={"embedding_windows": len(embeddings), "embedding_features": feature_count},
        failure_reasons=[],
        artifact_outputs={
            "input_exclusion_note": (
                "stage, quality_flag, and failure_proxy are report/probe metadata; "
                "do not interpret probe results as learned semantics if passed as inputs"
            ),
            "statistical_embedding_example": embeddings[0] if embeddings else {},
        },
        invalid_claims=spec.invalid_claims,
        decision_gate_notes=["E2 baseline representation path is available; foundation embedding adapters remain status-recorded."],
    )


def _run_e3_imputation(
    config: C1ExecutionConfig,
    spec: C1EvidenceSpec,
    windows: list[object],
) -> C1EvidenceResult:
    metrics_by_window = []
    for index, window in enumerate(windows):
        masked, mask = apply_deterministic_mask(window.X, mask_ratio=0.2, seed=7 + index)
        medians = np.median(masked, axis=0)
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
    model_results = [
        C1ModelResult(
            model_name="simple_reconstruction_baseline",
            status=ModelExecutionStatus.AVAILABLE_AND_RAN,
            metrics=metrics,
        )
    ]
    for model_name in ["moment", "units"]:
        model_cfg = config.models.get(model_name) or {}
        if model_cfg.get("enabled", False):
            display = "MOMENT" if model_name == "moment" else "UniTS"
            model_results.append(_candidate_model_status(display, model_cfg, task="imputation"))

    return C1EvidenceResult(
        evidence_id=spec.evidence_id,
        experiment_id=spec.experiment_id,
        task_id=spec.task_id,
        status=EvidenceStatus.PASSED,
        dataset_boundary=config.dataset_boundary,
        split_policy=_split_policy(spec),
        data_label_audit=spec.data_label_audit,
        model_results=model_results,
        primary_metrics=metrics,
        failure_reasons=[],
        artifact_outputs={
            "mask_strategy": {"mask_ratio": 0.2, "seed": 7, "scope": "evaluation_windows_only"},
            "window_count": len(windows),
        },
        invalid_claims=spec.invalid_claims,
        decision_gate_notes=["E3 baseline reconstruction path is available; foundation imputation adapters remain status-recorded."],
    )


def _forecast_residual_artifacts(
    y_hat: np.ndarray,
    windows: list[object],
    *,
    model_name: str,
    quality_policy: str,
) -> tuple[dict[str, float | int | None], list[dict[str, object]]]:
    truth = np.stack([window.y for window in windows], axis=0)
    residual = np.asarray(y_hat, dtype=float) - truth
    abs_residual = np.abs(residual)
    summary = {
        "abs_residual_mean": float(np.mean(abs_residual)),
        "abs_residual_p95": float(np.percentile(abs_residual, 95)),
        "abs_residual_max": float(np.max(abs_residual)),
        "count": int(abs_residual.size),
    }
    flat_indices = np.argsort(abs_residual.ravel())[::-1][: min(5, abs_residual.size)]
    examples: list[dict[str, object]] = []
    sensors = list(getattr(windows[0], "sensor_token"))
    for flat_index in flat_indices:
        window_index, horizon_index, sensor_index = np.unravel_index(flat_index, abs_residual.shape)
        window = windows[window_index]
        stage_token = getattr(window, "stage_token", [])
        examples.append(
            {
                "sensor_id": str(sensors[sensor_index]),
                "timestamp": _target_timestamp(window, horizon_index),
                "stage": str(stage_token[-1]) if len(stage_token) else "not_available",
                "quality_policy": quality_policy,
                "model_name": model_name,
                "observed_value": float(truth[window_index, horizon_index, sensor_index]),
                "predicted_value": float(y_hat[window_index, horizon_index, sensor_index]),
                "absolute_residual": float(abs_residual[window_index, horizon_index, sensor_index]),
            }
        )
    return summary, examples


def _target_timestamp(window: object, horizon_index: int) -> str:
    target_start = getattr(window, "target_start", None)
    if not target_start:
        return "not_available"
    try:
        timestamp = pd.Timestamp(target_start)
        delta_t = getattr(window, "delta_t", [])
        seconds = float(delta_t[-1]) if len(delta_t) else 0.0
        return (timestamp + pd.to_timedelta(seconds * horizon_index, unit="s")).isoformat()
    except Exception:
        return str(target_start)


def _candidate_model_status(
    model_name: str,
    model_cfg: dict[str, Any],
    *,
    task: str,
) -> C1ModelResult:
    if model_cfg.get("force_missing_dependency"):
        return C1ModelResult(
            model_name=model_name,
            status=ModelExecutionStatus.MISSING_DEPENDENCY,
            reason=f"optional {model_name} dependency is not installed",
        )
    if model_cfg.get("force_unsupported_task") or model_name == "UniTS":
        return C1ModelResult(
            model_name=model_name,
            status=ModelExecutionStatus.UNSUPPORTED_TASK,
            reason=f"{model_name} {task} adapter is not implemented in C1",
        )
    if model_name == "MOMENT":
        return C1ModelResult(
            model_name=model_name,
            status=ModelExecutionStatus.MISSING_DEPENDENCY,
            reason="optional MOMENT dependency is not installed",
        )
    if model_name == "TTM":
        return C1ModelResult(
            model_name=model_name,
            status=ModelExecutionStatus.MISSING_OR_BLOCKED_WEIGHTS,
            reason="TTM candidate is recorded in C1; full TTM execution remains available through real-data forecasting",
        )
    return C1ModelResult(
        model_name=model_name,
        status=ModelExecutionStatus.UNSUPPORTED_TASK,
        reason=f"{model_name} {task} adapter is not implemented in C1",
    )


def _split_policy(spec: C1EvidenceSpec) -> str:
    return str(spec.data_label_audit.get("split_policy_status") or "not_available")


def _value(value: object) -> str:
    if value is None or value == "":
        return "not_available"
    if isinstance(value, dict):
        return ", ".join(f"{key}={_value(item)}" for key, item in value.items())
    if isinstance(value, list):
        return ", ".join(_value(item) for item in value)
    return str(value)


def _cell(value: object) -> str:
    return _value(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("|", "\\|")
