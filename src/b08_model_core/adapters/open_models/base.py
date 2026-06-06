from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Callable, Iterable

from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class OpenModelAdapterStatus(StrEnum):
    READY = "ready"
    AVAILABLE_AND_RAN = "available_and_ran"
    MISSING_DEPENDENCY = "missing_dependency"
    MISSING_OR_BLOCKED_WEIGHTS = "missing_or_blocked_weights"
    UNSUPPORTED_TASK = "unsupported_task"
    UNSUPPORTED_WINDOW_SHAPE = "unsupported_window_shape"
    RUNTIME_FAILED = "runtime_failed"
    TIMEOUT = "timeout"
    LICENSE_OR_INTERFACE_NEEDS_REVIEW = "license_or_interface_needs_review"
    SKIPPED_BY_CONFIG = "skipped_by_config"


@dataclass
class AdapterExecutionContext:
    allow_network: bool
    allow_download: bool
    cache_dir: str | Path
    # Applied to each model-task attempt, not to the full evaluation run.
    timeout_seconds_per_model: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterReadiness:
    model_id: str
    dependency_status: str
    weight_status: str
    adapter_status: OpenModelAdapterStatus
    adapter_name: str = ""
    model_ref: str | None = None
    cache_dir: str | Path | None = None
    actual_network_used: bool | None = None
    known_limitations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterTaskOutput:
    model_id: str
    task_id: C21TaskId
    status: OpenModelAdapterStatus
    predictions: Any = None
    representations: Any = None
    imputations: Any = None
    metrics: dict[str, Any] = field(default_factory=dict)
    baseline_metrics: dict[str, Any] = field(default_factory=dict)
    input_shape: dict[str, Any] = field(default_factory=dict)
    output_shape: dict[str, Any] = field(default_factory=dict)
    runtime_seconds: float | None = None
    adapter_name: str = ""
    model_ref: str | None = None
    cache_dir: str | Path | None = None
    actual_network_used: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterFailure:
    model_id: str
    task_id: C21TaskId
    status: OpenModelAdapterStatus
    failure_stage: str
    failure_reason: str = ""
    error_type: str = ""
    error_detail: str = ""
    dependency_status: str = "unknown"
    weight_status: str = "unknown"
    input_shape: dict[str, Any] = field(default_factory=dict)
    expected_shape_or_constraint: str | None = None
    adapter_name: str = ""
    runtime_seconds: float | None = None
    model_ref: str | None = None
    cache_dir: str | Path | None = None
    actual_network_used: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


AdapterRunResult = AdapterTaskOutput | AdapterFailure


class OpenModelAdapter:
    model_id = ""
    supported_tasks: tuple[C21TaskId, ...] = ()

    def inspect_environment(self, context: AdapterExecutionContext) -> AdapterReadiness:
        return AdapterReadiness(
            model_id=self.model_id,
            dependency_status="unknown",
            weight_status="unknown",
            adapter_status=OpenModelAdapterStatus.LICENSE_OR_INTERFACE_NEEDS_REVIEW,
            adapter_name=self.__class__.__name__,
            cache_dir=context.cache_dir,
        )

    def load(self, context: AdapterExecutionContext) -> OpenModelAdapter:
        return self

    def run_forecasting(
        self,
        windows: Iterable[Any],
        context: AdapterExecutionContext,
    ) -> AdapterRunResult:
        return self.unsupported_task(C21TaskId.FORECASTING, windows, context)

    def run_representation(
        self,
        windows: Iterable[Any],
        context: AdapterExecutionContext,
    ) -> AdapterRunResult:
        return self.unsupported_task(C21TaskId.REPRESENTATION, windows, context)

    def run_imputation(
        self,
        windows: Iterable[Any],
        context: AdapterExecutionContext,
    ) -> AdapterRunResult:
        return self.unsupported_task(C21TaskId.IMPUTATION, windows, context)

    def unsupported_task(
        self,
        task_id: C21TaskId,
        windows: Iterable[Any],
        context: AdapterExecutionContext,
    ) -> AdapterRunResult:
        return AdapterFailure(
            model_id=self.model_id,
            task_id=task_id,
            status=OpenModelAdapterStatus.UNSUPPORTED_TASK,
            failure_stage="execute",
            failure_reason=f"{self.model_id} adapter does not support {task_id.value}",
            input_shape={"windows": _safe_len(windows)},
            expected_shape_or_constraint="supported task implementation",
            adapter_name=self.__class__.__name__,
            cache_dir=context.cache_dir,
        )


def dependency_status(
    modules: Iterable[str],
    dependency_checker: Callable[[str], bool] | None = None,
) -> str:
    checker = dependency_checker or _module_available
    module_names = tuple(modules)
    if not module_names:
        return "not_required"

    missing = [module_name for module_name in module_names if not checker(module_name)]
    if missing:
        return f"missing:{','.join(missing)}"
    return "available"


def _module_available(module_name: str) -> bool:
    try:
        return find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def _safe_len(value: Iterable[Any]) -> int | None:
    try:
        return len(value)  # type: ignore[arg-type]
    except TypeError:
        return None
