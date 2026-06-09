from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class C31CmapssConfigError(ValueError):
    """Raised when the C3.1 C-MAPSS config is invalid."""


class C31LicenseDecision(StrEnum):
    APPROVED_FOR_SCHEMA_VALIDATION = "approved_for_schema_validation"
    APPROVED_FOR_RESEARCH_TRAINING = "approved_for_research_training"
    BLOCKED_BY_LICENSE_REVIEW = "blocked_by_license_review"
    NEEDS_REVIEW = "needs_review"


class C31TopLevelStatus(StrEnum):
    BLOCKED = "blocked"
    READY_FOR_LOCAL_MAPPING = "ready_for_local_mapping"
    SCHEMA_VALIDATED_PENDING_TRAINING_USE_REVIEW = "schema_validated_pending_training_use_review"
    SCHEMA_VALIDATED_READY_FOR_C32 = "schema_validated_ready_for_c32"


class C31BlockedReason(StrEnum):
    BLOCKED_BY_SOURCE_REVIEW = "blocked_by_source_review"
    BLOCKED_BY_LICENSE_REVIEW = "blocked_by_license_review"
    BLOCKED_BY_DOWNLOAD_POLICY = "blocked_by_download_policy"
    BLOCKED_BY_MISSING_RAW_FILES = "blocked_by_missing_raw_files"
    BLOCKED_BY_RAW_SCHEMA_MISMATCH = "blocked_by_raw_schema_mismatch"
    BLOCKED_BY_MAPPING_SCHEMA = "blocked_by_mapping_schema"
    BLOCKED_BY_LEAKAGE_GUARD = "blocked_by_leakage_guard"
    BLOCKED_BY_LABEL_SEMANTICS = "blocked_by_label_semantics"


EXPECTED_CMAPSS_SUBSETS = ("FD001", "FD002", "FD003", "FD004")
EXPECTED_CMAPSS_FILE_ROLES = ("train", "test", "RUL")

_EXPECTED_STAGE = "C3_1_cmapss_minimal_ingestion"
_EXPECTED_DATASET_ID = "nasa_cmapss"
_VALID_SOURCE_STATUSES = ("verified", "needs_review", "unavailable", "deprecated")
_VALID_REVIEW_STATUSES = (
    "verified",
    "allowed",
    "research_only",
    "not_allowed",
    "needs_review",
    "restricted",
    "unknown",
)
_VALID_SAFETY_FLAG_COMBINATIONS = {
    (False, False, False, False),
    (True, False, False, False),
    (False, False, True, False),
    (False, False, True, True),
    (True, True, True, False),
    (True, True, True, True),
}


@dataclass(frozen=True)
class C31CalibrationSource:
    name: str
    url: str
    handling: str


@dataclass(frozen=True)
class C31Source:
    primary_source_name: str
    primary_source_url: str
    download_target_url: str
    source_status: str
    citation: str
    calibration_sources: tuple[C31CalibrationSource, ...]


@dataclass(frozen=True)
class C31LicenseReview:
    decision: C31LicenseDecision
    license_status: str
    redistribution_status: str
    training_use_status: str
    citation_required: bool


@dataclass(frozen=True)
class C31DownloadPolicy:
    allow_network: bool
    allow_download: bool
    allow_local_raw_data: bool
    allow_write_processed: bool
    raw_dir: Path
    processed_dir: Path
    checksum_policy: str
    expected_files: tuple[str, ...]


@dataclass(frozen=True)
class C31MappingPolicy:
    subsets: tuple[str, ...]
    pseudo_timestamp_start: str
    file_roles: tuple[str, ...]
    sensor_count: int
    setting_count: int
    use_capped_rul: bool


@dataclass(frozen=True)
class C31SplitPolicy:
    split_unit: str
    validation_source: str
    forbidden_leakage_modes: tuple[str, ...]


@dataclass(frozen=True)
class C31Outputs:
    report: Path
    processed_dir: Path


@dataclass(frozen=True)
class C31CmapssConfig:
    stage: str
    dataset_id: str
    source: C31Source
    license_review: C31LicenseReview
    download_policy: C31DownloadPolicy
    mapping_policy: C31MappingPolicy
    split_policy: C31SplitPolicy
    outputs: C31Outputs


@dataclass(frozen=True)
class C31CmapssRunResult:
    stage: str
    dataset_id: str
    config_path: str | Path | None
    status: C31TopLevelStatus
    blocked_reasons: tuple[C31BlockedReason, ...]
    raw_files_present: tuple[str, ...]
    raw_files_missing: tuple[str, ...]


