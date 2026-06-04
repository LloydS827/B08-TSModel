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

ALLOWED_EXPERIMENT_STATUSES = {"planned", "needs-review", "blocked"}

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
    if not isinstance(contract, dict):
        raise CStageContractError("contract must be a dict")

    experiments = contract.get("experiments")
    if not isinstance(experiments, list) or not experiments:
        raise CStageContractError("experiments must be a non-empty list")
    if len(experiments) != 5:
        raise CStageContractError("contract must declare exactly 5 experiments")

    for item in experiments:
        if not isinstance(item, dict):
            raise CStageContractError("each experiment must be a dict")

    evidence_id_list = [item.get("evidence_id") for item in experiments]
    duplicate_evidence_ids = sorted(
        evidence_id
        for evidence_id in set(evidence_id_list)
        if evidence_id_list.count(evidence_id) > 1
    )
    if duplicate_evidence_ids:
        raise CStageContractError(f"duplicate evidence ids: {duplicate_evidence_ids}")

    evidence_ids = set(evidence_id_list)
    if evidence_ids != REQUIRED_EVIDENCE_IDS:
        missing = sorted(REQUIRED_EVIDENCE_IDS - evidence_ids)
        extra = sorted(evidence_ids - REQUIRED_EVIDENCE_IDS)
        raise CStageContractError(
            f"contract evidence ids missing {missing}; extra {extra}"
        )

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

        if item["status"] not in ALLOWED_EXPERIMENT_STATUSES:
            raise CStageContractError(f"{item['experiment_id']} has unknown status")

        for field in [
            "input_contract",
            "comparison",
            "valid_when",
            "no_go_when",
            "invalid_claims",
        ]:
            if not item[field]:
                raise CStageContractError(f"{item['experiment_id']} has empty {field}")

        dataset = item["dataset"]
        if not isinstance(dataset, dict):
            raise CStageContractError(f"{item['experiment_id']} dataset must be a dict")
        if not isinstance(dataset.get("name"), list) or not dataset["name"]:
            raise CStageContractError(f"{item['experiment_id']} dataset.name must be a list")

        comparison = item["comparison"]
        if not isinstance(comparison, dict):
            raise CStageContractError(f"{item['experiment_id']} comparison must be a dict")
        if not isinstance(comparison.get("candidate_model"), list) or not comparison["candidate_model"]:
            raise CStageContractError(
                f"{item['experiment_id']} comparison.candidate_model must be a list"
            )
        if not isinstance(comparison.get("same_split_required"), bool):
            raise CStageContractError(
                f"{item['experiment_id']} comparison.same_split_required must be a bool"
            )

        data_label_audit = item["data_label_audit"]
        if not isinstance(data_label_audit, dict):
            raise CStageContractError(
                f"{item['experiment_id']} data_label_audit must be a dict"
            )
        if not data_label_audit:
            raise CStageContractError(f"{item['experiment_id']} has empty data_label_audit")

        missing_audit_fields = REQUIRED_DATA_LABEL_AUDIT_FIELDS - set(data_label_audit)
        if missing_audit_fields:
            raise CStageContractError(
                f"{item['experiment_id']} missing audit fields {sorted(missing_audit_fields)}"
            )

    decision_gate = contract.get("decision_gate", {})
    if not isinstance(decision_gate, dict):
        raise CStageContractError("decision_gate must be a dict")
    if set(decision_gate.get("allowed_decisions", [])) != ALLOWED_DECISIONS:
        raise CStageContractError("decision_gate.allowed_decisions must match the allowed set")

    requires = decision_gate.get("requires")
    requires_set = set(requires) if isinstance(requires, list) else set()
    if (
        not isinstance(requires, list)
        or len(requires) != len(REQUIRED_EVIDENCE_IDS)
        or requires_set != REQUIRED_EVIDENCE_IDS
    ):
        missing = sorted(REQUIRED_EVIDENCE_IDS - requires_set)
        extra = sorted(requires_set - REQUIRED_EVIDENCE_IDS)
        raise CStageContractError(
            f"decision_gate.requires must exactly cover E1-E5; missing {missing}; extra {extra}"
        )

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
