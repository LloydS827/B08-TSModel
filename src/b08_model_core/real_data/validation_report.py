from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from b08_model_core.real_data.schema_map import RealDataSchemaMap, load_schema_map, normalize_real_data_frame
from b08_model_core.tasks.schema import validate_observation_frame


@dataclass(frozen=True)
class RealDataValidationReport:
    schema_valid: bool
    rows: int
    sensors: int
    stages: int
    missing_columns: set[str]
    missing_sensor_columns: set[str]
    unexpected_null_columns: set[str]
    unknown_sensors: set[str]
    unmapped_stages: set[str]
    timestamp_parse_errors: int
    non_numeric_values: int
    duplicate_points: int
    missing_values: int


def read_real_data(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        return pd.read_csv(source)
    if source.suffix.lower() == ".parquet":
        return pd.read_parquet(source)
    raise ValueError(f"unsupported real-data format: {source.suffix}")


def _unknown_sensors(raw_df: pd.DataFrame, schema_map: RealDataSchemaMap) -> set[str]:
    known = set(schema_map.sensor_by_source)
    if schema_map.source_format == "long":
        source_col = schema_map.column_mapping.get("sensor_id")
        if not source_col or source_col not in raw_df.columns:
            return set()
        return set(map(str, raw_df[source_col].dropna().unique())) - known
    id_cols = set(schema_map.column_mapping.values())
    source_cols = set(raw_df.columns) - id_cols
    return source_cols - known


def _missing_mapped_columns(raw_df: pd.DataFrame, schema_map: RealDataSchemaMap) -> set[str]:
    if schema_map.source_format == "long":
        required = {"timestamp", "device_id", "batch_id", "stage", "sensor_id", "value"}
        return {
            canonical
            for canonical in required
            if not schema_map.column_mapping.get(canonical) or schema_map.column_mapping[canonical] not in raw_df.columns
        }

    required = {"timestamp", "device_id", "batch_id", "stage"}
    missing = {
        canonical
        for canonical in required
        if not schema_map.column_mapping.get(canonical) or schema_map.column_mapping[canonical] not in raw_df.columns
    }
    if not any(sensor.source in raw_df.columns for sensor in schema_map.sensors):
        missing |= {"sensor_id", "value"}
    return missing


def _missing_sensor_columns(raw_df: pd.DataFrame, schema_map: RealDataSchemaMap) -> set[str]:
    if schema_map.source_format != "wide":
        return set()
    return {sensor.source for sensor in schema_map.sensors if sensor.source not in raw_df.columns}


def _unmapped_stages(raw_df: pd.DataFrame, schema_map: RealDataSchemaMap) -> set[str]:
    source_col = schema_map.column_mapping.get("stage")
    if not source_col or source_col not in raw_df.columns:
        return set()
    known = set(schema_map.stage_map) | set(schema_map.stage_map.values())
    return set(map(str, raw_df[source_col].dropna().unique())) - known


def _parse_error_count(raw_df: pd.DataFrame, schema_map: RealDataSchemaMap) -> int:
    source_col = schema_map.column_mapping.get("timestamp")
    if not source_col or source_col not in raw_df.columns:
        return 0
    parsed = pd.to_datetime(raw_df[source_col], errors="coerce", format="mixed")
    return int(parsed.isna().sum())


def _non_numeric_count(raw_df: pd.DataFrame, schema_map: RealDataSchemaMap) -> int:
    if schema_map.source_format == "long":
        source_col = schema_map.column_mapping.get("value")
        if not source_col or source_col not in raw_df.columns:
            return 0
        parsed = pd.to_numeric(raw_df[source_col], errors="coerce")
        return int(parsed.isna().sum())
    sensor_cols = [sensor.source for sensor in schema_map.sensors if sensor.source in raw_df.columns]
    if not sensor_cols:
        return 0
    parsed = raw_df[sensor_cols].apply(pd.to_numeric, errors="coerce")
    return int(parsed.isna().sum().sum())


def build_validation_report(raw_df: pd.DataFrame, schema_map: RealDataSchemaMap) -> tuple[RealDataValidationReport, pd.DataFrame]:
    normalized = normalize_real_data_frame(raw_df, schema_map)
    result = validate_observation_frame(normalized)
    missing_columns = result.missing_columns | _missing_mapped_columns(raw_df, schema_map)
    missing_sensor_columns = _missing_sensor_columns(raw_df, schema_map)
    duplicate_subset = ["timestamp", "device_id", "batch_id", "stage", "sensor_id"]
    duplicate_points = int(normalized.duplicated(subset=duplicate_subset).sum())
    unknown_sensors = _unknown_sensors(raw_df, schema_map)
    unmapped_stages = _unmapped_stages(raw_df, schema_map)
    timestamp_parse_errors = _parse_error_count(raw_df, schema_map)
    non_numeric_values = _non_numeric_count(raw_df, schema_map)
    missing_values = int(normalized["value"].isna().sum())
    schema_valid = (
        result.valid
        and not missing_columns
        and not missing_sensor_columns
        and not unknown_sensors
        and not unmapped_stages
        and timestamp_parse_errors == 0
        and non_numeric_values == 0
        and duplicate_points == 0
        and missing_values == 0
    )
    report = RealDataValidationReport(
        schema_valid=schema_valid,
        rows=len(normalized),
        sensors=normalized["sensor_id"].nunique(),
        stages=normalized["stage"].nunique(),
        missing_columns=missing_columns,
        missing_sensor_columns=missing_sensor_columns,
        unexpected_null_columns=result.unexpected_null_columns,
        unknown_sensors=unknown_sensors,
        unmapped_stages=unmapped_stages,
        timestamp_parse_errors=timestamp_parse_errors,
        non_numeric_values=non_numeric_values,
        duplicate_points=duplicate_points,
        missing_values=missing_values,
    )
    return report, normalized


def render_validation_report(report: RealDataValidationReport, normalized: pd.DataFrame) -> str:
    sensors = ", ".join(sorted(map(str, normalized["sensor_id"].dropna().unique())))
    stages = ", ".join(sorted(map(str, normalized["stage"].dropna().unique())))
    return "\n".join(
        [
            "# Real Data Validation",
            "",
            f"- schema_valid: {report.schema_valid}",
            f"- rows: {report.rows}",
            f"- sensor coverage: {report.sensors} sensors ({sensors})",
            f"- stage coverage: {report.stages} stages ({stages})",
            f"- missing_columns: {sorted(report.missing_columns)}",
            f"- missing_sensor_columns: {sorted(report.missing_sensor_columns)}",
            f"- unexpected_null_columns: {sorted(report.unexpected_null_columns)}",
            f"- unknown_sensors: {sorted(report.unknown_sensors)}",
            f"- unmapped_stages: {sorted(report.unmapped_stages)}",
            f"- timestamp_parse_errors: {report.timestamp_parse_errors}",
            f"- non_numeric_values: {report.non_numeric_values}",
            f"- duplicate_points: {report.duplicate_points}",
            f"- missing_values: {report.missing_values}",
        ]
    ) + "\n"


def validate_real_data_file(input_path: str | Path, schema_map_path: str | Path, output_path: str | Path) -> RealDataValidationReport:
    schema_map = load_schema_map(schema_map_path)
    raw = read_real_data(input_path)
    report, normalized = build_validation_report(raw, schema_map)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_validation_report(report, normalized), encoding="utf-8")
    return report
