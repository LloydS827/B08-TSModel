from __future__ import annotations

import numpy as np


class MedianReconstructionBaseline:
    def __init__(self) -> None:
        self.center_: np.ndarray | None = None

    def fit(self, windows: list[object]) -> "MedianReconstructionBaseline":
        if not windows:
            raise ValueError("at least one window is required")
        self.center_ = np.nanmedian(np.concatenate([window.X for window in windows], axis=0), axis=0)
        return self

    def reconstruct(self, windows: list[object]) -> np.ndarray:
        if self.center_ is None:
            raise RuntimeError("fit must be called before reconstruct")
        return np.stack([np.where(window.mask, window.X, self.center_) for window in windows], axis=0)
