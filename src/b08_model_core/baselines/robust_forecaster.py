from __future__ import annotations

import numpy as np


class RobustStageForecaster:
    """Robust median/MAD forecaster used as the minimum forecasting bar."""

    def __init__(self, interval_width: float = 1.64) -> None:
        self.interval_width = interval_width
        self.global_center_: np.ndarray | None = None
        self.global_scale_: np.ndarray | None = None
        self.stage_centers_: dict[str, np.ndarray] = {}
        self.stage_scales_: dict[str, np.ndarray] = {}

    @staticmethod
    def _stage(window: object) -> str:
        stage_token = getattr(window, "stage_token", None)
        if stage_token is not None and len(stage_token):
            return str(stage_token[0])
        metadata = getattr(window, "metadata", {})
        return str(metadata.get("stage", "__global__")) if isinstance(metadata, dict) else "__global__"

    @staticmethod
    def _center_scale(arrays: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
        stacked = np.concatenate(arrays, axis=0)
        center = np.nanmedian(stacked, axis=0)
        mad = np.nanmedian(np.abs(stacked - center), axis=0)
        return center, np.maximum(1.4826 * mad, 1e-6)

    def fit(self, windows: list[object]) -> "RobustStageForecaster":
        if not windows:
            raise ValueError("at least one training window is required")
        self.global_center_, self.global_scale_ = self._center_scale([window.y for window in windows])
        grouped: dict[str, list[np.ndarray]] = {}
        for window in windows:
            grouped.setdefault(self._stage(window), []).append(window.y)
        self.stage_centers_ = {}
        self.stage_scales_ = {}
        for stage, arrays in grouped.items():
            self.stage_centers_[stage], self.stage_scales_[stage] = self._center_scale(arrays)
        return self

    def predict(self, windows: list[object]) -> dict[str, np.ndarray]:
        if self.global_center_ is None or self.global_scale_ is None:
            raise RuntimeError("fit must be called before predict")
        y_hats = []
        scales = []
        stages = []
        for window in windows:
            stage = self._stage(window)
            stages.append(stage)
            center = self.stage_centers_.get(stage, self.global_center_)
            scale = self.stage_scales_.get(stage, self.global_scale_)
            y_hats.append(np.tile(center, (window.y.shape[0], 1)))
            scales.append(np.tile(scale, (window.y.shape[0], 1)))
        y_hat = np.stack(y_hats, axis=0)
        scale = np.stack(scales, axis=0)
        return {
            "y_hat": y_hat,
            "q_low": y_hat - self.interval_width * scale,
            "q_high": y_hat + self.interval_width * scale,
            "stage": np.array(stages, dtype=object),
        }
