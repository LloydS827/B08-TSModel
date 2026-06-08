from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21ExecutionConfig,
    C21ModelTaskAttempt,
    C21ModelTaskResult,
    C21RunResult,
    C21TaskId,
    REQUIRED_C21_TASKS,
    run_c21_executable_evaluation,
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

_KNOWN_TARGET_MODEL_REFS = {
    "ttm_latest": "ibm-granite/granite-timeseries-ttm-r2",
    "ttm_current_local_adapter": "ibm-granite/granite-timeseries-ttm-r2",
    "chronos_2": "amazon/chronos-2",
    "chronos_bolt": "amazon/chronos-bolt-base",
    "timesfm_2_5": "google/timesfm-2.5-200m-pytorch",
    "moirai_2_0_current_uni2ts": "Salesforce/moirai-2.0-R-small",
    "moirai_1_x_interface": "Salesforce/moirai-1.1-R-small",
    "moment_current": "AutonLab/MOMENT-1-large",
    "moment_current_interface": "https://github.com/moment-timeseries-foundation-model/moment",
    "units_current": "thuml/UniTS",
    "units_current_interface": "https://github.com/mims-harvard/UniTS",
}

_KNOWN_FALLBACK_MODEL_REFS = {
    "chronos_bolt": "amazon/chronos-bolt-base",
}

_TARGET_PACKAGE_HINTS = {
    "ttm": "tsfm_public",
    "chronos": "chronos",
    "timesfm": "timesfm",
    "moirai_uni2ts": "uni2ts",
    "moment": "momentfm",
    "units": "units",
}

_TARGET_RESOURCE_NOTES = {
    "ttm": "CPU-compatible local cache preferred for FU13-scale windows.",
    "chronos": (
        "Large pretrained forecasting model; local weights and dependency review required."
    ),
    "timesfm": "Large forecasting model; local weights and dependency review required.",
    "moirai_uni2ts": "Forecasting package and checkpoint compatibility require review.",
    "moment": (
        "Representation/imputation adapter fit requires local dependency and shape review."
    ),
    "units": "Unified task model; representation/imputation interface requires review.",
}

_TARGET_LICENSE_NOTES = {
    "ttm": "review model card/license before promotion",
    "chronos": "review model card/license before promotion",
    "timesfm": "review model card/license before promotion",
    "moirai_uni2ts": "review model card/license before promotion",
    "moment": "review model card/license before promotion",
    "units": "review model card/license before promotion",
}


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
    cache_dir: str | Path | None = None
    actual_network_used: bool | str | None = None
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

    @property
    def has_priority_or_core_failure(self) -> bool:
        from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus

        by_attempt = {
            (item.model_id, item.task_id): item
            for item in self.target_results
        }
        for model_id, task_ids in REQUIRED_C21_TASKS.items():
            for task_id in task_ids:
                item = by_attempt.get((model_id, task_id))
                if item is None:
                    return True
                if item.status != OpenModelAdapterStatus.AVAILABLE_AND_RAN:
                    return True
        return False


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


def build_c21_config_from_c22(config: C22ExecutionConfig) -> C21ExecutionConfig:
    return C21ExecutionConfig(
        stage="C2_1_executable_open_model_evaluation",
        upstream_c2_config=Path("configs/c_stage_c2_open_model_evaluation.yaml"),
        dataset_path=config.dataset_path,
        fu13_config_path=config.fu13_config_path,
        dataset_boundary=config.dataset_boundary,
        window_mode=config.window_mode,
        context_length=config.context_length,
        prediction_length=config.prediction_length,
        max_windows=config.max_windows,
        mask_ratio=config.mask_ratio,
        seed=config.seed,
        allow_network=config.allow_network,
        allow_download=config.allow_download,
        strict_model_success=config.strict_model_success,
        record_failure=config.record_failure,
        do_not_over_claim=config.do_not_over_claim,
        continue_on_model_failure=config.continue_on_model_failure,
        timeout_seconds_per_model=config.timeout_seconds_per_model,
        cache_dir=config.cache_dir,
        reuse_existing_cache=config.reuse_existing_cache,
        write_cache_manifest=config.write_cache_manifest,
        report_path=config.report_path,
        cache_manifest_path=config.cache_manifest_path,
    )


