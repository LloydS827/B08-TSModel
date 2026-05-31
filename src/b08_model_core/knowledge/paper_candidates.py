from __future__ import annotations

from b08_model_core.knowledge.patent_candidates import KnowledgeCandidate


def paper_candidates() -> list[KnowledgeCandidate]:
    return [
        KnowledgeCandidate("Stage-Conditioned Foundation Modeling for Industrial Furnace Time Series", "Industrial furnace data is multivariate, phase-dependent, and sparsely labeled.", "A benchmark that separates model-core IO design from system delivery.", ("FU13 simulated dataset", "task dataset construction", "open-source comparison"), "model-capability-matrix"),
        KnowledgeCandidate("Synthetic Degradation Benchmarks for Predictive Maintenance Time-Series Models", "Failure labels are rare in early predictive-maintenance projects.", "Physically motivated degradation injection for batch-stage trajectories.", ("failure proxy lead time", "sensor-domain ablation", "benchmark reproducibility"), "model_core_evaluation"),
        KnowledgeCandidate("When to Reuse, Fine-Tune, or Pretrain Time-Series Foundation Models in Equipment Maintenance", "Open-source time-series model selection lacks engineering route criteria.", "A route gate connecting IO coverage, baseline lift, adaptation cost, and knowledge value.", ("candidate matrix", "adapter feasibility", "route decision report"), "open-source-model-fit"),
    ]
