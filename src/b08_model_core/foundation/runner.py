from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.baselines.seasonal_naive import StageSeasonalNaiveForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.foundation.results import FoundationForecastResult, recommend_route
from b08_model_core.tasks.window_builder import build_model_windows


FALLBACK_FOUNDATION_CANDIDATES = ["FlowState", "TimesFM", "Chronos", "Moirai"]


@dataclass
class FoundationExperimentResult:
    dataset_path: str
    model_name: str
    train_count: int
    test_count: int
    context_length: int
    prediction_length: int
    sensor_count: int
    baseline_metrics: dict[str, dict[str, float | None]]
    foundation_result: FoundationForecastResult
    route_recommendation: str
    fallback_candidates: list[str]


class FoundationForecastRunner:
    def run(
        self,
        dataset_path: str | Path,
        model_name: str,
        adapter: object,
        context_length: int,
        prediction_length: int,
        max_windows: int,
        allow_download: bool,
        model_cache_dir: str | None = None,
    ) -> FoundationExperimentResult:
        if max_windows <= 0:
            raise ValueError("max_windows must be greater than 0")
        dataset = Path(dataset_path)
        df = pd.read_parquet(dataset)
        windows = build_model_windows(
            df,
            context_length=context_length,
            prediction_length=prediction_length,
            stride=prediction_length,
        )[:max_windows]
        if len(windows) < 2:
            raise ValueError(
                "not enough windows for foundation forecasting runner: "
                f"need at least 2, got {len(windows)}"
            )

        split = max(1, int(len(windows) * 0.7))
        train = windows[:split]
        test = windows[split:]
        if not test:
            raise ValueError("not enough windows for foundation forecasting runner test split")

        robust_predictions = RobustStageForecaster().fit(train).predict(test)
        seasonal_predictions = StageSeasonalNaiveForecaster().fit(train).predict(test)
        baseline_metrics = {
            "RobustStageForecaster": forecasting_metrics(robust_predictions, test),
            "StageSeasonalNaiveForecaster": forecasting_metrics(seasonal_predictions, test),
        }

        foundation_result = adapter.predict(
            test,
            context_length=context_length,
            prediction_length=prediction_length,
            allow_download=allow_download,
            model_cache_dir=model_cache_dir,
        )
        if foundation_result.succeeded and foundation_result.predictions():
            foundation_result.metrics = forecasting_metrics(foundation_result.predictions(), test)

        baseline_mae = baseline_metrics["RobustStageForecaster"]["mae"]
        route_recommendation = recommend_route(foundation_result, baseline_mae=baseline_mae)

        return FoundationExperimentResult(
            dataset_path=str(dataset),
            model_name=model_name,
            train_count=len(train),
            test_count=len(test),
            context_length=context_length,
            prediction_length=prediction_length,
            sensor_count=int(windows[0].X.shape[1]),
            baseline_metrics=baseline_metrics,
            foundation_result=foundation_result,
            route_recommendation=route_recommendation,
            fallback_candidates=list(FALLBACK_FOUNDATION_CANDIDATES),
        )


def run_foundation_forecasting(**kwargs: object) -> FoundationExperimentResult:
    return FoundationForecastRunner().run(**kwargs)
