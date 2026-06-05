from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


CORE_MODEL_IDS = ("ttm", "moment", "chronos", "timesfm", "moirai_uni2ts", "units")


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
class C2ModelRegistry:
    by_model_id: dict[str, C2ModelSpec]
    attempts: list[C2ModelTaskAttempt]


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

    return C2ExecutionConfig(
        stage=str(raw.get("stage", "")),
        upstream_c1_config=Path(raw.get("upstream_c1_config", "")),
        dataset_path=Path(dataset.get("fu13_observations", "")),
        fu13_config_path=Path(dataset.get("fu13_config", "")),
        dataset_boundary=str(dataset.get("boundary", "")),
        window_mode=str(window.get("window_mode", "cross-stage")),
        context_length=int(window.get("context_length", 90)),
        prediction_length=int(window.get("prediction_length", 16)),
        max_windows=int(window.get("max_windows", 40)),
        mask_ratio=float(window.get("mask_ratio", 0.2)),
        seed=int(window.get("seed", 7)),
        core_models=[_load_model_spec(item) for item in core_models],
        task_policy=_load_task_policy(task_policy),
        allow_download=_load_bool(cache_policy, "allow_download", False),
        model_cache_dir=cache_policy.get("cache_dir"),
        strict_model_success=_load_bool(execution_policy, "strict_model_success", False),
        no_network_by_default=_load_bool(execution_policy, "no_network_by_default", True),
        record_failure=_load_bool(execution_policy, "record_failure", True),
        do_not_over_claim=_load_bool(execution_policy, "do_not_over_claim", True),
        report_path=Path(outputs.get("report", "reports/c_stage_c2_open_model_evaluation.md")),
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
    covered_model_ids: set[str] = set()
    for task_id, model_ids in config.task_policy.items():
        for model_id in model_ids:
            if model_id not in by_model_id:
                raise C2OpenModelConfigError(f"task policy references unknown core model: {model_id}")
            attempts.append(C2ModelTaskAttempt(model_id=model_id, task_id=task_id))
            covered_model_ids.add(model_id)

    for model in config.core_models:
        if not model.primary_tasks:
            raise C2OpenModelConfigError(f"{model.model_id} must declare at least one primary task")
        if model.model_id not in covered_model_ids:
            attempts.extend(C2ModelTaskAttempt(model_id=model.model_id, task_id=task_id) for task_id in model.primary_tasks)

    return C2ModelRegistry(by_model_id=by_model_id, attempts=attempts)


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
