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
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class _ForecastingOpenModelAdapter(_DependencyFirstOpenModelAdapter):
    official_api_detail = ""

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
            known_limitations=(
                "official runtime loading is gated behind interface/weight review",
            ),
            metadata=self._execution_metadata(context),
        )

    def load(
        self,
        context: AdapterExecutionContext,
    ) -> _ForecastingOpenModelAdapter | AdapterFailure:
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
            expected = np.stack(
                [np.asarray(window.y, dtype=float) for window in window_list]
            )
        except ValueError as exc:
            return self._failure(
                C21TaskId.FORECASTING,
                OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE,
                "execute",
                f"{self.display_name} windows must contain stackable target arrays",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=dependency,
                runtime_seconds=time.monotonic() - started,
                input_shape={"windows": len(window_list)},
            )

        try:
            raw_prediction = self._predict(window_list, context)
        except ModuleNotFoundError as exc:
            return self._failure(
                C21TaskId.FORECASTING,
                OpenModelAdapterStatus.MISSING_DEPENDENCY,
                "execute",
                f"{self.display_name} dependency import failed",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=f"missing:{exc.name or ','.join(self.required_modules)}",
                runtime_seconds=time.monotonic() - started,
                input_shape=self._forecasting_input_shape(window_list),
            )
        except Exception as exc:
            status, weight = self._load_exception_status(exc)
            return self._failure(
                C21TaskId.FORECASTING,
                status,
                "execute",
                f"{self.display_name} forecasting runtime failed",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=dependency,
                weight=weight,
                runtime_seconds=time.monotonic() - started,
                input_shape=self._forecasting_input_shape(window_list),
            )

        if isinstance(raw_prediction, AdapterFailure):
            return raw_prediction

        predictions = np.asarray(raw_prediction, dtype=float)
        if predictions.shape != expected.shape:
            return self._failure(
                C21TaskId.FORECASTING,
                OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE,
                "execute",
                (
                    f"{self.display_name} prediction shape mismatch: "
                    f"expected {expected.shape}, got {predictions.shape}"
                ),
                "ShapeMismatch",
                f"expected={expected.shape}; got={predictions.shape}",
                context=context,
                dependency=dependency,
                weight="available",
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
            actual_network_used=False,
            metadata={
                **self._execution_metadata(context),
                "dependency_status": dependency,
                "weight_status": "available",
            },
        )

    def _predict(
        self,
        windows: list[Any],
        context: AdapterExecutionContext,
    ) -> AdapterFailure:
        for module_name in self.required_modules:
            self._import_dependency(module_name)
        return self._failure(
            C21TaskId.FORECASTING,
            OpenModelAdapterStatus.LICENSE_OR_INTERFACE_NEEDS_REVIEW,
            "execute",
            (
                f"{self.display_name} dependency import succeeded, but the official "
                "forecasting API path still needs review before loading weights"
            ),
            "InterfaceNeedsReview",
            self.official_api_detail,
            context=context,
            dependency="available",
            weight="not_checked",
            input_shape=self._forecasting_input_shape(windows),
        )

    def _dependency_available(self, name: str) -> bool:
        return dependency_status((name,)) == "available"

    def _dependency_status(self) -> str:
        return dependency_status(self.required_modules, self._dependency_available)

    def _missing_dependency(
        self,
        stage: str,
        dependency: str,
        context: AdapterExecutionContext,
    ) -> AdapterFailure:
        return self._failure(
            C21TaskId.FORECASTING,
            OpenModelAdapterStatus.MISSING_DEPENDENCY,
            stage,
            f"{self.display_name} dependency modules are unavailable",
            "MissingDependency",
            dependency,
            context=context,
            dependency=dependency,
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
            actual_network_used=False,
            metadata=self._execution_metadata(context),
        )

    @staticmethod
    def _forecasting_input_shape(windows: list[Any]) -> dict[str, Any]:
        first = windows[0] if windows else None
        return {
            "windows": len(windows),
            "X": list(np.asarray(first.X).shape) if first is not None else None,
            "y": list(np.asarray(first.y).shape) if first is not None else None,
        }

    @staticmethod
    def _execution_metadata(context: AdapterExecutionContext) -> dict[str, Any]:
        return {
            "allow_network": context.allow_network,
            "allow_download": context.allow_download,
        }
