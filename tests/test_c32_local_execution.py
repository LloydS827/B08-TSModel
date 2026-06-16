from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from b08_model_core.cli import main
from b08_model_core.evaluation.metrics import (
    forecasting_residual_ranking,
    nasa_rul_score,
    rul_regression_metrics,
)
from b08_model_core.experiments.c31_cmapss_minimal_ingestion import (
    C31RawSchemaMismatch,
    load_cmapss_rul_baseline_dataset,
)
from b08_model_core.experiments.c32_open_model_cross_dataset_evaluation import (
    load_c32_config,
    render_c32_report,
    run_c32_open_model_cross_dataset_evaluation,
)


def test_rul_regression_metrics_include_nasa_score():
    truth = np.array([10.0, 20.0, 30.0])
    prediction = np.array([12.0, 18.0, 30.0])

    metrics = rul_regression_metrics(prediction, truth)

    assert metrics["mae"] == 4.0 / 3.0
    assert metrics["rmse"] == math.sqrt(8.0 / 3.0)
    assert metrics["nasa_score"] == nasa_rul_score(prediction, truth)
    assert metrics["count"] == 3


def test_forecasting_residual_ranking_groups_by_sensor():
    truth = np.zeros((2, 2, 3))
    prediction = np.array(
        [
            [[1.0, 0.0, 3.0], [1.0, 0.0, 3.0]],
            [[2.0, 0.0, 1.0], [2.0, 0.0, 1.0]],
        ]
    )

    ranking = forecasting_residual_ranking(
        {"y_hat": prediction},
        truth,
        ["s1", "s2", "s3"],
        top_k=2,
    )

    assert ranking == (
        {"rank": 1, "sensor_id": "s3", "mean_abs_residual": 2.0},
        {"rank": 2, "sensor_id": "s1", "mean_abs_residual": 1.5},
    )


def _write_fd001_fixture(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True)
    train_rows = [
        "1 1 0 0 0 " + " ".join(["1"] * 21),
        "1 2 0 0 0 " + " ".join(["1"] * 21),
        "1 3 0 0 0 " + " ".join(["1"] * 21),
        "2 1 0 0 0 " + " ".join(["2"] * 21),
        "2 2 0 0 0 " + " ".join(["2"] * 21),
    ]
    test_rows = [
        "1 1 0 0 0 " + " ".join(["3"] * 21),
        "1 2 0 0 0 " + " ".join(["3"] * 21),
        "2 1 0 0 0 " + " ".join(["4"] * 21),
    ]
    (raw_dir / "train_FD001.txt").write_text(
        "\n".join(train_rows) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "test_FD001.txt").write_text(
        "\n".join(test_rows) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "RUL_FD001.txt").write_text("7\n5\n", encoding="utf-8")


def test_load_cmapss_rul_baseline_dataset_from_local_raw(tmp_path):
    raw_dir = tmp_path / "data/public/cmapss/raw"
    _write_fd001_fixture(raw_dir)

    dataset = load_cmapss_rul_baseline_dataset(raw_dir, subsets=("FD001",))

    assert dataset.subsets == ("FD001",)
    assert len(dataset.train_records) == 5
    assert len(dataset.test_final_records) == 2
    assert dataset.test_final_records[0].rul == 7
    assert dataset.test_final_records[1].rul == 5


def test_load_cmapss_rul_baseline_dataset_reports_schema_mismatch(tmp_path):
    raw_dir = tmp_path / "data/public/cmapss/raw"
    _write_fd001_fixture(raw_dir)
    (raw_dir / "train_FD001.txt").write_text("1 1 0\n", encoding="utf-8")

    with pytest.raises(C31RawSchemaMismatch, match="expected 26 columns"):
        load_cmapss_rul_baseline_dataset(raw_dir, subsets=("FD001",))


def _c32_fd001_local_config(tmp_path: Path) -> Path:
    source = Path("configs/local/c_stage_c32_explicit_local_execution.example.yaml")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    raw_dir = tmp_path / "data/public/cmapss/raw"
    data["local_execution"]["cmapss"]["raw_dir"] = str(raw_dir)
    data["local_execution"]["cmapss"]["subsets"] = ["FD001"]
    path = tmp_path / "c32_fd001.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    _write_fd001_fixture(raw_dir)
    return path


