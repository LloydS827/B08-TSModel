from b08_model_core.simulation.furnace_scenario import generate_batch_timeline
from b08_model_core.simulation.signal_generators import generate_signals


def test_signals_cover_all_physical_domains():
    timeline = generate_batch_timeline(days=2, seed=2)
    df = generate_signals(timeline, seed=2)
    assert {"mechanical", "hydraulic", "thermal", "atmosphere", "electrical", "fluid"} <= set(df["domain"])
    assert df["sensor_id"].nunique() >= 15
    assert df["value"].notna().mean() > 0.95


def test_signals_use_config_sensor_list(tmp_path):
    cfg = tmp_path / "sensors.yaml"
    cfg.write_text(
        """
device_id: FU99
sample_period_seconds: 10
days: 1
target_batches: 1
stages:
  - {name: 抽真空, min_minutes: 1, max_minutes: 1}
sensors:
  - {id: PumpShake1, domain: mechanical, unit: mm/s}
  - {id: CustomOxygen, domain: atmosphere, unit: percent}
""".strip(),
        encoding="utf-8",
    )

    timeline = generate_batch_timeline(seed=5, config_path=cfg)
    df = generate_signals(timeline, seed=5, config_path=cfg)

    assert set(df["sensor_id"].unique()) == {"PumpShake1", "CustomOxygen"}
    assert set(df["domain"].unique()) == {"mechanical", "atmosphere"}
