from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from pathlib import Path
from typing import Any

import yaml

from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21ModelTaskAttempt,
    C21TaskId,
)


class C22ConfigError(ValueError):
    """Raised when the C2.2 executable upgrade config cannot be used."""


class C22ModelRole(StrEnum):
    ANCHOR = "anchor"
    PRIORITY_REAL_EXECUTION = "priority_real_execution"
    CORE_RUN_REVIEW = "core_run_review"
    CORE_INTERFACE = "core_interface"


@dataclass(frozen=True)
class C22ModelTarget:
    model_id: str
    role: C22ModelRole
    target: str
    tasks: tuple[C21TaskId, ...]
    fallback: str | None = None


@dataclass(frozen=True)
class C22WatchlistConfig:
    audit_only: bool
    promote_to_real_execution: bool
    targets: tuple[str, ...]


@dataclass
class C22ExecutionConfig:
    stage: str
    upstream_c21_config: Path
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
    model_targets: dict[str, C22ModelTarget]
    frontier_watchlist: C22WatchlistConfig
    report_path: Path
    cache_manifest_path: Path


def load_c22_config(path: str | Path) -> C22ExecutionConfig:
    raw = _load_mapping(Path(path))
    dataset = _load_mapping(raw, "dataset")
    window = _load_mapping(raw, "window")
    execution_policy = _load_mapping(raw, "execution_policy")
    model_cache_policy = _load_mapping(raw, "model_cache_policy")
    outputs = _load_mapping(raw, "outputs")

    stage = _load_required_string(raw, "stage")
    if stage != "C2_2_open_model_executable_upgrade":
        raise C22ConfigError("C2.2 stage must be C2_2_open_model_executable_upgrade")

    allow_network = _load_bool(execution_policy, "allow_network")
    allow_download = _load_bool(execution_policy, "allow_download")
    record_failure = _load_bool(execution_policy, "record_failure")
    continue_on_model_failure = _load_bool(execution_policy, "continue_on_model_failure")
    reuse_existing_cache = _load_bool(model_cache_policy, "reuse_existing_cache")
    if allow_download and not allow_network:
        raise C22ConfigError("allow_download requires allow_network=true")
    if not record_failure:
        raise C22ConfigError("record_failure=false is not supported")
    if not continue_on_model_failure:
        raise C22ConfigError("continue_on_model_failure=false is not supported")
    if not reuse_existing_cache:
        raise C22ConfigError("reuse_existing_cache=false is not supported")

    return C22ExecutionConfig(
        stage=stage,
        upstream_c21_config=Path(_load_required_string(raw, "upstream_c21_config")),
        dataset_path=Path(_load_required_string(dataset, "fu13_observations")),
        fu13_config_path=Path(_load_required_string(dataset, "fu13_config")),
        dataset_boundary=_load_required_string(dataset, "boundary"),
        window_mode=_load_window_mode(window),
        context_length=_load_positive_int(window, "context_length"),
        prediction_length=_load_positive_int(window, "prediction_length"),
        max_windows=_load_positive_int(window, "max_windows"),
        mask_ratio=_load_mask_ratio(window, "mask_ratio"),
        seed=_load_nonnegative_int(window, "seed"),
        allow_network=allow_network,
        allow_download=allow_download,
        strict_model_success=_load_bool(execution_policy, "strict_model_success"),
        record_failure=record_failure,
        do_not_over_claim=_load_bool(execution_policy, "do_not_over_claim"),
        continue_on_model_failure=continue_on_model_failure,
        timeout_seconds_per_model=_load_positive_number(
            execution_policy,
            "timeout_seconds_per_model",
        ),
        cache_dir=Path(_load_required_string(model_cache_policy, "cache_dir")),
        reuse_existing_cache=reuse_existing_cache,
        write_cache_manifest=_load_bool(model_cache_policy, "write_cache_manifest"),
        model_targets=_load_model_targets(_load_mapping(raw, "model_targets")),
        frontier_watchlist=_load_watchlist(_load_mapping(raw, "frontier_watchlist")),
        report_path=Path(_load_required_string(outputs, "report")),
        cache_manifest_path=Path(_load_required_string(outputs, "cache_manifest")),
    )


