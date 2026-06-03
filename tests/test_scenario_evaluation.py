import numpy as np
import pandas as pd

from b08_model_core.foundation import FoundationForecastResult, FoundationModelStatus
from b08_model_core.real_data.fu13_config import load_fu13_real_data_config
from b08_model_core.real_data.scenario_evaluation import (
    render_scenario_evaluation_report,
    run_scenario_evaluation,
    select_scenario_observations,
)


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


def _long_leak_frame(path):
    timestamps = pd.date_range("2026-05-01", periods=220, freq="5s", tz="UTC")
    rows = []
    for i, ts in enumerate(timestamps):
        stage = "溶解" if i < 110 else "浇筑"
        value = 10 + np.sin(i / 8)
        if i in {150, 151, 152}:
            value += 15
        rows.append(
            {
                "timestamp": ts,
                "device_id": "FU13",
                "batch_id": "cycle_0001",
                "stage": stage,
                "sensor_id": "LeakElec",
                "value": value,
                "unit": "ma",
                "domain": "electrical",
                "quality_flag": "good",
                "degradation_label": "normal",
                "failure_proxy": False,
            }
        )
    pd.DataFrame(rows).to_parquet(path, index=False)


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


def test_run_scenario_evaluation_reports_rolling_baseline_and_candidate_signals(tmp_path):
    dataset = tmp_path / "leak.parquet"
    _long_leak_frame(dataset)
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    result = run_scenario_evaluation(
        dataset,
        cfg,
        scenario="leak_current_monitoring",
        model="baseline",
        quality_modes=["good_only"],
        stage_scopes=["related"],
        context_length=32,
        prediction_length=8,
        max_windows=8,
        rolling_window_size=4,
        allow_download=False,
        model_cache_dir=None,
    )
    text = render_scenario_evaluation_report(result)

    assert result.scenario == "leak_current_monitoring"
    assert result.model == "BaselineOnly"
    assert "RollingSensorForecaster" in result.runs[0].metrics
    assert "candidate residual signals" in text
    assert "candidate_signal_source" in text
    assert "not a failure prediction" in text
    assert "候选异常信号" in text
    assert "residual_mae" in text
    assert "residual_rmse" in text
    assert "top_window_stage_summary" in text
    assert "within-run empirical residual distribution" in text
    assert "context window only" in text
    assert result.runs[0].candidate_signal["candidate_signal_source"] == "RollingSensorForecaster"
    assert result.runs[0].candidate_signal["abs_residual_p95"] >= 0
    assert result.runs[0].candidate_signal["residual_mae"] >= 0
    assert result.runs[0].candidate_signal["residual_rmse"] >= 0
    assert result.runs[0].candidate_signal["top_windows"]


def test_run_scenario_evaluation_reports_not_enough_windows(tmp_path):
    dataset = tmp_path / "short.parquet"
    timestamps = pd.date_range("2026-05-01", periods=20, freq="5s", tz="UTC")
    pd.DataFrame(
        [
            {
                "timestamp": ts,
                "device_id": "FU13",
                "batch_id": "cycle_0001",
                "stage": "溶解",
                "sensor_id": "LeakElec",
                "value": float(i),
                "unit": "ma",
                "domain": "electrical",
                "quality_flag": "good",
                "degradation_label": "normal",
                "failure_proxy": False,
            }
            for i, ts in enumerate(timestamps)
        ]
    ).to_parquet(dataset, index=False)
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    result = run_scenario_evaluation(
        dataset,
        cfg,
        scenario="leak_current_monitoring",
        model="baseline",
        quality_modes=["good_only"],
        stage_scopes=["related"],
        context_length=32,
        prediction_length=8,
        max_windows=8,
        rolling_window_size=4,
        allow_download=False,
        model_cache_dir=None,
    )

    assert result.runs[0].candidate_signal["status"] == "not_enough_windows"
    assert result.runs[0].test_windows == 0


def test_run_scenario_evaluation_reports_ttm_failure_rolling_fallback(tmp_path, monkeypatch):
    class FakeTTMForecastAdapter:
        name = "TTM"

        def predict(
            self,
            windows,
            *,
            context_length,
            prediction_length,
            allow_download,
            model_cache_dir,
        ):
            return FoundationForecastResult(
                model_name="TTM",
                adapter_name="ttm",
                status=FoundationModelStatus.RUNTIME_FAILED,
                reason="forced failure",
                dependency_status="installed",
                weight_status="available",
            )

    monkeypatch.setattr(
        "b08_model_core.real_data.scenario_evaluation.TTMForecastAdapter",
        FakeTTMForecastAdapter,
    )
    dataset = tmp_path / "leak.parquet"
    _long_leak_frame(dataset)
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    result = run_scenario_evaluation(
        dataset,
        cfg,
        scenario="leak_current_monitoring",
        model="ttm",
        quality_modes=["good_only"],
        stage_scopes=["related"],
        context_length=32,
        prediction_length=8,
        max_windows=8,
        rolling_window_size=4,
        allow_download=False,
        model_cache_dir=None,
    )
    report = render_scenario_evaluation_report(result)
    run = result.runs[0]

    assert result.model == "TTM"
    assert run.foundation_result.status is FoundationModelStatus.RUNTIME_FAILED
    assert "runtime_failed" in report
    assert "forced failure" in report
    assert run.candidate_signal["candidate_signal_source"] == "RollingSensorForecaster"
    assert "rolling fallback used" in report
