from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from b08_model_core.cli import main
from b08_model_core.experiments.c2_open_model_evaluation import (
    C2AuditStatus,
    C2ModelAuditRecord,
    C2ModelSpec,
    C2ModelTaskStatus,
    C2OpenModelConfigError,
    CORE_MODEL_IDS,
    C2TaskId,
    _value,
    _imputation_baseline,
    _model_task_status,
    build_c2_model_registry,
    load_c2_open_model_config,
    render_c2_open_model_report,
    run_c2_open_model_evaluation,
    run_c2_model_audit,
)
from b08_model_core.experiments.c1_evidence import apply_deterministic_mask, reconstruction_metrics
from b08_model_core.tasks.window_builder import ModelWindow


CONFIG_PATH = Path("configs/c_stage_c2_open_model_evaluation.yaml")


def _write_config(tmp_path, raw):
    path = tmp_path / "c2_config.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


def _load_raw_config():
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_c2_config_lists_all_six_core_models():
    config = load_c2_open_model_config(CONFIG_PATH)
    assert config.stage == "C2_open_model_evaluation"
    assert config.upstream_c1_config == Path("configs/c_stage_c1_execution.yaml")
    assert config.allow_download is False
    assert config.strict_model_success is False
    assert [model.model_id for model in config.core_models] == list(CORE_MODEL_IDS)
    for model_id in ["moment", "chronos", "timesfm", "moirai_uni2ts", "units"]:
        assert config.by_model_id[model_id].model_card_ref == "needs_review"
        assert config.by_model_id[model_id].license_note == "needs_review"


def test_c2_registry_generates_attempt_for_every_core_model():
    config = load_c2_open_model_config(CONFIG_PATH)
    registry = build_c2_model_registry(config)
    assert set(registry.by_model_id) == set(CORE_MODEL_IDS)
    assert set(attempt.model_id for attempt in registry.attempts) == set(CORE_MODEL_IDS)
    assert registry.by_model_id["ttm"].display_name == "TTM / TinyTimeMixer"
    assert C2TaskId.FORECASTING in registry.by_model_id["chronos"].primary_tasks
    assert C2TaskId.REPRESENTATION in registry.by_model_id["moment"].primary_tasks
    assert C2TaskId.IMPUTATION in registry.by_model_id["units"].primary_tasks


def test_c2_audit_creates_record_for_every_core_model():
    config = load_c2_open_model_config(CONFIG_PATH)
    records = run_c2_model_audit(build_c2_model_registry(config))
    assert all(isinstance(record, C2ModelAuditRecord) for record in records)
    assert set(record.model_id for record in records) == set(CORE_MODEL_IDS)
    ttm = next(record for record in records if record.model_id == "ttm")
    assert ttm.source_ref
    assert ttm.model_card_ref
    assert ttm.license_note
    assert "forecasting" in ttm.supported_tasks
    assert ttm.weights_status == "download_disabled"
    assert ttm.offline_feasibility == "no_network_by_default:true"
    assert ttm.audit_status in set(C2AuditStatus)


def test_c2_audit_records_dependency_review_when_dependency_missing():
    config = load_c2_open_model_config(CONFIG_PATH)
    config.by_model_id["chronos"].dependency_modules = ["definitely_missing_chronos_module"]
    records = run_c2_model_audit(build_c2_model_registry(config))
    chronos = next(record for record in records if record.model_id == "chronos")
    assert chronos.audit_status == C2AuditStatus.NEEDS_DEPENDENCY_REVIEW
    assert chronos.dependency_status.startswith("missing:")


def test_c2_audit_records_license_review_without_blocking_attempts():
    config = load_c2_open_model_config(CONFIG_PATH)
    config.by_model_id["timesfm"].license_note = "needs_review"
    registry = build_c2_model_registry(config)
    records = run_c2_model_audit(registry, dependency_checker=lambda _: True)
    timesfm = next(record for record in records if record.model_id == "timesfm")
    assert timesfm.audit_status == C2AuditStatus.NEEDS_LICENSE_REVIEW
    assert any(attempt.model_id == "timesfm" for attempt in registry.attempts)


