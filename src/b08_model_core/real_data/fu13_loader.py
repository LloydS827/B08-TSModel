from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from b08_model_core.real_data.cycle_builder import assign_cycle_ids, summarize_cycles
from b08_model_core.real_data.fu13_config import FU13SensorConfig, load_fu13_real_data_config


CANONICAL_COLUMNS = [
    "timestamp",
    "device_id",
    "batch_id",
    "stage",
    "sensor_id",
    "value",
    "unit",
    "domain",
    "quality_flag",
    "degradation_label",
    "failure_proxy",
]


def assemble_fu13_observations(input_dir: str | Path, config_path: str | Path) -> tuple[pd.DataFrame, dict[str, int]]:
    root = Path(input_dir)
    cfg = load_fu13_real_data_config(config_path)
    stage_events = _read_stage_events(root / cfg.stage_file)
    assigned_stages, cycles = assign_cycle_ids(stage_events, cfg.cycle_rules)
    aligned_stages = assigned_stages.rename(columns={"time": "timestamp", "stage_name": "stage"}).sort_values(
        "timestamp"
    )

    frames = [_read_sensor(root, cfg.device_id, sensor, aligned_stages) for sensor in cfg.sensors]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return _empty_observation_frame(), summarize_cycles(cycles)

    observations = pd.concat(frames, ignore_index=True).sort_values(["timestamp", "sensor_id"])
    observations["batch_id"] = observations["batch_id"].fillna("unassigned_cycle")
    observations["quality_flag"] = observations.apply(_quality_flag, axis=1)
    observations["stage"] = observations["stage"].fillna("unassigned_stage")
    return observations[CANONICAL_COLUMNS], summarize_cycles(cycles)


def missing_fu13_source_files(input_dir: str | Path, config_path: str | Path) -> list[str]:
    root = Path(input_dir)
    cfg = load_fu13_real_data_config(config_path)
    expected = [cfg.stage_file, *(sensor.source_file for sensor in cfg.sensors)]
    return [source_file for source_file in expected if not (root / source_file).exists()]


def _read_stage_events(path: Path) -> pd.DataFrame:
    events = pd.read_csv(path, encoding="utf-8-sig")
    events["time"] = pd.to_datetime(events["time"], utc=True, format="mixed")
    return events.sort_values("time")


def _read_sensor(root: Path, device_id: str, sensor: FU13SensorConfig, stages: pd.DataFrame) -> pd.DataFrame:
    try:
        raw = pd.read_csv(root / sensor.source_file, encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()
    if raw.empty:
        return pd.DataFrame()

    raw["timestamp"] = pd.to_datetime(raw["time"], utc=True, format="mixed")
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    raw = raw.sort_values("timestamp")
    merged = pd.merge_asof(raw[["timestamp", "value"]], stages, on="timestamp", direction="backward")
    merged["device_id"] = device_id
    merged["batch_id"] = merged["cycle_id"]
    merged["sensor_id"] = sensor.sensor_id
    merged["unit"] = sensor.unit
    merged["domain"] = sensor.domain
    merged["lower_limit"] = sensor.lower_limit
    merged["upper_limit"] = sensor.upper_limit
    merged["degradation_label"] = "normal"
    merged["failure_proxy"] = False
    return merged


def _empty_observation_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=CANONICAL_COLUMNS)


def _quality_flag(row: pd.Series) -> str:
    if pd.isna(row.get("stage")):
        return "unassigned_stage"
    if pd.isna(row.get("cycle_id")):
        return "unassigned_cycle"
    if pd.isna(row.get("value")):
        return "missing"
    if row["value"] < row["lower_limit"] or row["value"] > row["upper_limit"]:
        return "invalid"
    return "good"
