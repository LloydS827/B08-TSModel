from __future__ import annotations

import numpy as np


class RollingSensorForecaster:
    def __init__(self, window_size: int = 8) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be greater than 0")
        self.window_size = window_size

    def fit(self, windows: list[object]) -> "RollingSensorForecaster":
        return self

    def predict(self, windows: list[object]) -> dict[str, np.ndarray]:
        predictions = []
        for window in windows:
            context = np.asarray(window.X, dtype=float)
            mask = np.asarray(window.mask, dtype=bool)
            tail = context[-self.window_size :]
            tail_mask = mask[-self.window_size :]
            baseline = self._masked_mean(tail, tail_mask)
            horizon = int(window.y.shape[0])
            predictions.append(np.repeat(baseline[None, :], horizon, axis=0))
        return {"y_hat": np.stack(predictions, axis=0)}

    @staticmethod
    def _masked_mean(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
        counts = mask.sum(axis=0)
        totals = np.where(mask, values, 0.0).sum(axis=0)
        return np.divide(totals, counts, out=np.zeros_like(totals, dtype=float), where=counts > 0)
