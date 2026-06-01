import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from b08_model_core.experiments import forecasting as forecasting_module
from b08_model_core.simulation.export_dataset import simulate_dataset
from b08_model_core.evaluation.open_source_matrix import candidate_matrix


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_default_forecasting_cli_runs_baseline_only_without_external_weights(tmp_path):
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
    assert "Forecasting Foundation Model Experiment" in text
    assert "RobustStageForecaster" in text
    assert "StageSeasonalNaiveForecaster" in text
    assert "Route Recommendation" in text
    assert "BaselineOnly" in text
    assert "baseline" in text
    assert "skipped_by_user" in text


def test_baseline_forecasting_experiment_does_not_instantiate_ttm(tmp_path, monkeypatch):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "forecasting_experiment.md"
    simulate_dataset(days=3, seed=23, output_path=dataset)

    def fail_if_used(*args, **kwargs):
        raise AssertionError("baseline mode must not instantiate TTMForecastAdapter")

    monkeypatch.setattr(forecasting_module, "TTMForecastAdapter", fail_if_used, raising=False)

    output = forecasting_module.run_forecasting_experiment(
        dataset_path=dataset,
        output_path=report,
        max_windows=40,
        model="baseline",
    )

    assert output == report
    assert "skipped_by_user" in report.read_text(encoding="utf-8")


def test_ttm_forecasting_cli_returns_nonzero_for_non_success_but_writes_report(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "ttm_forecasting_experiment.md"
    empty_cache = tmp_path / "empty_hf_cache"
    empty_cache.mkdir()
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
            "--model",
            "ttm",
            "--model-cache-dir",
            str(empty_cache),
            "--no-download",
        ],
        text=True,
        capture_output=True,
    )

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "TTM" in text
    assert "Foundation Model Status" in text
    assert result.returncode == 1, text
    assert any(
        status in text
        for status in [
            "missing_dependency",
            "missing_or_blocked_weights",
            "unsupported_window_shape",
            "runtime_failed",
        ]
    )


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


@pytest.mark.parametrize("option", ["--context-length", "--prediction-length"])
def test_forecasting_experiment_rejects_non_positive_lengths(tmp_path, option):
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
            option,
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


def test_foundation_ttm_extra_and_local_model_artifacts_are_documented():
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    foundation_ttm = set(pyproject["project"]["optional-dependencies"]["foundation-ttm"])
    assert {"granite-tsfm", "torch", "transformers", "huggingface_hub"} <= foundation_ttm

    ignore_rules = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "hf_cache/" in ignore_rules
    assert "model_cache/" in ignore_rules
    assert ".cache/" in ignore_rules
    assert "reports/*.md" in ignore_rules

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "uv sync --extra dev --extra foundation-ttm" in readme
    assert "--allow-download" in readme
    assert "HF_HOME=hf_cache" in readme
    assert "不要把这些文件上传到 GitHub" in readme
