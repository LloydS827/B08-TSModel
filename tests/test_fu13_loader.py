from pathlib import Path

import pandas as pd

from b08_model_core.real_data.fu13_loader import assemble_fu13_observations
from b08_model_core.tasks.schema import REQUIRED_OBSERVATION_COLUMNS, validate_observation_frame


def _write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    pd.DataFrame(rows, columns=["time", "value"]).to_csv(path, index=False)


def test_assemble_fu13_observations_from_multiple_sensor_files(tmp_path):
    (tmp_path / "stage_data.csv").write_text(
        "time,stage_name\n"
        "2026-05-01T00:00:00Z,上盖关闭\n"
        "2026-05-01T00:00:05Z,溶解\n"
        "2026-05-01T00:00:10Z,浇筑\n",
        encoding="utf-8",
    )
    _write_csv(tmp_path / "FU13_Record_O2Content.csv", [("2026-05-01T00:00:06Z", -20.0)])
    _write_csv(tmp_path / "FU13_Record_LeakElec.csv", [("2026-05-01T00:00:11Z", 61.0)])

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
  waiting_stages: [上盖开启]
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

    observations, cycle_summary = assemble_fu13_observations(tmp_path, config)

    assert REQUIRED_OBSERVATION_COLUMNS <= set(observations.columns)
    assert validate_observation_frame(observations).valid
    assert set(observations["sensor_id"]) == {"O2Content", "LeakElec"}
    assert observations.loc[observations["sensor_id"].eq("O2Content"), "stage"].iloc[0] == "溶解"
    assert observations.loc[observations["sensor_id"].eq("LeakElec"), "quality_flag"].iloc[0] == "invalid"
    assert observations["batch_id"].iloc[0] == "cycle_0001"
    assert cycle_summary["complete_cycles"] == 1
