from __future__ import annotations

import numpy as np


def forecasting_metrics(predictions: dict[str, np.ndarray], windows: list[object]) -> dict[str, float]:
    truth = np.stack([window.y for window in windows], axis=0)
    y_hat = predictions["y_hat"]
    mae = float(np.mean(np.abs(y_hat - truth)))
    coverage = float(np.mean((truth >= predictions["q_low"]) & (truth <= predictions["q_high"])))
    return {"mae": mae, "interval_coverage": coverage}
