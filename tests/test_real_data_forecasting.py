import numpy as np
import pandas as pd

from b08_model_core.real_data.forecasting import (
    render_real_data_forecasting_report,
    run_real_data_forecasting,
)


def _dataset(path):
    timestamps = pd.date_range("2026-05-01", periods=220, freq="5s", tz="UTC")
    rows = []
    for i, ts in enumerate(timestamps):
        stage = "溶解" if i < 110 else "浇筑"
        for sensor, domain, scenario, value in [
            ("O2Content", "atmosphere", "atmosphere_detection", -20 + np.sin(i / 10)),
            ("SysSelfPressure", "hydraulic", "hydraulic_system_detection", 10 + np.cos(i / 10)),
        ]:
            rows.append(
                {
                    "timestamp": ts,
                    "device_id": "FU13",
                    "batch_id": "cycle_0001",
                    "stage": stage,
                    "sensor_id": sensor,
                    "value": value,
                    "unit": "%",
                    "domain": domain,
                    "quality_flag": "good",
                    "degradation_label": "normal",
                    "failure_proxy": False,
                }
            )
    pd.DataFrame(rows).to_parquet(path, index=False)


def test_real_data_forecasting_baseline_report_breaks_down_metrics(tmp_path):
    dataset = tmp_path / "real.parquet"
    _dataset(dataset)

    result = run_real_data_forecasting(
        dataset,
        model="baseline",
        window_mode="cross-stage",
        context_length=32,
        prediction_length=8,
        max_windows=8,
        allow_download=False,
        model_cache_dir=None,
        sensor_scenario={
            "O2Content": "atmosphere_detection",
            "SysSelfPressure": "hydraulic_system_detection",
        },
    )
    text = render_real_data_forecasting_report(result)

    assert "Real FU13 Forecasting" in text
    assert "window_mode: cross-stage" in text
    assert "O2Content" in text
    assert "SysSelfPressure" in text
    assert "atmosphere_detection" in text
    assert "hydraulic_system_detection" in text
    assert result.sensor_metrics["O2Content"]["count"] == 24
    assert result.scenario_metrics["atmosphere_detection"]["count"] == 24


def test_real_data_forecasting_ttm_missing_dependency_is_reported(tmp_path):
    dataset = tmp_path / "real.parquet"
    _dataset(dataset)

    result = run_real_data_forecasting(
        dataset,
        model="ttm",
        window_mode="cross-stage",
        context_length=32,
        prediction_length=8,
        max_windows=8,
        allow_download=False,
        model_cache_dir=None,
        dependency_checker=lambda name: False,
        sensor_scenario={
            "O2Content": "atmosphere_detection",
            "SysSelfPressure": "hydraulic_system_detection",
        },
    )
    text = render_real_data_forecasting_report(result)

    assert "model: TTM" in text
    assert "missing_dependency" in text
    assert "Baseline Comparison" in text
    assert "grouped_metrics_source: RobustStageForecaster fallback" in text


def test_real_data_forecasting_report_escapes_markdown_metric_labels(tmp_path):
    timestamps = pd.date_range("2026-05-01", periods=220, freq="5s", tz="UTC")
    rows = []
    for i, ts in enumerate(timestamps):
        for sensor, domain, value in [
            ("Pipe|Sensor\nOne", "unsafe|domain", -20 + np.sin(i / 10)),
            ("PlainSensor", "plain", 10 + np.cos(i / 10)),
        ]:
            rows.append(
                {
                    "timestamp": ts,
                    "device_id": "FU13",
                    "batch_id": "cycle_0001",
                    "stage": "溶解",
                    "sensor_id": sensor,
                    "value": value,
                    "unit": "%",
                    "domain": domain,
                    "quality_flag": "good",
                    "degradation_label": "normal",
                    "failure_proxy": False,
                }
            )
    dataset = tmp_path / "unsafe.parquet"
    pd.DataFrame(rows).to_parquet(dataset, index=False)

    result = run_real_data_forecasting(
        dataset,
        model="baseline",
        window_mode="cross-stage",
        context_length=32,
        prediction_length=8,
        max_windows=8,
        allow_download=False,
        model_cache_dir=None,
        sensor_scenario={"Pipe|Sensor\nOne": "scenario|alpha\nbeta"},
    )
    text = render_real_data_forecasting_report(result)

    assert result.sensor_metrics["Pipe|Sensor\nOne"]["count"] == 24
    assert result.scenario_metrics["scenario|alpha\nbeta"]["count"] == 24
    assert "Pipe\\|Sensor One" in text
    assert "scenario\\|alpha beta" in text
    assert "Pipe|Sensor\nOne" not in text
    assert "scenario|alpha\nbeta" not in text
