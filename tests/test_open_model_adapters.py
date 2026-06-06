import sys
import types

import numpy as np
import pytest

import b08_model_core.adapters.open_models as open_models
import b08_model_core.adapters.open_models.base as open_model_base
from b08_model_core.adapters.open_models import build_open_model_adapter
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


def test_base_imputation_contract_accepts_mask_policy_and_returns_unsupported_task():
    adapter = FakeAdapter()
    context = AdapterExecutionContext(False, False, "hf_cache", 900)
    failure = adapter.run_imputation([], {"mask_ratio": 0.2, "seed": 7}, context)
    assert isinstance(failure, AdapterFailure)
    assert failure.status == OpenModelAdapterStatus.UNSUPPORTED_TASK
    assert failure.failure_stage == "execute"


def test_adapter_factory_returns_all_c21_adapters_without_importing_optional_packages():
    for model_id in ["ttm", "chronos", "timesfm", "moirai_uni2ts", "moment", "units"]:
        adapter = build_open_model_adapter(model_id)
        assert adapter.model_id == model_id


def test_adapter_factory_rejects_unknown_model():
    with pytest.raises(ValueError, match="unknown open model adapter"):
        build_open_model_adapter("unknown")


def test_package_root_does_not_expose_dependency_status():
    assert not hasattr(open_models, "dependency_status")


def test_cached_download_import_error_is_not_weight_failure():
    adapter = build_open_model_adapter("chronos")
    status, _weight_status = adapter._load_exception_status(
        RuntimeError("cached_download import error")
    )
    assert status != OpenModelAdapterStatus.MISSING_OR_BLOCKED_WEIGHTS
    assert status == OpenModelAdapterStatus.RUNTIME_FAILED


def test_dependency_status_reports_missing_dotted_module_without_raising():
    assert (
        dependency_status(["definitely_missing_parent.child"])
        == "missing:definitely_missing_parent.child"
    )


def test_dependency_status_reports_loaded_module_without_spec_as_missing(monkeypatch):
    module_name = "c21_loaded_without_spec"
    module = types.ModuleType(module_name)
    module.__spec__ = None
    monkeypatch.setitem(sys.modules, module_name, module)

    assert dependency_status([module_name]) == f"missing:{module_name}"


def test_dependency_status_reports_dotted_parent_spec_exception_as_missing(monkeypatch):
    module_name = "c21_parent.child"

    def raise_runtime_error(name):
        if name == module_name:
            raise RuntimeError("simulated parent import failure")
        return None

    monkeypatch.setattr(open_model_base, "find_spec", raise_runtime_error)

    assert dependency_status([module_name]) == f"missing:{module_name}"
