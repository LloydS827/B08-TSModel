import numpy as np

from b08_model_core.baselines.rolling import RollingSensorForecaster
from b08_model_core.tasks.window_builder import ModelWindow


def _window(values, mask=None):
    x = np.asarray(values, dtype=float)
    if mask is None:
        mask = np.ones_like(x, dtype=bool)
    return ModelWindow(
        X=x,
        mask=np.asarray(mask, dtype=bool),
        delta_t=np.zeros(x.shape[0]),
        stage_token=np.array(["溶解"] * x.shape[0], dtype=object),
        sensor_token=["LeakElec", "Other"],
        domain_token=["electrical", "other"],
        device_token="FU13",
        y=np.zeros((3, x.shape[1])),
        degradation_label="normal",
    )


def test_rolling_sensor_forecaster_repeats_context_tail_mean():
    window = _window([[1, 10], [2, 20], [3, 30], [4, 40]])

    predictions = RollingSensorForecaster(window_size=2).fit([]).predict([window])

    assert predictions["y_hat"].shape == (1, 3, 2)
    np.testing.assert_allclose(predictions["y_hat"][0], [[3.5, 35.0], [3.5, 35.0], [3.5, 35.0]])


def test_rolling_sensor_forecaster_ignores_masked_context_values():
    window = _window(
        [[1, 10], [2, 20], [3, 30], [4, 40]],
        mask=[[True, True], [True, True], [False, True], [True, False]],
    )

    predictions = RollingSensorForecaster(window_size=2).fit([]).predict([window])

    np.testing.assert_allclose(predictions["y_hat"][0], [[4.0, 30.0], [4.0, 30.0], [4.0, 30.0]])
