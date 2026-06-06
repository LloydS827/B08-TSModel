from __future__ import annotations

from dataclasses import dataclass, field
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
        "- scope: executable open model adapter result schema and offline-safe report rendering.",
        "- boundary: no runner, CLI, concrete adapter, external cache, download, or model call is performed.",
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
