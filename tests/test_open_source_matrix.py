from pathlib import Path

from b08_model_core.adapters.base import TimeSeriesFoundationAdapter
from b08_model_core.evaluation.benchmark import run_benchmark
from b08_model_core.evaluation.open_source_matrix import candidate_matrix
from b08_model_core.simulation.export_dataset import simulate_dataset


def test_candidate_matrix_covers_required_models_and_decisions():
    matrix = candidate_matrix()
    names = {m.name for m in matrix}
    assert {"TSPulse", "MOMENT", "TTM", "Chronos", "TimesFM", "UniTS", "Moirai"} <= names
    for model in matrix:
        assert model.supported_tasks
        assert model.direct_use_score is not None
        assert model.fine_tune_score is not None
        assert model.route in {"direct_reuse", "fine_tune", "baseline_only", "not_fit"}


def test_adapter_base_optional_dependency_contract():
    adapter = TimeSeriesFoundationAdapter(name="example", supported_heads={"forecasting"}, available=False, reason="missing")
    assert adapter.available is False
    assert "missing" in adapter.reason


def test_benchmark_report_contract(tmp_path):
    report = tmp_path / "model_core_evaluation.md"
    run_benchmark(dataset_path=None, output_path=report)
    text = Path(report).read_text(encoding="utf-8")
    for required in ["model name", "task", "metric", "baseline comparison", "route recommendation", "reason"]:
        assert required in text
    assert "TSPulse" in text
    assert "domain_pretraining" in text


def test_benchmark_runs_baseline_metrics_on_dataset(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "model_core_evaluation.md"
    simulate_dataset(days=3, seed=19, output_path=dataset)

    run_benchmark(dataset_path=dataset, output_path=report, context_length=64, prediction_length=16, max_windows=80)
    text = report.read_text(encoding="utf-8")

    assert "RobustStageForecaster MAE" in text
    assert "interval_coverage" in text
    assert "Adapter availability" in text
    assert "model_route_decision" in text
