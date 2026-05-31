from dataclasses import dataclass

import numpy as np

from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.baselines.seasonal_naive import StageSeasonalNaiveForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics


def test_robust_stage_forecaster_outputs_intervals(model_windows):
    model = RobustStageForecaster()
    preds = model.fit(model_windows.train).predict(model_windows.test)
    assert {"y_hat", "q_low", "q_high"} <= set(preds)
    metrics = forecasting_metrics(preds, model_windows.test)
    assert "mae" in metrics
    assert "interval_coverage" in metrics
    assert metrics["interval_coverage"] >= 0


def test_robust_stage_forecaster_is_stage_aware():
    @dataclass
    class Window:
        y: np.ndarray
        X: np.ndarray
        stage_token: np.ndarray

    low_stage = Window(y=np.full((4, 1), 1.0), X=np.zeros((4, 1)), stage_token=np.array(["抽真空"] * 4))
    high_stage = Window(y=np.full((4, 1), 10.0), X=np.zeros((4, 1)), stage_token=np.array(["溶解"] * 4))

    preds = RobustStageForecaster().fit([low_stage, high_stage]).predict([low_stage, high_stage])

    assert set(preds["stage"]) == {"抽真空", "溶解"}
    assert preds["y_hat"][0, :, 0].mean() < preds["y_hat"][1, :, 0].mean()


def test_stage_seasonal_naive_uses_stage_history():
    @dataclass
    class Window:
        y: np.ndarray
        X: np.ndarray
        stage_token: np.ndarray

    vacuum = Window(y=np.full((3, 2), 2.0), X=np.full((5, 2), 1.0), stage_token=np.array(["抽真空"] * 5))
    melting = Window(y=np.full((3, 2), 20.0), X=np.full((5, 2), 10.0), stage_token=np.array(["溶解"] * 5))

    preds = StageSeasonalNaiveForecaster().fit([vacuum, melting]).predict([vacuum, melting])

    assert preds["y_hat"][0, :, :].mean() < preds["y_hat"][1, :, :].mean()
