from pathlib import Path
from copy import deepcopy

import pytest
import yaml

from b08_model_core.experiments.c_stage_contract import (
    CStageContractError,
    load_c_stage_contract,
    validate_c_stage_contract,
)


CONFIG_PATH = Path("configs/c_stage_minimum_evidence.yaml")

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


def test_c_stage_contract_file_exists():
    assert CONFIG_PATH.exists()


def test_contract_declares_all_required_evidence_ids():
    contract = load_c_stage_contract(CONFIG_PATH)
    evidence_ids = {item["evidence_id"] for item in contract["experiments"]}
    assert evidence_ids == {
        "E1_forecasting_residual",
        "E2_representation",
        "E3_imputation",
        "E4_open_data_pm",
        "E5_patent_effect",
    }


def test_contract_declares_ct4_decision_gate_explicitly():
    contract = load_c_stage_contract(CONFIG_PATH)
    contribution_ids = {
        contribution
        for item in contract["experiments"]
        for contribution in item.get("paper_contribution_ids", [])
    }
    assert "CT4_decision_gate" in contribution_ids


def test_each_experiment_has_invalid_claims():
    contract = load_c_stage_contract(CONFIG_PATH)
    for item in contract["experiments"]:
        assert item["invalid_claims"]
        invalid_claims_text = " ".join(item["invalid_claims"])
        assert any(
            forbidden in invalid_claims_text
            for forbidden in ["生产告警", "FU13 RUL", "自动维修", "专利授权"]
        )


def test_each_experiment_has_full_execution_contract():
    contract = load_c_stage_contract(CONFIG_PATH)
    for item in contract["experiments"]:
        assert REQUIRED_EXPERIMENT_FIELDS.issubset(item)
        assert item["input_contract"]
        assert item["comparison"]
        assert item["valid_when"]
        assert item["no_go_when"]


def test_each_experiment_has_data_label_audit_checklist():
    contract = load_c_stage_contract(CONFIG_PATH)
    for item in contract["experiments"]:
        assert REQUIRED_DATA_LABEL_AUDIT_FIELDS.issubset(item["data_label_audit"])


def test_patent_effect_examples_cover_p1_to_p5():
    contract = load_c_stage_contract(CONFIG_PATH)
    patent_effect = next(
        item
        for item in contract["experiments"]
        if item["evidence_id"] == "E5_patent_effect"
    )
    assert set(patent_effect["patent_effect_examples"]) == {
        "P1_stage_sensor_encoding",
        "P2_small_sample_pretraining",
        "P3_weak_label_anomaly_signal",
        "P4_real_open_data_fusion",
        "P5_multitask_health_evaluation",
    }


def test_decision_gate_declares_go_no_go_criteria():
    contract = load_c_stage_contract(CONFIG_PATH)
    criteria = contract["decision_gate"]["criteria"]
    assert criteria["primary_task"]
    assert criteria["strong_baseline"]
    assert criteria["minimum_gain"]
    assert criteria["seed_policy"]
    assert criteria["confidence_interval_policy"]
    assert criteria["failure_conditions"]


def test_decision_gate_allowed_decisions_are_exact():
    contract = load_c_stage_contract(CONFIG_PATH)
    assert contract["decision_gate"]["allowed_decisions"] == [
        "Go_to_B_minimal_prototype",
        "Stay_in_C_adaptation",
        "Knowledge_only_consolidation",
        "No_Go_hold",
    ]


def test_contract_validation_rejects_missing_invalid_claims():
    contract = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    contract["experiments"][0]["invalid_claims"] = []
    with pytest.raises(CStageContractError):
        validate_c_stage_contract(contract)


def test_contract_validation_rejects_extra_experiment_count():
    contract = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    contract["experiments"].append(deepcopy(contract["experiments"][0]))
    with pytest.raises(CStageContractError, match="exactly 5 experiments"):
        validate_c_stage_contract(contract)


def test_contract_validation_rejects_duplicate_evidence_id():
    contract = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    contract["experiments"][1]["evidence_id"] = "E1_forecasting_residual"
    with pytest.raises(CStageContractError, match="duplicate evidence ids"):
        validate_c_stage_contract(contract)


def test_contract_validation_reports_missing_and_extra_evidence_ids():
    contract = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    contract["experiments"][0]["evidence_id"] = "E6_unplanned"
    with pytest.raises(
        CStageContractError,
        match="missing .*E1_forecasting_residual.*extra .*E6_unplanned",
    ):
        validate_c_stage_contract(contract)


def test_contract_validation_rejects_missing_decision_gate_requirements():
    contract = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    contract["decision_gate"]["requires"].remove("E5_patent_effect")
    with pytest.raises(CStageContractError, match="decision_gate.requires"):
        validate_c_stage_contract(contract)


def test_contract_validation_rejects_non_dict_contract():
    with pytest.raises(CStageContractError, match="contract must be a dict"):
        validate_c_stage_contract([])


def test_contract_validation_rejects_non_dict_experiment():
    contract = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    contract["experiments"][0] = "not a dict"
    with pytest.raises(CStageContractError, match="each experiment must be a dict"):
        validate_c_stage_contract(contract)


def test_contract_validation_rejects_non_dict_data_label_audit():
    contract = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    contract["experiments"][0]["data_label_audit"] = []
    with pytest.raises(CStageContractError, match="data_label_audit must be a dict"):
        validate_c_stage_contract(contract)


def test_contract_validation_accepts_current_contract():
    contract = load_c_stage_contract(CONFIG_PATH)
    validate_c_stage_contract(contract)
