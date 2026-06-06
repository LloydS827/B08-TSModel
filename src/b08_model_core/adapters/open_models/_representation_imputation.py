from __future__ import annotations

import time
from typing import Any, Iterable, Mapping

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


class _RepresentationImputationOpenModelAdapter(_DependencyFirstOpenModelAdapter):
    official_api_detail = ""

    def inspect_environment(
        self,
        context: AdapterExecutionContext,
    ) -> AdapterReadiness | AdapterFailure:
        dependency = self._dependency_status()
        if dependency != "available":
            return self._missing_dependency(
                self.supported_tasks[0],
                "inspect",
                dependency,
                context,
            )
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
    ) -> _RepresentationImputationOpenModelAdapter | AdapterFailure:
        dependency = self._dependency_status()
        if dependency != "available":
            return self._missing_dependency(
                self.supported_tasks[0],
                "load",
                dependency,
                context,
            )
        return self

    def run_representation(
        self,
        windows: Iterable[Any],
        context: AdapterExecutionContext,
    ) -> AdapterTaskOutput | AdapterFailure:
        started = time.monotonic()
        window_list = list(windows)
        dependency = self._dependency_status()
        if dependency != "available":
            return self._missing_dependency(
                C21TaskId.REPRESENTATION,
                "execute",
                dependency,
                context,
            )

        try:
            raw_embedding = self._embed(window_list, context)
        except ModuleNotFoundError as exc:
            return self._failure(
                C21TaskId.REPRESENTATION,
                OpenModelAdapterStatus.MISSING_DEPENDENCY,
                "execute",
                f"{self.display_name} dependency import failed",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=f"missing:{exc.name or ','.join(self.required_modules)}",
                runtime_seconds=time.monotonic() - started,
                input_shape=self._input_shape(window_list),
            )
        except Exception as exc:
            status, weight = self._load_exception_status(exc)
            return self._failure(
                C21TaskId.REPRESENTATION,
                status,
                "execute",
                f"{self.display_name} representation runtime failed",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=dependency,
                weight=weight,
                runtime_seconds=time.monotonic() - started,
                input_shape=self._input_shape(window_list),
            )

        if isinstance(raw_embedding, AdapterFailure):
            return raw_embedding

        representations = np.asarray(raw_embedding, dtype=float)
        if representations.ndim == 0 or (
            window_list and representations.shape[0] != len(window_list)
        ):
            return self._failure(
                C21TaskId.REPRESENTATION,
                OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE,
                "execute",
                (
                    f"{self.display_name} embedding batch shape mismatch: "
                    f"expected first dimension {len(window_list)}, "
                    f"got {representations.shape}"
                ),
                "ShapeMismatch",
                f"expected_batch={len(window_list)}; got={representations.shape}",
                context=context,
                dependency=dependency,
                weight="available",
                runtime_seconds=time.monotonic() - started,
                input_shape=self._input_shape(window_list),
                expected_shape_or_constraint=(
                    f"first dimension == {len(window_list)}"
                ),
            )

        runtime_seconds = time.monotonic() - started
        output_shape = {
            "representations": list(representations.shape),
            "embedding_shape": list(representations.shape),
        }
        return AdapterTaskOutput(
            model_id=self.model_id,
            task_id=C21TaskId.REPRESENTATION,
            status=OpenModelAdapterStatus.AVAILABLE_AND_RAN,
            representations=representations,
            metrics={
                "runtime_seconds": runtime_seconds,
                "finite_value_ratio": self._finite_value_ratio(representations),
            },
            input_shape=self._input_shape(window_list),
            output_shape=output_shape,
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

    def run_imputation(
        self,
        windows: Iterable[Any],
        mask_policy: Mapping[str, object],
        context: AdapterExecutionContext,
    ) -> AdapterTaskOutput | AdapterFailure:
        started = time.monotonic()
        window_list = list(windows)
        dependency = self._dependency_status()
        if dependency != "available":
            return self._missing_dependency(
                C21TaskId.IMPUTATION,
                "execute",
                dependency,
                context,
            )

        try:
            expected = np.stack(
                [np.asarray(window.X, dtype=float) for window in window_list]
            )
        except ValueError as exc:
            return self._failure(
                C21TaskId.IMPUTATION,
                OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE,
                "execute",
                f"{self.display_name} windows must contain stackable input arrays",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=dependency,
                runtime_seconds=time.monotonic() - started,
                input_shape={"windows": len(window_list)},
                metadata_extra={"mask_policy": dict(mask_policy)},
            )

        try:
            raw_reconstruction = self._impute(window_list, mask_policy, context)
        except ModuleNotFoundError as exc:
            return self._failure(
                C21TaskId.IMPUTATION,
                OpenModelAdapterStatus.MISSING_DEPENDENCY,
                "execute",
                f"{self.display_name} dependency import failed",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=f"missing:{exc.name or ','.join(self.required_modules)}",
                runtime_seconds=time.monotonic() - started,
                input_shape=self._input_shape(window_list),
                metadata_extra={"mask_policy": dict(mask_policy)},
            )
        except Exception as exc:
            status, weight = self._load_exception_status(exc)
            return self._failure(
                C21TaskId.IMPUTATION,
                status,
                "execute",
                f"{self.display_name} imputation runtime failed",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=dependency,
                weight=weight,
                runtime_seconds=time.monotonic() - started,
                input_shape=self._input_shape(window_list),
                metadata_extra={"mask_policy": dict(mask_policy)},
            )

        if isinstance(raw_reconstruction, AdapterFailure):
            return raw_reconstruction

        imputations = np.asarray(raw_reconstruction, dtype=float)
        if imputations.shape != expected.shape:
            return self._failure(
                C21TaskId.IMPUTATION,
                OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE,
                "execute",
                (
                    f"{self.display_name} reconstruction shape mismatch: "
                    f"expected {expected.shape}, got {imputations.shape}"
                ),
                "ShapeMismatch",
                f"expected={expected.shape}; got={imputations.shape}",
                context=context,
                dependency=dependency,
                weight="available",
                runtime_seconds=time.monotonic() - started,
                input_shape=self._input_shape(window_list),
                expected_shape_or_constraint=str(expected.shape),
                metadata_extra={"mask_policy": dict(mask_policy)},
            )

        runtime_seconds = time.monotonic() - started
        return AdapterTaskOutput(
            model_id=self.model_id,
            task_id=C21TaskId.IMPUTATION,
            status=OpenModelAdapterStatus.AVAILABLE_AND_RAN,
            imputations=imputations,
            metrics={
                "runtime_seconds": runtime_seconds,
                "finite_value_ratio": self._finite_value_ratio(imputations),
            },
            input_shape=self._input_shape(window_list),
            output_shape={"imputations": list(imputations.shape)},
            runtime_seconds=runtime_seconds,
            adapter_name=self.__class__.__name__,
            model_ref=self.model_ref,
            cache_dir=context.cache_dir,
            actual_network_used=False,
            metadata={
                **self._execution_metadata(context),
                "dependency_status": dependency,
                "weight_status": "available",
                "mask_policy": dict(mask_policy),
            },
        )

    def _embed(
        self,
        windows: list[Any],
        context: AdapterExecutionContext,
    ) -> AdapterFailure:
        for module_name in self.required_modules:
            self._import_dependency(module_name)
        return self._interface_review_failure(
            C21TaskId.REPRESENTATION,
            windows,
            context,
            "representation",
        )

    def _impute(
        self,
        windows: list[Any],
        mask_policy: Mapping[str, object],
        context: AdapterExecutionContext,
    ) -> AdapterFailure:
        for module_name in self.required_modules:
            self._import_dependency(module_name)
        return self._interface_review_failure(
            C21TaskId.IMPUTATION,
            windows,
            context,
            "imputation",
            {"mask_policy": dict(mask_policy)},
        )

    def _dependency_available(self, name: str) -> bool:
        return dependency_status((name,)) == "available"

    def _dependency_status(self) -> str:
        return dependency_status(self.required_modules, self._dependency_available)

    def _missing_dependency(
        self,
        task_id: C21TaskId,
        stage: str,
        dependency: str,
        context: AdapterExecutionContext,
    ) -> AdapterFailure:
        return self._failure(
            task_id,
            OpenModelAdapterStatus.MISSING_DEPENDENCY,
            stage,
            f"{self.display_name} dependency modules are unavailable",
            "MissingDependency",
            dependency,
            context=context,
            dependency=dependency,
        )

    def _interface_review_failure(
        self,
        task_id: C21TaskId,
        windows: list[Any],
        context: AdapterExecutionContext,
        task_name: str,
        metadata_extra: dict[str, Any] | None = None,
    ) -> AdapterFailure:
        return self._failure(
            task_id,
            OpenModelAdapterStatus.LICENSE_OR_INTERFACE_NEEDS_REVIEW,
            "execute",
            (
                f"{self.display_name} dependency import succeeded, but the official "
                f"{task_name} API path still needs review before loading weights"
            ),
            "InterfaceNeedsReview",
            self.official_api_detail,
            context=context,
            dependency="available",
            weight="not_checked",
            input_shape=self._input_shape(windows),
            metadata_extra=metadata_extra,
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
        metadata_extra: dict[str, Any] | None = None,
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
            metadata={
                **self._execution_metadata(context),
                **({} if metadata_extra is None else metadata_extra),
            },
        )

    @staticmethod
    def _input_shape(windows: list[Any]) -> dict[str, Any]:
        first = windows[0] if windows else None
        return {
            "windows": len(windows),
            "X": list(np.asarray(first.X).shape) if first is not None else None,
        }

    @staticmethod
    def _execution_metadata(context: AdapterExecutionContext) -> dict[str, Any]:
        return {
            "allow_network": context.allow_network,
            "allow_download": context.allow_download,
        }

    @staticmethod
    def _finite_value_ratio(values: np.ndarray) -> float:
        if values.size == 0:
            return 1.0
        return float(np.isfinite(values).sum() / values.size)
