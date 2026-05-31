import subprocess
import sys

from b08_model_core.simulation.export_dataset import simulate_dataset
from b08_model_core.evaluation.open_source_matrix import candidate_matrix


def test_forecasting_experiment_scaffold_runs_without_external_weights(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "forecasting_experiment.md"
    simulate_dataset(days=3, seed=23, output_path=dataset)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "experiment",
            "forecasting",
            "--dataset",
            str(dataset),
            "--output",
            str(report),
            "--max-windows",
            "40",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    text = report.read_text(encoding="utf-8")
    assert "Forecasting Experiment" in text
    assert "RobustStageForecaster" in text
    assert "FlowState" in text
    assert "TTM" in text
    assert "TimesFM" in text
    assert "Chronos" in text
    assert "Moirai" in text
    assert "skipped_optional_dependency" in text


def test_forecasting_experiment_rejects_non_positive_max_windows(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "forecasting_experiment.md"
    simulate_dataset(days=3, seed=23, output_path=dataset)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "experiment",
            "forecasting",
            "--dataset",
            str(dataset),
            "--output",
            str(report),
            "--max-windows",
            "0",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "must be greater than 0" in result.stderr
    assert not report.exists()


def test_forecasting_candidate_matrix_includes_current_forecast_first_models():
    names = {candidate.name for candidate in candidate_matrix()}
    assert {"FlowState", "TTM", "TimesFM", "Chronos", "Moirai"} <= names
