from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from b08_model_core.adapters.base import TimeSeriesFoundationAdapter, dependency_available
from b08_model_core.foundation.results import FoundationForecastResult, FoundationModelStatus


DEFAULT_TTM_CHECKPOINT = "ibm-granite/granite-timeseries-ttm-r2"
REQUIRED_TTM_MODULES = ("tsfm_public", "transformers")


@dataclass
class PreparedTTMWindows:
    past_values: np.ndarray
    past_observed_mask: np.ndarray
    future_values: np.ndarray
    sensor_token: list[str]
    channel_center: np.ndarray
    channel_scale: np.ndarray


class TTMForecastAdapter:
    name = "TTM"
    adapter_name = "ttm"

    def __init__(
        self,
        checkpoint: str = DEFAULT_TTM_CHECKPOINT,
        dependency_checker: Callable[[str], bool] = dependency_available,
    ) -> None:
        self.checkpoint = checkpoint
        self.dependency_checker = dependency_checker

    def dependency_status(self) -> tuple[bool, str]:
        missing = [module for module in REQUIRED_TTM_MODULES if not self.dependency_checker(module)]
        if missing:
            return False, f"missing: {', '.join(missing)}"
        return True, "installed"

    def available(self) -> bool:
        available, _ = self.dependency_status()
        return available

    def prepare_windows(
        self,
        windows: list[object],
        context_length: int,
        prediction_length: int,
    ) -> PreparedTTMWindows:
        if not windows:
            raise ValueError("windows must contain at least one window")

        past_values = np.stack([np.asarray(window.X, dtype=float) for window in windows])
        past_observed_mask = np.stack([np.asarray(window.mask, dtype=bool) for window in windows])
        future_values = np.stack([np.asarray(window.y, dtype=float) for window in windows])
        sensor_tokens_by_window = [list(getattr(window, "sensor_token")) for window in windows]

        if past_values.ndim != 3:
            raise ValueError("window.X must be a 2D array for each window")
        if past_observed_mask.shape != past_values.shape:
            raise ValueError("window.mask must match window.X shape")
        if future_values.ndim != 3:
            raise ValueError("window.y must be a 2D array for each window")
        if past_values.shape[1] != context_length:
            raise ValueError(f"context_length mismatch: expected {context_length}, got {past_values.shape[1]}")
        if future_values.shape[1] != prediction_length:
            raise ValueError(f"prediction_length mismatch: expected {prediction_length}, got {future_values.shape[1]}")
        if future_values.shape[2] != past_values.shape[2]:
            raise ValueError("window.y channel count must match window.X channel count")
        for index, tokens in enumerate(sensor_tokens_by_window):
            if len(tokens) != past_values.shape[2]:
                raise ValueError(f"sensor_token length mismatch at window {index}")
            if tokens != sensor_tokens_by_window[0]:
                raise ValueError(f"sensor_token order mismatch at window {index}")

        channel_center, channel_scale = self._masked_channel_stats(past_values, past_observed_mask)
        scaled_past = (past_values - channel_center[:, np.newaxis, :]) / channel_scale[:, np.newaxis, :]
        scaled_future = (future_values - channel_center[:, np.newaxis, :]) / channel_scale[:, np.newaxis, :]

        return PreparedTTMWindows(
            past_values=scaled_past,
            past_observed_mask=past_observed_mask,
            future_values=scaled_future,
            sensor_token=sensor_tokens_by_window[0],
            channel_center=channel_center,
            channel_scale=channel_scale,
        )

    def predict(
        self,
        windows: list[object],
        context_length: int,
        prediction_length: int,
        *,
        allow_download: bool = False,
        model_cache_dir: str | None = None,
    ) -> FoundationForecastResult:
        dependency_ready, dependency_status = self.dependency_status()
        if not dependency_ready:
            return FoundationForecastResult(
                model_name=self.name,
                adapter_name=self.adapter_name,
                status=FoundationModelStatus.MISSING_DEPENDENCY,
                reason=(
                    "TTM optional dependencies are not installed. Run "
                    "`uv sync --extra dev --extra foundation-ttm` before enabling TTM inference."
                ),
                metadata={"checkpoint": self.checkpoint, "allow_download": allow_download},
                io_coverage={
                    "point_forecast": False,
                    "prediction_interval": False,
                    "sensor_token_preserved": True,
                },
                dependency_status=dependency_status,
                weight_status="not_attempted",
                cache_dir=model_cache_dir,
            )

        try:
            prepared = self.prepare_windows(windows, context_length, prediction_length)
            return self._predict_with_ttm(prepared, allow_download=allow_download, model_cache_dir=model_cache_dir)
        except NotImplementedError as exc:
            return FoundationForecastResult(
                model_name=self.name,
                adapter_name=self.adapter_name,
                status=FoundationModelStatus.RUNTIME_FAILED,
                reason=str(exc),
                metadata={"checkpoint": self.checkpoint, "allow_download": allow_download},
                dependency_status=dependency_status,
                weight_status="not_attempted",
                cache_dir=model_cache_dir,
            )

    def _predict_with_ttm(
        self,
        prepared: PreparedTTMWindows,
        *,
        allow_download: bool,
        model_cache_dir: str | None,
    ) -> FoundationForecastResult:
        raise NotImplementedError("TTM runtime inference is intentionally deferred to Task 4")

    @staticmethod
    def _masked_channel_stats(values: np.ndarray, observed_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        observed = observed_mask.astype(float)
        counts = observed.sum(axis=1)
        safe_counts = np.where(counts == 0.0, 1.0, counts)
        center = (values * observed).sum(axis=1) / safe_counts
        variance = (((values - center[:, np.newaxis, :]) ** 2) * observed).sum(axis=1) / safe_counts
        scale = np.sqrt(variance)
        scale = np.where((counts == 0.0) | (scale == 0.0), 1.0, scale)
        return center, scale


def build_adapter() -> TimeSeriesFoundationAdapter:
    adapter = TTMForecastAdapter()
    available = adapter.available()
    return TimeSeriesFoundationAdapter(
        "TTM",
        {"forecasting"},
        available,
        "" if available else "optional TTM dependency is not installed",
    )
