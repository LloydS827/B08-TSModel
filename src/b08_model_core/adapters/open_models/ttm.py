from __future__ import annotations

import time
from typing import Any, Iterable

import numpy as np

from b08_model_core.adapters.open_models import _DependencyFirstOpenModelAdapter
from b08_model_core.adapters.open_models.base import (
    AdapterExecutionContext,
    AdapterFailure,
    AdapterReadiness,
    AdapterTaskOutput,
    OpenModelAdapterStatus,
    dependency_status,
)
from b08_model_core.adapters.ttm_adapter import REQUIRED_TTM_MODULES, TTMForecastAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId
from b08_model_core.foundation.results import FoundationForecastResult, FoundationModelStatus


class TTMOpenModelAdapter(_DependencyFirstOpenModelAdapter):
    model_id = "ttm"
    display_name = "TTM / TinyTimeMixer"
    required_modules = REQUIRED_TTM_MODULES
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "ibm-granite/granite-timeseries-ttm-r2"

    def inspect_environment(
        self,
        context: AdapterExecutionContext,
    ) -> AdapterReadiness | AdapterFailure:
        dependency = self._dependency_status()
        if dependency != "available":
            return self._missing_dependency("inspect", dependency, context)
        return AdapterReadiness(
            model_id=self.model_id,
            dependency_status=dependency,
            weight_status="not_checked",
            adapter_status=OpenModelAdapterStatus.READY,
            adapter_name=self.__class__.__name__,
            model_ref=self.model_ref,
            cache_dir=context.cache_dir,
            actual_network_used=False,
        )

    def load(
        self,
        context: AdapterExecutionContext,
    ) -> TTMOpenModelAdapter | AdapterFailure:
        dependency = self._dependency_status()
        if dependency != "available":
            return self._missing_dependency("load", dependency, context)
        return self

    def run_forecasting(
        self,
        windows: Iterable[Any],
        context: AdapterExecutionContext,
    ) -> AdapterTaskOutput | AdapterFailure:
        started = time.monotonic()
        window_list = list(windows)
        dependency = self._dependency_status()
        if dependency != "available":
            return self._missing_dependency("execute", dependency, context)

        try:
            expected = np.stack([np.asarray(window.y, dtype=float) for window in window_list])
        except ValueError as exc:
            return self._failure(
                C21TaskId.FORECASTING,
                OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE,
                "execute",
                "TTM forecasting windows must contain stackable target arrays",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=dependency,
                runtime_seconds=time.monotonic() - started,
                input_shape={"windows": len(window_list)},
            )

        try:
            raw_prediction = self._predict_with_ttm(window_list, context)
        except Exception as exc:
            status, weight = self._load_exception_status(exc)
            if status == OpenModelAdapterStatus.LICENSE_OR_INTERFACE_NEEDS_REVIEW:
                status = OpenModelAdapterStatus.RUNTIME_FAILED
            return self._failure(
                C21TaskId.FORECASTING,
                status,
                "execute",
                "TTM forecasting runtime failed",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=dependency,
                weight=weight,
                runtime_seconds=time.monotonic() - started,
                input_shape=self._forecasting_input_shape(window_list),
            )

        if isinstance(raw_prediction, FoundationForecastResult):
            if raw_prediction.status != FoundationModelStatus.AVAILABLE_AND_RAN:
                return self._foundation_failure(
                    raw_prediction,
                    context,
                    time.monotonic() - started,
                    self._forecasting_input_shape(window_list),
                )
            predictions = np.asarray(raw_prediction.y_hat, dtype=float)
            weight_status = raw_prediction.weight_status
        else:
            predictions = np.asarray(raw_prediction, dtype=float)
            weight_status = "available"

        if predictions.shape != expected.shape:
            return self._failure(
                C21TaskId.FORECASTING,
                OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE,
                "execute",
                (
                    "TTM prediction shape mismatch: "
                    f"expected {expected.shape}, got {predictions.shape}"
                ),
                "ShapeMismatch",
                f"expected={expected.shape}; got={predictions.shape}",
                context=context,
                dependency=dependency,
                weight=weight_status,
                runtime_seconds=time.monotonic() - started,
                input_shape=self._forecasting_input_shape(window_list),
                expected_shape_or_constraint=str(expected.shape),
            )

        runtime_seconds = time.monotonic() - started
        return AdapterTaskOutput(
            model_id=self.model_id,
            task_id=C21TaskId.FORECASTING,
            status=OpenModelAdapterStatus.AVAILABLE_AND_RAN,
            predictions=predictions,
            metrics={"runtime_seconds": runtime_seconds},
            input_shape=self._forecasting_input_shape(window_list),
            output_shape={"predictions": list(predictions.shape)},
            runtime_seconds=runtime_seconds,
            adapter_name=self.__class__.__name__,
            model_ref=self.model_ref,
            cache_dir=context.cache_dir,
            actual_network_used=self._network_usage(context),
            metadata={"weight_status": weight_status},
        )

    def _predict_with_ttm(
        self,
        windows: list[Any],
        context: AdapterExecutionContext,
    ) -> FoundationForecastResult:
        if not windows:
            raise ValueError("windows must contain at least one window")
        context_length = int(np.asarray(windows[0].X).shape[0])
        prediction_length = int(np.asarray(windows[0].y).shape[0])
        return TTMForecastAdapter(
            dependency_checker=self._dependency_available,
        ).predict(
            windows,
            context_length,
            prediction_length,
            allow_download=context.allow_download,
            model_cache_dir=str(context.cache_dir),
        )

    def _dependency_available(self, name: str) -> bool:
        return dependency_status((name,)) == "available"

    def _dependency_status(self) -> str:
        return dependency_status(self.required_modules, self._dependency_available)

    def _foundation_failure(
        self,
        result: FoundationForecastResult,
        context: AdapterExecutionContext,
        runtime_seconds: float,
        input_shape: dict[str, Any],
    ) -> AdapterFailure:
        status = self._map_foundation_status(result.status)
        return self._failure(
            C21TaskId.FORECASTING,
            status,
            "execute",
            result.reason or "TTM foundation adapter did not produce predictions",
            "FoundationForecastResult",
            result.status.value,
            context=context,
            dependency=result.dependency_status,
            weight=result.weight_status,
            runtime_seconds=runtime_seconds,
            input_shape=input_shape,
        )

    def _failure(
        self,
        task_id: C21TaskId,
        status: OpenModelAdapterStatus,
        failure_stage: str,
        failure_reason: str,
        error_type: str,
        error_detail: str,
        *,
        context: AdapterExecutionContext,
        dependency: str = "available",
        weight: str = "not_checked",
        runtime_seconds: float | None = None,
        input_shape: dict[str, Any] | None = None,
        expected_shape_or_constraint: str | None = None,
    ) -> AdapterFailure:
        return AdapterFailure(
            model_id=self.model_id,
            task_id=task_id,
            status=status,
            failure_stage=failure_stage,
            failure_reason=failure_reason,
            error_type=error_type,
            error_detail=error_detail,
            dependency_status=dependency,
            weight_status=weight,
            input_shape={} if input_shape is None else input_shape,
            expected_shape_or_constraint=expected_shape_or_constraint,
            adapter_name=self.__class__.__name__,
            runtime_seconds=runtime_seconds,
            model_ref=self.model_ref,
            cache_dir=context.cache_dir,
            actual_network_used=self._network_usage(context),
        )

    @staticmethod
    def _map_foundation_status(status: FoundationModelStatus) -> OpenModelAdapterStatus:
        if status == FoundationModelStatus.MISSING_DEPENDENCY:
            return OpenModelAdapterStatus.MISSING_DEPENDENCY
        if status == FoundationModelStatus.MISSING_OR_BLOCKED_WEIGHTS:
            return OpenModelAdapterStatus.MISSING_OR_BLOCKED_WEIGHTS
        if status == FoundationModelStatus.UNSUPPORTED_WINDOW_SHAPE:
            return OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE
        if status == FoundationModelStatus.RUNTIME_FAILED:
            return OpenModelAdapterStatus.RUNTIME_FAILED
        return OpenModelAdapterStatus.RUNTIME_FAILED

    @staticmethod
    def _forecasting_input_shape(windows: list[Any]) -> dict[str, Any]:
        first = windows[0] if windows else None
        return {
            "windows": len(windows),
            "X": list(np.asarray(first.X).shape) if first is not None else None,
            "y": list(np.asarray(first.y).shape) if first is not None else None,
        }

    @staticmethod
    def _network_usage(context: AdapterExecutionContext) -> bool | str:
        if context.allow_download:
            return "download_allowed_not_verified"
        if context.allow_network:
            return "network_allowed_not_verified"
        return False