def test_c32_local_execution_runs_rul_and_forecasting_reference(tmp_path):
    config_path = _c32_fd001_local_config(tmp_path)
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(
        config,
        config_path=config_path,
    )

    assert result.status == "local_execution_baseline_reference_ready"
    assert result.rul_baseline_result is not None
    assert result.rul_baseline_result.overall_metrics["subset_count"] == 1
    assert result.rul_baseline_result.overall_metrics["count"] == 2
    assert result.forecasting_reference_result is not None
    assert set(result.forecasting_reference_result.baseline_metrics) == {
        "RobustStageForecaster",
        "StageSeasonalNaiveForecaster",
    }
    assert result.local_metric_summary is not None
    for metric in (
        *config.metric_contract.rul_metrics,
        *config.metric_contract.forecasting_metrics,
    ):
        assert metric in result.local_metric_summary
    text = render_c32_report(result)
    assert "C-MAPSS RUL Baseline Evaluation" in text
    assert "FU13-like Forecasting Reference" in text
    assert "Local Metric Summary" in text
    assert "Separated Metric Interpretation" in text
    assert "Leaderboard allowed: False" in text


def test_c32_local_execution_rul_baseline_uses_deterministic_progress_profile(
    tmp_path,
):
    config_path = _c32_fd001_local_config(tmp_path)
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(
        config,
        config_path=config_path,
    )

    assert result.rul_baseline_result is not None
    subset = result.rul_baseline_result.subset_metrics[0]
    assert subset.subset == "FD001"
    assert subset.predictions == (1.0, 2.0)
    assert subset.truth == (7.0, 5.0)
    assert subset.metrics["mae"] == 4.5
    assert subset.metrics["rmse"] == math.sqrt(22.5)
    expected_nasa = (math.exp(6.0 / 13.0) - 1.0) + (
        math.exp(3.0 / 13.0) - 1.0
    )
    assert subset.metrics["nasa_score"] == pytest.approx(expected_nasa)
    assert result.rul_baseline_result.overall_metrics["mae"] == 4.5
    assert result.rul_baseline_result.overall_metrics["rmse"] == math.sqrt(22.5)
    assert result.rul_baseline_result.overall_metrics["nasa_score"] == pytest.approx(
        expected_nasa
    )


def test_c32_local_execution_blocks_when_raw_missing(tmp_path):
    config_path = _c32_fd001_local_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    missing_dir = tmp_path / "data/public/cmapss/missing"
    data["local_execution"]["cmapss"]["raw_dir"] = str(missing_dir)
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(
        config,
        config_path=config_path,
    )

    assert result.status == "blocked_missing_cmapss_raw"
    assert result.rul_baseline_result is None


def test_c32_local_execution_blocks_on_raw_schema_mismatch(tmp_path):
    config_path = _c32_fd001_local_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw_dir = Path(data["local_execution"]["cmapss"]["raw_dir"])
    (raw_dir / "train_FD001.txt").write_text("1 1 0\n", encoding="utf-8")
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(
        config,
        config_path=config_path,
    )

    assert result.status == "blocked_cmapss_raw_schema_mismatch"
    assert "expected 26 columns" in result.local_execution_blocked_reason
    assert result.rul_baseline_result is None


def test_c32_local_execution_blocks_when_fu13_like_windows_are_insufficient(
    tmp_path,
):
    config_path = _c32_fd001_local_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["local_execution"]["fu13_like"]["days"] = 1
    data["local_execution"]["fu13_like"]["context_length"] = 100000
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(
        config,
        config_path=config_path,
    )

    assert result.status == "blocked_insufficient_fu13_like_windows"
    assert result.forecasting_reference_result is None


def test_c32_local_execution_does_not_import_open_model_adapters(
    tmp_path,
    monkeypatch,
):
    import builtins
    import importlib

    forbidden = (
        "b08_model_core.adapters.open_models",
        "b08_model_core.adapters.ttm_adapter",
    )
    original_import = builtins.__import__
    original_import_module = importlib.import_module

    def guarded_import(name, *args, **kwargs):
        if name.startswith(forbidden):
            raise AssertionError(f"C3.2 local execution imported adapters: {name}")
        return original_import(name, *args, **kwargs)

    def guarded_import_module(name, *args, **kwargs):
        if name.startswith(forbidden):
            raise AssertionError(
                f"C3.2 local execution imported adapter module: {name}"
            )
        return original_import_module(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(importlib, "import_module", guarded_import_module)
    config_path = _c32_fd001_local_config(tmp_path)
    config = load_c32_config(config_path)

    result = run_c32_open_model_cross_dataset_evaluation(
        config,
        config_path=config_path,
    )

    assert result.status == "local_execution_baseline_reference_ready"


def test_cli_c_stage_c32_runs_explicit_local_execution(tmp_path):
    config_path = _c32_fd001_local_config(tmp_path)
    output = tmp_path / "c32_local.md"

    exit_code = main(
        [
            "experiment",
            "c-stage-c32",
            "--config",
            str(config_path),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "local_execution_baseline_reference_ready" in text
    assert "C-MAPSS RUL Baseline Evaluation" in text
    assert "FU13-like Forecasting Reference" in text
