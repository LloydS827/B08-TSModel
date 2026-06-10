from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from b08_model_core.tasks.schema import validate_observation_frame


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
_PROTECTED_RAW_DIR = Path("data/public/cmapss/raw")
_PROTECTED_PROCESSED_DIR = Path("data/processed/cmapss")
_EXPECTED_CHECKSUM_POLICY = "record_if_downloaded"
_EXPECTED_SENSOR_COUNT = 21
_EXPECTED_SETTING_COUNT = 3
_EXPECTED_PSEUDO_TIMESTAMP_START = "2000-01-01T00:00:00Z"
_PSEUDO_TIMESTAMP_RULE = "2000-01-01T00:00:00Z + cycle_index seconds"
_EXPECTED_SPLIT_UNIT = "trajectory_id"
_EXPECTED_VALIDATION_SOURCE = "train_trajectories"
_EXPECTED_FORBIDDEN_LEAKAGE_MODES = (
    "trajectory_id_overlap",
    "target_columns_in_input_features",
    "window_adjacency_across_splits",
)
_VALID_SOURCE_STATUSES = ("verified", "needs_review", "unavailable", "deprecated")
_VALID_LICENSE_STATUSES = (
    "verified",
    "needs_review",
    "restricted",
    "unknown",
)
_VALID_REDISTRIBUTION_STATUSES = ("allowed", "not_allowed", "needs_review", "unknown")
_VALID_TRAINING_USE_STATUSES = (
    "allowed",
    "research_only",
    "needs_review",
    "not_allowed",
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


class _C31NoDuplicateKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping_without_duplicate_keys(
    loader: yaml.SafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key: {key}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_C31NoDuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_without_duplicate_keys,
)


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
class C31MappedObservationSummary:
    observation_rows: int
    trajectory_count: int
    trajectory_ids: tuple[str, ...]
    required_schema_valid: bool
    pseudo_timestamp_rule: str
    uses_capped_rul: bool


@dataclass(frozen=True)
class C31RulTarget:
    subset: str
    file_role: str
    trajectory_id: str
    unit_id: int
    cycle_index: int
    rul: int


@dataclass(frozen=True)
class C31CmapssRunResult:
    stage: str
    dataset_id: str
    config_path: str | Path | None
    status: C31TopLevelStatus
    blocked_reasons: tuple[C31BlockedReason, ...]
    raw_files_present: tuple[str, ...]
    raw_files_missing: tuple[str, ...]
    mapping_summary: C31MappedObservationSummary | None = None
    rul_targets: tuple[C31RulTarget, ...] = ()


@dataclass(frozen=True)
class _C31CmapssRawRow:
    subset: str
    file_role: str
    unit_id: int
    cycle_index: int
    settings: tuple[float, float, float]
    sensors: tuple[float, ...]


class _C31RawSchemaMismatch(ValueError):
    pass


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
    outputs = _load_outputs(raw)
    _validate_download_policy(download_policy, outputs)

    return C31CmapssConfig(
        stage=stage,
        dataset_id=dataset_id,
        source=_load_source(raw),
        license_review=_load_license_review(raw),
        download_policy=download_policy,
        mapping_policy=mapping_policy,
        split_policy=_load_split_policy(raw),
        outputs=outputs,
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

    if blocked_reasons:
        return C31CmapssRunResult(
            stage=config.stage,
            dataset_id=config.dataset_id,
            config_path=config_path,
            status=C31TopLevelStatus.BLOCKED,
            blocked_reasons=tuple(blocked_reasons),
            raw_files_present=(),
            raw_files_missing=tuple(config.download_policy.expected_files),
        )

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
            status=C31TopLevelStatus.BLOCKED,
            blocked_reasons=tuple(blocked_reasons),
            raw_files_present=present,
            raw_files_missing=missing,
        )

    try:
        mapping_summary, rul_targets = _map_cmapss_rows_to_observations(config)
    except _C31RawSchemaMismatch:
        blocked_reasons.append(C31BlockedReason.BLOCKED_BY_RAW_SCHEMA_MISMATCH)
        return C31CmapssRunResult(
            stage=config.stage,
            dataset_id=config.dataset_id,
            config_path=config_path,
            status=C31TopLevelStatus.BLOCKED,
            blocked_reasons=tuple(blocked_reasons),
            raw_files_present=present,
            raw_files_missing=missing,
        )

    if not mapping_summary.required_schema_valid:
        blocked_reasons.append(C31BlockedReason.BLOCKED_BY_MAPPING_SCHEMA)

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
        mapping_summary=mapping_summary,
        rul_targets=rul_targets,
    )


