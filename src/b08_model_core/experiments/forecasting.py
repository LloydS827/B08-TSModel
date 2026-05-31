from __future__ import annotations

from pathlib import Path

import pandas as pd

from b08_model_core.adapters.chronos_adapter import build_adapter as build_chronos_adapter
from b08_model_core.adapters.timesfm_adapter import build_adapter as build_timesfm_adapter
from b08_model_core.adapters.ttm_adapter import build_adapter as build_ttm_adapter
from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.evaluation.open_source_matrix import candidate_matrix
from b08_model_core.tasks.window_builder import build_model_windows


FORECASTING_CANDIDATES = {"FlowState", "TTM", "TimesFM", "Chronos", "Moirai"}


def _adapter_status() -> dict[str, str]:
    adapters = [build_ttm_adapter(), build_timesfm_adapter(), build_chronos_adapter()]
    return {
        adapter.name: ("available" if adapter.available else f"skipped_optional_dependency: {adapter.reason}")
        for adapter in adapters
    }


def run_forecasting_experiment(
    dataset_path: str | Path,
    output_path: str | Path,
    context_length: int = 128,
    prediction_length: int = 32,
    max_windows: int = 120,
) -> Path:
    df = pd.read_parquet(dataset_path)
    windows = build_model_windows(df, context_length=context_length, prediction_length=prediction_length, stride=prediction_length)
    windows = windows[:max_windows]
    split = max(1, int(len(windows) * 0.7))
    train = windows[:split]
    test = windows[split:] or windows[-1:]

    preds = RobustStageForecaster().fit(train).predict(test)
    metrics = forecasting_metrics(preds, test)
    adapters = _adapter_status()

    lines = [
        "# Forecasting Experiment",
        "",
        f"Dataset: {dataset_path}",
        f"Windows: train={len(train)}, test={len(test)}",
        f"RobustStageForecaster MAE: {metrics['mae']:.6f}",
        f"RobustStageForecaster interval_coverage: {metrics['interval_coverage']:.6f}",
        "",
        "| candidate | route | status | reason |",
        "| --- | --- | --- | --- |",
    ]
    for candidate in candidate_matrix():
        if candidate.name not in FORECASTING_CANDIDATES:
            continue
        status = adapters.get(candidate.name, "skipped_optional_dependency: no local adapter implemented yet")
        lines.append(f"| {candidate.name} | {candidate.route} | {status} | {candidate.reason} |")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
