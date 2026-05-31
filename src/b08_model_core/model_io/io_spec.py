from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TensorSpec:
    name: str
    shape: str
    description: str


class ModelInputSpec:
    def __init__(self, inputs: list[TensorSpec]):
        self.inputs = inputs

    @classmethod
    def default(cls) -> "ModelInputSpec":
        return cls(
            [
                TensorSpec("X", "B,L,C", "multi-sensor value window"),
                TensorSpec("mask", "B,L,C", "observed-value mask"),
                TensorSpec("delta_t", "B,L", "irregular sampling interval"),
                TensorSpec("stage_token", "B,L", "PLC process stage token"),
                TensorSpec("sensor_token", "C", "sensor identity and unit token"),
                TensorSpec("domain_token", "C", "physical domain token"),
                TensorSpec("device_token", "B", "equipment identity token"),
            ]
        )

    def has_input(self, name: str, shape: str | None = None) -> bool:
        for item in self.inputs:
            if item.name == name and (shape is None or item.shape == shape):
                return True
        return False


@dataclass(frozen=True)
class OutputHead:
    name: str
    purpose: str


class OutputHeadRegistry:
    def __init__(self, heads: list[OutputHead]):
        self.heads = heads

    @property
    def names(self) -> set[str]:
        return {head.name for head in self.heads}

    @classmethod
    def default(cls) -> "OutputHeadRegistry":
        return cls(
            [
                OutputHead("forecasting", "future sequence and uncertainty"),
                OutputHead("imputation", "masked value recovery"),
                OutputHead("reconstruction", "normal window reconstruction"),
                OutputHead("representation", "state embeddings"),
                OutputHead("degradation", "pre-damage and change evidence"),
                OutputHead("adaptation", "risk or RUL with limited labels"),
            ]
        )
