import sys
import types

import numpy as np
import pytest

import b08_model_core.adapters.open_models as open_models
import b08_model_core.adapters.open_models.base as open_model_base
from b08_model_core.adapters.open_models import build_open_model_adapter
from b08_model_core.adapters.open_models.chronos import ChronosOpenModelAdapter
from b08_model_core.adapters.open_models.moirai_uni2ts import (
    MoiraiUni2TSOpenModelAdapter,
)
from b08_model_core.adapters.open_models.moment import MomentOpenModelAdapter
from b08_model_core.adapters.open_models.timesfm import TimesFMOpenModelAdapter
from b08_model_core.adapters.open_models.ttm import TTMOpenModelAdapter
from b08_model_core.adapters.open_models.units import UniTSOpenModelAdapter
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
from b08_model_core.tasks.window_builder import ModelWindow


@pytest.fixture
def model_windows():
    windows = []
    for index in range(2):
        x = np.arange(8, dtype=float).reshape(4, 2) + index
        y = np.arange(4, dtype=float).reshape(2, 2) + index
        windows.append(
            ModelWindow(
                X=x,
                mask=np.ones_like(x, dtype=bool),
                delta_t=np.zeros(x.shape[0]),
                stage_token=np.array(["stage"] * x.shape[0], dtype=object),
                sensor_token=["sensor_0", "sensor_1"],
                domain_token=["domain", "domain"],
                device_token="FU13",
                y=y,
                degradation_label="normal",
            )
        )
    return windows


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


def test_chronos_adapter_declares_chronos2_primary_and_bolt_fallback():
    adapter = ChronosOpenModelAdapter()
    assert adapter.model_ref == "amazon/chronos-2"
    assert adapter.target_model_ref == "amazon/chronos-2"
    assert adapter.fallback_model_ref == "amazon/chronos-bolt-base"
    assert "chronos" in adapter.target_package_hint.lower()
    assert "forecasting" in adapter.target_task_fit


def test_timesfm_adapter_declares_timesfm25_target():
    adapter = TimesFMOpenModelAdapter()
    assert adapter.model_ref == "google/timesfm-2.5-200m-pytorch"
    assert adapter.target_model_ref == "google/timesfm-2.5-200m-pytorch"
    assert adapter.fallback_model_ref is None
    assert "timesfm" in adapter.target_package_hint.lower()
    assert "forecasting" in adapter.target_task_fit


def test_moirai_adapter_declares_moirai20_target_and_license_note():
    adapter = MoiraiUni2TSOpenModelAdapter()
    assert adapter.model_ref == "Salesforce/moirai-2.0-R-small"
    assert adapter.target_model_ref == "Salesforce/moirai-2.0-R-small"
    assert adapter.fallback_model_ref == "Salesforce/moirai-1.1-R-small"
    assert "uni2ts" in adapter.target_package_hint.lower()
    assert "license" in adapter.target_license_note.lower()


def test_moment_and_units_adapters_declare_interface_targets():
    moment = MomentOpenModelAdapter()
    units = UniTSOpenModelAdapter()
    assert "representation" in moment.target_task_fit
    assert "imputation" in moment.target_task_fit
    assert "representation" in units.target_task_fit
    assert "imputation" in units.target_task_fit


def test_ttm_adapter_runs_forecasting_when_runtime_is_injected(monkeypatch, model_windows):
    adapter = TTMOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(adapter, "_predict_with_ttm", lambda windows, context: np.stack([w.y for w in windows]))
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    output = adapter.run_forecasting(model_windows[:2], context)

    assert output.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert output.predictions.shape == np.stack([w.y for w in model_windows[:2]]).shape


def test_ttm_adapter_records_download_allowed_as_network_not_verified(
    monkeypatch,
    model_windows,
):
    adapter = TTMOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(
        adapter,
        "_predict_with_ttm",
        lambda windows, context: np.stack([w.y for w in windows]),
    )
    context = AdapterExecutionContext(True, True, "hf_cache", 900)

    output = adapter.run_forecasting(model_windows[:2], context)

    assert output.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert output.actual_network_used == "download_allowed_not_verified"