def build_c22_core_attempts(config: C22ExecutionConfig) -> list[C21ModelTaskAttempt]:
    if config.stage != "C2_2_open_model_executable_upgrade":
        raise C22ConfigError("C2.2 attempts require a C2.2 executable upgrade config")

    return [
        C21ModelTaskAttempt(model_id=model_id, task_id=task_id)
        for model_id, target in config.model_targets.items()
        for task_id in target.tasks
    ]


def _load_mapping(raw: dict[str, Any] | Path, key: str | None = None) -> dict[str, Any]:
    if isinstance(raw, Path):
        loaded = yaml.safe_load(raw.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise C22ConfigError("C2.2 executable upgrade config must be a mapping")
        return loaded

    value = raw.get(key)
    if not isinstance(value, dict):
        raise C22ConfigError(f"{key} must be a mapping")
    return value


def _load_required_string(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise C22ConfigError(f"{key} must be a non-empty string")
    return value


def _load_optional_string(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise C22ConfigError(f"{key} must be a non-empty string")
    return value


def _load_bool(raw: dict[str, Any], key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise C22ConfigError(f"{key} must be a boolean")
    return value


def _load_window_mode(raw: dict[str, Any]) -> str:
    value = _load_required_string(raw, "window_mode")
    if value not in {"stage-local", "cross-stage"}:
        raise C22ConfigError("window_mode must be stage-local or cross-stage")
    return value


def _load_positive_int(raw: dict[str, Any], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise C22ConfigError(f"{key} must be a positive integer")
    return value


def _load_nonnegative_int(raw: dict[str, Any], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise C22ConfigError(f"{key} must be a nonnegative integer")
    return value


def _load_positive_number(raw: dict[str, Any], key: str) -> float:
    value = raw.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise C22ConfigError(f"{key} must be a positive number")
    number = float(value)
    if not math.isfinite(number):
        raise C22ConfigError(f"{key} must be finite")
    return number


def _load_mask_ratio(raw: dict[str, Any], key: str) -> float:
    value = raw.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise C22ConfigError(f"{key} must be a number in (0, 1]")
    ratio = float(value)
    if not 0 < ratio <= 1:
        raise C22ConfigError(f"{key} must be in (0, 1]")
    return ratio


def _load_model_targets(raw: dict[str, Any]) -> dict[str, C22ModelTarget]:
    targets: dict[str, C22ModelTarget] = {}
    for model_id, value in raw.items():
        if not isinstance(model_id, str) or not model_id:
            raise C22ConfigError("model target ids must be non-empty strings")
        if not isinstance(value, dict):
            raise C22ConfigError(f"model_targets.{model_id} must be a mapping")
        targets[model_id] = C22ModelTarget(
            model_id=model_id,
            role=_load_model_role(value, model_id),
            target=_load_required_string(value, "target"),
            fallback=_load_optional_string(value, "fallback"),
            tasks=_load_task_ids(value, model_id),
        )
    if not targets:
        raise C22ConfigError("model_targets must not be empty")
    return targets


def _load_model_role(raw: dict[str, Any], model_id: str) -> C22ModelRole:
    role = _load_required_string(raw, "role")
    try:
        return C22ModelRole(role)
    except ValueError as exc:
        raise C22ConfigError(f"model_targets.{model_id}.role is unknown: {role}") from exc


def _load_task_ids(raw: dict[str, Any], model_id: str) -> tuple[C21TaskId, ...]:
    values = raw.get("tasks")
    if not isinstance(values, list) or not values:
        raise C22ConfigError(f"model_targets.{model_id}.tasks must be a non-empty list")

    task_ids = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise C22ConfigError(f"model_targets.{model_id}.tasks must contain strings")
        try:
            task_ids.append(C21TaskId(value))
        except ValueError as exc:
            raise C22ConfigError(
                f"model_targets.{model_id}.tasks contains unknown task: {value}"
            ) from exc
    return tuple(task_ids)


def _load_watchlist(raw: dict[str, Any]) -> C22WatchlistConfig:
    targets = raw.get("targets")
    if not isinstance(targets, list):
        raise C22ConfigError("frontier_watchlist.targets must be a list")
    if not all(isinstance(target, str) and target for target in targets):
        raise C22ConfigError("frontier_watchlist.targets must contain non-empty strings")

    return C22WatchlistConfig(
        audit_only=_load_bool(raw, "audit_only"),
        promote_to_real_execution=_load_bool(raw, "promote_to_real_execution"),
        targets=tuple(targets),
    )
