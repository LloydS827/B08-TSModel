from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from b08_model_core.experiments.c2_open_model_evaluation import (
    C2AuditStatus,
    C2ModelAuditRecord,
    C2OpenModelConfigError,
    CORE_MODEL_IDS,
    C2TaskId,
    build_c2_model_registry,
    load_c2_open_model_config,
    run_c2_model_audit,
)


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
