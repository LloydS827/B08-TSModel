from __future__ import annotations

from b08_model_core.adapters.base import TimeSeriesFoundationAdapter, dependency_available


def build_adapter() -> TimeSeriesFoundationAdapter:
    available = dependency_available("tsfm_public") or dependency_available("tsfm")
    return TimeSeriesFoundationAdapter("TTM", {"forecasting"}, available, "" if available else "optional TTM dependency is not installed")
