from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

import numpy as np
import pandas as pd

STAGE_NAMES = [
    "上盖开启",
    "上盖关闭",
    "抽真空",
    "浇筑",
    "溶解",
    "测温",
    "冷却",
    "氩气导入",
]

STAGE_DURATION_MINUTES = {
    "上盖开启": (2, 5),
    "上盖关闭": (1, 3),
    "抽真空": (18, 35),
    "浇筑": (4, 10),
    "溶解": (35, 65),
    "测温": (2, 6),
    "冷却": (45, 90),
    "氩气导入": (5, 12),
}


def _rng(seed: Optional[int]) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_batch_timeline(
    days: int = 45,
    seed: int = 42,
    start: datetime | None = None,
    target_batches: int | None = None,
) -> pd.DataFrame:
    """Generate stage intervals for a furnace with irregular idle gaps."""
    random = _rng(seed)
    if start is None:
        start = datetime(2026, 4, 1, 8, 0, tzinfo=timezone(timedelta(hours=8)))

    end = start + timedelta(days=days)
    current = start
    rows = []
    batch_index = 1
    target = target_batches or max(1, int(days * 3.55))

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
        for stage in STAGE_NAMES:
            low, high = STAGE_DURATION_MINUTES[stage]
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
