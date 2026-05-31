from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateModel:
    name: str
    supported_tasks: tuple[str, ...]
    multivariate_support: str
    context_support: str
    local_deployment: str
    license_risk: str
    direct_use_score: float
    fine_tune_score: float
    research_value: str
    route: str
    reason: str


def candidate_matrix() -> list[CandidateModel]:
    return [
        CandidateModel("TSPulse", ("forecasting", "representation", "anomaly"), "strong", "moderate", "self-host feasible", "medium", 0.62, 0.82, "Industrial multivariate foundation-model reference.", "fine_tune", "Promising backbone, but B08 stage/domain conditioning needs adaptation."),
        CandidateModel("MOMENT", ("forecasting", "imputation", "classification", "representation"), "strong", "adapter-friendly", "self-host feasible", "low", 0.70, 0.86, "Universal representation and multi-task baseline.", "fine_tune", "Covers many heads, but degradation labels require project-specific heads."),
        CandidateModel("TTM", ("forecasting",), "moderate", "weak", "lightweight local deployment", "low", 0.75, 0.78, "Fast direct forecasting comparator.", "direct_reuse", "Useful as a frozen forecasting gate before custom work."),
        CandidateModel("Chronos", ("forecasting",), "mostly univariate", "weak", "self-host depends on model size", "low", 0.58, 0.60, "Probabilistic forecasting reference.", "baseline_only", "Limited fit for multivariate equipment-state representation."),
        CandidateModel("TimesFM", ("forecasting",), "moderate", "weak", "self-host feasible with dependency checks", "medium", 0.74, 0.76, "Strong forecast-only comparison.", "direct_reuse", "Good for forecast head, insufficient for full B08 IO contract."),
        CandidateModel("UniTS", ("forecasting", "classification", "imputation"), "strong", "moderate", "research-code risk", "medium", 0.64, 0.83, "Unified-task architecture aligns with multi-head requirement.", "fine_tune", "Needs adapter work but maps well to the B08 task mix."),
        CandidateModel("Moirai", ("forecasting",), "strong", "moderate", "self-host feasible", "medium", 0.72, 0.79, "Probabilistic multivariate forecasting comparator.", "direct_reuse", "Good for forecasting benchmark before custom heads are justified."),
    ]
