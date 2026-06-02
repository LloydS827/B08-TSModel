from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class FU13CycleRules(BaseModel):
    start_stage: str
    required_order: list[str]
    optional_stages: list[str] = []
    waiting_stages: list[str] = []


class FU13SensorConfig(BaseModel):
    parameter_name: str
    collector: str
    source_tag: str
    sensor_id: str
    source_file: str
    lower_limit: float
    upper_limit: float
    unit: str
    domain: str
    scenario: str
    related_stages: list[str]


class FU13RealDataConfig(BaseModel):
    device_id: str
    timezone_policy: str
    stage_file: str
    cycle_rules: FU13CycleRules
    sensors: list[FU13SensorConfig]

    @property
    def sensor_by_id(self) -> dict[str, FU13SensorConfig]:
        return {sensor.sensor_id: sensor for sensor in self.sensors}

    @property
    def sensor_by_file(self) -> dict[str, FU13SensorConfig]:
        return {sensor.source_file: sensor for sensor in self.sensors}


def load_fu13_real_data_config(path: str | Path) -> FU13RealDataConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return FU13RealDataConfig.model_validate(payload)
