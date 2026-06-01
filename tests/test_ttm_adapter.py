from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
import sys
from types import ModuleType

import numpy as np
import pytest

import b08_model_core.adapters.ttm_adapter as ttm_adapter
from b08_model_core.adapters.ttm_adapter import TTMForecastAdapter
from b08_model_core.foundation.results import FoundationModelStatus


@dataclass
class Window:
    X: np.ndarray
    mask: np.ndarray
    y: np.ndarray
    sensor_token: list[str]


def _windows_for_runtime() -> list[Window]:
    return [
        Window(
            X=np.array([[8.0, 90.0], [10.0, 100.0], [12.0, 110.0]]),
            mask=np.ones((3, 2), dtype=bool),
            y=np.array([[14.0, 120.0], [16.0, 130.0]]),
            sensor_token=["pressure", "temperature"],
        )
    ]


class FakeRuntime:
    def __init__(self, output: np.ndarray | Exception) -> None:
        self.output = output
        self.calls: list[tuple[object, str, int, bool, str | None]] = []

    def predict(
        self,
        prepared: object,
        checkpoint: str,
        prediction_length: int,
        allow_download: bool,
        model_cache_dir: str | None,
    ) -> np.ndarray:
        self.calls.append((prepared, checkpoint, prediction_length, allow_download, model_cache_dir))
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


def test_missing_dependency_predict_returns_result_without_weight_imports():
    checked_modules: list[str] = []

    def dependency_checker(module_name: str) -> bool:
        checked_modules.append(module_name)
        return False

    adapter = TTMForecastAdapter(dependency_checker=dependency_checker)

    result = adapter.predict([], context_length=2, prediction_length=1, model_cache_dir="/private/tmp/b08-model-cache")

    assert result.status == FoundationModelStatus.MISSING_DEPENDENCY
    assert result.model_name == "TTM"
    assert result.adapter_name == "ttm"
    assert "uv sync --extra dev --extra foundation-ttm" in result.reason
    assert result.dependency_status.startswith("missing:")
    assert result.weight_status == "not_attempted"
    assert result.cache_dir == "/private/tmp/b08-model-cache"
    assert checked_modules == ["tsfm_public", "transformers"]


def test_injected_runtime_predict_succeeds_and_unscales_output():
    runtime = FakeRuntime(np.array([[[2.0, 3.0], [4.0, 5.0]]]))
    adapter = TTMForecastAdapter(
        checkpoint="local-ttm",
        dependency_checker=lambda _: True,
        runtime_factory=lambda: runtime,
    )

    result = adapter.predict(
        _windows_for_runtime(),
        context_length=3,
        prediction_length=2,
        allow_download=True,
        model_cache_dir="/private/tmp/b08-model-cache",
    )

    assert result.status == FoundationModelStatus.AVAILABLE_AND_RAN
    assert result.weight_status == "available"
    assert result.dependency_status == "installed"
    assert result.cache_dir == "/private/tmp/b08-model-cache"
    np.testing.assert_allclose(
        result.y_hat,
        np.array([[[13.26598632, 124.49489743], [16.53197265, 140.82482905]]]),
    )
    assert len(runtime.calls) == 1
    prepared, checkpoint, prediction_length, allow_download, model_cache_dir = runtime.calls[0]
    assert checkpoint == "local-ttm"
    assert prediction_length == 2
    assert allow_download is True
    assert model_cache_dir == "/private/tmp/b08-model-cache"
    np.testing.assert_allclose(
        prepared.future_values,
        np.array([[[2.44948974, 2.44948974], [3.67423461, 3.67423461]]]),
    )


def test_injected_runtime_shape_mismatch_returns_unsupported_window_shape():
    adapter = TTMForecastAdapter(
        dependency_checker=lambda _: True,
        runtime_factory=lambda: FakeRuntime(np.ones((1, 1, 2))),
    )

    result = adapter.predict(_windows_for_runtime(), context_length=3, prediction_length=2)

    assert result.status == FoundationModelStatus.UNSUPPORTED_WINDOW_SHAPE
    assert "shape" in result.reason
    assert result.weight_status == "unknown"
    assert result.y_hat is None


