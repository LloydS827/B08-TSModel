from __future__ import annotations

from b08_model_core.adapters.base import TimeSeriesFoundationAdapter, dependency_available


def build_adapter() -> TimeSeriesFoundationAdapter:
    available = dependency_available("momentfm")
    return TimeSeriesFoundationAdapter("MOMENT", {"forecasting", "imputation", "representation"}, available, "" if available else "optional MOMENT dependency is not installed")
