from pathlib import Path

from b08_model_core.real_data.fu13_config import load_fu13_real_data_config


def test_load_fu13_real_data_config_maps_all_sensors():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    assert cfg.device_id == "FU13"
    assert cfg.timezone_policy == "UTC"
    assert cfg.stage_file == "stage_data.csv"
    assert len(cfg.sensors) == 8
    assert {sensor.sensor_id for sensor in cfg.sensors} == {
        "O2Content2",
        "CrucibleForwardPressure",
        "CrucibleReturnPressure",
        "PumpShake1",
        "PumpShake2",
        "LeakElec",
        "O2Content",
        "SysSelfPressure",
    }
    assert cfg.sensor_by_id["O2Content"].domain == "atmosphere"
    assert cfg.sensor_by_id["LeakElec"].scenario == "leak_current_monitoring"
    assert (
        Path(cfg.sensor_by_id["PumpShake1"].source_file).name
        == "FU13_Pump_01_PumpShake1.csv"
    )