def _parse_cmapss_data_file(
    path: Path,
    subset: str,
    file_role: str,
) -> tuple[_C31CmapssRawRow, ...]:
    rows: list[_C31CmapssRawRow] = []
    seen_cycles: set[tuple[int, int]] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise _C31RawSchemaMismatch(str(exc)) from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        columns = line.split()
        if len(columns) != 2 + _EXPECTED_SETTING_COUNT + _EXPECTED_SENSOR_COUNT:
            raise _C31RawSchemaMismatch(
                f"{path}:{line_number} expected 26 columns, got {len(columns)}"
            )
        try:
            unit_id = int(columns[0])
            cycle_index = int(columns[1])
            settings = tuple(float(value) for value in columns[2:5])
            sensors = tuple(float(value) for value in columns[5:])
        except ValueError as exc:
            raise _C31RawSchemaMismatch(
                f"{path}:{line_number} contains non-numeric raw values"
            ) from exc
        if unit_id <= 0:
            raise _C31RawSchemaMismatch(
                f"{path}:{line_number} unit_id must be positive"
            )
        if cycle_index <= 0:
            raise _C31RawSchemaMismatch(
                f"{path}:{line_number} cycle_index must be positive"
            )
        if len(settings) != _EXPECTED_SETTING_COUNT:
            raise _C31RawSchemaMismatch(f"{path}:{line_number} has bad settings")
        if len(sensors) != _EXPECTED_SENSOR_COUNT:
            raise _C31RawSchemaMismatch(f"{path}:{line_number} has bad sensors")
        if not all(math.isfinite(value) for value in (*settings, *sensors)):
            raise _C31RawSchemaMismatch(
                f"{path}:{line_number} contains non-finite raw values"
            )
        cycle_key = (unit_id, cycle_index)
        if cycle_key in seen_cycles:
            raise _C31RawSchemaMismatch(
                f"{path}:{line_number} duplicates unit_id/cycle_index"
            )
        seen_cycles.add(cycle_key)
        rows.append(
            _C31CmapssRawRow(
                subset=subset,
                file_role=file_role,
                unit_id=unit_id,
                cycle_index=cycle_index,
                settings=settings,
                sensors=sensors,
            )
        )
    if not rows:
        raise _C31RawSchemaMismatch(f"{path} has no raw rows")
    return tuple(rows)


def _parse_rul_file(path: Path) -> tuple[int, ...]:
    values: list[int] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise _C31RawSchemaMismatch(str(exc)) from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        columns = line.split()
        if len(columns) != 1:
            raise _C31RawSchemaMismatch(
                f"{path}:{line_number} expected one RUL column"
            )
        try:
            value = int(columns[0])
        except ValueError as exc:
            raise _C31RawSchemaMismatch(
                f"{path}:{line_number} contains non-integer RUL"
            ) from exc
        if value < 0:
            raise _C31RawSchemaMismatch(
                f"{path}:{line_number} RUL must be non-negative"
            )
        values.append(value)
    if not values:
        raise _C31RawSchemaMismatch(f"{path} has no RUL rows")
    return tuple(values)


