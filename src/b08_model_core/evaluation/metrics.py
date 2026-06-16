from __future__ import annotations

import numpy as np


def nasa_rul_score(prediction: object, truth: object) -> float:
    prediction_array, truth_array = _validated_metric_arrays(prediction, truth)
    error = prediction_array - truth_array
    score = np.where(
        error < 0,
        np.exp(-error / 13.0) - 1.0,
        np.exp(error / 10.0) - 1.0,
    )
    return float(np.sum(score))


def rul_regression_metrics(prediction: object, truth: object) -> dict[str, float | int]:
    prediction_array, truth_array = _validated_metric_arrays(prediction, truth)
    error = prediction_array - truth_array
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "nasa_score": nasa_rul_score(prediction_array, truth_array),
        "count": int(error.size),
    }


def forecasting_residual_ranking(
    predictions: dict[str, np.ndarray],
    truth: object,
    sensor_ids: list[str] | tuple[str, ...],
    top_k: int = 5,
) -> tuple[dict[str, float | int | str], ...]:
    y_hat, truth_array = _validated_metric_arrays(predictions["y_hat"], truth)
    sensor_ids = tuple(sensor_ids)
    if y_hat.ndim < 2:
        raise ValueError("forecasting arrays must include at least one sensor axis")
    if y_hat.shape[-1] != len(sensor_ids):
        raise ValueError("sensor_ids length must match the final prediction axis")
    if top_k < 0:
        raise ValueError("top_k must be non-negative")

    residual_by_sensor = np.mean(
        np.abs(y_hat - truth_array),
        axis=tuple(range(y_hat.ndim - 1)),
    )
    ranked = sorted(
        zip(sensor_ids, residual_by_sensor, strict=True),
        key=lambda item: (-float(item[1]), item[0]),
    )
    return tuple(
        {
            "rank": rank,
            "sensor_id": sensor_id,
            "mean_abs_residual": float(mean_abs_residual),
        }
        for rank, (sensor_id, mean_abs_residual) in enumerate(
            ranked[:top_k],
            start=1,
        )
    )


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


def _validated_metric_arrays(
    prediction: object,
    truth: object,
) -> tuple[np.ndarray, np.ndarray]:
    prediction_array = np.asarray(prediction, dtype=float)
    truth_array = np.asarray(truth, dtype=float)
    if prediction_array.shape != truth_array.shape:
        raise ValueError("prediction and truth must have matching shapes")
    if prediction_array.size == 0:
        raise ValueError("prediction and truth must be non-empty")
    return prediction_array, truth_array