def test_c2_registry_rejects_missing_core_model():
    config = load_c2_open_model_config(CONFIG_PATH)
    config.core_models = [model for model in config.core_models if model.model_id != "timesfm"]
    with pytest.raises(C2OpenModelConfigError, match="missing core models"):
        build_c2_model_registry(config)


def test_c2_registry_rejects_wrong_core_model_order():
    config = load_c2_open_model_config(CONFIG_PATH)
    config.core_models[0], config.core_models[1] = config.core_models[1], config.core_models[0]
    with pytest.raises(C2OpenModelConfigError, match="core model order"):
        build_c2_model_registry(config)


def test_c2_registry_rejects_extra_core_model():
    config = load_c2_open_model_config(CONFIG_PATH)
    config.core_models.append(replace(config.core_models[0], model_id="extra_model"))
    with pytest.raises(C2OpenModelConfigError, match="extra core models"):
        build_c2_model_registry(config)


def test_c2_registry_rejects_duplicate_core_model():
    config = load_c2_open_model_config(CONFIG_PATH)
    config.core_models.append(config.core_models[0])
    with pytest.raises(C2OpenModelConfigError, match="duplicate core models"):
        build_c2_model_registry(config)


def test_c2_config_rejects_unknown_task_id(tmp_path):
    raw = _load_raw_config()
    raw["task_policy"] = {"not_a_task": ["ttm"]}
    with pytest.raises(C2OpenModelConfigError, match="unknown C2 task id"):
        load_c2_open_model_config(_write_config(tmp_path, raw))


def test_c2_registry_rejects_task_policy_unknown_model():
    config = load_c2_open_model_config(CONFIG_PATH)
    config.task_policy = {C2TaskId.FORECASTING: ["unknown_model"]}
    with pytest.raises(C2OpenModelConfigError, match="task policy references unknown core model"):
        build_c2_model_registry(config)


def test_c2_config_rejects_malformed_task_policy_value(tmp_path):
    raw = _load_raw_config()
    raw["task_policy"] = {"forecasting": "moment"}
    with pytest.raises(C2OpenModelConfigError, match="task policy values must be lists"):
        load_c2_open_model_config(_write_config(tmp_path, raw))


@pytest.mark.parametrize(
    "section",
    ["dataset", "window", "model_cache_policy", "execution_policy", "outputs", "task_policy"],
)
def test_c2_config_rejects_non_mapping_sections(tmp_path, section):
    raw = _load_raw_config()
    raw[section] = []
    with pytest.raises(C2OpenModelConfigError, match=f"{section} must be a mapping"):
        load_c2_open_model_config(_write_config(tmp_path, raw))


def test_c2_config_rejects_non_list_core_models(tmp_path):
    raw = _load_raw_config()
    raw["core_models"] = {"model_id": "ttm"}
    with pytest.raises(C2OpenModelConfigError, match="core_models must be a list"):
        load_c2_open_model_config(_write_config(tmp_path, raw))


@pytest.mark.parametrize("field", ["dependency_modules", "primary_tasks", "supported_tasks"])
def test_c2_config_rejects_non_list_model_fields(tmp_path, field):
    raw = _load_raw_config()
    raw["core_models"][0][field] = "forecasting"
    with pytest.raises(C2OpenModelConfigError, match=f"{field} must be a list"):
        load_c2_open_model_config(_write_config(tmp_path, raw))


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("model_cache_policy", "allow_download"),
        ("execution_policy", "strict_model_success"),
        ("execution_policy", "no_network_by_default"),
        ("execution_policy", "record_failure"),
        ("execution_policy", "do_not_over_claim"),
    ],
)
def test_c2_config_rejects_non_boolean_policy_fields(tmp_path, section, field):
    raw = _load_raw_config()
    raw[section][field] = "false"
    with pytest.raises(C2OpenModelConfigError, match=f"{field} must be a boolean"):
        load_c2_open_model_config(_write_config(tmp_path, raw))


def test_c2_registry_falls_back_to_primary_tasks_when_policy_omits_model():
    config = load_c2_open_model_config(CONFIG_PATH)
    config.task_policy = {
        task_id: [model_id for model_id in model_ids if model_id != "moment"]
        for task_id, model_ids in config.task_policy.items()
    }
    registry = build_c2_model_registry(config)
    moment_attempts = [
        attempt.task_id for attempt in registry.attempts if attempt.model_id == "moment"
    ]
    assert moment_attempts == [C2TaskId.REPRESENTATION, C2TaskId.IMPUTATION]