def run_c22_open_model_executable_upgrade(
    config_or_path: C22ExecutionConfig | str | Path,
    *,
    adapter_factory: Any = None,
    c21_runner: Any = None,
) -> C22RunResult:
    config_source: str | Path = "provided_config"
    if isinstance(config_or_path, C22ExecutionConfig):
        config = config_or_path
    else:
        config_source = config_or_path
        config = load_c22_config(config_or_path)

    c21_config = build_c21_config_from_c22(config)
    runner = c21_runner or run_c21_executable_evaluation
    c21_result: C21RunResult = runner(c21_config, adapter_factory=adapter_factory)

    return C22RunResult(
        run_id=_c22_run_id(c21_result.run_id),
        config_path=config_source,
        upstream_c21_config=config.upstream_c21_config,
        dataset_boundary=c21_result.dataset_boundary,
        config_allows_network=c21_result.config_allows_network,
        config_allows_download=c21_result.config_allows_download,
        cache_dir=c21_result.cache_dir,
        tested_windows=c21_result.tested_windows,
        target_results=[
            _c21_task_result_to_c22_target_result(task_result, config)
            for task_result in c21_result.task_results
        ],
        watchlist_audit=build_frontier_watchlist_audit(config),
        invalid_claims=_c22_invalid_claims(c21_result.invalid_claims),
    )


def build_frontier_watchlist_audit(
    config: C22ExecutionConfig,
) -> list[C22FrontierWatchlistAudit]:
    return [
        _WATCHLIST_AUDIT_BY_ID.get(target_id, _unknown_watchlist_audit(target_id))
        for target_id in config.frontier_watchlist.targets
    ]


def _c21_task_result_to_c22_target_result(
    task_result: C21ModelTaskResult,
    config: C22ExecutionConfig,
) -> C22TargetResult:
    target = config.model_targets.get(task_result.model_id)
    if target is None:
        raise C22ConfigError(
            f"C2.1 result has unknown C2.2 model target: {task_result.model_id}"
        )

    return C22TargetResult(
        model_id=task_result.model_id,
        role=target.role,
        target=target.target,
        fallback=target.fallback,
        task_id=task_result.task_id,
        status=task_result.status,
        metrics=dict(task_result.metrics),
        baseline_metrics=dict(task_result.baseline_metrics),
        failure_stage=task_result.failure_stage,
        failure_reason=task_result.failure_reason,
        dependency_status=task_result.dependency_status,
        weight_status=task_result.weight_status,
        adapter_name=task_result.adapter_name,
        model_ref=task_result.model_ref,
        cache_dir=task_result.cache_dir,
        actual_network_used=task_result.actual_network_used,
        runtime_seconds=task_result.runtime_seconds,
        target_metadata=_target_metadata(task_result, target),
    )


def _target_metadata(
    task_result: C21ModelTaskResult,
    target: C22ModelTarget,
) -> dict[str, Any]:
    return {
        "target_model_ref": _KNOWN_TARGET_MODEL_REFS.get(target.target, target.target),
        "executed_model_ref": task_result.model_ref,
        "fallback_model_ref": _KNOWN_TARGET_MODEL_REFS.get(
            target.fallback or "",
            _KNOWN_FALLBACK_MODEL_REFS.get(target.fallback or "", target.fallback),
        ),
        "target_package_hint": _TARGET_PACKAGE_HINTS.get(target.model_id, "needs_review"),
        "target_task_fit": ", ".join(task_id.value for task_id in target.tasks),
        "target_resource_note": _TARGET_RESOURCE_NOTES.get(
            target.model_id,
            "resource requirements require review",
        ),
        "target_license_note": _TARGET_LICENSE_NOTES.get(
            target.model_id,
            "license requires review before promotion",
        ),
    }


def _c22_run_id(c21_run_id: str) -> str:
    if c21_run_id.startswith("c21-"):
        return c21_run_id.replace("c21-", "c22-", 1)
    return f"c22-from-{c21_run_id}"


