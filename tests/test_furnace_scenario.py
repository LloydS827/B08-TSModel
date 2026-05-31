from b08_model_core.simulation.furnace_scenario import generate_batch_timeline


def test_batch_timeline_has_all_stages_and_idle_gaps():
    timeline = generate_batch_timeline(days=3, seed=7)
    stages = set(timeline["stage"])
    assert {"上盖开启", "上盖关闭", "抽真空", "浇筑", "溶解", "测温", "冷却", "氩气导入"} <= stages
    assert "停机" in stages
    assert timeline["batch_id"].nunique() >= 5


def test_batch_timeline_is_deterministic_for_seed():
    left = generate_batch_timeline(days=1, seed=13)
    right = generate_batch_timeline(days=1, seed=13)
    assert left.equals(right)


def test_batch_timeline_uses_config_stage_durations_and_target_batches(tmp_path):
    cfg = tmp_path / "short.yaml"
    cfg.write_text(
        """
device_id: FU99
sample_period_seconds: 10
days: 2
target_batches: 2
stages:
  - {name: 抽真空, min_minutes: 1, max_minutes: 1}
  - {name: 冷却, min_minutes: 2, max_minutes: 2}
sensors:
  - {id: PumpShake1, domain: mechanical, unit: mm/s}
""".strip(),
        encoding="utf-8",
    )

    timeline = generate_batch_timeline(seed=3, config_path=cfg)
    active = timeline[timeline["stage"] != "停机"]

    assert set(active["stage"]) == {"抽真空", "冷却"}
    assert active["batch_id"].nunique() == 2
    assert sorted(active["duration_seconds"].unique()) == [60.0, 120.0]
