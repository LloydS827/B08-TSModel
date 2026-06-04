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
REPORT_TEMPLATE_PATH = Path("reports/c_stage_minimum_evidence_template.md")

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

ALLOWED_EXPERIMENT_STATUSES = {"planned", "needs-review", "blocked"}


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


def test_each_experiment_status_uses_shared_allowed_values():
    contract = load_c_stage_contract(CONFIG_PATH)
    for item in contract["experiments"]:
        assert item["status"] in ALLOWED_EXPERIMENT_STATUSES


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


def test_contract_validation_rejects_unknown_status():
    contract = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    contract["experiments"][0]["status"] = "needs_review"
    with pytest.raises(CStageContractError, match="unknown status"):
        validate_c_stage_contract(contract)


def test_contract_validation_accepts_current_contract():
    contract = load_c_stage_contract(CONFIG_PATH)
    validate_c_stage_contract(contract)


def test_c_stage_minimum_evidence_report_template_contains_required_static_terms():
    template = REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    required_terms = {
        "E1_forecasting_residual",
        "E2_representation",
        "E3_imputation",
        "E4_open_data_pm",
        "E5_patent_effect",
        "CT4_decision_gate",
        "C -> B",
        "数据与标签核对",
        "primary_task",
        "strong_baseline",
        "minimum_gain",
        "seed_policy",
        "confidence_interval_policy",
        "failure_conditions",
        "P1_stage_sensor_encoding",
        "P2_small_sample_pretraining",
        "P3_weak_label_anomaly_signal",
        "P4_real_open_data_fusion",
        "P5_multitask_health_evaluation",
    }
    missing_terms = sorted(term for term in required_terms if term not in template)
    assert missing_terms == []


def _markdown_section(markdown: str, heading: str) -> str:
    start = markdown.index(f"## {heading}")
    next_start = markdown.find("\n## ", start + 1)
    if next_start == -1:
        return markdown[start:]
    return markdown[start:next_start]


def test_c_stage_minimum_evidence_report_template_has_required_section_fields():
    template = REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    for evidence_id in [
        "E1_forecasting_residual",
        "E2_representation",
        "E3_imputation",
        "E4_open_data_pm",
        "E5_patent_effect",
    ]:
        section = _markdown_section(template, evidence_id)
        assert "experiment_id" in section
        assert "result_summary" in section or "summary" in section
        assert "failure_cases" in section or "failure" in section or "boundary" in section
        assert "invalid_claims" in section


def test_c_stage_minimum_evidence_report_template_has_data_audit_status_fields():
    template = REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    section = _markdown_section(template, "数据与标签核对")
    for field in [
        "source_status",
        "license_status",
        "schema_status",
        "label_status",
        "split_policy_status",
    ]:
        assert field in section


def test_c_stage_minimum_evidence_report_template_has_overclaim_boundaries():
    template = REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    section = _markdown_section(template, "禁止过度解释")
    for term in [
        "planned",
        "needs-review",
        "failed",
        "线上业务结论",
        "FU13 剩余寿命",
        "自动维修建议",
        "专利授权",
        "新颖性",
        "创造性",
        "缺少核对项",
        "不得 Go",
    ]:
        assert term in section


def test_default_docs_reference_c_stage_evidence_assets():
    readme = Path("README.md").read_text(encoding="utf-8")
    docs_index = Path("docs/index.html").read_text(encoding="utf-8")
    details = Path("details.md").read_text(encoding="utf-8")

    assert "configs/c_stage_minimum_evidence.yaml" in readme
    assert "c-stage-minimum-evidence-register.html" in docs_index
    assert "C 阶段最小证据" in details


def test_c_stage_minimum_evidence_register_wraps_wide_tables():
    html = Path("docs/research/c-stage-minimum-evidence-register.html").read_text(
        encoding="utf-8"
    )
    assert html.count('<div class="table-wrap">') == 2
