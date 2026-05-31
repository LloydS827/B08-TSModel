from __future__ import annotations

import numpy as np

from b08_model_core.baselines.robust_forecaster import RobustStageForecaster


class StageSeasonalNaiveForecaster:
    """Repeat the latest observed stage-specific pattern as a simple delivery baseline."""

    def __init__(self) -> None:
        self.stage_patterns_: dict[str, np.ndarray] = {}
        self.global_pattern_: np.ndarray | None = None

    def fit(self, windows: list[object]) -> "StageSeasonalNaiveForecaster":
        if not windows:
            raise ValueError("at least one training window is required")
        self.global_pattern_ = windows[-1].y.copy()
        self.stage_patterns_ = {}
        for window in windows:
            self.stage_patterns_[RobustStageForecaster._stage(window)] = window.y.copy()
        return self

    @staticmethod
    def _resize_pattern(pattern: np.ndarray, prediction_length: int) -> np.ndarray:
        if len(pattern) == prediction_length:
            return pattern
        repeats = int(np.ceil(prediction_length / len(pattern)))
        return np.tile(pattern, (repeats, 1))[:prediction_length]

    def predict(self, windows: list[object]) -> dict[str, np.ndarray]:
        if self.global_pattern_ is None:
            raise RuntimeError("fit must be called before predict")
        y_hats = []
        stages = []
        for window in windows:
            stage = RobustStageForecaster._stage(window)
            stages.append(stage)
            pattern = self.stage_patterns_.get(stage, self.global_pattern_)
            y_hats.append(self._resize_pattern(pattern, window.y.shape[0]))
        y_hat = np.stack(y_hats, axis=0)
        return {"y_hat": y_hat, "q_low": y_hat, "q_high": y_hat, "stage": np.array(stages, dtype=object)}