def _c22_invalid_claims(c21_invalid_claims: list[str]) -> list[str]:
    claims = list(c21_invalid_claims)
    for claim in (
        "不得解释为 frontier watchlist 模型已执行",
        "不得解释为 C2.2 watchlist 模型可进入 C3",
    ):
        if claim not in claims:
            claims.append(claim)
    return claims


def render_c22_report(result: C22RunResult, config: C22ExecutionConfig) -> str:
    lines = [
        "# C2.2 Open Model Executable Evaluation Upgrade Report",
        "",
        "## Report Metadata",
        "",
        f"- run_id: {_text(result.run_id)}",
        f"- config_path: {_text(result.config_path)}",
        f"- upstream_c21_config: {_text(result.upstream_c21_config)}",
        f"- dataset_boundary: {_text(result.dataset_boundary)}",
        f"- tested_windows: {_text(result.tested_windows)}",
        f"- config_allows_network: {_text(result.config_allows_network)}",
        f"- config_allows_download: {_text(result.config_allows_download)}",
        f"- cache_dir: {_text(result.cache_dir)}",
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
                "| model_id | display_name | task_id | target | target_model_ref | "
                "executed_model_ref | status | metrics | baseline_metrics | failure_stage | "
                "failure_reason | runtime_seconds |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
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
        lines.append("| none | none | none | none | none | none | none | none | none | none | none | none |")

    lines.extend(
        [
            "",
            "## Core Model-Task Result Matrix",
            "",
            (
                "| model_id | display_name | task_id | target | target_model_ref | "
                "executed_model_ref | status | metrics | baseline_metrics | failure_stage | "
                "failure_reason | runtime_seconds |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if result.target_results:
        for item in result.target_results:
            lines.append(_target_result_row(item))
    else:
        lines.append("| none | none | none | none | none | none | none | none | none | none | none | none |")

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
    lines.extend(f"- {_text(note)}" for note in (result.c3_handoff_notes or ["none"]))
    lines.extend(["", "## C2.2 -> B Decision Notes", ""])
    lines.extend(f"- {_text(note)}" for note in (result.b_decision_notes or ["none"]))
    lines.extend(["", "## Invalid Claims", ""])
    lines.extend(f"- {_text(claim)}" for claim in (result.invalid_claims or ["none"]))
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
        (
            "| model_id | task_id | target | fallback | adapter_name | cache_dir | "
            "weight_status | actual_network_used | target_model_ref | executed_model_ref |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    if result.target_results:
        for item in result.target_results:
            lines.append(
                (
                    f"| {_cell(item.model_id)} | {_cell(item.task_id)} | {_cell(item.target)} | "
                    f"{_cell(item.fallback)} | {_cell(item.adapter_name)} | {_cell(item.cache_dir)} | "
                    f"{_cell(item.weight_status)} | {_cell(item.actual_network_used)} | "
                    f"{_cell(_target_model_ref(item))} | {_cell(_executed_model_ref(item))} |"
                )
            )
    else:
        lines.append("| none | none | none | none | none | none | none | none | none | none |")
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
        f"{_cell(item.task_id)} | {_cell(item.target)} | "
        f"{_cell(_target_model_ref(item))} | {_cell(_executed_model_ref(item))} | "
        f"{_cell(item.status)} | {_cell(item.metrics)} | {_cell(item.baseline_metrics)} | "
        f"{_cell(item.failure_stage)} | {_cell(item.failure_reason)} | "
        f"{_cell(item.runtime_seconds)} |"
    )


def _target_model_ref(item: C22TargetResult) -> Any:
    return item.target_metadata.get("target_model_ref") or _KNOWN_TARGET_MODEL_REFS.get(
        item.target
    )


def _executed_model_ref(item: C22TargetResult) -> Any:
    return item.target_metadata.get("executed_model_ref") or item.model_ref


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


def _text(value: object) -> str:
    return (
        _value(value)
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("|", "\\|")
    )


def _cell(value: object) -> str:
    return _text(value)


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