def test_ttm_adapter_reports_missing_dependency_without_runtime(monkeypatch, model_windows):
    adapter = TTMOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: False)
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    readiness = adapter.inspect_environment(context)
    output = adapter.run_forecasting(model_windows[:1], context)

    assert readiness.status == OpenModelAdapterStatus.MISSING_DEPENDENCY
    assert readiness.failure_stage == "inspect"
    assert output.status == OpenModelAdapterStatus.MISSING_DEPENDENCY
    assert output.failure_stage == "execute"


@pytest.mark.parametrize(
    "adapter_class",
    [
        ChronosOpenModelAdapter,
        TimesFMOpenModelAdapter,
        MoiraiUni2TSOpenModelAdapter,
    ],
)
def test_forecasting_adapter_reports_missing_dependency(adapter_class, monkeypatch):
    adapter = adapter_class()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: False)
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    failure = adapter.inspect_environment(context)

    assert failure.status == OpenModelAdapterStatus.MISSING_DEPENDENCY
    assert failure.failure_stage == "inspect"


@pytest.mark.parametrize(
    "adapter_class",
    [
        ChronosOpenModelAdapter,
        TimesFMOpenModelAdapter,
        MoiraiUni2TSOpenModelAdapter,
    ],
)
def test_forecasting_adapter_runs_with_injected_runtime(
    adapter_class,
    monkeypatch,
    model_windows,
):
    adapter = adapter_class()
    expected = np.stack([window.y for window in model_windows[:2]])
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(
        adapter,
        "_predict",
        lambda windows, context: np.stack([window.y for window in windows]),
    )
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    output = adapter.run_forecasting(model_windows[:2], context)

    assert output.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert output.predictions.shape == expected.shape
    assert output.input_shape["windows"] == 2
    assert output.output_shape["predictions"] == list(expected.shape)
    assert output.actual_network_used is False


def test_forecasting_adapter_accepts_explicit_runtime_hook(
    monkeypatch,
    model_windows,
):
    adapter = ChronosOpenModelAdapter(
        runtime_predictor=lambda windows, context: np.stack([window.y for window in windows])
    )
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    output = adapter.run_forecasting(model_windows[:2], context)

    assert output.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert output.predictions.shape == np.stack([w.y for w in model_windows[:2]]).shape


def test_forecasting_adapter_records_download_allowed_as_network_not_verified(
    monkeypatch,
    model_windows,
):
    adapter = ChronosOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(
        adapter,
        "_predict",
        lambda windows, context: np.stack([window.y for window in windows]),
    )
    context = AdapterExecutionContext(True, True, "hf_cache", 900)

    output = adapter.run_forecasting(model_windows[:2], context)

    assert output.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert output.actual_network_used == "download_allowed_not_verified"


def test_chronos_adapter_rejects_prediction_shape_mismatch(monkeypatch, model_windows):
    adapter = ChronosOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(
        adapter,
        "_predict",
        lambda windows, context: np.zeros((len(windows), 1, 1)),
    )
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    failure = adapter.run_forecasting(model_windows[:2], context)

    assert failure.status == OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE
    assert failure.expected_shape_or_constraint == str(
        np.stack([window.y for window in model_windows[:2]]).shape
    )


def test_chronos_adapter_maps_offline_runtime_exception_to_blocked_weights(
    monkeypatch,
    model_windows,
):
    adapter = ChronosOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)

    def fail_to_download(_windows, _context):
        raise RuntimeError("offline mode blocked checkpoint download")

    monkeypatch.setattr(adapter, "_predict", fail_to_download)
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    failure = adapter.run_forecasting(model_windows[:1], context)

    assert failure.status == OpenModelAdapterStatus.MISSING_OR_BLOCKED_WEIGHTS
    assert failure.weight_status == "missing_or_blocked"


@pytest.mark.parametrize(
    "adapter_class",
    [
        MomentOpenModelAdapter,
        UniTSOpenModelAdapter,
    ],
)
def test_representation_imputation_adapter_reports_missing_dependency(
    adapter_class,
    monkeypatch,
):
    adapter = adapter_class()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: False)
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    failure = adapter.inspect_environment(context)

    assert failure.status == OpenModelAdapterStatus.MISSING_DEPENDENCY
    assert failure.failure_stage == "inspect"