def test_injected_runtime_offline_cache_error_returns_missing_or_blocked_weights():
    adapter = TTMForecastAdapter(
        dependency_checker=lambda _: True,
        runtime_factory=lambda: FakeRuntime(RuntimeError("offline cache miss")),
    )

    result = adapter.predict(_windows_for_runtime(), context_length=3, prediction_length=2)

    assert result.status == FoundationModelStatus.MISSING_OR_BLOCKED_WEIGHTS
    assert result.weight_status == "blocked_or_unknown"
    assert "offline cache miss" in result.reason


def test_injected_runtime_unexpected_error_returns_runtime_failed():
    adapter = TTMForecastAdapter(
        dependency_checker=lambda _: True,
        runtime_factory=lambda: FakeRuntime(RuntimeError("boom")),
    )

    result = adapter.predict(_windows_for_runtime(), context_length=3, prediction_length=2)

    assert result.status == FoundationModelStatus.RUNTIME_FAILED
    assert result.weight_status == "unknown"
    assert "boom" in result.reason


def test_hf_runtime_environment_restores_existing_values_when_prediction_raises(monkeypatch):
    monkeypatch.setenv("HF_HOME", "/existing/hf")
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")

    with pytest.raises(RuntimeError, match="forced"):
        with ttm_adapter.hf_runtime_environment("/private/tmp/new-hf-cache", allow_download=False):
            assert os.environ["HF_HOME"] == "/private/tmp/new-hf-cache"
            assert os.environ["HF_HUB_OFFLINE"] == "1"
            raise RuntimeError("forced")

    assert os.environ["HF_HOME"] == "/existing/hf"
    assert os.environ["HF_HUB_OFFLINE"] == "0"


def test_hf_runtime_environment_clears_offline_flag_for_download_and_restores_absent_values(monkeypatch):
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)

    with ttm_adapter.hf_runtime_environment("/private/tmp/new-hf-cache", allow_download=True):
        assert os.environ["HF_HOME"] == "/private/tmp/new-hf-cache"
        assert "HF_HUB_OFFLINE" not in os.environ

    assert "HF_HOME" not in os.environ
    assert "HF_HUB_OFFLINE" not in os.environ


def test_ttm_runtime_model_call_supplies_oov_frequency_token(monkeypatch):
    torch = pytest.importorskip("torch")
    captured: dict[str, object] = {}
    prepared = ttm_adapter.PreparedTTMWindows(
        past_values=np.ones((1, 3, 2)),
        past_observed_mask=np.ones((1, 3, 2), dtype=bool),
        future_values=np.ones((1, 2, 2)),
        sensor_token=["pressure", "temperature"],
        channel_center=np.zeros((1, 2)),
        channel_scale=np.ones((1, 2)),
    )

    class FakeModel:
        def eval(self):
            captured["eval_called"] = True

        def __call__(self, **kwargs):
            captured["kwargs"] = kwargs
            return type("PredictionOutput", (), {"prediction_outputs": torch.zeros((1, 2, 2))})()

    fake_tsfm = ModuleType("tsfm_public")
    fake_toolkit = ModuleType("tsfm_public.toolkit")
    fake_get_model = ModuleType("tsfm_public.toolkit.get_model")
    fake_get_model.get_model = lambda *args, **kwargs: FakeModel()
    monkeypatch.setitem(sys.modules, "tsfm_public", fake_tsfm)
    monkeypatch.setitem(sys.modules, "tsfm_public.toolkit", fake_toolkit)
    monkeypatch.setitem(sys.modules, "tsfm_public.toolkit.get_model", fake_get_model)

    output = ttm_adapter.TTMRuntime().predict(
        prepared,
        checkpoint="local-ttm",
        prediction_length=2,
        allow_download=False,
        model_cache_dir=None,
    )

    kwargs = captured["kwargs"]
    assert captured["eval_called"] is True
    assert kwargs["return_loss"] is False
    assert int(kwargs["freq_token"][0].item()) == 0
    assert kwargs["freq_token"].dtype == torch.int
    np.testing.assert_array_equal(output, np.zeros_like(prepared.future_values))


