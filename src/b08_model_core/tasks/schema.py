from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from pydantic import BaseModel

REQUIRED_OBSERVATION_COLUMNS = {
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
}


class ObservationRow(BaseModel):
    timestamp: object
    device_id: str
    batch_id: str
    stage: str
    sensor_id: str
    value: float
    unit: str
    domain: str
    quality_flag: str
    degradation_label: str
    failure_proxy: bool


@dataclass(frozen=True)
class SchemaValidationResult:
    valid: bool
    missing_columns: set[str]
    unexpected_null_columns: set[str]


def validate_observation_frame(df: pd.DataFrame) -> SchemaValidationResult:
    missing = REQUIRED_OBSERVATION_COLUMNS - set(df.columns)
    unexpected_nulls = {
        column for column in REQUIRED_OBSERVATION_COLUMNS & set(df.columns) if column != "value" and df[column].isna().any()
    }
    return SchemaValidationResult(
        valid=not missing and not unexpected_nulls and not df.empty,
        missing_columns=missing,
        unexpected_null_columns=unexpected_nulls,
    )
