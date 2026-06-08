from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21ModelTaskAttempt,
    C21TaskId,
    REQUIRED_C21_TASKS,
)


class C22ConfigError(ValueError):
    """Raised when the C2.2 executable upgrade config cannot be used."""


class C22ModelRole(StrEnum):
    ANCHOR = "anchor"
    PRIORITY_REAL_EXECUTION = "priority_real_execution"
    CORE_RUN_REVIEW = "core_run_review"
    CORE_INTERFACE = "core_interface"


REQUIRED_C22_MODEL_TARGET_IDS = (
    "ttm",
    "chronos",
    "timesfm",
    "moirai_uni2ts",
    "moment",
    "units",
)

REQUIRED_C22_WATCHLIST_TARGET_IDS = (
    "time_moe",
    "sundial",
    "timer_s1_timer_xl",
    "kairos",
    "toto",
    "ibm_flowstate_tspulse",
    "tabpfn_ts",
)


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


@dataclass(frozen=True)
class C22FrontierWatchlistAudit:
    model_or_route: str
    latest_known_version_or_paper: str
    primary_tasks: tuple[str, ...]
    repository_or_model_card: str
    package_availability: str
    weight_availability: str
    license_status: str
    resource_requirement: str
    input_output_fit: str
    fu13_task_fit: str
    status: str
    default_c22_action: str
    promotion_condition: str


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
    timeout_seconds_per_model: int
    cache_dir: Path
    reuse_existing_cache: bool
    write_cache_manifest: bool
    model_targets: dict[str, C22ModelTarget]
    frontier_watchlist: C22WatchlistConfig
    report_path: Path
    cache_manifest_path: Path