def expected_cmapss_files() -> tuple[str, ...]:
    files: list[str] = []
    for subset in EXPECTED_CMAPSS_SUBSETS:
        files.extend(
            (f"train_{subset}.txt", f"test_{subset}.txt", f"RUL_{subset}.txt")
        )
    return tuple(files)


def load_c31_cmapss_config(path: str | Path) -> C31CmapssConfig:
    raw = _load_mapping(Path(path))
    stage = _load_required_string(raw, "stage")
    if stage != _EXPECTED_STAGE:
        raise C31CmapssConfigError(f"stage must be {_EXPECTED_STAGE}")

    dataset_id = _load_required_string(raw, "dataset_id")
    if dataset_id != _EXPECTED_DATASET_ID:
        raise C31CmapssConfigError(f"dataset_id must be {_EXPECTED_DATASET_ID}")

    mapping_policy = _load_mapping_policy(raw)
    download_policy = _load_download_policy(raw, mapping_policy)
    _validate_download_policy(download_policy)

    return C31CmapssConfig(
        stage=stage,
        dataset_id=dataset_id,
        source=_load_source(raw),
        license_review=_load_license_review(raw),
        download_policy=download_policy,
        mapping_policy=mapping_policy,
        split_policy=_load_split_policy(raw),
        outputs=_load_outputs(raw),
    )


def run_c31_cmapss_minimal_ingestion(
    config: C31CmapssConfig,
    *,
    config_path: str | Path | None = None,
) -> C31CmapssRunResult:
    blocked_reasons: list[C31BlockedReason] = []
    if config.source.source_status != "verified":
        blocked_reasons.append(C31BlockedReason.BLOCKED_BY_SOURCE_REVIEW)
    if config.license_review.decision in (
        C31LicenseDecision.NEEDS_REVIEW,
        C31LicenseDecision.BLOCKED_BY_LICENSE_REVIEW,
    ):
        blocked_reasons.append(C31BlockedReason.BLOCKED_BY_LICENSE_REVIEW)

    if not config.download_policy.allow_local_raw_data:
        blocked_reasons.append(C31BlockedReason.BLOCKED_BY_DOWNLOAD_POLICY)
        return C31CmapssRunResult(
            stage=config.stage,
            dataset_id=config.dataset_id,
            config_path=config_path,
            status=C31TopLevelStatus.BLOCKED,
            blocked_reasons=tuple(blocked_reasons),
            raw_files_present=(),
            raw_files_missing=tuple(config.download_policy.expected_files),
        )

    present, missing = _inspect_expected_raw_files(config.download_policy)
    if missing:
        blocked_reasons.append(C31BlockedReason.BLOCKED_BY_MISSING_RAW_FILES)

    return C31CmapssRunResult(
        stage=config.stage,
        dataset_id=config.dataset_id,
        config_path=config_path,
        status=(
            C31TopLevelStatus.BLOCKED
            if blocked_reasons
            else C31TopLevelStatus.READY_FOR_LOCAL_MAPPING
        ),
        blocked_reasons=tuple(blocked_reasons),
        raw_files_present=present,
        raw_files_missing=missing,
    )


def _load_source(raw: dict[str, Any]) -> C31Source:
    source = _load_mapping(raw, "source")
    source_status = _load_required_string(source, "source_status", "source")
    _validate_allowed(source_status, _VALID_SOURCE_STATUSES, "source.source_status")
    calibration_sources_raw = source.get("calibration_sources")
    if not isinstance(calibration_sources_raw, list):
        raise C31CmapssConfigError("source.calibration_sources must be a list")
    return C31Source(
        primary_source_name=_load_required_string(
            source, "primary_source_name", "source"
        ),
        primary_source_url=_load_required_string(source, "primary_source_url", "source"),
        download_target_url=_load_required_string(
            source, "download_target_url", "source"
        ),
        source_status=source_status,
        citation=_load_required_string(source, "citation", "source"),
        calibration_sources=tuple(
            _load_calibration_source(item, index)
            for index, item in enumerate(calibration_sources_raw)
        ),
    )


