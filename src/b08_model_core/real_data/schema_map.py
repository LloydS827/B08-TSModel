from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from pydantic import BaseModel, Field

from b08_model_core.tasks.schema import REQUIRED_OBSERVATION_COLUMNS

CANONICAL_OBSERVATION_COLUMNS = [
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


class SensorMap(BaseModel):
    source: str
    sensor_id: str
    domain: str
    unit: str


class RealDataSchemaMap(BaseModel):
    source_format: str = Field(pattern="^(long|wide)$")
    column_mapping: dict[str, str]
    sensors: list[SensorMap]
    stage_map: dict[str, str] = Field(default_factory=dict)
    defaults: dict[str, Any] = Field(default_factory=dict)

    @property
    def sensor_by_source(self) -> dict[str, SensorMap]:
        return {sensor.source: sensor for sensor in self.sensors}


def load_schema_map(path: str | Path) -> RealDataSchemaMap:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return RealDataSchemaMap.model_validate(payload)


def _apply_common_fields(df: pd.DataFrame, schema_map: RealDataSchemaMap) -> pd.DataFrame:
    out = df.copy()
    if "timestamp" in out:
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", format="mixed")
    if "stage" in out:
        out["stage"] = out["stage"].map(lambda value: schema_map.stage_map.get(str(value), value))
    if "value" in out:
        out["value"] = pd.to_numeric(out["value"], errors="coerce")
    for column in ["quality_flag", "degradation_label", "failure_proxy"]:
        if column not in out:
            out[column] = schema_map.defaults.get(column, False if column == "failure_proxy" else "normal")
    out["failure_proxy"] = out["failure_proxy"].astype(bool)
    return out


def _normalize_long(df: pd.DataFrame, schema_map: RealDataSchemaMap) -> pd.DataFrame:
    rename = {source: canonical for canonical, source in schema_map.column_mapping.items() if source in df.columns}
    out = df.rename(columns=rename)
    sensor_lookup = schema_map.sensor_by_source

    def sensor_id(value: object) -> str:
        item = sensor_lookup.get(str(value))
        return item.sensor_id if item else str(value)

    def sensor_attr(value: object, attr: str) -> str:
        item = sensor_lookup.get(str(value))
        return getattr(item, attr) if item else ""

    if "sensor_id" in out:
        source_sensor = out["sensor_id"].astype(str)
        out["sensor_id"] = source_sensor.map(sensor_id)
        out["domain"] = source_sensor.map(lambda value: sensor_attr(value, "domain"))
        out["unit"] = source_sensor.map(lambda value: sensor_attr(value, "unit"))
    else:
        out["sensor_id"] = ""
        out["domain"] = ""
        out["unit"] = ""
    return _apply_common_fields(out, schema_map)


def _normalize_wide(df: pd.DataFrame, schema_map: RealDataSchemaMap) -> pd.DataFrame:
    base_mapping = {
        canonical: source
        for canonical, source in schema_map.column_mapping.items()
        if canonical in {"timestamp", "device_id", "batch_id", "stage"} and source in df.columns
    }
    id_columns = list(base_mapping.values())
    sensor_sources = [sensor.source for sensor in schema_map.sensors if sensor.source in df.columns]
    melted = df.melt(id_vars=id_columns, value_vars=sensor_sources, var_name="source_sensor", value_name="value")
    melted = melted.rename(columns={source: canonical for canonical, source in base_mapping.items()})
    sensor_lookup = schema_map.sensor_by_source
    melted["sensor_id"] = melted["source_sensor"].map(lambda value: sensor_lookup[value].sensor_id)
    melted["domain"] = melted["source_sensor"].map(lambda value: sensor_lookup[value].domain)
    melted["unit"] = melted["source_sensor"].map(lambda value: sensor_lookup[value].unit)
    melted = melted.drop(columns=["source_sensor"])
    return _apply_common_fields(melted, schema_map)


def normalize_real_data_frame(df: pd.DataFrame, schema_map: RealDataSchemaMap) -> pd.DataFrame:
    if schema_map.source_format == "long":
        out = _normalize_long(df, schema_map)
    else:
        out = _normalize_wide(df, schema_map)
    for column in REQUIRED_OBSERVATION_COLUMNS - set(out.columns):
        fallback = pd.NA if column in {"timestamp", "value"} else ""
        out[column] = schema_map.defaults.get(column, fallback)
    return out[CANONICAL_OBSERVATION_COLUMNS]
