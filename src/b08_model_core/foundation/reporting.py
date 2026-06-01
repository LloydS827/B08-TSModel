from __future__ import annotations

from collections.abc import Mapping, Sequence

from b08_model_core.foundation.results import FoundationForecastResult


MetricValue = float | int | None


def render_foundation_report(
    dataset_summary: Mapping[str, object] | None,
    baseline_metrics: Mapping[str, Mapping[str, MetricValue] | None] | None,
    foundation_result: FoundationForecastResult,
    route_recommendation: str,
    fallback_candidates: Sequence[str],
) -> str:
    lines: list[str] = [
        "# Forecasting Foundation Model Experiment",
        "",
        "## Dataset Summary",
    ]
    lines.extend(_render_mapping(dataset_summary))
    lines.extend(
        [
            "",
            "## Selected Foundation Model",
            f"- model: {_format_value(foundation_result.model_name)}",
            f"- adapter: {_format_value(foundation_result.adapter_name)}",
            "",
            "## Foundation Model Status",
            f"- status: {foundation_result.status.value}",
            f"- reason: {_format_value(foundation_result.reason)}",
            "",
            "## Baseline Comparison",
        ]
    )

    if baseline_metrics:
        for baseline_name, metrics in baseline_metrics.items():
            lines.append(f"- {baseline_name}")
            if metrics:
                for metric_name, metric_value in metrics.items():
                    lines.append(f"  - {metric_name}: {_format_metric(metric_value)}")
            else:
                lines.append("  - not_available")
    else:
        lines.append("- not_available")

    lines.append("- foundation metrics")
    for metric_name, metric_value in foundation_result.metrics.items():
        lines.append(f"  - foundation {metric_name}: {_format_metric(metric_value)}")

    baseline_for_delta = _first_metrics(baseline_metrics)
    mae_delta = _metric_delta(foundation_result.metrics.get("mae"), baseline_for_delta.get("mae"))
    rmse_delta = _metric_delta(foundation_result.metrics.get("rmse"), baseline_for_delta.get("rmse"))
    lines.extend(
        [
            f"- MAE delta: {_format_metric(mae_delta)}",
            f"- RMSE delta: {_format_metric(rmse_delta)}",
            "",
            "## Local Model Environment",
            f"- cache_dir: {_format_value(foundation_result.cache_dir)}",
            f"- dependency_status: {_format_value(foundation_result.dependency_status)}",
            f"- weight_status: {_format_value(foundation_result.weight_status)}",
            f"- fallback candidates: {_format_candidates(fallback_candidates)}",
            "",
            "## IO Coverage",
        ]
    )

    if foundation_result.io_coverage:
        lines.extend(_render_bool_mapping(foundation_result.io_coverage))
    else:
        lines.append("- not_available")

    lines.extend(
        [
            "",
            "## Route Recommendation",
            f"- route: {_format_value(route_recommendation)}",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_mapping(values: Mapping[str, object]) -> list[str]:
    if not values:
        return ["- not_available"]
    return [f"- {key}: {_format_value(value)}" for key, value in values.items()]


def _render_bool_mapping(values: Mapping[str, bool]) -> list[str]:
    return [f"- {key}: {'yes' if value else 'no'}" for key, value in values.items()]


def _first_metrics(
    baseline_metrics: Mapping[str, Mapping[str, MetricValue] | None] | None,
) -> Mapping[str, MetricValue]:
    if baseline_metrics:
        for metrics in baseline_metrics.values():
            if metrics:
                return metrics
    return {}


def _metric_delta(model_value: MetricValue, baseline_value: MetricValue) -> float | None:
    if model_value is None or baseline_value is None:
        return None
    return float(model_value) - float(baseline_value)


def _format_metric(value: MetricValue) -> str:
    if value is None:
        return "not_available"
    return f"{float(value):.6f}"


def _format_candidates(candidates: Sequence[str]) -> str:
    if not candidates:
        return "not_available"
    return ", ".join(candidates)


def _format_value(value: object) -> str:
    if value is None or value == "":
        return "not_available"
    return str(value)
