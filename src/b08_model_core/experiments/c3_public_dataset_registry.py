from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class C3RegistryConfigError(ValueError):
    """Raised when the C3 public dataset registry config is invalid."""


class C3DatasetRole(StrEnum):
    INTERNAL_ANCHOR = "internal_anchor"
    OPEN_BENCHMARK_CANDIDATE = "open_benchmark_candidate"
    WATCHLIST_CANDIDATE = "watchlist_candidate"


@dataclass(frozen=True)
class C3DatasetEntry:
    dataset_id: str
    display_name: str
    dataset_role: C3DatasetRole
    source_type: str
    official_source_url: str
    source_status: str
    license_status: str
    redistribution_status: str
    training_use_status: str
    task_families: tuple[str, ...]
    label_semantics: str
    schema_mapping_status: str
    canonical_mapping_notes: str
    split_policy: str
    leakage_risks: str
    allowed_metrics: tuple[str, ...]
    go_no_go_prerequisites: tuple[str, ...]
    invalid_claims: tuple[str, ...]
    next_action: str
    risk_level: str


@dataclass(frozen=True)
class C3RegistryOutputs:
    report: Path


@dataclass(frozen=True)
class C3RegistryConfig:
    stage: str
    latest_source_calibration: dict[str, Any]
    outputs: C3RegistryOutputs
    datasets: tuple[C3DatasetEntry, ...]


@dataclass(frozen=True)
class C3DatasetReadiness:
    dataset_id: str
    readiness: str
    reasons: tuple[str, ...]
    next_action: str


@dataclass(frozen=True)
class C3RegistryRunResult:
    stage: str
    config_path: str | Path
    datasets: tuple[C3DatasetEntry, ...]
    readiness: tuple[C3DatasetReadiness, ...]
    latest_source_calibration: dict[str, Any]
    invalid_claims: tuple[str, ...]


_EXPECTED_STAGE = "C3_public_dataset_registry"

_REQUIRED_DATASET_FIELDS = (
    "dataset_id",
    "display_name",
    "dataset_role",
    "source_type",
    "official_source_url",
    "source_status",
    "license_status",
    "redistribution_status",
    "training_use_status",
    "task_families",
    "label_semantics",
    "schema_mapping_status",
    "canonical_mapping_notes",
    "split_policy",
    "leakage_risks",
    "allowed_metrics",
    "go_no_go_prerequisites",
    "invalid_claims",
    "next_action",
    "risk_level",
)

_LIST_FIELDS = (
    "task_families",
    "allowed_metrics",
    "go_no_go_prerequisites",
    "invalid_claims",
)

_ALLOWED_VALUES = {
    "dataset_role": tuple(role.value for role in C3DatasetRole),
    "source_type": ("internal", "official_public", "paper_hosted", "repository", "unknown"),
    "source_status": ("verified", "needs_review", "unavailable", "deprecated"),
    "license_status": ("verified", "needs_review", "restricted", "unknown"),
    "redistribution_status": ("allowed", "not_allowed", "needs_review", "unknown"),
    "training_use_status": (
        "allowed",
        "research_only",
        "needs_review",
        "not_allowed",
        "unknown",
    ),
    "schema_mapping_status": ("mapped", "partial", "planned", "blocked", "needs_review"),
    "risk_level": ("low", "medium", "high"),
}

_ALLOWED_TASK_FAMILIES = (
    "forecasting",
    "imputation",
    "representation",
    "weak_label",
    "fault_classification",
    "rul",
    "run_to_failure",
    "anomaly_detection",
    "process_monitoring",
)

_ALLOWED_METRICS = (
    "forecasting_mae",
    "forecasting_rmse",
    "mask_reconstruction_error",
    "linear_probe_macro_f1",
    "rul_mae",
    "rul_rmse",
    "trend_forecasting_error",
    "macro_f1",
    "auroc",
    "detection_delay",
)

_SOURCE_LICENSE_REVIEW_VALUES = {
    "unknown",
    "needs_review",
    "restricted",
    "not_allowed",
    "blocked",
    "unavailable",
    "deprecated",
}

_READY_ACTION_TOKENS = ("ready", "training-ready", "train-ready")


def load_c3_registry_config(path: str | Path) -> C3RegistryConfig:
    raw = _load_mapping(Path(path))
    stage = _load_required_string(raw, "stage")
    if stage != _EXPECTED_STAGE:
        raise C3RegistryConfigError(f"stage must be {_EXPECTED_STAGE}")

    outputs = _load_outputs(raw)
    datasets = _load_datasets(raw)

    return C3RegistryConfig(
        stage=stage,
        latest_source_calibration=_load_latest_source_calibration(raw),
        outputs=outputs,
        datasets=datasets,
    )


