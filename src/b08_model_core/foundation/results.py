from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class FoundationModelStatus(StrEnum):
    AVAILABLE_AND_RAN = "available_and_ran"
    MISSING_DEPENDENCY = "missing_dependency"
    MISSING_OR_BLOCKED_WEIGHTS = "missing_or_blocked_weights"
    UNSUPPORTED_WINDOW_SHAPE = "unsupported_window_shape"
    RUNTIME_FAILED = "runtime_failed"
    SKIPPED_BY_USER = "skipped_by_user"


@dataclass(init=False)
class FoundationForecastResult:
    model_name: str
    adapter_name: str
    status: FoundationModelStatus
    reason: str
    metrics: dict[str, float | None]
    y_hat: np.ndarray | None
    q_low: np.ndarray | None
    q_high: np.ndarray | None
    metadata: dict[str, object]
    io_coverage: dict[str, bool]
    dependency_status: str
    weight_status: str
    cache_dir: str | None

    def __init__(
        self,
        model_name: str | None = None,
        adapter_name: str | None = None,
        status: FoundationModelStatus = FoundationModelStatus.SKIPPED_BY_USER,
        *,
        model: str | None = None,
        adapter: str | None = None,
        reason: str = "",
        metrics: dict[str, float | None] | None = None,
        y_hat: np.ndarray | None = None,
        q_low: np.ndarray | None = None,
        q_high: np.ndarray | None = None,
        metadata: dict[str, object] | None = None,
        io_coverage: dict[str, bool] | None = None,
        dependency_status: str = "unknown",
        weight_status: str = "unknown",
        cache_dir: str | None = None,
    ) -> None:
        self.model_name = model_name if model_name is not None else (model or "")
        self.adapter_name = adapter_name if adapter_name is not None else (adapter or "")
        self.status = status
        self.reason = reason
        self.metrics = {} if metrics is None else metrics
        self.y_hat = y_hat
        self.q_low = q_low
        self.q_high = q_high
        self.metadata = {} if metadata is None else metadata
        self.io_coverage = {} if io_coverage is None else io_coverage
        self.dependency_status = dependency_status
        self.weight_status = weight_status
        self.cache_dir = cache_dir

    @property
    def model(self) -> str:
        return self.model_name

    @property
    def adapter(self) -> str:
        return self.adapter_name

    @property
    def succeeded(self) -> bool:
        return self.status == FoundationModelStatus.AVAILABLE_AND_RAN

    def predictions(self) -> dict[str, np.ndarray]:
        if self.y_hat is None:
            return {}
        payload = {"y_hat": self.y_hat}
        if self.q_low is not None and self.q_high is not None:
            payload["q_low"] = self.q_low
            payload["q_high"] = self.q_high
        return payload


def recommend_route(result: FoundationForecastResult, baseline_mae: float | None) -> str:
    if result.status == FoundationModelStatus.MISSING_DEPENDENCY:
        return "no_go_missing_dependency"
    if result.status == FoundationModelStatus.MISSING_OR_BLOCKED_WEIGHTS:
        return "no_go_missing_or_blocked_weights"
    if result.status == FoundationModelStatus.UNSUPPORTED_WINDOW_SHAPE:
        return "no_go_unsupported_window_shape"
    if result.status == FoundationModelStatus.RUNTIME_FAILED:
        return "no_go_runtime_failed"
    if result.status == FoundationModelStatus.SKIPPED_BY_USER:
        return "baseline_only"

    model_mae = result.metrics.get("mae")
    if not result.succeeded or model_mae is None or baseline_mae is None:
        return "fallback_comparator"
    if model_mae < baseline_mae * 0.98:
        return "direct_reuse_candidate"
    if model_mae <= baseline_mae * 1.10:
        return "fine_tune_candidate"
    return "fallback_comparator"
