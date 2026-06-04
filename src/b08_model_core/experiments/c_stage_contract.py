from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_EVIDENCE_IDS = {
    "E1_forecasting_residual",
    "E2_representation",
    "E3_imputation",
    "E4_open_data_pm",
    "E5_patent_effect",
}

REQUIRED_EXPERIMENT_FIELDS = {
    "experiment_id",
    "evidence_id",
    "paper_contribution_ids",
    "patent_ids",
    "dataset",
    "task_id",
    "model_or_baseline",
    "input_contract",
    "primary_metric",
    "comparison",
    "valid_when",
    "no_go_when",
    "artifact_output",
    "data_label_audit",
    "status",
    "invalid_claims",
}

REQUIRED_DATA_LABEL_AUDIT_FIELDS = {
    "source_status",
    "license_status",
    "schema_status",
    "label_status",
    "split_policy_status",
}

REQUIRED_PATENT_IDS = {
    "P1_stage_sensor_encoding",
    "P2_small_sample_pretraining",
    "P3_weak_label_anomaly_signal",
    "P4_real_open_data_fusion",
    "P5_multitask_health_evaluation",
}

ALLOWED_DECISIONS = {
    "Go_to_B_minimal_prototype",
    "Stay_in_C_adaptation",
    "Knowledge_only_consolidation",
    "No_Go_hold",
}

REQUIRED_DECISION_CRITERIA = {
    "primary_task",
    "strong_baseline",
    "minimum_gain",
    "seed_policy",
    "confidence_interval_policy",
    "failure_conditions",
}


class CStageContractError(ValueError):
    """Raised when the C-stage evidence contract is incomplete."""


def load_c_stage_contract(path: str | Path) -> dict[str, Any]:
    contract_path = Path(path)
    return yaml.safe_load(contract_path.read_text(encoding="utf-8"))


def validate_c_stage_contract(contract: dict[str, Any]) -> None:
    experiments = contract.get("experiments")
    if not isinstance(experiments, list) or not experiments:
        raise CStageContractError("experiments must be a non-empty list")

    evidence_ids = {item.get("evidence_id") for item in experiments}
    if evidence_ids != REQUIRED_EVIDENCE_IDS:
        raise CStageContractError("contract must declare exactly E1-E5 evidence ids")

    contribution_ids = {
        contribution
        for item in experiments
        for contribution in item.get("paper_contribution_ids", [])
    }
    if "CT4_decision_gate" not in contribution_ids:
        raise CStageContractError("CT4_decision_gate must be explicit")

    for item in experiments:
        missing = REQUIRED_EXPERIMENT_FIELDS - set(item)
        if missing:
            raise CStageContractError(f"{item.get('experiment_id')} missing {sorted(missing)}")

        for field in [
            "input_contract",
            "comparison",
            "valid_when",
            "no_go_when",
            "data_label_audit",
            "invalid_claims",
        ]:
            if not item[field]:
                raise CStageContractError(f"{item['experiment_id']} has empty {field}")

        missing_audit_fields = REQUIRED_DATA_LABEL_AUDIT_FIELDS - set(item["data_label_audit"])
        if missing_audit_fields:
            raise CStageContractError(
                f"{item['experiment_id']} missing audit fields {sorted(missing_audit_fields)}"
            )

    decision_gate = contract.get("decision_gate", {})
    if set(decision_gate.get("allowed_decisions", [])) != ALLOWED_DECISIONS:
        raise CStageContractError("decision_gate.allowed_decisions must match the allowed set")

    criteria = decision_gate.get("criteria", {})
    for field in REQUIRED_DECISION_CRITERIA:
        if not criteria.get(field):
            raise CStageContractError(f"decision_gate.criteria missing {field}")

    patent_effect = next(
        item for item in experiments if item.get("evidence_id") == "E5_patent_effect"
    )
    if set(patent_effect.get("patent_effect_examples", {})) != REQUIRED_PATENT_IDS:
        raise CStageContractError("E5 must declare patent_effect_examples for P1-P5")


def load_and_validate_c_stage_contract(path: str | Path) -> dict[str, Any]:
    contract = load_c_stage_contract(path)
    validate_c_stage_contract(contract)
    return contract
