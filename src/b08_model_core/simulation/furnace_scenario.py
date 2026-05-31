from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from b08_model_core.config import load_config

DEFAULT_CONFIG_PATH = Path("configs/furnace_fu13_sim.yaml")


def _rng(seed: Optional[int]) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_batch_timeline(
    days: int | None = 45,
    seed: int = 42,
    start: datetime | None = None,
    target_batches: int | None = None,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> pd.DataFrame:
    """Generate stage intervals for a furnace with irregular idle gaps."""
    cfg = load_config(config_path)
    random = _rng(seed)
    if start is None:
        start = datetime(2026, 4, 1, 8, 0, tzinfo=timezone(timedelta(hours=8)))

    days = cfg.days if days is None else days
    end = start + timedelta(days=days)
    current = start
    rows = []
    batch_index = 1
    target = target_batches or cfg.target_batches or max(1, int(days * 3.55))

    while current < end and batch_index <= target:
        if batch_index > 1:
            idle_minutes = float(random.uniform(25, 220))
            idle_start = current
            idle_end = min(idle_start + timedelta(minutes=idle_minutes), end)
            rows.append(
                {
                    "batch_id": f"B{batch_index - 1:04d}_idle",
                    "stage": "停机",
                    "start_time": idle_start,
                    "end_time": idle_end,
                    "duration_seconds": (idle_end - idle_start).total_seconds(),
                }
            )
            current = idle_end
            if current >= end:
                break

        batch_id = f"B{batch_index:04d}"
        for stage_cfg in cfg.stages:
            stage = stage_cfg.name
            low, high = stage_cfg.min_minutes, stage_cfg.max_minutes
            minutes = float(random.uniform(low, high))
            stage_start = current
            stage_end = min(stage_start + timedelta(minutes=minutes), end)
            rows.append(
                {
                    "batch_id": batch_id,
                    "stage": stage,
                    "start_time": stage_start,
                    "end_time": stage_end,
                    "duration_seconds": (stage_end - stage_start).total_seconds(),
                }
            )
            current = stage_end
            if current >= end:
                break
        batch_index += 1

    return pd.DataFrame(rows)


def expand_stage_samples(
    timeline: pd.DataFrame,
    sample_period_seconds: int = 5,
    include_idle: bool = True,
) -> pd.DataFrame:
    rows = []
    for record in timeline.itertuples(index=False):
        if record.stage == "停机" and not include_idle:
            continue
        times = pd.date_range(
            start=record.start_time,
            end=record.end_time,
            freq=f"{sample_period_seconds}s",
            inclusive="left",
        )
        for position, timestamp in enumerate(times):
            rows.append(
                {
                    "timestamp": timestamp,
                    "batch_id": record.batch_id,
                    "stage": record.stage,
                    "stage_position": position / max(1, len(times) - 1),
                    "stage_elapsed_seconds": position * sample_period_seconds,
                }
            )
    return pd.DataFrame(rows)
