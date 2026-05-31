from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec


def dependency_available(module_name: str) -> bool:
    return find_spec(module_name) is not None


@dataclass
class TimeSeriesFoundationAdapter:
    name: str
    supported_heads: set[str]
    available: bool = True
    reason: str = ""

    def prepare_input(self, model_window: object) -> dict[str, object]:
        return {
            "X": getattr(model_window, "X"),
            "mask": getattr(model_window, "mask"),
            "stage_token": getattr(model_window, "stage_token"),
            "sensor_token": getattr(model_window, "sensor_token"),
            "domain_token": getattr(model_window, "domain_token"),
        }

    def predict(self, model_window: object) -> object:
        if not self.available:
            return {"available": False, "reason": self.reason}
        raise NotImplementedError(f"{self.name} adapter prediction is a prototype boundary")

    def embed(self, model_window: object) -> object:
        if not self.available:
            return {"available": False, "reason": self.reason}
        raise NotImplementedError(f"{self.name} adapter embedding is a prototype boundary")
