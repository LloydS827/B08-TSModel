from pathlib import Path

import pytest

from b08_model_core.experiments.c1_evidence import (
    C1EvidenceConfigError,
    C1EvidenceResult,
    C1ModelResult,
    EvidenceStatus,
    ModelExecutionStatus,
    build_c1_registry,
    load_c1_execution_config,
    render_c1_evidence_report,
)


def test_c1_execution_config_references_c0_contract():
    config = load_c1_execution_config("configs/c_stage_c1_execution.yaml")
    assert config.stage == "C1_evidence_execution"
    assert config.contract_path == Path("configs/c_stage_minimum_evidence.yaml")
    assert config.enabled_evidence == [
        "E1_forecasting_residual",
        "E2_representation",
        "E3_imputation",
    ]
    assert config.allow_download is False


def test_c1_registry_inherits_contract_fields_and_preserves_e4_e5():
    config = load_c1_execution_config("configs/c_stage_c1_execution.yaml")
    registry = build_c1_registry(config)
    e1 = registry.by_evidence_id["E1_forecasting_residual"]
    assert e1.experiment_id == "c0_fu13_forecast_residual_v1"
    assert e1.data_label_audit["source_status"]
    assert e1.invalid_claims
    assert registry.execution_status["E4_open_data_pm"] == EvidenceStatus.PLANNED_NOT_EXECUTED
    assert registry.execution_status["E5_patent_effect"] == EvidenceStatus.PLANNED_NOT_EXECUTED


def test_c1_registry_rejects_unknown_enabled_evidence():
    config = load_c1_execution_config("configs/c_stage_c1_execution.yaml")
    config.enabled_evidence = ["E99_unknown"]
    with pytest.raises(C1EvidenceConfigError, match="unknown enabled evidence"):
        build_c1_registry(config)


def test_c1_report_contains_audit_invalid_claims_failures_and_decision_gate():
    result = C1EvidenceResult(
        evidence_id="E2_representation",
        experiment_id="c0_fu13_representation_probe_v1",
        task_id="fu13_representation_probe_v1",
        status=EvidenceStatus.NEEDS_REVIEW,
        dataset_boundary="internal_fu13_no_raw_data_committed",
        split_policy="time_batch_or_run_split_to_define",
        data_label_audit={"source_status": "internal_source_record_required"},
        model_results=[
            C1ModelResult(
                model_name="MOMENT",
                status=ModelExecutionStatus.MISSING_DEPENDENCY,
                reason="optional MOMENT dependency is not installed",
            )
        ],
        primary_metrics={"macro_F1": None},
        failure_reasons=["candidate model unavailable"],
        artifact_outputs={"representation_probe_report": "not_available"},
        invalid_claims=["不得解释为生产告警"],
        decision_gate_notes=["needs MOMENT/UniTS verification"],
    )
    text = render_c1_evidence_report([result], planned_not_executed=["E4_open_data_pm"])
    assert "E2_representation" in text
    assert "missing_dependency" in text
    assert "data_label_audit" in text
    assert "不得解释为生产告警" in text
    assert "CT4 Decision Gate Draft" in text
    assert "E4_open_data_pm" in text
    assert "planned_not_executed" in text
