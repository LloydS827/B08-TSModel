from b08_model_core.simulation.furnace_scenario import generate_batch_timeline
from b08_model_core.simulation.signal_generators import generate_signals


def test_signals_cover_all_physical_domains():
    timeline = generate_batch_timeline(days=2, seed=2)
    df = generate_signals(timeline, seed=2)
    assert {"mechanical", "hydraulic", "thermal", "atmosphere", "electrical", "fluid"} <= set(df["domain"])
    assert df["sensor_id"].nunique() >= 15
    assert df["value"].notna().mean() > 0.95
