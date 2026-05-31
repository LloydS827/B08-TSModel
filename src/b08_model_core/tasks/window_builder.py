from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd


@dataclass
class ModelWindow:
    X: np.ndarray
    mask: np.ndarray
    delta_t: np.ndarray
    stage_token: np.ndarray
    sensor_token: list[str]
    domain_token: list[str]
    device_token: str
    y: np.ndarray
    degradation_label: str


def build_model_windows(
    df: pd.DataFrame,
    context_length: int = 128,
    prediction_length: int = 32,
    stride: int = 64,
    allow_cross_stage: bool = False,
) -> list[ModelWindow]:
    windows: list[ModelWindow] = []
    sensors = sorted(df["sensor_id"].unique())
    domain_map = df.drop_duplicates("sensor_id").set_index("sensor_id")["domain"].to_dict()

    for (device_id, batch_id, stage), group in df.groupby(["device_id", "batch_id", "stage"], sort=False):
        if stage == "停机" and not allow_cross_stage:
            continue
        pivot = (
            group.pivot_table(index="timestamp", columns="sensor_id", values="value", aggfunc="mean")
            .reindex(columns=sensors)
            .sort_index()
        )
        if len(pivot) < context_length + prediction_length:
            continue
        values = pivot.to_numpy(dtype=float)
        mask = ~np.isnan(values)
        values = np.nan_to_num(values, nan=0.0)
        timestamps = pd.to_datetime(pivot.index)
        dt = timestamps.to_series().diff().dt.total_seconds().fillna(0).to_numpy(dtype=float)
        labels = group.groupby("timestamp")["degradation_label"].agg(lambda x: x.iloc[0]).reindex(pivot.index)
        for start in range(0, len(values) - context_length - prediction_length + 1, stride):
            end = start + context_length
            y_end = end + prediction_length
            label_slice = labels.iloc[start:y_end]
            label = "risk_event" if (label_slice == "risk_event").any() else (
                "incipient_degradation" if (label_slice == "incipient_degradation").any() else "normal"
            )
            windows.append(
                ModelWindow(
                    X=values[start:end],
                    mask=mask[start:end],
                    delta_t=dt[start:end],
                    stage_token=np.array([stage] * context_length),
                    sensor_token=sensors,
                    domain_token=[domain_map[sensor] for sensor in sensors],
                    device_token=device_id,
                    y=values[end:y_end],
                    degradation_label=label,
                )
            )
    return windows
