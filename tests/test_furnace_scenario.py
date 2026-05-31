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