def test_moment_adapter_attempts_representation_and_imputation_with_injected_runtime(
    monkeypatch,
    model_windows,
):
    adapter = MomentOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(
        adapter,
        "_embed",
        lambda windows, context: np.ones((len(windows), 4)),
    )
    monkeypatch.setattr(
        adapter,
        "_impute",
        lambda windows, mask_policy, context: np.stack([w.X for w in windows]),
    )
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    rep = adapter.run_representation(model_windows[:2], context)
    imp = adapter.run_imputation(
        model_windows[:2],
        {"mask_ratio": 0.2, "seed": 7},
        context,
    )

    assert rep.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert rep.representations.shape == (2, 4)
    assert rep.output_shape["representations"] == [2, 4]
    assert rep.output_shape["embedding_shape"] == [2, 4]
    assert rep.metrics["finite_value_ratio"] == 1.0
    assert imp.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert imp.imputations.shape == np.stack([w.X for w in model_windows[:2]]).shape
    assert imp.output_shape["imputations"] == list(imp.imputations.shape)


def test_units_adapter_attempts_representation_and_imputation_with_injected_runtime(
    monkeypatch,
    model_windows,
):
    adapter = UniTSOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(
        adapter,
        "_embed",
        lambda windows, context: np.ones((len(windows), 4)),
    )
    monkeypatch.setattr(
        adapter,
        "_impute",
        lambda windows, mask_policy, context: np.stack([w.X for w in windows]),
    )
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    rep = adapter.run_representation(model_windows[:2], context)
    imp = adapter.run_imputation(
        model_windows[:2],
        {"mask_ratio": 0.2, "seed": 7},
        context,
    )

    assert rep.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert rep.representations.shape == (2, 4)
    assert rep.output_shape["representations"] == [2, 4]
    assert rep.output_shape["embedding_shape"] == [2, 4]
    assert rep.metrics["finite_value_ratio"] == 1.0
    assert imp.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert imp.imputations.shape == np.stack([w.X for w in model_windows[:2]]).shape
    assert imp.output_shape["imputations"] == list(imp.imputations.shape)


def test_representation_imputation_adapter_accepts_explicit_runtime_hooks(
    monkeypatch,
    model_windows,
):
    adapter = MomentOpenModelAdapter(
        embedding_runtime=lambda windows, context: np.ones((len(windows), 4)),
        imputation_runtime=lambda windows, mask_policy, context: np.stack(
            [window.X for window in windows]
        ),
    )
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    rep = adapter.run_representation(model_windows[:2], context)
    imp = adapter.run_imputation(model_windows[:2], {"mask_ratio": 0.2}, context)

    assert rep.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert rep.representations.shape == (2, 4)
    assert imp.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert imp.imputations.shape == np.stack([w.X for w in model_windows[:2]]).shape


def test_representation_adapter_records_download_allowed_as_network_not_verified(
    monkeypatch,
    model_windows,
):
    adapter = MomentOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(
        adapter,
        "_embed",
        lambda windows, context: np.ones((len(windows), 4)),
    )
    context = AdapterExecutionContext(True, True, "hf_cache", 900)

    output = adapter.run_representation(model_windows[:2], context)

    assert output.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert output.actual_network_used == "download_allowed_not_verified"


@pytest.mark.parametrize(
    "adapter_class",
    [
        MomentOpenModelAdapter,
        UniTSOpenModelAdapter,
    ],
)
def test_representation_imputation_adapter_rejects_imputation_shape_mismatch(
    adapter_class,
    monkeypatch,
    model_windows,
):
    adapter = adapter_class()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(
        adapter,
        "_impute",
        lambda windows, mask_policy, context: np.zeros((len(windows), 1, 1)),
    )
    context = AdapterExecutionContext(False, False, "hf_cache", 900)

    failure = adapter.run_imputation(model_windows[:2], {"mask_ratio": 0.2}, context)

    assert failure.status == OpenModelAdapterStatus.UNSUPPORTED_WINDOW_SHAPE
    assert failure.expected_shape_or_constraint == str(
        np.stack([w.X for w in model_windows[:2]]).shape
    )


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


@pytest.mark.parametrize(
    "message",
    [
        "weighted loss produced nan",
        "lightweight runtime failed",
    ],
)
def test_weight_substrings_are_not_blocked_weight_failures(message):
    adapter = build_open_model_adapter("chronos")

    status, _weight_status = adapter._load_exception_status(RuntimeError(message))

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
