from b08_model_core.config import load_config


def test_furnace_config_has_required_context():
    cfg = load_config("configs/furnace_fu13_sim.yaml")
    assert cfg.device_id == "FU13"
    assert len(cfg.stages) == 8
    assert {"mechanical", "hydraulic", "thermal", "atmosphere", "electrical", "fluid"} <= set(cfg.domains)
    assert cfg.sample_period_seconds == 5
