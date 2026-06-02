import pandas as pd

from b08_model_core.real_data.diagnostics import build_fu13_diagnostics, render_fu13_diagnostics
from b08_model_core.real_data.fu13_config import FU13CycleRules, FU13RealDataConfig, FU13SensorConfig


def _cfg():
    sensors = [
        FU13SensorConfig(parameter_name="氧1", collector="c", source_tag="O2Content", sensor_id="O2Content", source_file="o2.csv", lower_limit=-21, upper_limit=0, unit="%", domain="atmosphere", scenario="atmosphere_detection", related_stages=["溶解"]),
        FU13SensorConfig(parameter_name="氧2", collector="c", source_tag="O2Content2", sensor_id="O2Content2", source_file="o22.csv", lower_limit=-21, upper_limit=0, unit="%", domain="atmosphere", scenario="atmosphere_detection", related_stages=["浇筑"]),
        FU13SensorConfig(parameter_name="振动", collector="c", source_tag="PumpShake1", sensor_id="PumpShake1", source_file="p.csv", lower_limit=0, upper_limit=10, unit="um", domain="mechanical", scenario="pump_vibration", related_stages=["抽真空"]),
        FU13SensorConfig(parameter_name="压力", collector="c", source_tag="SysSelfPressure", sensor_id="SysSelfPressure", source_file="s.csv", lower_limit=0, upper_limit=15, unit="MPa", domain="hydraulic", scenario="hydraulic_system_detection", related_stages=["浇筑"]),
        FU13SensorConfig(parameter_name="电流", collector="c", source_tag="LeakElec", sensor_id="LeakElec", source_file="l.csv", lower_limit=0, upper_limit=60, unit="ma", domain="electrical", scenario="leak_current_monitoring", related_stages=["溶解"]),
    ]
    return FU13RealDataConfig(
        device_id="FU13",
        timezone_policy="UTC",
        stage_file="stage_data.csv",
        cycle_rules=FU13CycleRules(start_stage="上盖关闭", required_order=["上盖关闭", "溶解", "浇筑"]),
        sensors=sensors,
    )


def test_render_fu13_diagnostics_mentions_scenarios_and_quality():
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-05-01T00:00:00Z"] * 6, utc=True),
            "device_id": ["FU13"] * 6,
            "batch_id": ["cycle_0001"] * 6,
            "stage": ["溶解", "浇筑", "抽真空", "浇筑", "溶解", "line\nbreak"],
            "sensor_id": ["O2Content", "O2Content2", "PumpShake1", "SysSelfPressure", "LeakElec", "x|y"],
            "value": [-20, -19, 4, 14, 61, 7],
            "unit": ["%", "%", "um", "MPa", "ma", "C"],
            "domain": ["atmosphere", "atmosphere", "mechanical", "hydraulic", "electrical", "unknown"],
            "quality_flag": ["good", "good", "good", "good", "invalid", "invalid"],
            "degradation_label": ["normal"] * 6,
            "failure_proxy": [False] * 6,
        }
    )

    report = build_fu13_diagnostics(df, _cfg())
    text = render_fu13_diagnostics(report)
    scenario_rows = report.scenario_summary.set_index("scenario")

    assert "Real FU13 Data Diagnostics" in text
    assert report.quality_counts == {"good": 4, "invalid": 2}
    assert scenario_rows.loc["leak_current_monitoring", "invalid_rows"] == 1
    assert scenario_rows.loc["unmapped_sensor", "rows"] == 1
    assert scenario_rows.loc["unmapped_sensor", "invalid_rows"] == 1
    assert "atmosphere_detection" in text
    assert "pump_vibration" in text
    assert "hydraulic_system_detection" in text
    assert "leak_current_monitoring" in text
    assert "unmapped_sensor" in text
    assert "x\\|y" in text
    assert "line break" in text
    assert "line\nbreak" not in text
