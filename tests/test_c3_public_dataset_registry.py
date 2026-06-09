from pathlib import Path

import pytest
import yaml

from b08_model_core.cli import main
from b08_model_core.experiments.c3_public_dataset_registry import (
    C3DatasetRole,
    C3RegistryConfigError,
    load_c3_registry_config,
    render_c3_registry_report,
    run_c3_public_dataset_registry,
)

_DEFAULT_REGISTRY = Path("configs/c_stage_c3_public_dataset_registry.yaml")


def _load_default_registry_yaml() -> dict:
    return yaml.safe_load(_DEFAULT_REGISTRY.read_text(encoding="utf-8"))


def _write_registry_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _write_modified_default_registry(tmp_path, update) -> Path:
    data = _load_default_registry_yaml()
    update(data)
    path = tmp_path / "broken.yaml"
    _write_registry_yaml(path, data)
    return path


def _dataset_by_id(data: dict, dataset_id: str) -> dict:
    for dataset in data["datasets"]:
        if dataset["dataset_id"] == dataset_id:
            return dataset
    raise AssertionError(f"missing dataset_id={dataset_id}")


def test_c3_default_registry_config_has_initial_dataset_set():
    config = load_c3_registry_config(_DEFAULT_REGISTRY)

    assert config.stage == "C3_public_dataset_registry"
    assert config.outputs.report == Path("reports/c_stage_c3_public_dataset_registry.md")
    assert tuple(item.dataset_id for item in config.datasets) == (
        "fu13_internal",
        "nasa_cmapss",
        "ims_bearing",
        "pronostia_femto",
        "tennessee_eastman_process",
    )
    assert config.datasets[0].dataset_role == C3DatasetRole.INTERNAL_ANCHOR
    assert all(item.invalid_claims for item in config.datasets)


def test_cli_c_stage_c3_writes_registry_report(tmp_path):
    output = tmp_path / "c3_registry.md"

    exit_code = main(
        [
            "experiment",
            "c-stage-c3",
            "--config",
            "configs/c_stage_c3_public_dataset_registry.yaml",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "C3 Public Dataset Registry Report" in text
    assert "fu13_internal" in text
    assert "nasa_cmapss" in text


def test_c3_registry_rejects_missing_required_dataset_field(tmp_path):
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        """
stage: C3_public_dataset_registry
latest_source_calibration:
  enabled: true
  policy: watchlist_only
outputs:
  report: reports/c_stage_c3_public_dataset_registry.md
datasets:
  - dataset_id: missing_display_name
""",
        encoding="utf-8",
    )

    with pytest.raises(C3RegistryConfigError, match="display_name"):
        load_c3_registry_config(broken)


def test_c3_registry_rejects_non_mapping_latest_source_calibration(tmp_path):
    broken = _write_modified_default_registry(
        tmp_path,
        lambda data: data.update({"latest_source_calibration": ["enabled"]}),
    )

    with pytest.raises(C3RegistryConfigError, match="latest_source_calibration"):
        load_c3_registry_config(broken)


def test_c3_registry_wraps_malformed_yaml_errors(tmp_path):
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        """
stage: C3_public_dataset_registry
latest_source_calibration:
  enabled: true
outputs:
  report: reports/c_stage_c3_public_dataset_registry.md
datasets:
  - dataset_id: malformed
    display_name: Broken
    dataset_role: internal_anchor
    source_type: internal
    official_source_url: internal
    source_status: needs_review
    license_status: needs_review
    redistribution_status: needs_review
    training_use_status: needs_review
    task_families: [forecasting
""",
        encoding="utf-8",
    )

    with pytest.raises(C3RegistryConfigError, match="YAML"):
        load_c3_registry_config(broken)


def test_c3_registry_rejects_invalid_enum_value(tmp_path):
    broken = _write_modified_default_registry(
        tmp_path,
        lambda data: _dataset_by_id(data, "nasa_cmapss").update(
            {"license_status": "verifed"}
        ),
    )

    with pytest.raises(C3RegistryConfigError, match="license_status"):
        load_c3_registry_config(broken)


