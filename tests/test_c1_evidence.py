from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from b08_model_core.experiments.c1_evidence import (
    C1EvidenceConfigError,
    C1EvidenceResult,
    C1ModelResult,
    EvidenceStatus,
    ModelExecutionStatus,
    apply_deterministic_mask,
    build_c1_registry,
    load_c1_execution_config,
    reconstruction_metrics,
    render_c1_evidence_report,
    run_c1_evidence,
    simple_statistical_embedding,
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


def test_deterministic_mask_is_reproducible():
    values = np.arange(24, dtype=float).reshape(6, 4)
    masked_a, mask_a = apply_deterministic_mask(values, mask_ratio=0.25, seed=7)
    masked_b, mask_b = apply_deterministic_mask(values, mask_ratio=0.25, seed=7)
    assert np.array_equal(mask_a, mask_b)
    assert np.array_equal(masked_a, masked_b)
    assert mask_a.sum() == 6


def test_statistical_embedding_summarizes_window_shape():
    values = np.array([[1.0, 2.0], [3.0, 6.0]])
    embedding = simple_statistical_embedding(values)
    assert embedding["mean_sensor_0"] == 2.0
    assert embedding["std_sensor_1"] == 2.0


def test_reconstruction_metrics_reports_masked_error_only():
    truth = np.array([[1.0, 2.0], [3.0, 4.0]])
    reconstructed = np.array([[1.0, 0.0], [0.0, 4.0]])
    mask = np.array([[False, True], [True, False]])
    metrics = reconstruction_metrics(truth, reconstructed, mask)
    assert metrics["mae"] == 2.5
    assert metrics["count"] == 2


def test_c1_runner_e1_outputs_residual_summary_and_traceable_topk(tmp_path):
    config_path = _write_c1_fixture_config(tmp_path, candidate_model_failures=True)
    results = run_c1_evidence(load_c1_execution_config(config_path))
    e1 = _result_by_id(results, "E1_forecasting_residual")
    assert e1.status == EvidenceStatus.PASSED
    assert e1.primary_metrics["mae"] is not None
    assert e1.artifact_outputs["residual_summary"]["abs_residual_p95"] is not None
    top_example = e1.artifact_outputs["top_k_candidate_examples"][0]
    assert {
        "sensor_id",
        "timestamp",
        "stage",
        "quality_policy",
        "absolute_residual",
        "model_name",
    }.issubset(top_example)


def test_c1_runner_outputs_e2_e3_and_candidate_model_statuses(tmp_path):
    config_path = _write_c1_fixture_config(tmp_path, candidate_model_failures=True)
    results = run_c1_evidence(load_c1_execution_config(config_path))
    e2 = _result_by_id(results, "E2_representation")
    e3 = _result_by_id(results, "E3_imputation")
    e4 = _result_by_id(results, "E4_open_data_pm")

    assert e2.status == EvidenceStatus.PASSED
    assert "input_exclusion_note" in e2.artifact_outputs
    assert any(model.model_name == "statistical_embedding" for model in e2.model_results)
    assert any(model.status in {ModelExecutionStatus.MISSING_DEPENDENCY, ModelExecutionStatus.UNSUPPORTED_TASK} for model in e2.model_results)

    assert e3.status == EvidenceStatus.PASSED
    assert e3.artifact_outputs["mask_strategy"]["seed"] == 7
    assert e3.primary_metrics["mae"] is not None
    assert any(model.model_name == "simple_reconstruction_baseline" for model in e3.model_results)
    assert e4.status == EvidenceStatus.PLANNED_NOT_EXECUTED


def _result_by_id(results, evidence_id):
    return next(result for result in results if result.evidence_id == evidence_id)


def _write_c1_fixture_config(tmp_path, *, candidate_model_failures=False, strict_model_success=False):
    dataset = tmp_path / "fu13.parquet"
    _write_fu13_fixture(dataset)
    config = {
        "stage": "C1_evidence_execution",
        "contract_path": "configs/c_stage_minimum_evidence.yaml",
        "dataset": {
            "fu13_observations": str(dataset),
            "fu13_config": "configs/fu13_real_data_schema.yaml",
            "boundary": "test_fixture_no_private_data",
        },
        "enabled_evidence": [
            "E1_forecasting_residual",
            "E2_representation",
            "E3_imputation",
        ],
        "window": {
            "window_mode": "cross-stage",
            "context_length": 24,
            "prediction_length": 6,
            "max_windows": 8,
        },
        "models": {
            "baseline": {"enabled": True},
            "ttm": {
                "enabled": True,
                "model_cache_dir": None,
                "allow_download": False,
                "force_missing_dependency": candidate_model_failures,
            },
            "moment": {"enabled": True, "force_missing_dependency": candidate_model_failures},
            "units": {"enabled": True, "force_unsupported_task": candidate_model_failures},
        },
        "outputs": {"report": str(tmp_path / "report.md")},
        "execution_policy": {
            "strict_model_success": strict_model_success,
            "no_network_by_default": True,
            "record_failure": True,
            "do_not_over_claim": True,
        },
    }
    path = tmp_path / "c1.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return path


def _write_fu13_fixture(path):
    timestamps = pd.date_range("2026-05-01", periods=120, freq="5s", tz="UTC")
    rows = []
    for i, ts in enumerate(timestamps):
        stage = "溶解" if i < 60 else "浇筑"
        quality = "good" if i % 17 else "unassigned_cycle"
        for sensor, domain, value in [
            ("LeakElec", "electrical", 10 + np.sin(i / 7)),
            ("O2Content", "atmosphere", -20 + np.cos(i / 9)),
        ]:
            rows.append(
                {
                    "timestamp": ts,
                    "device_id": "FU13",
                    "batch_id": "cycle_0001",
                    "stage": stage,
                    "sensor_id": sensor,
                    "value": value,
                    "unit": "%",
                    "domain": domain,
                    "quality_flag": quality,
                    "degradation_label": "normal",
                    "failure_proxy": False,
                }
            )
    pd.DataFrame(rows).to_parquet(path, index=False)