def _map_cmapss_rows_to_observations(
    config: C31CmapssConfig,
) -> tuple[C31MappedObservationSummary, tuple[C31RulTarget, ...]]:
    observation_rows: list[dict[str, Any]] = []
    rul_targets: list[C31RulTarget] = []

    for subset in config.mapping_policy.subsets:
        train_rows = _parse_cmapss_data_file(
            config.download_policy.raw_dir / f"train_{subset}.txt",
            subset,
            "train",
        )
        test_rows = _parse_cmapss_data_file(
            config.download_policy.raw_dir / f"test_{subset}.txt",
            subset,
            "test",
        )
        final_test_ruls = _parse_rul_file(
            config.download_policy.raw_dir / f"RUL_{subset}.txt"
        )

        observation_rows.extend(_observation_rows_for_raw_rows(train_rows))
        observation_rows.extend(_observation_rows_for_raw_rows(test_rows))
        rul_targets.extend(_train_rul_targets(train_rows))
        rul_targets.extend(_test_rul_targets(test_rows, final_test_ruls))

    observations = pd.DataFrame(observation_rows)
    schema_result = validate_observation_frame(observations)
    trajectory_ids = tuple(sorted(observations["device_id"].unique()))
    return (
        C31MappedObservationSummary(
            observation_rows=len(observations),
            trajectory_count=len(trajectory_ids),
            trajectory_ids=trajectory_ids,
            required_schema_valid=schema_result.valid,
            pseudo_timestamp_rule=_PSEUDO_TIMESTAMP_RULE,
            uses_capped_rul=config.mapping_policy.use_capped_rul,
        ),
        tuple(rul_targets),
    )


def _observation_rows_for_raw_rows(
    raw_rows: tuple[_C31CmapssRawRow, ...],
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        trajectory_id = _trajectory_id(
            raw_row.subset,
            raw_row.file_role,
            raw_row.unit_id,
        )
        timestamp = _pseudo_timestamp_for_cycle(raw_row.cycle_index)
        degradation_label = (
            "run_to_failure_known"
            if raw_row.file_role == "train"
            else "partial_trajectory_with_rul_target"
        )
        for setting_index, value in enumerate(raw_row.settings, start=1):
            rows.append(
                _observation_row(
                    raw_row,
                    trajectory_id,
                    timestamp,
                    f"setting_{setting_index}",
                    value,
                    "operational_condition",
                    degradation_label,
                )
            )
        for sensor_index, value in enumerate(raw_row.sensors, start=1):
            rows.append(
                _observation_row(
                    raw_row,
                    trajectory_id,
                    timestamp,
                    f"sensor_{sensor_index:02d}",
                    value,
                    "turbofan_sensor",
                    degradation_label,
                )
            )
    return tuple(rows)


def _pseudo_timestamp_for_cycle(cycle_index: int) -> pd.Timestamp:
    try:
        return pd.Timestamp(_EXPECTED_PSEUDO_TIMESTAMP_START) + pd.to_timedelta(
            cycle_index,
            unit="s",
        )
    except Exception as exc:
        raise _C31RawSchemaMismatch(
            "cycle_index cannot be converted to timestamp"
        ) from exc


def _observation_row(
    raw_row: _C31CmapssRawRow,
    trajectory_id: str,
    timestamp: pd.Timestamp,
    sensor_id: str,
    value: float,
    domain: str,
    degradation_label: str,
) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "device_id": trajectory_id,
        "batch_id": trajectory_id,
        "stage": raw_row.subset,
        "sensor_id": sensor_id,
        "value": value,
        "unit": "normalized",
        "domain": domain,
        "quality_flag": "good",
        "degradation_label": degradation_label,
        "failure_proxy": False,
    }


def _train_rul_targets(
    train_rows: tuple[_C31CmapssRawRow, ...],
) -> tuple[C31RulTarget, ...]:
    last_cycle_by_unit = _last_cycle_by_unit(train_rows)
    return tuple(
        C31RulTarget(
            subset=row.subset,
            file_role=row.file_role,
            trajectory_id=_trajectory_id(row.subset, row.file_role, row.unit_id),
            unit_id=row.unit_id,
            cycle_index=row.cycle_index,
            rul=last_cycle_by_unit[row.unit_id] - row.cycle_index,
        )
        for row in train_rows
    )