def test_c3_registry_does_not_allow_needs_review_training_use_as_ready():
    config = load_c3_registry_config(_DEFAULT_REGISTRY)
    result = run_c3_public_dataset_registry(config)

    by_id = {item.dataset_id: item for item in result.readiness}

    assert by_id["nasa_cmapss"].readiness == "needs_source_license_review"
    assert "training_use_status=needs_review" in by_id["nasa_cmapss"].reasons
    assert by_id["nasa_cmapss"].readiness != "ready_for_next_mapping"


def test_c3_registry_does_not_allow_unknown_training_use_as_ready(tmp_path):
    broken = _write_modified_default_registry(
        tmp_path,
        lambda data: _dataset_by_id(data, "fu13_internal").update(
            {"training_use_status": "unknown"}
        ),
    )
    config = load_c3_registry_config(broken)
    result = run_c3_public_dataset_registry(config)

    by_id = {item.dataset_id: item for item in result.readiness}

    assert by_id["fu13_internal"].readiness == "needs_source_license_review"
    assert "training_use_status=unknown" in by_id["fu13_internal"].reasons
    assert by_id["fu13_internal"].readiness != "ready_for_next_mapping"


def test_c3_registry_rejects_verified_source_with_needs_review_source_url(tmp_path):
    broken = _write_modified_default_registry(
        tmp_path,
        lambda data: _dataset_by_id(data, "nasa_cmapss").update(
            {"source_status": "verified", "official_source_url": "needs_review"}
        ),
    )

    with pytest.raises(C3RegistryConfigError, match="source_status|official_source_url"):
        load_c3_registry_config(broken)


def test_c3_registry_flags_split_policy_review_for_rul_data(tmp_path):
    broken = _write_modified_default_registry(
        tmp_path,
        lambda data: _dataset_by_id(data, "nasa_cmapss").update(
            {"split_policy": "time_split"}
        ),
    )
    config = load_c3_registry_config(broken)

    result = run_c3_public_dataset_registry(config)
    by_id = {item.dataset_id: item for item in result.readiness}

    assert by_id["nasa_cmapss"].readiness == "split_policy_review"
    assert "unit_or_run_split_required_for_rul" in by_id["nasa_cmapss"].reasons


def test_c3_registry_flags_process_fault_leakage_review(tmp_path):
    broken = _write_modified_default_registry(
        tmp_path,
        lambda data: _dataset_by_id(data, "tennessee_eastman_process").update(
            {"leakage_risks": "needs split review"}
        ),
    )
    config = load_c3_registry_config(broken)

    result = run_c3_public_dataset_registry(config)
    by_id = {item.dataset_id: item for item in result.readiness}

    assert by_id["tennessee_eastman_process"].readiness == "split_policy_review"
    assert (
        "fault_or_condition_leakage_guard_required"
        in by_id["tennessee_eastman_process"].reasons
    )


def test_c3_registry_report_contains_required_sections():
    config = load_c3_registry_config(_DEFAULT_REGISTRY)
    result = run_c3_public_dataset_registry(config)
    text = render_c3_registry_report(result)

    assert "C3 Public Dataset Registry Report" in text
    assert "Registry Summary" in text
    assert "Dataset Readiness Table" in text
    assert "Source And License Audit" in text
    assert "Task And Metric Mapping" in text
    assert "Canonical Schema Mapping Status" in text
    assert "Split Policy And Leakage Guard" in text
    assert "Latest Source Calibration Notes" in text
    assert "Go / No-Go For Next C3 Loop" in text
    assert "Invalid Claims" in text
    assert "不下载公开数据原始文件" in text
    assert "不提交公开数据或派生 parquet" in text
    assert "不运行模型训练" in text
    assert (
        "| Dataset | Decision | Required Next Action | Prerequisites | Risk Level |"
        in text
    )
    assert "official_source_confirmed, license_and_training_use_reviewed" in text
    assert "| nasa_cmapss | No-Go / Review: needs_source_license_review |" in text
    assert "| high |" in text
