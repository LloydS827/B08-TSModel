import subprocess
import sys

import numpy as np
import pandas as pd


def test_cli_assembles_and_diagnoses_fu13_real_data(tmp_path):
    (tmp_path / "stage_data.csv").write_text(
        "time,stage_name\n"
        "2026-05-01T00:00:00Z,上盖关闭\n"
        "2026-05-01T00:00:05Z,溶解\n"
        "2026-05-01T00:00:10Z,浇筑\n",
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "time": ["2026-05-01T00:00:06Z"],
            "value": [-20.0],
        }
    ).to_csv(tmp_path / "FU13_Record_O2Content.csv", index=False)
    pd.DataFrame(
        {
            "time": ["2026-05-01T00:00:11Z"],
            "value": [61.0],
        }
    ).to_csv(tmp_path / "FU13_Record_LeakElec.csv", index=False)

    config = tmp_path / "config.yaml"
    config.write_text(
        """
device_id: FU13
timezone_policy: UTC
stage_file: stage_data.csv
cycle_rules:
  start_stage: 上盖关闭
  required_order: [上盖关闭, 溶解, 浇筑]
  optional_stages: []
  waiting_stages: []
sensors:
  - parameter_name: 真空管氧含量
    collector: FU13_Record
    source_tag: O2Content
    sensor_id: O2Content
    source_file: FU13_Record_O2Content.csv
    lower_limit: -21
    upper_limit: 0
    unit: "%"
    domain: atmosphere
    scenario: atmosphere_detection
    related_stages: [溶解]
  - parameter_name: 泄漏电流
    collector: FU13_Record
    source_tag: LeakElec
    sensor_id: LeakElec
    source_file: FU13_Record_LeakElec.csv
    lower_limit: 0
    upper_limit: 60
    unit: ma
    domain: electrical
    scenario: leak_current_monitoring
    related_stages: [浇筑]
""".strip(),
        encoding="utf-8",
    )
    output_parquet = tmp_path / "fu13_observations.parquet"
    validation_report = tmp_path / "validation.md"
    diagnostics_report = tmp_path / "diagnostics.md"

    assemble = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "real-data",
            "assemble-fu13",
            "--input-dir",
            str(tmp_path),
            "--config",
            str(config),
            "--output",
            str(output_parquet),
            "--report",
            str(validation_report),
        ],
        text=True,
        capture_output=True,
    )

    assert assemble.returncode == 0, assemble.stderr
    assert output_parquet.exists()
    assert validation_report.exists()
    assert "Real FU13 Data Validation" in validation_report.read_text(encoding="utf-8")

    diagnose = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "real-data",
            "diagnose-fu13",
            "--dataset",
            str(output_parquet),
            "--config",
            str(config),
            "--output",
            str(diagnostics_report),
        ],
        text=True,
        capture_output=True,
    )

    assert diagnose.returncode == 0, diagnose.stderr
    assert diagnostics_report.exists()
    assert "Real FU13 Data Diagnostics" in diagnostics_report.read_text(encoding="utf-8")


def test_cli_forecasts_fu13_real_data_baseline(tmp_path):
    timestamps = pd.date_range("2026-05-01", periods=220, freq="5s", tz="UTC")
    rows = []
    for i, ts in enumerate(timestamps):
        stage = "溶解" if i < 110 else "浇筑"
        rows.append(
            {
                "timestamp": ts,
                "device_id": "FU13",
                "batch_id": "cycle_0001",
                "stage": stage,
                "sensor_id": "O2Content",
                "value": -20 + np.sin(i / 10),
                "unit": "%",
                "domain": "atmosphere",
                "quality_flag": "good",
                "degradation_label": "normal",
                "failure_proxy": False,
            }
        )
        rows.append(
            {
                "timestamp": ts,
                "device_id": "FU13",
                "batch_id": "cycle_0001",
                "stage": stage,
                "sensor_id": "SysSelfPressure",
                "value": 10 + np.cos(i / 10),
                "unit": "%",
                "domain": "hydraulic",
                "quality_flag": "good",
                "degradation_label": "normal",
                "failure_proxy": False,
            }
        )
    dataset = tmp_path / "real.parquet"
    pd.DataFrame(rows).to_parquet(dataset, index=False)

    config = tmp_path / "config.yaml"
    config.write_text(
        """
device_id: FU13
timezone_policy: UTC
stage_file: stage_data.csv
cycle_rules:
  start_stage: 上盖关闭
  required_order: [上盖关闭, 溶解, 浇筑]
  optional_stages: []
  waiting_stages: []
sensors:
  - parameter_name: 真空管氧含量
    collector: FU13_Record
    source_tag: O2Content
    sensor_id: O2Content
    source_file: FU13_Record_O2Content.csv
    lower_limit: -21
    upper_limit: 0
    unit: "%"
    domain: atmosphere
    scenario: atmosphere_detection
    related_stages: [溶解]
  - parameter_name: 系统自压
    collector: FU13_Record
    source_tag: SysSelfPressure
    sensor_id: SysSelfPressure
    source_file: FU13_Record_SysSelfPressure.csv
    lower_limit: 0
    upper_limit: 60
    unit: "%"
    domain: hydraulic
    scenario: hydraulic_system_detection
    related_stages: [浇筑]
""".strip(),
        encoding="utf-8",
    )
    output = tmp_path / "forecast.md"

    forecast = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "real-data",
            "forecast-fu13",
            "--dataset",
            str(dataset),
            "--config",
            str(config),
            "--output",
            str(output),
            "--model",
            "baseline",
            "--context-length",
            "32",
            "--prediction-length",
            "8",
            "--max-windows",
            "8",
            "--no-download",
        ],
        text=True,
        capture_output=True,
    )

    assert forecast.returncode == 0, forecast.stderr
    text = output.read_text(encoding="utf-8")
    assert "Real FU13 Forecasting" in text
    assert "atmosphere_detection" in text
    assert "hydraulic_system_detection" in text