def _test_rul_targets(
    test_rows: tuple[_C31CmapssRawRow, ...],
    final_test_ruls: tuple[int, ...],
) -> tuple[C31RulTarget, ...]:
    test_units = tuple(sorted({row.unit_id for row in test_rows}))
    if len(final_test_ruls) != len(test_units):
        raise _C31RawSchemaMismatch("RUL file row count must match test units")

    last_cycle_by_unit = _last_cycle_by_unit(test_rows)
    final_rul_by_unit = dict(zip(test_units, final_test_ruls, strict=True))
    return tuple(
        C31RulTarget(
            subset=row.subset,
            file_role=row.file_role,
            trajectory_id=_trajectory_id(row.subset, row.file_role, row.unit_id),
            unit_id=row.unit_id,
            cycle_index=row.cycle_index,
            rul=final_rul_by_unit[row.unit_id]
            + (last_cycle_by_unit[row.unit_id] - row.cycle_index),
        )
        for row in test_rows
    )


def _last_cycle_by_unit(rows: tuple[_C31CmapssRawRow, ...]) -> dict[int, int]:
    last_cycle_by_unit: dict[int, int] = {}
    for row in rows:
        last_cycle_by_unit[row.unit_id] = max(
            row.cycle_index,
            last_cycle_by_unit.get(row.unit_id, row.cycle_index),
        )
    return last_cycle_by_unit


def _trajectory_id(subset: str, file_role: str, unit_id: int) -> str:
    return f"cmapss_{subset}_{file_role}_unit_{unit_id}"


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
        allowed_values = {
            "license_status": _VALID_LICENSE_STATUSES,
            "redistribution_status": _VALID_REDISTRIBUTION_STATUSES,
            "training_use_status": _VALID_TRAINING_USE_STATUSES,
        }[field]
        _validate_allowed(value, allowed_values, f"license_review.{field}")

    review = C31LicenseReview(
        decision=decision,
        license_status=license_status,
        redistribution_status=redistribution_status,
        training_use_status=training_use_status,
        citation_required=_load_required_bool(
            review, "citation_required", "license_review"
        ),
    )
    _validate_license_decision_consistency(review)
    return review


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
    _validate_unique(subsets, "mapping_policy.subsets")
    for subset in subsets:
        _validate_allowed(subset, EXPECTED_CMAPSS_SUBSETS, "mapping_policy.subsets")

    file_roles = _load_required_string_list(policy, "file_roles", "mapping_policy")
    _validate_unique(file_roles, "mapping_policy.file_roles")
    for file_role in file_roles:
        _validate_allowed(
            file_role, EXPECTED_CMAPSS_FILE_ROLES, "mapping_policy.file_roles"
        )
    if file_roles != EXPECTED_CMAPSS_FILE_ROLES:
        raise C31CmapssConfigError(
            "mapping_policy.file_roles must be exactly train, test, RUL"
        )

    sensor_count = _load_required_int(policy, "sensor_count", "mapping_policy")
    if sensor_count != _EXPECTED_SENSOR_COUNT:
        raise C31CmapssConfigError(
            f"mapping_policy.sensor_count must be {_EXPECTED_SENSOR_COUNT}"
        )

    setting_count = _load_required_int(policy, "setting_count", "mapping_policy")
    if setting_count != _EXPECTED_SETTING_COUNT:
        raise C31CmapssConfigError(
            f"mapping_policy.setting_count must be {_EXPECTED_SETTING_COUNT}"
        )

    use_capped_rul = _load_required_bool(policy, "use_capped_rul", "mapping_policy")
    if use_capped_rul is not False:
        raise C31CmapssConfigError("mapping_policy.use_capped_rul must be false")

    pseudo_timestamp_start = _load_required_string(
        policy, "pseudo_timestamp_start", "mapping_policy"
    )
    if pseudo_timestamp_start != _EXPECTED_PSEUDO_TIMESTAMP_START:
        raise C31CmapssConfigError(
            "mapping_policy.pseudo_timestamp_start must be "
            f"{_EXPECTED_PSEUDO_TIMESTAMP_START}"
        )

    return C31MappingPolicy(
        subsets=subsets,
        pseudo_timestamp_start=pseudo_timestamp_start,
        file_roles=file_roles,
        sensor_count=sensor_count,
        setting_count=setting_count,
        use_capped_rul=use_capped_rul,
    )


