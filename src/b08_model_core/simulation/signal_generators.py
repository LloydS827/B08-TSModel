from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from b08_model_core.config import load_config
from b08_model_core.simulation.furnace_scenario import DEFAULT_CONFIG_PATH, expand_stage_samples


@dataclass(frozen=True)
class SensorMeta:
    sensor_id: str
    domain: str
    unit: str


DEFAULT_SENSORS = [
    SensorMeta("PumpShake1", "mechanical", "mm/s"),
    SensorMeta("PumpShake2", "mechanical", "mm/s"),
    SensorMeta("SysSelfPressure", "hydraulic", "MPa"),
    SensorMeta("CoverPressure", "hydraulic", "MPa"),
    SensorMeta("ValvePressure", "hydraulic", "MPa"),
    SensorMeta("CoolingWallTemp1", "thermal", "C"),
    SensorMeta("CoolingWallTemp2", "thermal", "C"),
    SensorMeta("CoolingWallTemp3", "thermal", "C"),
    SensorMeta("CoilReturnTemp1", "thermal", "C"),
    SensorMeta("CoilReturnTemp2", "thermal", "C"),
    SensorMeta("MeltingOxygen", "atmosphere", "percent"),
    SensorMeta("OutletOxygen", "atmosphere", "percent"),
    SensorMeta("CrucibleLeakCurrent", "electrical", "mA"),
    SensorMeta("RollerWaterFlow", "fluid", "L/min"),
    SensorMeta("CylinderWaterFlow", "fluid", "L/min"),
    SensorMeta("WaterTemp", "fluid", "C"),
]


def _sensors_from_config(config_path: str | Path) -> list[SensorMeta]:
    cfg = load_config(config_path)
    return [SensorMeta(sensor.id, sensor.domain, sensor.unit) for sensor in cfg.sensors]


def _stage_load(stage: str) -> float:
    return {
        "停机": 0.0,
        "上盖开启": 0.2,
        "上盖关闭": 0.25,
        "抽真空": 0.65,
        "浇筑": 0.9,
        "溶解": 1.0,
        "测温": 0.75,
        "冷却": 0.8,
        "氩气导入": 0.45,
    }.get(stage, 0.4)


def _value_for(sensor: SensorMeta, stage: str, pos: float, rng: np.random.Generator) -> float:
    load = _stage_load(stage)
    noise = float(rng.normal(0, 1))
    if sensor.domain == "mechanical":
        return 0.25 + 2.1 * load + 0.15 * noise
    if sensor.domain == "hydraulic":
        pulse = np.exp(-((pos - 0.25) ** 2) / 0.025) if stage in {"浇筑", "上盖关闭", "上盖开启"} else 0
        return max(0, 1.0 + 5.2 * pulse + 2.0 * load + 0.2 * noise)
    if sensor.domain == "thermal":
        if stage == "冷却":
            base = 340 - 145 * pos
        elif stage == "溶解":
            base = 160 + 180 * pos
        else:
            base = 45 + 55 * load
        offset = {"CoolingWallTemp2": 5, "CoolingWallTemp3": -4, "CoilReturnTemp1": -35, "CoilReturnTemp2": -31}.get(sensor.sensor_id, 0)
        return base + offset + 2.5 * noise
    if sensor.domain == "atmosphere":
        if stage == "抽真空":
            base = 2.2 * np.exp(-4.2 * pos) + 0.08
        elif stage == "氩气导入":
            base = 0.18 + 0.25 * np.sin(np.pi * pos)
        else:
            base = 0.16 + 0.08 * load
        return max(0, base + 0.015 * noise)
    if sensor.domain == "electrical":
        base = 1.2 + 9.0 * (stage == "溶解") + 3.0 * (stage == "浇筑")
        return max(0, base + 0.4 * noise)
    if sensor.domain == "fluid":
        if sensor.sensor_id == "WaterTemp":
            return 24 + 18 * (stage == "冷却") * pos + 4 * load + 0.5 * noise
        return max(0, 45 + 30 * (stage == "冷却") - 5 * (stage == "停机") + 1.0 * noise)
    return noise


def _values_for(sensor: SensorMeta, stage: str, pos: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    load = _stage_load(stage)
    noise = rng.normal(0, 1, len(pos))
    if sensor.domain == "mechanical":
        return 0.25 + 2.1 * load + 0.15 * noise
    if sensor.domain == "hydraulic":
        pulse = np.exp(-((pos - 0.25) ** 2) / 0.025) if stage in {"浇筑", "上盖关闭", "上盖开启"} else np.zeros_like(pos)
        return np.maximum(0, 1.0 + 5.2 * pulse + 2.0 * load + 0.2 * noise)
    if sensor.domain == "thermal":
        if stage == "冷却":
            base = 340 - 145 * pos
        elif stage == "溶解":
            base = 160 + 180 * pos
        else:
            base = np.full_like(pos, 45 + 55 * load, dtype=float)
        offset = {"CoolingWallTemp2": 5, "CoolingWallTemp3": -4, "CoilReturnTemp1": -35, "CoilReturnTemp2": -31}.get(sensor.sensor_id, 0)
        return base + offset + 2.5 * noise
    if sensor.domain == "atmosphere":
        if stage == "抽真空":
            base = 2.2 * np.exp(-4.2 * pos) + 0.08
        elif stage == "氩气导入":
            base = 0.18 + 0.25 * np.sin(np.pi * pos)
        else:
            base = np.full_like(pos, 0.16 + 0.08 * load, dtype=float)
        return np.maximum(0, base + 0.015 * noise)
    if sensor.domain == "electrical":
        base = 1.2 + 9.0 * (stage == "溶解") + 3.0 * (stage == "浇筑")
        return np.maximum(0, base + 0.4 * noise)
    if sensor.domain == "fluid":
        if sensor.sensor_id == "WaterTemp":
            return 24 + 18 * (stage == "冷却") * pos + 4 * load + 0.5 * noise
        return np.maximum(0, 45 + 30 * (stage == "冷却") - 5 * (stage == "停机") + 1.0 * noise)
    return noise


def generate_signals(
    timeline: pd.DataFrame,
    seed: int = 42,
    device_id: str | None = None,
    include_idle: bool = False,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> pd.DataFrame:
    cfg = load_config(config_path)
    sensors = _sensors_from_config(config_path) or DEFAULT_SENSORS
    rng = np.random.default_rng(seed)
    samples = expand_stage_samples(timeline, sample_period_seconds=cfg.sample_period_seconds, include_idle=include_idle)
    frames = []
    device = device_id or cfg.device_id
    for (_batch_id, stage), segment in samples.groupby(["batch_id", "stage"], sort=False):
        pos = segment["stage_position"].to_numpy(dtype=float)
        for sensor in sensors:
            frames.append(
                pd.DataFrame(
                    {
                        "timestamp": segment["timestamp"].to_numpy(),
                        "device_id": device,
                        "batch_id": segment["batch_id"].to_numpy(),
                        "stage": stage,
                        "sensor_id": sensor.sensor_id,
                        "value": _values_for(sensor, stage, pos, rng),
                        "unit": sensor.unit,
                        "domain": sensor.domain,
                        "quality_flag": "OK",
                        "degradation_label": "normal",
                        "failure_proxy": False,
                    }
                )
            )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
