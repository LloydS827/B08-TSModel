from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from b08_model_core.adapters.ttm_adapter import TTMForecastAdapter
from b08_model_core.foundation.results import FoundationModelStatus


@dataclass
class Window:
    X: np.ndarray
    mask: np.ndarray
    y: np.ndarray
    sensor_token: list[str]


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
