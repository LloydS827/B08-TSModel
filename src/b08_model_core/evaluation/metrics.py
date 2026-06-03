from __future__ import annotations

import numpy as np


def forecasting_metrics(predictions: dict[str, np.ndarray], windows: list[object]) -> dict[str, float | int | None]:
    truth = np.stack([window.y for window in windows], axis=0)
    y_hat = predictions["y_hat"]
    error = y_hat - truth
    mae = float(np.mean(np.abs(error)))
    rmse = float(np.sqrt(np.mean(error**2)))
    coverage = None
    if "q_low" in predictions and "q_high" in predictions:
        coverage = float(np.mean((truth >= predictions["q_low"]) & (truth <= predictions["q_high"])))
    return {"mae": mae, "rmse": rmse, "interval_coverage": coverage, "count": int(error.size)}