@dataclass
class C22TargetResult:
    model_id: str
    role: C22ModelRole
    target: str
    fallback: str | None
    task_id: C21TaskId
    status: Any
    metrics: dict[str, Any] = field(default_factory=dict)
    baseline_metrics: dict[str, Any] = field(default_factory=dict)
    failure_stage: str = ""
    failure_reason: str = ""
    dependency_status: str = ""
    weight_status: str = ""
    adapter_name: str = ""
    model_ref: str | None = None
    runtime_seconds: float | None = None
    target_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class C22RunResult:
    run_id: str
    config_path: str | Path
    upstream_c21_config: str | Path
    dataset_boundary: str
    config_allows_network: bool
    config_allows_download: bool
    cache_dir: str | Path
    tested_windows: int
    target_results: list[C22TargetResult]
    watchlist_audit: list[C22FrontierWatchlistAudit]
    invalid_claims: list[str]
    c3_handoff_notes: list[str] = field(
        default_factory=lambda: [
            "C2.2 promotes only models with executable evidence or clear promotion conditions to C3.",
            "Watchlist audit entries require re-check before cross-dataset validation.",
        ]
    )
    b_decision_notes: list[str] = field(
        default_factory=lambda: [
            "C2.2 is not a B-stage self-training Go decision.",
            "Model failures must be interpreted as dependency, weight, interface, task, or resource evidence before capability claims.",
        ]
    )


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
        timeout_seconds_per_model=_load_positive_int(
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


def build_frontier_watchlist_audit(
    config: C22ExecutionConfig,
) -> list[C22FrontierWatchlistAudit]:
    return [
        _WATCHLIST_AUDIT_BY_ID.get(target_id, _unknown_watchlist_audit(target_id))
        for target_id in config.frontier_watchlist.targets
    ]


def render_c22_report(result: C22RunResult, config: C22ExecutionConfig) -> str:
    lines = [
        "# C2.2 Open Model Executable Evaluation Upgrade Report",
        "",
        "## Report Metadata",
        "",
        f"- run_id: {_value(result.run_id)}",
        f"- config_path: {_value(result.config_path)}",
        f"- upstream_c21_config: {_value(result.upstream_c21_config)}",
        f"- dataset_boundary: {_value(result.dataset_boundary)}",
        f"- tested_windows: {_value(result.tested_windows)}",
        f"- config_allows_network: {_value(result.config_allows_network)}",
        f"- config_allows_download: {_value(result.config_allows_download)}",
        f"- cache_dir: {_value(result.cache_dir)}",
        "",
        "## Executive Summary",
        "",
        f"- core_model_task_results: {len(result.target_results)}",
        f"- frontier_watchlist_entries: {len(result.watchlist_audit)}",
        "- scope: C2.2 versioned open model target audit, executable-result reporting, and cache boundary recording.",
        (
            "- boundary: watchlist entries are audit-only; network and download remain governed "
            "by config and no C2.2 report claim implies production alert, RUL, maintenance, or C3/B Go status."
        ),
        "",
        "## Versioned Model Target Matrix",
        "",
        "| model_id | display_name | role | target | fallback | tasks |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for model_id, target in config.model_targets.items():
        lines.append(
            (
                f"| {_cell(model_id)} | {_cell(_display_name(model_id, target.target))} | "
                f"{_cell(target.role)} | {_cell(target.target)} | {_cell(target.fallback)} | "
                f"{_cell(target.tasks)} |"
            )
        )

    lines.extend(
        [
            "",
            "## Priority Real Execution Results",
            "",
            (
                "| model_id | display_name | task_id | target | status | metrics | baseline_metrics | "
                "failure_stage | failure_reason | runtime_seconds |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    priority_results = [
        item
        for item in result.target_results
        if item.role == C22ModelRole.PRIORITY_REAL_EXECUTION
    ]
    if priority_results:
        for item in priority_results:
            lines.append(_target_result_row(item))
    else:
        lines.append("| none | none | none | none | none | none | none | none | none | none |")

    lines.extend(
        [
            "",
            "## Core Model-Task Result Matrix",
            "",
            (
                "| model_id | display_name | task_id | target | status | metrics | baseline_metrics | "
                "failure_stage | failure_reason | runtime_seconds |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if result.target_results:
        for item in result.target_results:
            lines.append(_target_result_row(item))
    else:
        lines.append("| none | none | none | none | none | none | none | none | none | none |")

    lines.extend(
        [
            "",
            "## Frontier Watchlist Audit",
            "",
            (
                "| model_or_route | latest_known_version_or_paper | primary_tasks | "
                "repository_or_model_card | package_availability | weight_availability | "
                "license_status | resource_requirement | input_output_fit | fu13_task_fit | "
                "status | default_c22_action | promotion_condition |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if result.watchlist_audit:
        for item in result.watchlist_audit:
            lines.append(
                (
                    f"| {_cell(item.model_or_route)} | {_cell(item.latest_known_version_or_paper)} | "
                    f"{_cell(item.primary_tasks)} | {_cell(item.repository_or_model_card)} | "
                    f"{_cell(item.package_availability)} | {_cell(item.weight_availability)} | "
                    f"{_cell(item.license_status)} | {_cell(item.resource_requirement)} | "
                    f"{_cell(item.input_output_fit)} | {_cell(item.fu13_task_fit)} | "
                    f"{_cell(item.status)} | {_cell(item.default_c22_action)} | "
                    f"{_cell(item.promotion_condition)} |"
                )
            )
    else:
        lines.append("| none | none | none | none | none | none | none | none | none | none | none | none | none |")

    lines.extend(
        [
            "",
            "## Failure Taxonomy",
            "",
            "| model_id | task_id | status | failure_stage | failure_reason | dependency_status | weight_status |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    failure_results = [item for item in result.target_results if item.failure_reason]
    if failure_results:
        for item in failure_results:
            lines.append(
                (
                    f"| {_cell(item.model_id)} | {_cell(item.task_id)} | {_cell(item.status)} | "
                    f"{_cell(item.failure_stage)} | {_cell(item.failure_reason)} | "
                    f"{_cell(item.dependency_status)} | {_cell(item.weight_status)} |"
                )
            )
    else:
        lines.append("| none | none | none | none | none | none | none |")

    lines.extend(["", "## Cache / Download Manifest", ""])
    lines.extend(render_c22_cache_manifest(result).rstrip().splitlines())
    lines.extend(["", "## C2.2 -> C3 Handoff", ""])
    lines.extend(f"- {_value(note)}" for note in (result.c3_handoff_notes or ["none"]))
    lines.extend(["", "## C2.2 -> B Decision Notes", ""])
    lines.extend(f"- {_value(note)}" for note in (result.b_decision_notes or ["none"]))
    lines.extend(["", "## Invalid Claims", ""])
    lines.extend(f"- {_value(claim)}" for claim in (result.invalid_claims or ["none"]))
    return "\n".join(lines) + "\n"


def render_c22_cache_manifest(result: C22RunResult) -> str:
    lines = [
        "| key | value |",
        "| --- | --- |",
        f"| run_id | {_cell(result.run_id)} |",
        f"| cache_dir | {_cell(result.cache_dir)} |",
        f"| network_allowed | {_cell(result.config_allows_network)} |",
        f"| download_allowed | {_cell(result.config_allows_download)} |",
        f"| dataset_boundary | {_cell(result.dataset_boundary)} |",
        f"| watchlist_boundary | {_cell('audit_only_no_model_download')} |",
        "",
        "| model_id | task_id | target | fallback | adapter_name | cache_dir | weight_status | model_ref |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    if result.target_results:
        for item in result.target_results:
            lines.append(
                (
                    f"| {_cell(item.model_id)} | {_cell(item.task_id)} | {_cell(item.target)} | "
                    f"{_cell(item.fallback)} | {_cell(item.adapter_name)} | {_cell(result.cache_dir)} | "
                    f"{_cell(item.weight_status)} | {_cell(item.model_ref)} |"
                )
            )
    else:
        lines.append("| none | none | none | none | none | none | none | none |")
    return "\n".join(lines) + "\n"


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


def _load_mask_ratio(raw: dict[str, Any], key: str) -> float:
    value = raw.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise C22ConfigError(f"{key} must be a number in (0, 1]")
    ratio = float(value)
    if not 0 < ratio <= 1:
        raise C22ConfigError(f"{key} must be in (0, 1]")
    return ratio


def _load_model_targets(raw: dict[str, Any]) -> dict[str, C22ModelTarget]:
    _require_exact_ids(
        tuple(raw),
        REQUIRED_C22_MODEL_TARGET_IDS,
        "model_targets",
    )

    targets: dict[str, C22ModelTarget] = {}
    for model_id, value in raw.items():
        if not isinstance(model_id, str) or not model_id:
            raise C22ConfigError("model target ids must be non-empty strings")
        if not isinstance(value, dict):
            raise C22ConfigError(f"model_targets.{model_id} must be a mapping")
        task_ids = _load_task_ids(value, model_id)
        if task_ids != REQUIRED_C21_TASKS[model_id]:
            raise C22ConfigError(
                f"model_targets.{model_id}.tasks must match C2.1 required tasks"
            )
        targets[model_id] = C22ModelTarget(
            model_id=model_id,
            role=_load_model_role(value, model_id),
            target=_load_required_string(value, "target"),
            fallback=_load_optional_string(value, "fallback"),
            tasks=task_ids,
        )
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
    audit_only = _load_bool(raw, "audit_only")
    promote_to_real_execution = _load_bool(raw, "promote_to_real_execution")
    if not audit_only:
        raise C22ConfigError("frontier_watchlist.audit_only must be true")
    if promote_to_real_execution:
        raise C22ConfigError("frontier_watchlist.promote_to_real_execution must be false")

    targets = raw.get("targets")
    if not isinstance(targets, list):
        raise C22ConfigError("frontier_watchlist.targets must be a list")
    if not all(isinstance(target, str) and target for target in targets):
        raise C22ConfigError("frontier_watchlist.targets must contain non-empty strings")
    _require_exact_ids(
        tuple(targets),
        REQUIRED_C22_WATCHLIST_TARGET_IDS,
        "frontier_watchlist.targets",
    )

    return C22WatchlistConfig(
        audit_only=audit_only,
        promote_to_real_execution=promote_to_real_execution,
        targets=tuple(targets),
    )


def _require_exact_ids(
    actual_ids: tuple[str, ...],
    required_ids: tuple[str, ...],
    label: str,
) -> None:
    actual_set = set(actual_ids)
    required_set = set(required_ids)
    has_duplicates = len(actual_ids) != len(actual_set)
    if actual_set != required_set or has_duplicates:
        raise C22ConfigError(
            f"{label} must contain exactly: {', '.join(required_ids)}"
        )


def _target_result_row(item: C22TargetResult) -> str:
    return (
        f"| {_cell(item.model_id)} | {_cell(_display_name(item.model_id, item.target))} | "
        f"{_cell(item.task_id)} | {_cell(item.target)} | {_cell(item.status)} | "
        f"{_cell(item.metrics)} | {_cell(item.baseline_metrics)} | "
        f"{_cell(item.failure_stage)} | {_cell(item.failure_reason)} | "
        f"{_cell(item.runtime_seconds)} |"
    )


def _display_name(model_id: str, target: str) -> str:
    names = {
        "ttm": "TTM",
        "chronos": "Chronos-2",
        "timesfm": "TimesFM 2.5",
        "moirai_uni2ts": "Moirai 2.0 / Uni2TS",
        "moment": "MOMENT",
        "units": "UniTS",
    }
    return names.get(model_id, target)


def _unknown_watchlist_audit(model_or_route: str) -> C22FrontierWatchlistAudit:
    return C22FrontierWatchlistAudit(
        model_or_route=model_or_route,
        latest_known_version_or_paper="unknown",
        primary_tasks=("needs_research_review",),
        repository_or_model_card="unknown",
        package_availability="unknown",
        weight_availability="unknown",
        license_status="unknown",
        resource_requirement="unknown",
        input_output_fit="unknown",
        fu13_task_fit="unknown",
        status="needs_research_review",
        default_c22_action="watchlist_audit_only",
        promotion_condition="research metadata must be verified before any C2.2 promotion",
    )


def _watchlist_audit(
    model_or_route: str,
    latest_known_version_or_paper: str,
    primary_tasks: tuple[str, ...],
    repository_or_model_card: str,
    package_availability: str,
    weight_availability: str,
    license_status: str,
    resource_requirement: str,
    input_output_fit: str,
    fu13_task_fit: str,
    promotion_condition: str,
) -> C22FrontierWatchlistAudit:
    return C22FrontierWatchlistAudit(
        model_or_route=model_or_route,
        latest_known_version_or_paper=latest_known_version_or_paper,
        primary_tasks=primary_tasks,
        repository_or_model_card=repository_or_model_card,
        package_availability=package_availability,
        weight_availability=weight_availability,
        license_status=license_status,
        resource_requirement=resource_requirement,
        input_output_fit=input_output_fit,
        fu13_task_fit=fu13_task_fit,
        status="audit_only",
        default_c22_action="watchlist_audit_only",
        promotion_condition=promotion_condition,
    )


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
    return (
        _value(value)
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("|", "\\|")
    )


_WATCHLIST_AUDIT_BY_ID = {
    "time_moe": _watchlist_audit(
        model_or_route="time_moe",
        latest_known_version_or_paper="Time-MoE",
        primary_tasks=("forecasting",),
        repository_or_model_card="research repository/model card review pending",
        package_availability="not required for C2.2",
        weight_availability="not downloaded",
        license_status="needs review",
        resource_requirement="likely GPU or large cache",
        input_output_fit="forecasting interface review needed",
        fu13_task_fit="possible forecasting fit",
        promotion_condition="stable package, license, cache, and FU13 forecasting adapter verified",
    ),
    "sundial": _watchlist_audit(
        model_or_route="sundial",
        latest_known_version_or_paper="Sundial",
        primary_tasks=("forecasting",),
        repository_or_model_card="research repository/model card review pending",
        package_availability="not required for C2.2",
        weight_availability="not downloaded",
        license_status="needs review",
        resource_requirement="needs resource sizing",
        input_output_fit="forecasting horizon review needed",
        fu13_task_fit="possible forecasting fit",
        promotion_condition="official package, weights, license, and deterministic offline cache path verified",
    ),
    "timer_s1_timer_xl": _watchlist_audit(
        model_or_route="timer_s1_timer_xl",
        latest_known_version_or_paper="Timer-S1 / Timer-XL",
        primary_tasks=("forecasting",),
        repository_or_model_card="research repository/model card review pending",
        package_availability="not required for C2.2",
        weight_availability="not downloaded",
        license_status="needs review",
        resource_requirement="likely high memory for XL",
        input_output_fit="context and horizon review needed",
        fu13_task_fit="possible forecasting fit",
        promotion_condition="small enough target, offline cache, and adapter input/output contract verified",
    ),
    "kairos": _watchlist_audit(
        model_or_route="kairos",
        latest_known_version_or_paper="Kairos",
        primary_tasks=("forecasting", "representation"),
        repository_or_model_card="research repository/model card review pending",
        package_availability="not required for C2.2",
        weight_availability="not downloaded",
        license_status="needs review",
        resource_requirement="needs resource sizing",
        input_output_fit="task interface review needed",
        fu13_task_fit="possible forecasting or representation fit",
        promotion_condition="task contract, package availability, license, and cache behavior verified",
    ),
    "toto": _watchlist_audit(
        model_or_route="toto",
        latest_known_version_or_paper="Toto",
        primary_tasks=("forecasting",),
        repository_or_model_card="research repository/model card review pending",
        package_availability="not required for C2.2",
        weight_availability="not downloaded",
        license_status="needs review",
        resource_requirement="needs resource sizing",
        input_output_fit="forecasting API review needed",
        fu13_task_fit="possible forecasting fit",
        promotion_condition="official implementation, license, local weights, and FU13 adapter path verified",
    ),
    "ibm_flowstate_tspulse": _watchlist_audit(
        model_or_route="ibm_flowstate_tspulse",
        latest_known_version_or_paper="IBM FlowState / TSPulse",
        primary_tasks=("forecasting", "foundation_model"),
        repository_or_model_card="IBM route review pending",
        package_availability="not required for C2.2",
        weight_availability="not downloaded",
        license_status="needs review",
        resource_requirement="needs resource sizing",
        input_output_fit="API and task boundary review needed",
        fu13_task_fit="possible forecasting fit",
        promotion_condition="public package/model card, license, and offline cache boundary verified",
    ),
    "tabpfn_ts": _watchlist_audit(
        model_or_route="tabpfn_ts",
        latest_known_version_or_paper="TabPFN-TS",
        primary_tasks=("forecasting", "tabular_time_series"),
        repository_or_model_card="research repository/model card review pending",
        package_availability="not required for C2.2",
        weight_availability="not downloaded",
        license_status="needs review",
        resource_requirement="needs resource sizing",
        input_output_fit="tabular/time-series route review needed",
        fu13_task_fit="possible forecasting fit",
        promotion_condition="time-series API, license, cache path, and FU13 feature mapping verified",
    ),
}
