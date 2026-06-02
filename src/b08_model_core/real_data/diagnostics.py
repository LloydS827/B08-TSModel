from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from b08_model_core.real_data.fu13_config import FU13RealDataConfig


@dataclass(frozen=True)
class FU13DiagnosticsReport:
    rows: int
    sensors: int
    stages: int
    quality_counts: dict[str, int]
    sensor_summary: pd.DataFrame
    stage_summary: pd.DataFrame
    scenario_summary: pd.DataFrame


def build_fu13_diagnostics(df: pd.DataFrame, cfg: FU13RealDataConfig) -> FU13DiagnosticsReport:
    sensor_scenario = {sensor.sensor_id: sensor.scenario for sensor in cfg.sensors}
    enriched = df.copy()
    enriched["scenario"] = enriched["sensor_id"].map(sensor_scenario).fillna("unmapped_sensor")
    sensor_summary = (
        enriched.groupby("sensor_id")["value"]
        .agg(["count", "min", "median", "max"])
        .reset_index()
    )
    stage_summary = enriched.groupby("stage").size().reset_index(name="rows")
    scenario_summary = (
        enriched.groupby("scenario")
        .agg(rows=("value", "size"), invalid_rows=("quality_flag", lambda s: int((s == "invalid").sum())))
        .reset_index()
    )
    return FU13DiagnosticsReport(
        rows=len(df),
        sensors=int(df["sensor_id"].nunique()),
        stages=int(df["stage"].nunique()),
        quality_counts={str(k): int(v) for k, v in df["quality_flag"].value_counts().items()},
        sensor_summary=sensor_summary,
        stage_summary=stage_summary,
        scenario_summary=scenario_summary,
    )


def _to_markdown(df: pd.DataFrame) -> str:
    headers = [_format_markdown_cell(column) for column in df.columns]
    separator = ["---"] * len(headers)
    rows = [[_format_markdown_cell(value) for value in row] for row in df.itertuples(index=False, name=None)]

    def render_row(values: list[str]) -> str:
        return "| " + " | ".join(values) + " |"

    return "\n".join([render_row(headers), render_row(separator), *(render_row(row) for row in rows)])


def _format_markdown_cell(value: object) -> str:
    return str(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("|", "\\|")


def render_fu13_diagnostics(report: FU13DiagnosticsReport) -> str:
    lines = [
        "# Real FU13 Data Diagnostics",
        "",
        f"- rows: {report.rows}",
        f"- sensors: {report.sensors}",
        f"- stages: {report.stages}",
        f"- quality_counts: {report.quality_counts}",
        "",
        "## Sensor Summary",
        _to_markdown(report.sensor_summary),
        "",
        "## Stage Summary",
        _to_markdown(report.stage_summary),
        "",
        "## Scenario Summary",
        _to_markdown(report.scenario_summary),
        "",
        "## Interpretation Boundary",
        "This report describes data quality and candidate abnormal signals. It does not validate real failure prediction.",
    ]
    return "\n".join(lines) + "\n"
