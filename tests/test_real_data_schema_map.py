from pathlib import Path

import pandas as pd

from b08_model_core.real_data.schema_map import load_schema_map, normalize_real_data_frame
from b08_model_core.real_data.validation_report import build_validation_report
from b08_model_core.tasks.schema import REQUIRED_OBSERVATION_COLUMNS, validate_observation_frame


def _write_schema_map(path: Path, source_format: str = "long") -> None:
    path.write_text(
        f"""
source_format: {source_format}
column_mapping:
  timestamp: ts
  device_id: equipment
  batch_id: lot
  stage: phase
  sensor_id: tag
  value: reading
defaults:
  quality_flag: good
  degradation_label: normal
  failure_proxy: false
stage_map:
  vacuum: 抽真空
  cooling: 冷却
sensors:
  - source: p1
    sensor_id: PumpShake1
    domain: mechanical
    unit: mm/s
  - source: o2
    sensor_id: OutletOxygen
    domain: atmosphere
    unit: percent
""".strip(),
        encoding="utf-8",
    )


def test_long_real_data_map_normalizes_to_observation_schema(tmp_path):
    schema_path = tmp_path / "schema.yaml"
    _write_schema_map(schema_path)
    raw = pd.DataFrame(
        {
            "ts": ["2026-01-01 00:00:00", "2026-01-01 00:00:05"],
            "equipment": ["FU13", "FU13"],
            "lot": ["B001", "B001"],
            "phase": ["vacuum", "cooling"],
            "tag": ["p1", "o2"],
            "reading": [1.2, 0.08],
        }
    )

    normalized = normalize_real_data_frame(raw, load_schema_map(schema_path))

    assert REQUIRED_OBSERVATION_COLUMNS <= set(normalized.columns)
    assert set(normalized["stage"]) == {"抽真空", "冷却"}
    assert set(normalized["sensor_id"]) == {"PumpShake1", "OutletOxygen"}
    assert set(normalized["domain"]) == {"mechanical", "atmosphere"}
    assert validate_observation_frame(normalized).valid


def test_wide_real_data_map_normalizes_sensor_columns(tmp_path):
    schema_path = tmp_path / "schema.yaml"
    _write_schema_map(schema_path, source_format="wide")
    raw = pd.DataFrame(
        {
            "ts": ["2026-01-01 00:00:00"],
            "equipment": ["FU13"],
            "lot": ["B001"],
            "phase": ["vacuum"],
            "p1": [1.4],
            "o2": [0.12],
        }
    )

    normalized = normalize_real_data_frame(raw, load_schema_map(schema_path))

    assert len(normalized) == 2
    assert set(normalized["sensor_id"]) == {"PumpShake1", "OutletOxygen"}
    assert set(normalized["value"]) == {1.4, 0.12}


def test_validation_report_flags_missing_wide_sensor_columns(tmp_path):
    schema_path = tmp_path / "schema.yaml"
    _write_schema_map(schema_path, source_format="wide")
    raw = pd.DataFrame(
        {
            "ts": ["2026-01-01 00:00:00"],
            "equipment": ["FU13"],
            "lot": ["B001"],
            "phase": ["vacuum"],
            "p1": [1.4],
        }
    )

    report, _ = build_validation_report(raw, load_schema_map(schema_path))

    assert report.schema_valid is False
    assert report.missing_sensor_columns == {"o2"}


def test_validation_report_flags_common_real_data_mapping_errors(tmp_path):
    schema_path = tmp_path / "schema.yaml"
    _write_schema_map(schema_path)
    raw = pd.DataFrame(
        {
            "ts": ["bad timestamp", "2026-01-01 00:00:00", "2026-01-01 00:00:00"],
            "equipment": ["FU13", "FU13", "FU13"],
            "lot": ["B001", "B001", "B001"],
            "phase": ["unknown_stage", "vacuum", "vacuum"],
            "tag": ["unknown_tag", "p1", "p1"],
            "reading": ["oops", 1.2, 1.2],
        }
    )

    report, _ = build_validation_report(raw, load_schema_map(schema_path))

    assert report.schema_valid is False
    assert report.timestamp_parse_errors == 1
    assert report.non_numeric_values == 1
    assert report.duplicate_points == 1
    assert report.unknown_sensors == {"unknown_tag"}
    assert report.unmapped_stages == {"unknown_stage"}


def test_validation_report_flags_missing_required_source_columns(tmp_path):
    schema_path = tmp_path / "schema.yaml"
    _write_schema_map(schema_path)
    raw = pd.DataFrame(
        {
            "ts": ["2026-01-01 00:00:00"],
            "equipment": ["FU13"],
            "lot": ["B001"],
            "phase": ["vacuum"],
            "tag": ["p1"],
        }
    )

    report, normalized = build_validation_report(raw, load_schema_map(schema_path))

    assert report.schema_valid is False
    assert report.missing_columns == {"value"}
    assert normalized["value"].isna().all()
