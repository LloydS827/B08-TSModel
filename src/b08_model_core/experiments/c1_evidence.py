from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

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
