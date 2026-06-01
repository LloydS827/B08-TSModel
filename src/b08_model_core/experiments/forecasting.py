from __future__ import annotations

from pathlib import Path

from b08_model_core.adapters.ttm_adapter import TTMForecastAdapter
from b08_model_core.foundation import (
    FoundationForecastResult,
    FoundationForecastRunner,
    FoundationModelStatus,
    render_foundation_report,
)


SUPPORTED_EXPERIMENT_MODELS = {"baseline", "ttm"}


class BaselineOnlyAdapter:
    name = "BaselineOnly"
    adapter_name = "baseline"

    def predict(
        self,
        windows: list[object],
        *,
        context_length: int,
        prediction_length: int,
        allow_download: bool,
        model_cache_dir: str | None,
    ) -> FoundationForecastResult:
        return FoundationForecastResult(
            model_name=self.name,
            adapter_name=self.adapter_name,
            status=FoundationModelStatus.SKIPPED_BY_USER,
            reason="foundation model was not selected; baseline comparison only",
            metadata={
                "context_length": context_length,
                "prediction_length": prediction_length,
                "allow_download": allow_download,
                "window_count": len(windows),
            },
            io_coverage={
                "point_forecast": False,
                "prediction_interval": False,
                "sensor_token_preserved": True,
            },
            dependency_status="not_required",
            weight_status="not_attempted",
            cache_dir=model_cache_dir,
        )


def _adapter_for_model(model: str) -> object:
    if model == "baseline":
        return BaselineOnlyAdapter()
    if model == "ttm":
        return TTMForecastAdapter()
    raise ValueError(f"unsupported forecasting experiment model: {model}")


def run_forecasting_experiment(
    dataset_path: str | Path,
    output_path: str | Path,
    context_length: int = 128,
    prediction_length: int = 32,
    max_windows: int = 120,
    model: str = "baseline",
    model_cache_dir: str | None = None,
    allow_download: bool = False,
) -> Path:
    output, _ = run_forecasting_experiment_with_status(
        dataset_path=dataset_path,
        output_path=output_path,
        context_length=context_length,
        prediction_length=prediction_length,
        max_windows=max_windows,
        model=model,
        model_cache_dir=model_cache_dir,
        allow_download=allow_download,
    )
    return output


def run_forecasting_experiment_with_status(
    dataset_path: str | Path,
    output_path: str | Path,
    context_length: int = 128,
    prediction_length: int = 32,
    max_windows: int = 120,
    model: str = "baseline",
    model_cache_dir: str | None = None,
    allow_download: bool = False,
) -> tuple[Path, FoundationModelStatus]:
    if context_length <= 0:
        raise ValueError("context_length must be greater than 0")
    if prediction_length <= 0:
        raise ValueError("prediction_length must be greater than 0")
    if max_windows <= 0:
        raise ValueError("max_windows must be greater than 0")
    if model not in SUPPORTED_EXPERIMENT_MODELS:
        raise ValueError(f"unsupported forecasting experiment model: {model}")

    adapter = _adapter_for_model(model)
    runner_result = FoundationForecastRunner().run(
        dataset_path=dataset_path,
        model_name=adapter.name,
        adapter=adapter,
        context_length=context_length,
        prediction_length=prediction_length,
        max_windows=max_windows,
        allow_download=allow_download,
        model_cache_dir=model_cache_dir,
    )
    dataset_summary = {
        "dataset": runner_result.dataset_path,
        "train_windows": runner_result.train_count,
        "test_windows": runner_result.test_count,
        "context_length": runner_result.context_length,
        "prediction_length": runner_result.prediction_length,
        "sensors": runner_result.sensor_count,
    }
    report = render_foundation_report(
        dataset_summary=dataset_summary,
        baseline_metrics=runner_result.baseline_metrics,
        foundation_result=runner_result.foundation_result,
        route_recommendation=runner_result.route_recommendation,
        fallback_candidates=runner_result.fallback_candidates,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    return output, runner_result.foundation_result.status
