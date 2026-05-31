from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class StageConfig(BaseModel):
    name: str
    min_minutes: float = Field(gt=0)
    max_minutes: float = Field(gt=0)


class SensorConfig(BaseModel):
    id: str
    domain: str
    unit: str
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None


class FurnaceSimulationConfig(BaseModel):
    device_id: str
    sample_period_seconds: int = Field(gt=0)
    days: int = Field(gt=0)
    target_batches: int = Field(gt=0)
    stages: List[StageConfig]
    sensors: List[SensorConfig]

    @property
    def domains(self) -> List[str]:
        return sorted({sensor.domain for sensor in self.sensors})


def load_config(path: str | Path) -> FurnaceSimulationConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return FurnaceSimulationConfig.model_validate(data)
