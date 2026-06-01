from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from typing import Callable, Iterator, Protocol

import numpy as np

from b08_model_core.adapters.base import TimeSeriesFoundationAdapter, dependency_available
from b08_model_core.foundation.results import FoundationForecastResult, FoundationModelStatus


DEFAULT_TTM_CHECKPOINT = "ibm-granite/granite-timeseries-ttm-r2"
DEFAULT_TTM_FREQUENCY_TOKEN = 0
REQUIRED_TTM_MODULES = ("tsfm_public", "torch", "transformers", "huggingface_hub")


@dataclass
class PreparedTTMWindows:
    past_values: np.ndarray
    past_observed_mask: np.ndarray
    future_values: np.ndarray
    sensor_token: list[str]
    channel_center: np.ndarray
    channel_scale: np.ndarray


class TTMRuntimeProtocol(Protocol):
    def predict(
        self,
        prepared: PreparedTTMWindows,
        checkpoint: str,
        prediction_length: int,
        allow_download: bool,
        model_cache_dir: str | None,
    ) -> np.ndarray:
        ...


@contextmanager
def hf_runtime_environment(model_cache_dir: str | None, allow_download: bool) -> Iterator[None]:
    previous_hf_home = os.environ.get("HF_HOME")
    previous_hf_offline = os.environ.get("HF_HUB_OFFLINE")
    had_hf_home = "HF_HOME" in os.environ
    had_hf_offline = "HF_HUB_OFFLINE" in os.environ

    try:
        if model_cache_dir is not None:
            os.environ["HF_HOME"] = model_cache_dir
        if allow_download:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = "1"
        yield
    finally:
        if had_hf_home:
            os.environ["HF_HOME"] = previous_hf_home or ""
        else:
            os.environ.pop("HF_HOME", None)
        if had_hf_offline:
            os.environ["HF_HUB_OFFLINE"] = previous_hf_offline or ""
        else:
            os.environ.pop("HF_HUB_OFFLINE", None)


class TTMRuntime:
    def predict(
        self,
        prepared: PreparedTTMWindows,
        checkpoint: str,
        prediction_length: int,
        allow_download: bool,
        model_cache_dir: str | None,
    ) -> np.ndarray:
        with hf_runtime_environment(model_cache_dir, allow_download):
            import torch
            from tsfm_public.toolkit.get_model import get_model

            try:
                model = get_model(
                    checkpoint,
                    context_length=int(prepared.past_values.shape[1]),
                    prediction_length=prediction_length,
                )
            except TypeError:
                model = get_model(checkpoint)

            model.eval()
            past_values = torch.tensor(prepared.past_values, dtype=torch.float32)
            past_observed_mask = torch.tensor(prepared.past_observed_mask, dtype=torch.bool)
            freq_token = torch.full(
                (int(prepared.past_values.shape[0]),),
                DEFAULT_TTM_FREQUENCY_TOKEN,
                dtype=torch.int,
            )
            with torch.no_grad():
                prediction_output = model(
                    past_values=past_values,
                    past_observed_mask=past_observed_mask,
                    freq_token=freq_token,
                    return_loss=False,
                )
            predictions = getattr(prediction_output, "prediction_outputs", prediction_output)
            if isinstance(predictions, dict):
                predictions = predictions.get("prediction_outputs", next(iter(predictions.values())))
            if isinstance(predictions, tuple):
                predictions = predictions[0]
            if hasattr(predictions, "detach"):
                predictions = predictions.detach().cpu().numpy()
            return np.asarray(predictions, dtype=float)


class TTMForecastAdapter:
    name = "TTM"
    adapter_name = "ttm"

    def __init__(
        self,
        checkpoint: str = DEFAULT_TTM_CHECKPOINT,
        dependency_checker: Callable[[str], bool] = dependency_available,
        runtime_factory: Callable[[], TTMRuntimeProtocol] = TTMRuntime,
    ) -> None:
        self.checkpoint = checkpoint
        self.dependency_checker = dependency_checker
        self.runtime_factory = runtime_factory

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
        except ValueError as exc:
            return FoundationForecastResult(
                model_name=self.name,
                adapter_name=self.adapter_name,
                status=FoundationModelStatus.UNSUPPORTED_WINDOW_SHAPE,
                reason=str(exc),
                metadata={"checkpoint": self.checkpoint, "allow_download": allow_download},
                dependency_status=dependency_status,
                weight_status="unknown",
                cache_dir=model_cache_dir,
            )

    def _predict_with_ttm(
        self,
        prepared: PreparedTTMWindows,
        *,
        allow_download: bool,
        model_cache_dir: str | None,
    ) -> FoundationForecastResult:
        try:
            runtime = self.runtime_factory()
            scaled_prediction = np.asarray(
                runtime.predict(
                    prepared,
                    self.checkpoint,
                    prepared.future_values.shape[1],
                    allow_download,
                    model_cache_dir,
                ),
                dtype=float,
            )
        except Exception as exc:
            status, weight_status = self._runtime_error_status(exc)
            return FoundationForecastResult(
                model_name=self.name,
                adapter_name=self.adapter_name,
                status=status,
                reason=str(exc),
                metadata={"checkpoint": self.checkpoint, "allow_download": allow_download},
                dependency_status="installed",
                weight_status=weight_status,
                cache_dir=model_cache_dir,
            )

        if scaled_prediction.shape != prepared.future_values.shape:
            return FoundationForecastResult(
                model_name=self.name,
                adapter_name=self.adapter_name,
                status=FoundationModelStatus.UNSUPPORTED_WINDOW_SHAPE,
                reason=(
                    "TTM runtime prediction shape mismatch: "
                    f"expected {prepared.future_values.shape}, got {scaled_prediction.shape}"
                ),
                metadata={"checkpoint": self.checkpoint, "allow_download": allow_download},
                dependency_status="installed",
                weight_status="unknown",
                cache_dir=model_cache_dir,
            )

        y_hat = (
            scaled_prediction * prepared.channel_scale[:, np.newaxis, :]
            + prepared.channel_center[:, np.newaxis, :]
        )
        return FoundationForecastResult(
            model_name=self.name,
            adapter_name=self.adapter_name,
            status=FoundationModelStatus.AVAILABLE_AND_RAN,
            y_hat=y_hat,
            metadata={"checkpoint": self.checkpoint, "allow_download": allow_download},
            io_coverage={
                "point_forecast": True,
                "prediction_interval": False,
                "sensor_token_preserved": True,
            },
            dependency_status="installed",
            weight_status="available",
            cache_dir=model_cache_dir,
        )

    @staticmethod
    def _runtime_error_status(exc: Exception) -> tuple[FoundationModelStatus, str]:
        message = str(exc).lower()
        blocked_markers = ("offline", "download", "cache", "connection", "401", "403", "not found")
        if any(marker in message for marker in blocked_markers):
            return FoundationModelStatus.MISSING_OR_BLOCKED_WEIGHTS, "blocked_or_unknown"
        return FoundationModelStatus.RUNTIME_FAILED, "unknown"

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
