from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd


DEFAULT_MODES = [
    "vacuum_leak",
    "cooling_efficiency_decline",
    "hydraulic_seal_degradation",
    "pump_vibration_increase",
    "insulation_degradation",
]


def _progress(df: pd.DataFrame) -> pd.Series:
    order = df["timestamp"].rank(method="dense").astype(float)
    return (order - order.min()) / max(1.0, order.max() - order.min())


def inject_degradation(
    frame: pd.DataFrame,
    modes: Sequence[str] | None = None,
    seed: int = 42,
    start_fraction: float = 0.58,
    failure_fraction: float = 0.9,
) -> pd.DataFrame:
    """Inject gradual degradation before failure-proxy events."""
    modes = list(modes or DEFAULT_MODES)
    df = frame.copy()
    p = _progress(df)
    active = (p >= start_fraction).astype(float)
    severity = np.clip((p - start_fraction) / max(1e-9, failure_fraction - start_fraction), 0, 1)
    failure = p >= failure_fraction

    def mark(mask: pd.Series) -> None:
        df.loc[mask & (severity > 0), "degradation_label"] = "incipient_degradation"
        df.loc[mask & failure, "degradation_label"] = "risk_event"
        df.loc[mask & failure, "failure_proxy"] = True

    if "vacuum_leak" in modes:
        mask = df["sensor_id"].isin(["MeltingOxygen", "OutletOxygen"]) & df["stage"].eq("抽真空")
        df.loc[mask, "value"] += 0.55 * severity[mask]
        mark(mask)

    if "cooling_efficiency_decline" in modes:
        mask = df["domain"].eq("thermal") & df["stage"].eq("冷却")
        df.loc[mask, "value"] += 38 * severity[mask]
        mark(mask)

    if "hydraulic_seal_degradation" in modes:
        mask = df["domain"].eq("hydraulic") & df["stage"].isin(["浇筑", "上盖关闭", "上盖开启"])
        df.loc[mask, "value"] += 1.6 * severity[mask]
        mark(mask)

    if "pump_vibration_increase" in modes:
        mask = df["domain"].eq("mechanical") & ~df["stage"].eq("停机")
        df.loc[mask, "value"] += 1.2 * severity[mask]
        mark(mask)

    if "insulation_degradation" in modes:
        mask = df["sensor_id"].eq("CrucibleLeakCurrent") & df["stage"].isin(["溶解", "浇筑"])
        df.loc[mask, "value"] += 22 * severity[mask]
        mark(mask)

    return df
