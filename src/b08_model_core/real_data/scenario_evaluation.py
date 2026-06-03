from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from b08_model_core.real_data.fu13_config import FU13RealDataConfig


QUALITY_MODES = {"all", "good_only", "drop_invalid", "drop_unassigned_cycle"}
STAGE_SCOPES = {"related", "with_waiting"}


@dataclass
class ScenarioSelectionSummary:
    scenario: str
    sensor_ids: list[str]
    related_stages: list[str]
    waiting_stages: list[str]
    stage_scope: str
    quality_mode: str
    input_rows: int
    selected_rows: int
    waiting_rows: int
    quality_counts: dict[str, int]


def select_scenario_observations(
    df: pd.DataFrame,
    cfg: FU13RealDataConfig,
    *,
    scenario: str,
    quality_mode: str,
    stage_scope: str,
) -> tuple[pd.DataFrame, ScenarioSelectionSummary]:
    if quality_mode not in QUALITY_MODES:
        raise ValueError(f"unsupported quality_mode: {quality_mode}")
    if stage_scope not in STAGE_SCOPES:
        raise ValueError(f"unsupported stage_scope: {stage_scope}")

    sensors = [sensor for sensor in cfg.sensors if sensor.scenario == scenario]
    if not sensors:
        raise ValueError(f"unknown scenario: {scenario}")

    sensor_ids = [sensor.sensor_id for sensor in sensors]
    related_stages = _ordered_unique(stage for sensor in sensors for stage in sensor.related_stages)
    waiting_stages = list(cfg.cycle_rules.waiting_stages)
    allowed_stages = related_stages if stage_scope == "related" else _ordered_unique([*related_stages, *waiting_stages])

    mask = (
        (df["device_id"] == cfg.device_id)
        & df["sensor_id"].isin(sensor_ids)
        & df["stage"].isin(allowed_stages)
    )
    selected = df[mask].copy()
    selected = _apply_quality_mode(selected, quality_mode)
    waiting_rows = int(selected["stage"].isin(waiting_stages).sum())
    summary = ScenarioSelectionSummary(
        scenario=scenario,
        sensor_ids=sensor_ids,
        related_stages=related_stages,
        waiting_stages=waiting_stages,
        stage_scope=stage_scope,
        quality_mode=quality_mode,
        input_rows=int(len(df)),
        selected_rows=int(len(selected)),
        waiting_rows=waiting_rows,
        quality_counts={str(k): int(v) for k, v in selected["quality_flag"].value_counts().items()},
    )
    return selected, summary


def _apply_quality_mode(df: pd.DataFrame, quality_mode: str) -> pd.DataFrame:
    if quality_mode == "all":
        return df
    if quality_mode == "good_only":
        return df[df["quality_flag"] == "good"].copy()
    if quality_mode == "drop_invalid":
        return df[df["quality_flag"] != "invalid"].copy()
    if quality_mode == "drop_unassigned_cycle":
        return df[df["quality_flag"] != "unassigned_cycle"].copy()
    raise ValueError(f"unsupported quality_mode: {quality_mode}")


def _ordered_unique(values) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
