import pandas as pd

from b08_model_core.real_data.fu13_config import load_fu13_real_data_config
from b08_model_core.real_data.scenario_evaluation import select_scenario_observations


def _frame():
    rows = []
    ts = pd.date_range("2026-05-01", periods=6, freq="5s", tz="UTC")
    stages = ["抽真空", "溶解", "浇筑", "上盖开启", "冷却", "停机"]
    flags = ["good", "invalid", "unassigned_cycle", "good", "good", "good"]
    for i, stage in enumerate(stages):
        for sensor, scenario, domain in [
            ("LeakElec", "leak_current_monitoring", "electrical"),
            ("O2Content", "atmosphere_detection", "atmosphere"),
        ]:
            rows.append(
                {
                    "timestamp": ts[i],
                    "device_id": "FU13",
                    "batch_id": "cycle_0001" if flags[i] != "unassigned_cycle" else "unassigned_cycle",
                    "stage": stage,
                    "sensor_id": sensor,
                    "value": float(i),
                    "unit": "ma",
                    "domain": domain,
                    "quality_flag": flags[i],
                    "degradation_label": "normal",
                    "failure_proxy": False,
                }
            )
    return pd.DataFrame(rows)


def test_select_scenario_observations_uses_leakelec_related_stages():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    selected, summary = select_scenario_observations(
        _frame(),
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="all",
        stage_scope="related",
    )

    assert set(selected["sensor_id"]) == {"LeakElec"}
    assert "上盖开启" not in set(selected["stage"])
    assert "停机" not in set(selected["stage"])
    assert summary.scenario == "leak_current_monitoring"
    assert summary.sensor_ids == ["LeakElec"]
    assert summary.related_stages == ["抽真空", "氩气导入", "溶解", "测温", "浇筑", "冷却"]


def test_select_scenario_observations_can_include_waiting_stage_for_comparison():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    selected, summary = select_scenario_observations(
        _frame(),
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="all",
        stage_scope="with_waiting",
    )

    assert "上盖开启" in set(selected["stage"])
    assert summary.waiting_rows == 1


def test_select_scenario_observations_excludes_other_devices():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")
    frame = _frame()
    other_device = frame.iloc[[0]].copy()
    other_device["device_id"] = "FU14"
    other_device["value"] = 99.0
    frame = pd.concat([frame, other_device], ignore_index=True)

    selected, summary = select_scenario_observations(
        frame,
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="all",
        stage_scope="related",
    )

    assert set(selected["device_id"]) == {"FU13"}
    assert 99.0 not in set(selected["value"])
    assert summary.input_rows == len(frame)


def test_select_scenario_observations_applies_quality_modes():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    good_only, _ = select_scenario_observations(
        _frame(),
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="good_only",
        stage_scope="with_waiting",
    )
    drop_invalid, _ = select_scenario_observations(
        _frame(),
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="drop_invalid",
        stage_scope="with_waiting",
    )
    drop_unassigned, _ = select_scenario_observations(
        _frame(),
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="drop_unassigned_cycle",
        stage_scope="with_waiting",
    )

    assert set(good_only["quality_flag"]) == {"good"}
    assert "invalid" not in set(drop_invalid["quality_flag"])
    assert "unassigned_cycle" not in set(drop_unassigned["quality_flag"])


def test_drop_invalid_keeps_missing_and_reports_quality_counts():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")
    frame = _frame()
    missing_mask = (frame["sensor_id"] == "LeakElec") & (frame["stage"] == "溶解")
    frame.loc[missing_mask, "quality_flag"] = "missing"

    drop_invalid, summary = select_scenario_observations(
        frame,
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="drop_invalid",
        stage_scope="with_waiting",
    )
    good_only, _ = select_scenario_observations(
        frame,
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="good_only",
        stage_scope="with_waiting",
    )

    assert "missing" in set(drop_invalid["quality_flag"])
    assert summary.quality_counts["missing"] == 1
    assert "missing" not in set(good_only["quality_flag"])


def test_select_scenario_observations_counts_waiting_rows_after_quality_filtering():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")
    frame = _frame()
    frame.loc[frame["stage"] == "上盖开启", "quality_flag"] = "invalid"

    selected, summary = select_scenario_observations(
        frame,
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="drop_invalid",
        stage_scope="with_waiting",
    )

    assert "上盖开启" not in set(selected["stage"])
    assert summary.waiting_rows == 0
