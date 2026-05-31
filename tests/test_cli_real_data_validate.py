import subprocess
import sys

import pandas as pd


def test_cli_validates_real_data_export(tmp_path):
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        """
source_format: long
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
sensors:
  - source: p1
    sensor_id: PumpShake1
    domain: mechanical
    unit: mm/s
""".strip(),
        encoding="utf-8",
    )
    raw = tmp_path / "raw.csv"
    pd.DataFrame(
        {
            "ts": ["2026-01-01 00:00:00"],
            "equipment": ["FU13"],
            "lot": ["B001"],
            "phase": ["vacuum"],
            "tag": ["p1"],
            "reading": [1.2],
        }
    ).to_csv(raw, index=False)
    report = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "real-data",
            "validate",
            "--input",
            str(raw),
            "--schema-map",
            str(schema),
            "--output",
            str(report),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    text = report.read_text(encoding="utf-8")
    assert "Real Data Validation" in text
    assert "schema_valid" in text
    assert "rows" in text
    assert "sensor coverage" in text
    assert "stage coverage" in text


def test_cli_invalid_real_data_returns_nonzero_but_writes_report(tmp_path):
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        """
source_format: long
column_mapping:
  timestamp: ts
  device_id: equipment
  batch_id: lot
  stage: phase
  sensor_id: tag
  value: reading
stage_map:
  vacuum: 抽真空
sensors:
  - source: p1
    sensor_id: PumpShake1
    domain: mechanical
    unit: mm/s
""".strip(),
        encoding="utf-8",
    )
    raw = tmp_path / "raw.csv"
    pd.DataFrame(
        {
            "ts": ["not a timestamp"],
            "equipment": ["FU13"],
            "lot": ["B001"],
            "phase": ["unknown"],
            "tag": ["missing_tag"],
            "reading": ["bad number"],
        }
    ).to_csv(raw, index=False)
    report = tmp_path / "invalid_report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "real-data",
            "validate",
            "--input",
            str(raw),
            "--schema-map",
            str(schema),
            "--output",
            str(report),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    text = report.read_text(encoding="utf-8")
    assert "schema_valid: False" in text
    assert "unknown_sensors" in text
    assert "unmapped_stages" in text
    assert "missing_sensor_columns" in text
    assert "non_numeric_values" in text
