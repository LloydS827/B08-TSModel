from __future__ import annotations

import pandas as pd

from b08_model_core.real_data.fu13_config import FU13CycleRules

CYCLE_COLUMNS = ["cycle_id", "cycle_status", "start_time", "end_time", "stages"]


def assign_cycle_ids(stage_events: pd.DataFrame, rules: FU13CycleRules) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = stage_events.copy()
    events["time"] = pd.to_datetime(events["time"], utc=True, format="mixed")
    events = events.sort_values("time").reset_index(drop=True)
    events["cycle_id"] = pd.NA
    events["cycle_status"] = "unassigned_cycle"

    starts = events.index[events["stage_name"].eq(rules.start_stage)].tolist()
    cycle_records: list[dict[str, object]] = []
    for number, start_idx in enumerate(starts, start=1):
        next_start = starts[number] if number < len(starts) else len(events)
        idx = list(range(start_idx, next_start))
        cycle_id = f"cycle_{number:04d}"
        stages = events.loc[idx, "stage_name"].tolist()
        status = "complete" if _contains_required_order(stages, rules.required_order) else "partial_cycle"
        events.loc[idx, "cycle_id"] = cycle_id
        events.loc[idx, "cycle_status"] = status
        cycle_records.append(
            {
                "cycle_id": cycle_id,
                "cycle_status": status,
                "start_time": events.loc[start_idx, "time"],
                "end_time": events.loc[idx[-1], "time"],
                "stages": stages,
            }
        )

    cycles = pd.DataFrame(cycle_records, columns=CYCLE_COLUMNS)
    return events, cycles


def summarize_cycles(cycles: pd.DataFrame) -> dict[str, int]:
    statuses = cycles["cycle_status"].value_counts() if "cycle_status" in cycles else pd.Series(dtype=int)
    return {
        "total_cycles": int(len(cycles)),
        "complete_cycles": int(statuses.get("complete", 0)),
        "partial_cycles": int(statuses.get("partial_cycle", 0)),
    }


def _contains_required_order(stages: list[str], required_order: list[str]) -> bool:
    cursor = 0
    for stage in stages:
        if cursor < len(required_order) and stage == required_order[cursor]:
            cursor += 1
    return cursor == len(required_order)
