from __future__ import annotations

from pathlib import Path

import pandas as pd

from b08_model_core.simulation.degradation_modes import inject_degradation
from b08_model_core.simulation.furnace_scenario import generate_batch_timeline
from b08_model_core.simulation.signal_generators import generate_signals
from b08_model_core.tasks.schema import validate_observation_frame


def simulate_dataset(
    days: int = 45,
    seed: int = 42,
    output: str | Path | None = None,
    output_path: str | Path | None = None,
    config_path: str | Path = "configs/furnace_fu13_sim.yaml",
) -> pd.DataFrame:
    timeline = generate_batch_timeline(days=days, seed=seed, config_path=config_path)
    clean = generate_signals(timeline, seed=seed, config_path=config_path)
    degraded = inject_degradation(clean, seed=seed)
    degraded = degraded.sort_values(["timestamp", "sensor_id"]).reset_index(drop=True)
    validation = validate_observation_frame(degraded)
    if not validation.valid:
        raise ValueError(f"invalid simulated dataset: missing={sorted(validation.missing_columns)}")

    target = output_path or output
    if target is not None:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        degraded.to_parquet(path, index=False)
    return degraded
