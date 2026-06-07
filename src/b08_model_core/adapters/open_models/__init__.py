"""C2.1 open model adapter contract.

Concrete adapters are intentionally not imported here because they may require
optional model packages that are absent in the default offline workflow.
"""

from b08_model_core.adapters.open_models.base import (
    AdapterExecutionContext,
    AdapterFailure,
    AdapterReadiness,
    AdapterRunResult,
    AdapterTaskOutput,
    OpenModelAdapter,
    OpenModelAdapterStatus,
    dependency_status as _dependency_status,
)
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class _DependencyFirstOpenModelAdapter(OpenModelAdapter):
    display_name = ""
    required_modules: tuple[str, ...] = ()
    model_ref = "needs_review"

    def inspect_environment(
        self,
        context: AdapterExecutionContext,
    ) -> AdapterReadiness | AdapterFailure:
        dependency = _dependency_status(self.required_modules)
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
            known_limitations=("real model interface is not implemented in Task 5",),
        )

    def load(
        self,
        context: AdapterExecutionContext,
    ) -> OpenModelAdapter | AdapterFailure:
        dependency = _dependency_status(self.required_modules)
        if dependency != "available":
            return self._missing_dependency("load", dependency, context)

        try:
            for module_name in self.required_modules:
                self._import_dependency(module_name)
        except ModuleNotFoundError as exc:
            return self._failure(
                self.supported_tasks[0],
                OpenModelAdapterStatus.MISSING_DEPENDENCY,
                "load",
                f"{self.display_name} dependency import failed",
                type(exc).__name__,
                str(exc),
                context=context,
                dependency=f"missing:{exc.name or ','.join(self.required_modules)}",
            )
        except Exception as exc:
            status, weight = self._load_exception_status(exc)
            return self._failure(
                self.supported_tasks[0],
                status,
                "load",
                f"{self.display_name} dependency import or runtime setup failed",
                type(exc).__name__,
                str(exc),
                context=context,
                weight=weight,
            )

        return self._failure(
            self.supported_tasks[0],
            OpenModelAdapterStatus.LICENSE_OR_INTERFACE_NEEDS_REVIEW,
            "load",
            (
                f"{self.display_name} dependency import succeeded, but official model "
                "construction and inference are not implemented in Task 5"
            ),
            "InterfaceNeedsReview",
            "dependency import succeeded; real model call intentionally disabled",
            context=context,
        )

    def _missing_dependency(
        self,
        stage: str,
        dependency: str,
        context: AdapterExecutionContext,
    ) -> AdapterFailure:
        return self._failure(
            self.supported_tasks[0],
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
            adapter_name=self.__class__.__name__,
            model_ref=self.model_ref,
            cache_dir=context.cache_dir,
            actual_network_used=False,
        )

    @staticmethod
    def _import_dependency(module_name: str):
        from importlib import import_module

        return import_module(module_name)

    @staticmethod
    def _load_exception_status(exc: Exception) -> tuple[OpenModelAdapterStatus, str]:
        import re

        detail = str(exc).lower()
        if any(
            token in detail
            for token in (
                "checkpoint",
                "offline",
                "not found in cache",
                "cache file",
                "cache dir",
            )
        ) or re.search(
            r"(?<![a-z0-9_])weights?(?![a-z0-9_])",
            detail,
        ) or re.search(r"(?<![a-z0-9_])download(?![a-z0-9_])", detail):
            return OpenModelAdapterStatus.MISSING_OR_BLOCKED_WEIGHTS, "missing_or_blocked"
        if any(token in detail for token in ("license", "interface", "api", "review")):
            return OpenModelAdapterStatus.LICENSE_OR_INTERFACE_NEEDS_REVIEW, "not_checked"
        return OpenModelAdapterStatus.RUNTIME_FAILED, "unknown"


def build_open_model_adapter(model_id: str):
    if model_id == "ttm":
        from b08_model_core.adapters.open_models.ttm import TTMOpenModelAdapter

        return TTMOpenModelAdapter()
    if model_id == "chronos":
        from b08_model_core.adapters.open_models.chronos import ChronosOpenModelAdapter

        return ChronosOpenModelAdapter()
    if model_id == "timesfm":
        from b08_model_core.adapters.open_models.timesfm import TimesFMOpenModelAdapter

        return TimesFMOpenModelAdapter()
    if model_id == "moirai_uni2ts":
        from b08_model_core.adapters.open_models.moirai_uni2ts import (
            MoiraiUni2TSOpenModelAdapter,
        )

        return MoiraiUni2TSOpenModelAdapter()
    if model_id == "moment":
        from b08_model_core.adapters.open_models.moment import MomentOpenModelAdapter

        return MomentOpenModelAdapter()
    if model_id == "units":
        from b08_model_core.adapters.open_models.units import UniTSOpenModelAdapter

        return UniTSOpenModelAdapter()
    raise ValueError(f"unknown open model adapter: {model_id}")


__all__ = [
    "AdapterExecutionContext",
    "AdapterFailure",
    "AdapterReadiness",
    "AdapterRunResult",
    "AdapterTaskOutput",
    "build_open_model_adapter",
    "OpenModelAdapter",
    "OpenModelAdapterStatus",
]