def test_top_level_import_does_not_require_heavy_runtime_modules(monkeypatch):
    original_import = __import__
    heavy_modules = ("torch", "transformers", "tsfm_public")

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(heavy_modules):
            raise AssertionError(f"top-level import tried to import {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", guarded_import)
    monkeypatch.delitem(sys.modules, "b08_model_core.adapters.ttm_adapter", raising=False)

    module = importlib.import_module("b08_model_core.adapters.ttm_adapter")

    assert module.TTMForecastAdapter.name == "TTM"


def test_prepare_windows_preserves_shape_scaling_and_sensor_order():
    windows = [
        Window(
            X=np.array([[1.0, 10.0], [3.0, 10.0], [5.0, 30.0]]),
            mask=np.array([[True, True], [True, False], [True, True]]),
            y=np.array([[7.0, 50.0], [9.0, 70.0]]),
            sensor_token=["pressure", "temperature"],
        ),
        Window(
            X=np.array([[2.0, 100.0], [4.0, 140.0], [6.0, 180.0]]),
            mask=np.array([[True, True], [True, True], [True, True]]),
            y=np.array([[8.0, 220.0], [10.0, 260.0]]),
            sensor_token=["pressure", "temperature"],
        ),
    ]
    adapter = TTMForecastAdapter(dependency_checker=lambda _: False)

    prepared = adapter.prepare_windows(windows, context_length=3, prediction_length=2)

    assert prepared.past_values.shape == (2, 3, 2)
    assert prepared.past_observed_mask.shape == (2, 3, 2)
    assert prepared.future_values.shape == (2, 2, 2)
    assert prepared.sensor_token == ["pressure", "temperature"]
    np.testing.assert_allclose(prepared.channel_center[0], [3.0, 20.0])
    np.testing.assert_allclose(prepared.channel_scale[0], [np.sqrt(8.0 / 3.0), 10.0])
    np.testing.assert_allclose(prepared.past_values[0, :, 0], [-1.22474487, 0.0, 1.22474487])
    np.testing.assert_allclose(prepared.past_values[0, :, 1], [-1.0, -1.0, 1.0])
    np.testing.assert_allclose(prepared.future_values[0, :, 0], [2.44948974, 3.67423461])
    np.testing.assert_array_equal(prepared.past_observed_mask[0], windows[0].mask)


def test_prepare_windows_raises_value_error_for_shape_mismatch():
    windows = [
        Window(
            X=np.ones((2, 2)),
            mask=np.ones((2, 2), dtype=bool),
            y=np.ones((1, 2)),
            sensor_token=["pressure", "temperature"],
        )
    ]
    adapter = TTMForecastAdapter(dependency_checker=lambda _: False)

    with pytest.raises(ValueError, match="context_length"):
        adapter.prepare_windows(windows, context_length=3, prediction_length=1)


def test_prepare_windows_raises_value_error_for_sensor_order_mismatch():
    windows = [
        Window(
            X=np.ones((2, 2)),
            mask=np.ones((2, 2), dtype=bool),
            y=np.ones((1, 2)),
            sensor_token=["pressure", "temperature"],
        ),
        Window(
            X=np.ones((2, 2)),
            mask=np.ones((2, 2), dtype=bool),
            y=np.ones((1, 2)),
            sensor_token=["temperature", "pressure"],
        ),
    ]
    adapter = TTMForecastAdapter(dependency_checker=lambda _: False)

    with pytest.raises(ValueError, match="sensor_token order"):
        adapter.prepare_windows(windows, context_length=2, prediction_length=1)
