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

    return C3DatasetEntry(
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