def _load_latest_source_calibration(raw: dict[str, Any]) -> dict[str, Any]:
    value = raw.get("latest_source_calibration")
    if not isinstance(value, dict):
        raise C3RegistryConfigError("latest_source_calibration must be a mapping")
    return dict(value)


def _load_outputs(raw: dict[str, Any]) -> C3RegistryOutputs:
    outputs = _load_mapping(raw, "outputs")
    return C3RegistryOutputs(report=Path(_load_required_string(outputs, "report")))


def _load_datasets(raw: dict[str, Any]) -> tuple[C3DatasetEntry, ...]:
    datasets_raw = raw.get("datasets")
    if not isinstance(datasets_raw, list) or not datasets_raw:
        raise C3RegistryConfigError("datasets must be a non-empty list")

    dataset_ids: set[str] = set()
    entries: list[C3DatasetEntry] = []
    for index, item in enumerate(datasets_raw):
        if not isinstance(item, dict):
            raise C3RegistryConfigError(f"datasets[{index}] must be a mapping")
        entry = _load_dataset_entry(item, index)
        if entry.dataset_id in dataset_ids:
            raise C3RegistryConfigError(f"duplicate dataset_id: {entry.dataset_id}")
        dataset_ids.add(entry.dataset_id)
        entries.append(entry)
    return tuple(entries)


def _load_dataset_entry(raw: dict[str, Any], index: int) -> C3DatasetEntry:
    for field in _REQUIRED_DATASET_FIELDS:
        if field in _LIST_FIELDS:
            _load_required_string_list(raw, field, index)
        else:
            _load_required_string(raw, field, f"datasets[{index}]")

    for field, allowed_values in _ALLOWED_VALUES.items():
        value = _load_required_string(raw, field, f"datasets[{index}]")
        if value not in allowed_values:
            allowed = ", ".join(allowed_values)
            raise C3RegistryConfigError(
                f"datasets[{index}].{field} must be one of: {allowed}"
            )

    entry = C3DatasetEntry(
        dataset_id=_load_required_string(raw, "dataset_id", f"datasets[{index}]"),
        display_name=_load_required_string(raw, "display_name", f"datasets[{index}]"),
        dataset_role=C3DatasetRole(
            _load_required_string(raw, "dataset_role", f"datasets[{index}]")
        ),
        source_type=_load_required_string(raw, "source_type", f"datasets[{index}]"),
        official_source_url=_load_required_string(
            raw, "official_source_url", f"datasets[{index}]"
        ),
        source_status=_load_required_string(raw, "source_status", f"datasets[{index}]"),
        license_status=_load_required_string(
            raw, "license_status", f"datasets[{index}]"
        ),
        redistribution_status=_load_required_string(
            raw, "redistribution_status", f"datasets[{index}]"
        ),
        training_use_status=_load_required_string(
            raw, "training_use_status", f"datasets[{index}]"
        ),
        task_families=_load_required_string_list(raw, "task_families", index),
        label_semantics=_load_required_string(
            raw, "label_semantics", f"datasets[{index}]"
        ),
        schema_mapping_status=_load_required_string(
            raw, "schema_mapping_status", f"datasets[{index}]"
        ),
        canonical_mapping_notes=_load_required_string(
            raw, "canonical_mapping_notes", f"datasets[{index}]"
        ),
        split_policy=_load_required_string(raw, "split_policy", f"datasets[{index}]"),
        leakage_risks=_load_required_string(raw, "leakage_risks", f"datasets[{index}]"),
        allowed_metrics=_load_required_string_list(raw, "allowed_metrics", index),
        go_no_go_prerequisites=_load_required_string_list(
            raw, "go_no_go_prerequisites", index
        ),
        invalid_claims=_load_required_string_list(raw, "invalid_claims", index),
        next_action=_load_required_string(raw, "next_action", f"datasets[{index}]"),
        risk_level=_load_required_string(raw, "risk_level", f"datasets[{index}]"),
    )
    _validate_dataset_safety(entry, index)
    return entry


