from __future__ import annotations

from dataclasses import dataclass

import pytest

from b08_model_core.simulation.degradation_modes import inject_degradation
from b08_model_core.simulation.furnace_scenario import generate_batch_timeline
from b08_model_core.simulation.signal_generators import generate_signals
from b08_model_core.tasks.window_builder import build_model_windows


@pytest.fixture(scope="session")
def clean_signal_frame():
    timeline = generate_batch_timeline(days=3, seed=4)
    return generate_signals(timeline, seed=4)


@pytest.fixture(scope="session")
def simulated_frame(clean_signal_frame):
    return inject_degradation(clean_signal_frame, modes=["vacuum_leak", "pump_vibration_increase"], seed=4)


@pytest.fixture(scope="session")
def model_windows(simulated_frame):
    windows = build_model_windows(simulated_frame, context_length=64, prediction_length=16)
    split = max(1, int(len(windows) * 0.7))

    @dataclass
    class Split:
        train: list
        test: list

    return Split(train=windows[:split], test=windows[split:] or windows[-1:])