def test_c2_registry_rejects_core_model_without_primary_task():
    config = load_c2_open_model_config(CONFIG_PATH)
    config.by_model_id["moment"].primary_tasks = []
    with pytest.raises(C2OpenModelConfigError, match="at least one primary task"):
        build_c2_model_registry(config)


def test_c2_runner_outputs_attempt_for_every_core_model(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    result = run_c2_open_model_evaluation(load_c2_open_model_config(config_path))
    assert set(record.model_id for record in result.audit_records) == set(CORE_MODEL_IDS)
    assert set(attempt.model_id for attempt in result.task_results) == set(CORE_MODEL_IDS)
    assert any(attempt.task_id == C2TaskId.FORECASTING for attempt in result.task_results)
    assert any(attempt.task_id == C2TaskId.REPRESENTATION for attempt in result.task_results)
    assert any(attempt.task_id == C2TaskId.IMPUTATION for attempt in result.task_results)


def test_c2_runner_records_forecasting_and_representation_imputation_baselines(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    result = run_c2_open_model_evaluation(load_c2_open_model_config(config_path))
    ttm = _task_result(result, "ttm", C2TaskId.FORECASTING)
    moment_rep = _task_result(result, "moment", C2TaskId.REPRESENTATION)
    units_imp = _task_result(result, "units", C2TaskId.IMPUTATION)
    assert ttm.baseline_reference == "RobustStageForecaster"
    assert "mae" in ttm.baseline_metrics
    assert moment_rep.baseline_reference == "statistical_embedding"
    assert moment_rep.baseline_metrics["embedding_windows"] > 0
    assert units_imp.baseline_reference == "simple_reconstruction_baseline"
    assert units_imp.baseline_metrics["mae"] is not None


def test_c2_imputation_baseline_uses_unmasked_values_for_median_fill(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    config = load_c2_open_model_config(config_path)
    config.mask_ratio = 0.25
    config.seed = 3
    window = _model_window(
        np.array(
            [
                [10.0, 100.0],
                [20.0, 200.0],
                [30.0, 300.0],
                [40.0, 400.0],
            ]
        )
    )

    _, metrics, _ = _imputation_baseline(config, [window])

    masked, mask = apply_deterministic_mask(window.X, mask_ratio=config.mask_ratio, seed=config.seed)
    median_source = window.X.astype(float).copy()
    median_source[mask] = np.nan
    expected_medians = np.nanmedian(median_source, axis=0)
    expected_reconstructed = masked.copy()
    expected_reconstructed[mask] = np.take(expected_medians, np.where(mask)[1])
    expected_metrics = reconstruction_metrics(window.X, expected_reconstructed, mask)
    zero_masked_medians = np.median(masked, axis=0)
    zero_masked_reconstructed = masked.copy()
    zero_masked_reconstructed[mask] = np.take(zero_masked_medians, np.where(mask)[1])
    zero_masked_metrics = reconstruction_metrics(window.X, zero_masked_reconstructed, mask)

    assert metrics["mae"] == pytest.approx(expected_metrics["mae"])
    assert metrics["mae"] != pytest.approx(zero_masked_metrics["mae"])


def test_c2_runner_candidate_failures_are_structured(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    result = run_c2_open_model_evaluation(load_c2_open_model_config(config_path))
    statuses = {attempt.status for attempt in result.task_results}
    assert C2ModelTaskStatus.MISSING_DEPENDENCY in statuses or C2ModelTaskStatus.UNSUPPORTED_TASK in statuses
    assert all(
        attempt.status != C2ModelTaskStatus.AVAILABLE_AND_RAN
        for attempt in result.task_results
    )
    assert all(attempt.invalid_claims for attempt in result.task_results)
    assert result.failure_taxonomy


def test_c2_model_task_status_maps_missing_dependency_before_weight_blockers():
    model = _status_model()
    record = _status_audit_record(
        dependency_status="missing:definitely_missing_module",
        weights_status="download_disabled",
    )

    status, reason, detail = _model_task_status(model, C2TaskId.FORECASTING, record)

    assert status == C2ModelTaskStatus.MISSING_DEPENDENCY
    assert reason == "dependency modules are unavailable"
    assert detail == "missing:definitely_missing_module"


def test_c2_model_task_status_maps_unsupported_task_before_weight_blockers():
    model = _status_model(supported_tasks=[C2TaskId.FORECASTING])
    record = _status_audit_record(weights_status="download_disabled")

    status, reason, detail = _model_task_status(model, C2TaskId.IMPUTATION, record)

    assert status == C2ModelTaskStatus.UNSUPPORTED_TASK
    assert reason == "imputation is not listed in supported_tasks"
    assert detail == "forecasting"


@pytest.mark.parametrize(
    "audit_status",
    [C2AuditStatus.NEEDS_LICENSE_REVIEW, C2AuditStatus.NEEDS_INTERFACE_REVIEW],
)
def test_c2_model_task_status_maps_license_or_interface_review(audit_status):
    model = _status_model()
    record = _status_audit_record(
        audit_status=audit_status,
        weights_status="download_allowed",
    )

    status, reason, detail = _model_task_status(model, C2TaskId.FORECASTING, record)

    assert status == C2ModelTaskStatus.LICENSE_OR_INTERFACE_NEEDS_REVIEW
    assert reason == "license or interface review prevents external model execution"
    assert detail == audit_status.value


def test_c2_model_task_status_maps_blocked_weights():
    model = _status_model()
    record = _status_audit_record(weights_status="download_disabled")

    status, reason, detail = _model_task_status(model, C2TaskId.FORECASTING, record)

    assert status == C2ModelTaskStatus.MISSING_OR_BLOCKED_WEIGHTS
    assert reason == "model weights are unavailable because downloads are disabled"
    assert detail == "download_disabled"


def test_c2_runner_returns_data_error_when_no_windows(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True, rows=8)
    with pytest.raises(ValueError, match="not enough windows"):
        run_c2_open_model_evaluation(load_c2_open_model_config(config_path))


def test_c2_report_contains_required_sections(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    result = run_c2_open_model_evaluation(load_c2_open_model_config(config_path))
    text = render_c2_open_model_report(result, config_path=str(config_path))
    report_lines = set(text.splitlines())
    required_headings = [
        "# C2 Open Model Evaluation Report",
        "## Report Metadata",
        "## C2 Scope",
        "## Model Audit Table",
        "## Model-Task Result Matrix",
        "## Forecasting Results",
        "## Representation And Imputation Results",
        "## Baseline Comparison",
        "## Failure Taxonomy",
        "## C2 -> C3 Handoff",
        "## C2 -> B Decision Notes",
        "## Invalid Claims",
    ]
    for heading in required_headings:
        assert heading in report_lines
    for model_id in CORE_MODEL_IDS:
        assert model_id in text
    assert "不得解释为生产告警" in text
    assert "missing_dependency" in text
    assert "forced missing dependency status from C2 config" in text
    assert "force_missing_dependency:true" in text
    assert "C2 records baseline metrics and model-task readiness only." in text
    assert "C2 results are not a B-stage self-training Go decision." in text


def test_c2_value_renders_empty_containers_as_not_available():
    assert _value({}) == "not_available"
    assert _value([]) == "not_available"


def test_cli_c_stage_c2_writes_report_when_candidates_fail(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True, strict_model_success=False)
    output = tmp_path / "c2_report.md"
    result = main(["experiment", "c-stage-c2", "--config", str(config_path), "--output", str(output)])
    assert result == 0
    text = output.read_text(encoding="utf-8")
    assert "C2 Open Model Evaluation Report" in text
    assert "missing_dependency" in text or "unsupported_task" in text


def test_cli_c_stage_c2_strict_candidate_failure_returns_nonzero_but_writes_report(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True, strict_model_success=True)
    output = tmp_path / "c2_report.md"
    result = main(["experiment", "c-stage-c2", "--config", str(config_path), "--output", str(output)])
    assert result == 1
    assert output.exists()


def test_cli_c_stage_c2_returns_nonzero_for_missing_dataset(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw["dataset"]["fu13_observations"] = str(tmp_path / "missing.parquet")
    config_path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    output = tmp_path / "c2_report.md"
    result = main(["experiment", "c-stage-c2", "--config", str(config_path), "--output", str(output)])
    assert result == 1


def test_cli_c_stage_c2_returns_nonzero_when_report_cannot_be_written(tmp_path, monkeypatch):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)

    def fail_write_text(self, *args, **kwargs):
        raise PermissionError("read-only report target")

    monkeypatch.setattr(Path, "write_text", fail_write_text)
    result = main(
        [
            "experiment",
            "c-stage-c2",
            "--config",
            str(config_path),
            "--output",
            str(tmp_path / "c2_report.md"),
        ]
    )
    assert result == 1


def _task_result(result, model_id, task_id):
    return next(item for item in result.task_results if item.model_id == model_id and item.task_id == task_id)


def _status_model(*, supported_tasks=None):
    tasks = supported_tasks or [C2TaskId.FORECASTING]
    return C2ModelSpec(
        model_id="status_model",
        display_name="Status Model",
        source_kind="local",
        source_ref="source",
        model_card_ref="model_card",
        license_note="reviewed",
        dependency_modules=[],
        primary_tasks=list(tasks),
        supported_tasks=list(tasks),
    )


def _status_audit_record(
    *,
    dependency_status="available",
    weights_status="download_allowed",
    audit_status=C2AuditStatus.AUDIT_PASSED,
):
    return C2ModelAuditRecord(
        model_id="status_model",
        display_name="Status Model",
        source_kind="local",
        source_ref="source",
        model_card_ref="model_card",
        license_note="reviewed",
        dependency_status=dependency_status,
        weights_status=weights_status,
        supported_tasks=[C2TaskId.FORECASTING.value],
        input_constraints="supported_tasks:forecasting",
        offline_feasibility="no_network_by_default:true",
        audit_status=audit_status,
    )


def _model_window(values):
    return ModelWindow(
        X=values,
        mask=np.ones_like(values, dtype=bool),
        delta_t=np.zeros(values.shape[0]),
        stage_token=np.array(["stage"] * values.shape[0], dtype=object),
        sensor_token=[f"sensor_{index}" for index in range(values.shape[1])],
        domain_token=["domain"] * values.shape[1],
        device_token="FU13",
        y=np.empty((0, values.shape[1])),
        degradation_label="normal",
    )


def _write_c2_fixture_config(tmp_path, *, force_model_failures=False, rows=120, strict_model_success=False):
    dataset = tmp_path / "fu13.parquet"
    _write_fu13_fixture(dataset, rows=rows)
    raw = yaml.safe_load(Path("configs/c_stage_c2_open_model_evaluation.yaml").read_text(encoding="utf-8"))
    raw["dataset"]["fu13_observations"] = str(dataset)
    raw["dataset"]["boundary"] = "test_fixture_no_private_data"
    raw["window"]["context_length"] = 24
    raw["window"]["prediction_length"] = 6
    raw["window"]["max_windows"] = 8
    raw["outputs"]["report"] = str(tmp_path / "report.md")
    raw["execution_policy"]["strict_model_success"] = strict_model_success
    if force_model_failures:
        for model in raw["core_models"]:
            model["force_missing_dependency"] = model["model_id"] in {"ttm", "chronos", "timesfm", "moirai_uni2ts", "moment"}
            model["force_unsupported_task"] = model["model_id"] == "units"
    path = tmp_path / "c2.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return path


def _write_fu13_fixture(path, *, rows=120):
    timestamps = pd.date_range("2026-05-01", periods=rows, freq="5s", tz="UTC")
    records = []
    for i, ts in enumerate(timestamps):
        stage = "溶解" if i < rows // 2 else "浇筑"
        quality = "good" if i % 17 else "unassigned_cycle"
        for sensor, domain, value in [
            ("LeakElec", "electrical", 10 + np.sin(i / 7)),
            ("O2Content", "atmosphere", -20 + np.cos(i / 9)),
        ]:
            records.append(
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
    pd.DataFrame(records).to_parquet(path, index=False)