def _load_mapping(
    raw: dict[str, Any] | Path,
    key: str | None = None,
) -> dict[str, Any]:
    if isinstance(raw, Path):
        try:
            loaded = yaml.safe_load(raw.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise C3RegistryConfigError(f"invalid YAML in {raw}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise C3RegistryConfigError(f"{raw} must contain a mapping")
        return loaded

    value = raw.get(key or "")
    if not isinstance(value, dict):
        raise C3RegistryConfigError(f"{key} must be a mapping")
    return value


def _load_required_string(
    raw: dict[str, Any],
    key: str,
    context: str = "config",
) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise C3RegistryConfigError(f"{context}.{key} is required")
    return value


def _load_required_string_list(
    raw: dict[str, Any],
    key: str,
    dataset_index: int,
) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise C3RegistryConfigError(f"datasets[{dataset_index}].{key} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise C3RegistryConfigError(
            f"datasets[{dataset_index}].{key} must contain non-empty strings"
        )
    return tuple(value)


def _validate_dataset_safety(entry: C3DatasetEntry, index: int) -> None:
    if entry.official_source_url == "needs_review" and entry.source_status == "verified":
        raise C3RegistryConfigError(
            "datasets[{index}].source_status cannot be verified when "
            "official_source_url is needs_review".format(index=index)
        )

    if _next_action_implies_ready(entry.next_action):
        if entry.training_use_status == "unknown":
            raise C3RegistryConfigError(
                f"datasets[{index}].training_use_status cannot be unknown for a ready action"
            )
        if entry.license_status == "unknown":
            raise C3RegistryConfigError(
                f"datasets[{index}].license_status cannot be unknown for a ready action"
            )


def _next_action_implies_ready(next_action: str) -> bool:
    normalized = next_action.lower()
    return any(token in normalized for token in _READY_ACTION_TOKENS)


def run_c3_public_dataset_registry(
    config: C3RegistryConfig,
    config_path: str | Path = "",
) -> C3RegistryRunResult:
    readiness = tuple(_classify_dataset_readiness(dataset) for dataset in config.datasets)
    invalid_claims = tuple(
        dict.fromkeys(
            claim
            for dataset in config.datasets
            for claim in dataset.invalid_claims
        )
    )
    return C3RegistryRunResult(
        stage=config.stage,
        config_path=config_path,
        datasets=config.datasets,
        readiness=readiness,
        latest_source_calibration=config.latest_source_calibration,
        invalid_claims=invalid_claims,
    )


def _classify_dataset_readiness(entry: C3DatasetEntry) -> C3DatasetReadiness:
    task_mapping_reasons = _task_mapping_reasons(entry)
    split_policy_reasons = _split_policy_reasons(entry)
    source_license_reasons = _source_license_review_reasons(entry)

    if entry.dataset_role == C3DatasetRole.WATCHLIST_CANDIDATE:
        readiness = "watchlist_only"
        reasons = ("dataset_role=watchlist_candidate",)
    elif task_mapping_reasons:
        readiness = "task_mapping_review"
        reasons = task_mapping_reasons
    elif split_policy_reasons:
        readiness = "split_policy_review"
        reasons = split_policy_reasons
    elif source_license_reasons:
        readiness = "needs_source_license_review"
        reasons = source_license_reasons
    else:
        readiness = "ready_for_next_mapping"
        reasons = ("registry_prerequisites_satisfied",)

    return C3DatasetReadiness(
        dataset_id=entry.dataset_id,
        readiness=readiness,
        reasons=reasons,
        next_action=entry.next_action,
    )


def _task_mapping_reasons(entry: C3DatasetEntry) -> tuple[str, ...]:
    reasons = [
        f"unknown_task_family={task}"
        for task in entry.task_families
        if task not in _ALLOWED_TASK_FAMILIES
    ]
    reasons.extend(
        f"unknown_allowed_metric={metric}"
        for metric in entry.allowed_metrics
        if metric not in _ALLOWED_METRICS
    )
    return tuple(reasons)


def _split_policy_reasons(entry: C3DatasetEntry) -> tuple[str, ...]:
    reasons: list[str] = []
    task_families = set(entry.task_families)
    split_policy = entry.split_policy.lower()
    leakage_risks = entry.leakage_risks.lower()

    if task_families.intersection({"rul", "run_to_failure"}):
        if "unit" not in split_policy and "run" not in split_policy:
            reasons.append("unit_or_run_split_required_for_rul")

    if task_families.intersection({"process_monitoring", "fault_classification"}):
        leakage_guard_terms = ("fault", "trajectory", "condition", "工况", "故障")
        if not any(term in leakage_risks for term in leakage_guard_terms):
            reasons.append("fault_or_condition_leakage_guard_required")

    return tuple(reasons)


def _source_license_review_reasons(entry: C3DatasetEntry) -> tuple[str, ...]:
    fields = (
        ("source_type", entry.source_type),
        ("official_source_url", entry.official_source_url),
        ("source_status", entry.source_status),
        ("license_status", entry.license_status),
        ("redistribution_status", entry.redistribution_status),
        ("training_use_status", entry.training_use_status),
        ("schema_mapping_status", entry.schema_mapping_status),
    )
    return tuple(
        f"{field}={value}"
        for field, value in fields
        if value in _SOURCE_LICENSE_REVIEW_VALUES
    )


def render_c3_registry_report(result: C3RegistryRunResult) -> str:
    readiness_by_id = {item.dataset_id: item for item in result.readiness}
    lines = [
        "# C3 Public Dataset Registry Report",
        "",
        (
            "不下载公开数据原始文件，不提交公开数据或派生 parquet，"
            "不运行模型训练。"
        ),
        "",
        "## Registry Summary",
        "",
        f"- Stage: {result.stage}",
        f"- Config: {result.config_path or 'in_memory'}",
        f"- Dataset count: {len(result.datasets)}",
        "",
        "## Dataset Readiness Table",
        "",
        "| Dataset | Role | Readiness | Reasons | Next Action |",
        "| --- | --- | --- | --- | --- |",
    ]

    for dataset in result.datasets:
        readiness = readiness_by_id[dataset.dataset_id]
        lines.append(
            "| {dataset_id} | {role} | {readiness} | {reasons} | {next_action} |".format(
                dataset_id=dataset.dataset_id,
                role=dataset.dataset_role.value,
                readiness=readiness.readiness,
                reasons=", ".join(readiness.reasons),
                next_action=dataset.next_action,
            )
        )

    lines.extend(
        [
            "",
            "## Source And License Audit",
            "",
            "| Dataset | Source | Source Status | License | Redistribution | Training Use |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for dataset in result.datasets:
        lines.append(
            "| {dataset_id} | {source} | {source_status} | {license_status} | "
            "{redistribution_status} | {training_use_status} |".format(
                dataset_id=dataset.dataset_id,
                source=dataset.official_source_url,
                source_status=dataset.source_status,
                license_status=dataset.license_status,
                redistribution_status=dataset.redistribution_status,
                training_use_status=dataset.training_use_status,
            )
        )

    lines.extend(
        [
            "",
            "## Task And Metric Mapping",
            "",
            "| Dataset | Task Families | Allowed Metrics | Label Semantics |",
            "| --- | --- | --- | --- |",
        ]
    )
    for dataset in result.datasets:
        lines.append(
            "| {dataset_id} | {tasks} | {metrics} | {labels} |".format(
                dataset_id=dataset.dataset_id,
                tasks=", ".join(dataset.task_families),
                metrics=", ".join(dataset.allowed_metrics),
                labels=dataset.label_semantics,
            )
        )

    lines.extend(
        [
            "",
            "## Canonical Schema Mapping Status",
            "",
            "| Dataset | Status | Notes |",
            "| --- | --- | --- |",
        ]
    )
    for dataset in result.datasets:
        lines.append(
            "| {dataset_id} | {status} | {notes} |".format(
                dataset_id=dataset.dataset_id,
                status=dataset.schema_mapping_status,
                notes=dataset.canonical_mapping_notes,
            )
        )

    lines.extend(
        [
            "",
            "## Split Policy And Leakage Guard",
            "",
            "| Dataset | Split Policy | Leakage Risks |",
            "| --- | --- | --- |",
        ]
    )
    for dataset in result.datasets:
        lines.append(
            "| {dataset_id} | {split_policy} | {leakage_risks} |".format(
                dataset_id=dataset.dataset_id,
                split_policy=dataset.split_policy,
                leakage_risks=dataset.leakage_risks,
            )
        )

    lines.extend(
        [
            "",
            "## Latest Source Calibration Notes",
            "",
        ]
    )
    for key, value in result.latest_source_calibration.items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Go / No-Go For Next C3 Loop",
            "",
            "| Dataset | Decision | Required Next Action | Prerequisites | Risk Level |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for dataset in result.datasets:
        readiness = readiness_by_id[dataset.dataset_id]
        decision = (
            "Go"
            if readiness.readiness == "ready_for_next_mapping"
            else "No-Go / Review"
        )
        lines.append(
            f"| {dataset.dataset_id} | {decision}: {readiness.readiness} | "
            f"{dataset.next_action} | "
            f"{', '.join(dataset.go_no_go_prerequisites)} | {dataset.risk_level} |"
        )

    lines.extend(
        [
            "",
            "## Invalid Claims",
            "",
        ]
    )
    for claim in result.invalid_claims:
        lines.append(f"- {claim}")

    return "\n".join(lines) + "\n"
