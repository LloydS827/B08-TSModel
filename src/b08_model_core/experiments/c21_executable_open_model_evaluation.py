from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from pathlib import Path
from typing import Any

import yaml


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