def _load_calibration_source(raw: Any, index: int) -> C31CalibrationSource:
    if not isinstance(raw, dict):
        raise C31CmapssConfigError(
            f"source.calibration_sources[{index}] must be a mapping"
        )
    return C31CalibrationSource(
        name=_load_required_string(raw, "name", f"source.calibration_sources[{index}]"),
        url=_load_required_string(raw, "url", f"source.calibration_sources[{index}]"),
        handling=_load_required_string(
            raw, "handling", f"source.calibration_sources[{index}]"
        ),
    )


def _load_license_review(raw: dict[str, Any]) -> C31LicenseReview:
    review = _load_mapping(raw, "license_review")
    decision_value = _load_required_string(review, "decision", "license_review")
    try:
        decision = C31LicenseDecision(decision_value)
    except ValueError as exc:
        raise C31CmapssConfigError("license_review.decision is invalid") from exc

    license_status = _load_required_string(review, "license_status", "license_review")
    redistribution_status = _load_required_string(
        review, "redistribution_status", "license_review"
    )
    training_use_status = _load_required_string(
        review, "training_use_status", "license_review"
    )
    for field, value in (
        ("license_status", license_status),
        ("redistribution_status", redistribution_status),
        ("training_use_status", training_use_status),
    ):
        _validate_allowed(value, _VALID_REVIEW_STATUSES, f"license_review.{field}")

    return C31LicenseReview(
        decision=decision,
        license_status=license_status,
        redistribution_status=redistribution_status,
        training_use_status=training_use_status,
        citation_required=_load_required_bool(
            review, "citation_required", "license_review"
        ),
    )


def _load_download_policy(
    raw: dict[str, Any],
    mapping_policy: C31MappingPolicy,
) -> C31DownloadPolicy:
    policy = _load_mapping(raw, "download_policy")
    expected_files = _load_required_string_list(
        policy, "expected_files", "download_policy"
    )
    _validate_expected_files(expected_files, mapping_policy)
    return C31DownloadPolicy(
        allow_network=_load_required_bool(policy, "allow_network", "download_policy"),
        allow_download=_load_required_bool(policy, "allow_download", "download_policy"),
        allow_local_raw_data=_load_required_bool(
            policy, "allow_local_raw_data", "download_policy"
        ),
        allow_write_processed=_load_required_bool(
            policy, "allow_write_processed", "download_policy"
        ),
        raw_dir=Path(_load_required_string(policy, "raw_dir", "download_policy")),
        processed_dir=Path(
            _load_required_string(policy, "processed_dir", "download_policy")
        ),
        checksum_policy=_load_required_string(
            policy, "checksum_policy", "download_policy"
        ),
        expected_files=expected_files,
    )


def _load_mapping_policy(raw: dict[str, Any]) -> C31MappingPolicy:
    policy = _load_mapping(raw, "mapping_policy")
    subsets = _load_required_string_list(policy, "subsets", "mapping_policy")
    for subset in subsets:
        _validate_allowed(subset, EXPECTED_CMAPSS_SUBSETS, "mapping_policy.subsets")

    file_roles = _load_required_string_list(policy, "file_roles", "mapping_policy")
    for file_role in file_roles:
        _validate_allowed(
            file_role, EXPECTED_CMAPSS_FILE_ROLES, "mapping_policy.file_roles"
        )

    return C31MappingPolicy(
        subsets=subsets,
        pseudo_timestamp_start=_load_required_string(
            policy, "pseudo_timestamp_start", "mapping_policy"
        ),
        file_roles=file_roles,
        sensor_count=_load_required_int(policy, "sensor_count", "mapping_policy"),
        setting_count=_load_required_int(policy, "setting_count", "mapping_policy"),
        use_capped_rul=_load_required_bool(
            policy, "use_capped_rul", "mapping_policy"
        ),
    )


def _load_split_policy(raw: dict[str, Any]) -> C31SplitPolicy:
    policy = _load_mapping(raw, "split_policy")
    return C31SplitPolicy(
        split_unit=_load_required_string(policy, "split_unit", "split_policy"),
        validation_source=_load_required_string(
            policy, "validation_source", "split_policy"
        ),
        forbidden_leakage_modes=_load_required_string_list(
            policy, "forbidden_leakage_modes", "split_policy"
        ),
    )


def _load_outputs(raw: dict[str, Any]) -> C31Outputs:
    outputs = _load_mapping(raw, "outputs")
    return C31Outputs(
        report=Path(_load_required_string(outputs, "report", "outputs")),
        processed_dir=Path(_load_required_string(outputs, "processed_dir", "outputs")),
    )