def _load_split_policy(raw: dict[str, Any]) -> C31SplitPolicy:
    policy = _load_mapping(raw, "split_policy")
    split_unit = _load_required_string(policy, "split_unit", "split_policy")
    if split_unit != _EXPECTED_SPLIT_UNIT:
        raise C31CmapssConfigError(
            f"split_policy.split_unit must be {_EXPECTED_SPLIT_UNIT}"
        )

    validation_source = _load_required_string(
        policy, "validation_source", "split_policy"
    )
    if validation_source != _EXPECTED_VALIDATION_SOURCE:
        raise C31CmapssConfigError(
            f"split_policy.validation_source must be {_EXPECTED_VALIDATION_SOURCE}"
        )

    forbidden_leakage_modes = _load_required_string_list(
        policy, "forbidden_leakage_modes", "split_policy"
    )
    if forbidden_leakage_modes != _EXPECTED_FORBIDDEN_LEAKAGE_MODES:
        raise C31CmapssConfigError(
            "split_policy.forbidden_leakage_modes must match the C3.1 config contract"
        )

    return C31SplitPolicy(
        split_unit=split_unit,
        validation_source=validation_source,
        forbidden_leakage_modes=forbidden_leakage_modes,
    )


def _load_outputs(raw: dict[str, Any]) -> C31Outputs:
    outputs = _load_mapping(raw, "outputs")
    return C31Outputs(
        report=Path(_load_required_string(outputs, "report", "outputs")),
        processed_dir=Path(_load_required_string(outputs, "processed_dir", "outputs")),
    )


def _validate_download_policy(policy: C31DownloadPolicy, outputs: C31Outputs) -> None:
    if policy.checksum_policy != _EXPECTED_CHECKSUM_POLICY:
        raise C31CmapssConfigError(
            f"download_policy.checksum_policy must be {_EXPECTED_CHECKSUM_POLICY}"
        )
    _validate_path_within_boundary(
        policy.raw_dir, _PROTECTED_RAW_DIR, "download_policy.raw_dir"
    )
    _validate_path_within_boundary(
        policy.processed_dir,
        _PROTECTED_PROCESSED_DIR,
        "download_policy.processed_dir",
    )
    _validate_path_within_boundary(
        outputs.processed_dir,
        _PROTECTED_PROCESSED_DIR,
        "outputs.processed_dir",
    )

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


def _validate_license_decision_consistency(review: C31LicenseReview) -> None:
    if review.decision == C31LicenseDecision.APPROVED_FOR_SCHEMA_VALIDATION:
        if review.license_status != "verified":
            raise C31CmapssConfigError(
                "license_review approved_for_schema_validation requires license_status=verified"
            )
        if review.redistribution_status not in ("not_allowed", "allowed"):
            raise C31CmapssConfigError(
                "license_review approved_for_schema_validation requires explicit redistribution_status"
            )
        if review.training_use_status not in (
            "needs_review",
            "research_only",
            "allowed",
        ):
            raise C31CmapssConfigError(
                "license_review approved_for_schema_validation has unsafe training_use_status"
            )

    if review.decision == C31LicenseDecision.APPROVED_FOR_RESEARCH_TRAINING:
        if review.license_status != "verified":
            raise C31CmapssConfigError(
                "license_review approved_for_research_training requires license_status=verified"
            )
        if review.redistribution_status not in ("not_allowed", "allowed"):
            raise C31CmapssConfigError(
                "license_review approved_for_research_training requires explicit redistribution_status"
            )
        if review.training_use_status not in ("research_only", "allowed"):
            raise C31CmapssConfigError(
                "license_review approved_for_research_training requires explicit training_use_status"
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
            loaded = yaml.load(
                raw.read_text(encoding="utf-8"),
                Loader=_C31NoDuplicateKeyLoader,
            )
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


def _validate_unique(values: tuple[str, ...], field: str) -> None:
    if len(set(values)) != len(values):
        raise C31CmapssConfigError(f"{field} must not contain duplicates")


def _validate_path_within_boundary(path: Path, boundary: Path, field: str) -> None:
    if path.is_absolute() or ".." in path.parts:
        raise C31CmapssConfigError(f"{field} must be inside {boundary}")
    if path != boundary and not path.is_relative_to(boundary):
        raise C31CmapssConfigError(f"{field} must be inside {boundary}")
