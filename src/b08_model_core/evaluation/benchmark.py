from __future__ import annotations

from pathlib import Path

import pandas as pd

from b08_model_core.adapters.chronos_adapter import build_adapter as build_chronos_adapter
from b08_model_core.adapters.moment_adapter import build_adapter as build_moment_adapter
from b08_model_core.adapters.timesfm_adapter import build_adapter as build_timesfm_adapter
from b08_model_core.adapters.ttm_adapter import build_adapter as build_ttm_adapter
from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.baselines.seasonal_naive import StageSeasonalNaiveForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.evaluation.open_source_matrix import candidate_matrix
from b08_model_core.tasks.window_builder import build_model_windows


def _dataset_summary(dataset_path: str | Path | None) -> str:
    if dataset_path is None:
        return "metadata-only dry run; no dataset supplied"
    path = Path(dataset_path)
    if not path.exists():
        return f"dataset not found: {path}; matrix-only benchmark generated"
    df = pd.read_parquet(path, columns=["batch_id", "sensor_id", "stage", "failure_proxy"])
    return (
        f"rows={len(df)}, batches={df['batch_id'].nunique()}, sensors={df['sensor_id'].nunique()}, "
        f"stages={df['stage'].nunique()}, failure_proxy_rows={int(df['failure_proxy'].sum())}"
    )


def _baseline_section(
    dataset_path: str | Path | None,
    context_length: int,
    prediction_length: int,
    max_windows: int,
) -> tuple[list[str], dict[str, float]]:
    if dataset_path is None or not Path(dataset_path).exists():
        return ["Baseline metrics: skipped because no dataset was supplied."], {}

    df = pd.read_parquet(dataset_path)
    windows = build_model_windows(df, context_length=context_length, prediction_length=prediction_length, stride=prediction_length)
    if len(windows) < 4:
        return [f"Baseline metrics: skipped because only {len(windows)} windows were available."], {}
    windows = windows[:max_windows]
    split = max(1, int(len(windows) * 0.7))
    train = windows[:split]
    test = windows[split:] or windows[-1:]

    robust_preds = RobustStageForecaster().fit(train).predict(test)
    robust_metrics = forecasting_metrics(robust_preds, test)
    seasonal_preds = StageSeasonalNaiveForecaster().fit(train).predict(test)
    seasonal_metrics = forecasting_metrics(seasonal_preds, test)

    lines = [
        "## Baseline Metrics",
        "",
        f"Window count used: train={len(train)}, test={len(test)}, context_length={context_length}, prediction_length={prediction_length}.",
        f"RobustStageForecaster MAE: {robust_metrics['mae']:.6f}; interval_coverage: {robust_metrics['interval_coverage']:.6f}.",
        f"StageSeasonalNaiveForecaster MAE: {seasonal_metrics['mae']:.6f}; interval_coverage: {seasonal_metrics['interval_coverage']:.6f}.",
    ]
    return lines, robust_metrics


def _adapter_availability_lines() -> list[str]:
    adapters = [build_ttm_adapter(), build_moment_adapter(), build_chronos_adapter(), build_timesfm_adapter()]
    lines = ["## Adapter availability", ""]
    for adapter in adapters:
        status = "available" if adapter.available else f"unavailable: {adapter.reason}"
        lines.append(f"- {adapter.name}: {status}; heads={', '.join(sorted(adapter.supported_heads))}")
    return lines


def _write_route_decision_report(output_path: Path, robust_metrics: dict[str, float]) -> Path:
    target = output_path.parent / "model_route_decision.md"
    metric_line = (
        f"Current baseline evidence: RobustStageForecaster MAE={robust_metrics['mae']:.6f}, "
        f"interval_coverage={robust_metrics['interval_coverage']:.6f}."
        if robust_metrics
        else "Current baseline evidence: pending dataset-backed baseline run."
    )
    target.write_text(
        "\n".join(
            [
                "# B08 Model Route Decision",
                "",
                metric_line,
                "",
                "| Route | Go condition | No-Go condition | Evidence |",
                "| --- | --- | --- | --- |",
                "| direct_reuse | Frozen model beats baseline and covers required IO | Cannot encode stage/domain context | zero-shot metrics and adapter availability |",
                "| fine_tune | Backbone helps but domain gap remains | Fine-tuning gain is unstable or too costly | adapter/linear-probe lift against baseline |",
                "| domain_pretraining | Open models fail stage-conditioned degradation tasks | Data or compute is insufficient | custom pretraining objective beats baseline |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return target


def run_benchmark(
    dataset_path: str | Path | None,
    output_path: str | Path = "reports/model_core_evaluation.md",
    context_length: int = 128,
    prediction_length: int = 32,
    max_windows: int = 200,
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    baseline_lines, robust_metrics = _baseline_section(dataset_path, context_length, prediction_length, max_windows)
    route_report = _write_route_decision_report(out, robust_metrics)
    lines = [
        "# B08 Model Core Evaluation",
        "",
        f"Dataset summary: {_dataset_summary(dataset_path)}",
        "",
        "The stage-aware robust median/MAD forecaster is the baseline comparison for forecasting and interval coverage.",
        "",
        *baseline_lines,
        "",
        *_adapter_availability_lines(),
        "",
        f"Related route report: {route_report}",
        "",
        "| model name | task | metric | baseline comparison | route recommendation | reason |",
        "| --- | --- | --- | --- | --- | --- |",
        "| RobustStageForecaster | forecasting | MAE, interval_coverage | baseline | baseline | Minimum delivery bar for the model-core sandbox. |",
    ]
    for item in candidate_matrix():
        task = ", ".join(item.supported_tasks)
        comparison = f"{item.direct_use_score:.2f} direct / {item.fine_tune_score:.2f} fine-tune vs baseline"
        lines.append(
            f"| {item.name} | {task} | direct_use_score, fine_tune_score | {comparison} | {item.route} | {item.reason} |"
        )
    lines.extend(
        [
            "",
            "Domain pretraining gate: choose domain_pretraining when direct_reuse and fine_tune fail to cover stage-conditioned, multi-domain degradation representation.",
            "Route recommendation: first benchmark direct_reuse candidates, then fine_tune MOMENT/TSPulse/UniTS, then consider domain_pretraining only if required IO coverage remains below baseline.",
        ]
    )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
