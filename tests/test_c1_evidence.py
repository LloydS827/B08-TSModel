from pathlib import Path

import pytest

from b08_model_core.experiments.c1_evidence import (
    C1EvidenceConfigError,
    EvidenceStatus,
    build_c1_registry,
    load_c1_execution_config,
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
