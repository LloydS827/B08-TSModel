import pandas as pd

from b08_model_core.real_data.cycle_builder import assign_cycle_ids, summarize_cycles
from b08_model_core.real_data.fu13_config import FU13CycleRules


def _rules():
    return FU13CycleRules(
        start_stage="上盖关闭",
        required_order=["上盖关闭", "溶解", "浇筑"],
        optional_stages=["抽真空", "氩气导入", "测温", "冷却"],
        waiting_stages=["上盖开启"],
    )


def test_assign_cycle_ids_marks_valid_cycles():
    stages = pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2026-05-01T00:00:00Z",
                    "2026-05-01T00:01:00Z",
                    "2026-05-01T00:02:00Z",
                    "2026-05-01T00:03:00Z",
                    "2026-05-01T00:04:00Z",
                    "2026-05-01T00:05:00Z",
                ],
                utc=True,
            ),
            "stage_name": ["上盖开启", "上盖关闭", "抽真空", "溶解", "浇筑", "冷却"],
        }
    )

    assigned, cycles = assign_cycle_ids(stages, _rules())

    assert cycles.iloc[0]["cycle_id"] == "cycle_0001"
    assert cycles.iloc[0]["cycle_status"] == "complete"
    assert assigned.loc[assigned["stage_name"].eq("溶解"), "cycle_id"].iloc[0] == "cycle_0001"
    assert assigned.loc[assigned["stage_name"].eq("上盖开启"), "cycle_status"].iloc[0] == "unassigned_cycle"


def test_assign_cycle_ids_marks_missing_required_stage_as_partial():
    stages = pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2026-05-01T00:00:00Z", "2026-05-01T00:01:00Z", "2026-05-01T00:02:00Z"],
                utc=True,
            ),
            "stage_name": ["上盖关闭", "溶解", "冷却"],
        }
    )

    assigned, cycles = assign_cycle_ids(stages, _rules())

    assert cycles.iloc[0]["cycle_status"] == "partial_cycle"
    assert assigned["cycle_id"].dropna().unique().tolist() == ["cycle_0001"]


def test_summarize_cycles_counts_statuses():
    stages = pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2026-05-01T00:00:00Z",
                    "2026-05-01T00:01:00Z",
                    "2026-05-01T00:02:00Z",
                    "2026-05-01T00:03:00Z",
                    "2026-05-01T00:04:00Z",
                    "2026-05-01T00:05:00Z",
                    "2026-05-01T00:06:00Z",
                ],
                utc=True,
            ),
            "stage_name": ["上盖关闭", "溶解", "浇筑", "冷却", "上盖关闭", "溶解", "冷却"],
        }
    )
    _, cycles = assign_cycle_ids(stages, _rules())

    summary = summarize_cycles(cycles)

    assert summary["total_cycles"] == 2
    assert summary["complete_cycles"] == 1
    assert summary["partial_cycles"] == 1


def test_assign_cycle_ids_returns_cycle_columns_when_no_start_stage():
    stages = pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2026-05-01T00:00:00Z", "2026-05-01T00:01:00Z"],
                utc=True,
            ),
            "stage_name": ["上盖开启", "冷却"],
        }
    )

    assigned, cycles = assign_cycle_ids(stages, _rules())
    summary = summarize_cycles(cycles)

    assert cycles.columns.tolist() == ["cycle_id", "cycle_status", "start_time", "end_time", "stages"]
    assert cycles.empty
    assert assigned["cycle_status"].tolist() == ["unassigned_cycle", "unassigned_cycle"]
    assert summary == {"total_cycles": 0, "complete_cycles": 0, "partial_cycles": 0}