def _validate_download_policy(policy: C31DownloadPolicy) -> None:
    if policy.allow_download and not policy.allow_network:
        raise C31CmapssConfigError(
            "download_policy.allow_download requires allow_network"
        )
    if policy.allow_download and not policy.allow_local_raw_data:
        raise C31CmapssConfigError(
            "download_policy.allow_download requires allow_local_raw_data"
        )
    if policy.allow_write_processed and not policy.allow_local_raw_data:
        raise C31CmapssConfigError(
            "download_policy.allow_write_processed requires allow_local_raw_data"
        )

    flags = (
        policy.allow_network,
        policy.allow_download,
        policy.allow_local_raw_data,
        policy.allow_write_processed,
    )
    if flags not in _VALID_SAFETY_FLAG_COMBINATIONS:
        raise C31CmapssConfigError(
            "download_policy safety flags must match a documented safe combination"
        )


def _validate_expected_files(
    expected_files: tuple[str, ...],
    mapping_policy: C31MappingPolicy,
) -> None:
    if _is_full_classic_policy(mapping_policy):
        if expected_files != expected_cmapss_files():
            raise C31CmapssConfigError(
                "download_policy.expected_files must match full classic C-MAPSS files"
            )
        return

    expected_for_policy = _expected_files_for_policy(mapping_policy)
    if expected_files != expected_for_policy:
        raise C31CmapssConfigError(
            "download_policy.expected_files must match mapping_policy subsets and file_roles"
        )


def _is_full_classic_policy(mapping_policy: C31MappingPolicy) -> bool:
    return (
        set(mapping_policy.subsets) == set(EXPECTED_CMAPSS_SUBSETS)
        and len(mapping_policy.subsets) == len(EXPECTED_CMAPSS_SUBSETS)
        and set(mapping_policy.file_roles) == set(EXPECTED_CMAPSS_FILE_ROLES)
        and len(mapping_policy.file_roles) == len(EXPECTED_CMAPSS_FILE_ROLES)
    )


def _expected_files_for_policy(mapping_policy: C31MappingPolicy) -> tuple[str, ...]:
    files: list[str] = []
    for subset in mapping_policy.subsets:
        for file_role in mapping_policy.file_roles:
            files.append(f"{file_role}_{subset}.txt")
    return tuple(files)


def _inspect_expected_raw_files(
    policy: C31DownloadPolicy,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    present: list[str] = []
    missing: list[str] = []
    for filename in policy.expected_files:
        if (policy.raw_dir / filename).is_file():
            present.append(filename)
        else:
            missing.append(filename)
    return tuple(present), tuple(missing)


def _load_mapping(raw: Any, field: str | None = None) -> dict[str, Any]:
    if field is None:
        try:
            loaded = yaml.safe_load(raw.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise C31CmapssConfigError(f"YAML parse error: {exc}") from exc
        except OSError as exc:
            raise C31CmapssConfigError(f"could not read config: {exc}") from exc
        if not isinstance(loaded, dict):
            raise C31CmapssConfigError("config must be a mapping")
        return loaded

    value = raw.get(field)
    if not isinstance(value, dict):
        raise C31CmapssConfigError(f"{field} must be a mapping")
    return value


def _load_required_string(
    raw: dict[str, Any],
    field: str,
    context: str | None = None,
) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value:
        prefix = f"{context}." if context else ""
        raise C31CmapssConfigError(f"{prefix}{field} must be a non-empty string")
    return value


def _load_required_string_list(
    raw: dict[str, Any],
    field: str,
    context: str,
) -> tuple[str, ...]:
    value = raw.get(field)
    if not isinstance(value, list) or not value:
        raise C31CmapssConfigError(f"{context}.{field} must be a non-empty list")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise C31CmapssConfigError(
                f"{context}.{field}[{index}] must be a non-empty string"
            )
    return tuple(value)


def _load_required_bool(raw: dict[str, Any], field: str, context: str) -> bool:
    value = raw.get(field)
    if not isinstance(value, bool):
        raise C31CmapssConfigError(f"{context}.{field} must be a boolean")
    return value


def _load_required_int(raw: dict[str, Any], field: str, context: str) -> int:
    value = raw.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise C31CmapssConfigError(f"{context}.{field} must be an integer")
    return value


def _validate_allowed(value: str, allowed_values: tuple[str, ...], field: str) -> None:
    if value not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise C31CmapssConfigError(f"{field} must be one of: {allowed}")
