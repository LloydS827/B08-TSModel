from __future__ import annotations

from b08_model_core.adapters.base import TimeSeriesFoundationAdapter, dependency_available


def build_adapter() -> TimeSeriesFoundationAdapter:
    available = dependency_available("timesfm")
    return TimeSeriesFoundationAdapter("TimesFM", {"forecasting"}, available, "" if available else "optional TimesFM dependency is not installed")
