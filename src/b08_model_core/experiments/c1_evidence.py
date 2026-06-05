from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from b08_model_core.experiments.c_stage_contract import (
    load_and_validate_c_stage_contract,
)


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
