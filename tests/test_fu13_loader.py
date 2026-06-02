from pathlib import Path

import pandas as pd

from b08_model_core.real_data.fu13_loader import CANONICAL_COLUMNS, assemble_fu13_observations
from b08_model_core.tasks.schema import REQUIRED_OBSERVATION_COLUMNS, validate_observation_frame


def _write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    pd.DataFrame(rows, columns=["time", "value"]).to_csv(path, index=False)


def _write_stage_data(path: Path) -> None:
    path.write_text(
        "time,stage_name\n"
        "2026-05-01T00:00:00Z,上盖关闭\n"
        "2026-05-01T00:00:05Z,溶解\n"
        "2026-05-01T00:00:10Z,浇筑\n",
        encoding="utf-8",
    )


def _write_config(path: Path, sensors_yaml: str) -> None:
    stripped_sensors = sensors_yaml.strip("\n")
    sensors_block = "[]" if sensors_yaml == "[]" else f"\n{stripped_sensors}"
    path.write_text(
        f"""
device_id: FU13
timezone_policy: UTC
stage_file: stage_data.csv
cycle_rules:
  start_stage: 上盖关闭
  required_order: [上盖关闭, 溶解, 浇筑]
  optional_stages: []
  waiting_stages: [上盖开启]
sensors: {sensors_block}
""".strip(),
        encoding="utf-8",
    )


O2_SENSOR_YAML = """
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
"""


LEAK_SENSOR_YAML = """
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
"""


TEMP_SENSOR_YAML = """
  - parameter_name: 炉温
    collector: FU13_Record
    source_tag: Temperature
    sensor_id: Temperature
    source_file: FU13_Record_Temperature.csv
    lower_limit: 0
    upper_limit: 1000
    unit: C
    domain: thermal
    scenario: furnace_temperature_monitoring
    related_stages: [溶解]
"""


def test_assemble_fu13_observations_from_multiple_sensor_files(tmp_path):
    _write_stage_data(tmp_path / "stage_data.csv")
    _write_csv(tmp_path / "FU13_Record_O2Content.csv", [("2026-05-01T00:00:06Z", -20.0)])
    _write_csv(tmp_path / "FU13_Record_LeakElec.csv", [("2026-05-01T00:00:11Z", 61.0)])

    config = tmp_path / "config.yaml"
    _write_config(config, O2_SENSOR_YAML + LEAK_SENSOR_YAML)

    observations, cycle_summary = assemble_fu13_observations(tmp_path, config)

    assert REQUIRED_OBSERVATION_COLUMNS <= set(observations.columns)
    assert validate_observation_frame(observations).valid
    assert set(observations["sensor_id"]) == {"O2Content", "LeakElec"}
    assert observations.loc[observations["sensor_id"].eq("O2Content"), "stage"].iloc[0] == "溶解"
    assert observations.loc[observations["sensor_id"].eq("LeakElec"), "quality_flag"].iloc[0] == "invalid"
    assert observations["batch_id"].iloc[0] == "cycle_0001"
    assert cycle_summary["complete_cycles"] == 1


def test_empty_sensor_csvs_are_skipped_while_another_sensor_assembles(tmp_path):
    _write_stage_data(tmp_path / "stage_data.csv")
    _write_csv(tmp_path / "FU13_Record_O2Content.csv", [])
    (tmp_path / "FU13_Record_Temperature.csv").write_bytes(b"")
    _write_csv(tmp_path / "FU13_Record_LeakElec.csv", [("2026-05-01T00:00:11Z", 12.0)])

    config = tmp_path / "config.yaml"
    _write_config(config, O2_SENSOR_YAML + TEMP_SENSOR_YAML + LEAK_SENSOR_YAML)

    observations, cycle_summary = assemble_fu13_observations(tmp_path, config)

    assert list(observations.columns) == CANONICAL_COLUMNS
    assert set(observations["sensor_id"]) == {"LeakElec"}
    assert observations["quality_flag"].iloc[0] == "good"
    assert cycle_summary["complete_cycles"] == 1


def test_empty_sensor_config_returns_empty_canonical_frame(tmp_path):
    _write_stage_data(tmp_path / "stage_data.csv")

    config = tmp_path / "config.yaml"
    _write_config(config, "[]")

    observations, cycle_summary = assemble_fu13_observations(tmp_path, config)

    assert list(observations.columns) == CANONICAL_COLUMNS
    assert observations.empty
    assert cycle_summary["complete_cycles"] == 1


def test_row_before_first_stage_has_non_null_unassigned_stage(tmp_path):
    _write_stage_data(tmp_path / "stage_data.csv")
    _write_csv(tmp_path / "FU13_Record_O2Content.csv", [("2026-04-30T23:59:59Z", -20.0)])

    config = tmp_path / "config.yaml"
    _write_config(config, O2_SENSOR_YAML)

    observations, cycle_summary = assemble_fu13_observations(tmp_path, config)

    assert observations["quality_flag"].iloc[0] == "unassigned_stage"
    assert observations["stage"].iloc[0] == "unassigned_stage"
    assert validate_observation_frame(observations).valid
    assert cycle_summary["complete_cycles"] == 1
