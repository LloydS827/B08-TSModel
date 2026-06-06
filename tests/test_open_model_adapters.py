import numpy as np

from b08_model_core.adapters.open_models.base import (
    AdapterExecutionContext,
    AdapterFailure,
    AdapterReadiness,
    AdapterTaskOutput,
    OpenModelAdapter,
    OpenModelAdapterStatus,
    dependency_status,
)
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class FakeAdapter(OpenModelAdapter):
    model_id = "fake"
    supported_tasks = (C21TaskId.FORECASTING,)

    def inspect_environment(self, context):
        return AdapterReadiness(
            model_id=self.model_id,
            dependency_status="available",
            weight_status="not_required",
            adapter_status=OpenModelAdapterStatus.READY,
        )

    def load(self, context):
        return self

    def run_forecasting(self, windows, context):
        return AdapterTaskOutput(
            model_id=self.model_id,
            task_id=C21TaskId.FORECASTING,
            status=OpenModelAdapterStatus.AVAILABLE_AND_RAN,
            predictions=np.zeros((1, 1, 1)),
            metrics={"runtime_seconds": 0.01},
            input_shape={"windows": len(windows)},
            output_shape={"predictions": [1, 1, 1]},
        )


def test_fake_adapter_contract_returns_readiness_and_output():
    adapter = FakeAdapter()
    context = AdapterExecutionContext(
        allow_network=False,
        allow_download=False,
        cache_dir="hf_cache",
        timeout_seconds_per_model=900,
    )
    readiness = adapter.inspect_environment(context)
    assert readiness.adapter_status == OpenModelAdapterStatus.READY
    output = adapter.run_forecasting([], context)
    assert output.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert output.metrics["runtime_seconds"] == 0.01


def test_base_adapter_returns_unsupported_task_for_missing_method():
    adapter = FakeAdapter()
    context = AdapterExecutionContext(False, False, "hf_cache", 900)
    failure = adapter.run_representation([], context)
    assert isinstance(failure, AdapterFailure)
    assert failure.status == OpenModelAdapterStatus.UNSUPPORTED_TASK
    assert failure.failure_stage == "execute"


def test_dependency_status_reports_missing_dotted_module_without_raising():
    assert (
        dependency_status(["definitely_missing_parent.child"])
        == "missing:definitely_missing_parent.child"
    )
