from pathlib import Path

import pytest

from b08_model_core.experiments.c3_public_dataset_registry import (
    C3DatasetRole,
    C3RegistryConfigError,
    load_c3_registry_config,
    render_c3_registry_report,
    run_c3_public_dataset_registry,
)


def test_c3_default_registry_config_has_initial_dataset_set():
    config = load_c3_registry_config("configs/c_stage_c3_public_dataset_registry.yaml")

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
    text = Path("configs/c_stage_c3_public_dataset_registry.yaml").read_text(
        encoding="utf-8"
    )
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        text.replace(
            """latest_source_calibration:
  enabled: true
  policy: watchlist_only
  note: "Only records whether new 2025-2026 candidates should enter watchlist; no dataset download in C3 first loop."
""",
            """latest_source_calibration:
  - enabled
""",
            1,
        ),
        encoding="utf-8",
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
    text = Path("configs/c_stage_c3_public_dataset_registry.yaml").read_text(
        encoding="utf-8"
    )
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        text.replace("license_status: needs_review", "license_status: verifed", 1),
        encoding="utf-8",
    )

    with pytest.raises(C3RegistryConfigError, match="license_status"):
        load_c3_registry_config(broken)


def test_c3_registry_does_not_allow_needs_review_training_use_as_ready():
    config = load_c3_registry_config("configs/c_stage_c3_public_dataset_registry.yaml")
    result = run_c3_public_dataset_registry(config)

    by_id = {item.dataset_id: item for item in result.readiness}

    assert by_id["nasa_cmapss"].readiness == "needs_source_license_review"
    assert "training_use_status=needs_review" in by_id["nasa_cmapss"].reasons
    assert by_id["nasa_cmapss"].readiness != "ready_for_next_mapping"


def test_c3_registry_does_not_allow_unknown_training_use_as_ready(tmp_path):
    text = Path("configs/c_stage_c3_public_dataset_registry.yaml").read_text(
        encoding="utf-8"
    )
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        text.replace(
            "training_use_status: needs_review",
            "training_use_status: unknown",
            1,
        ),
        encoding="utf-8",
    )
    config = load_c3_registry_config(broken)
    result = run_c3_public_dataset_registry(config)

    by_id = {item.dataset_id: item for item in result.readiness}

    assert by_id["fu13_internal"].readiness == "needs_source_license_review"
    assert "training_use_status=unknown" in by_id["fu13_internal"].reasons
    assert by_id["fu13_internal"].readiness != "ready_for_next_mapping"


def test_c3_registry_rejects_verified_source_with_needs_review_source_url(tmp_path):
    text = Path("configs/c_stage_c3_public_dataset_registry.yaml").read_text(
        encoding="utf-8"
    )
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        text.replace("source_status: needs_review", "source_status: verified", 1)
        .replace(
            "official_source_url: internal_no_public_url",
            "official_source_url: needs_review",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(C3RegistryConfigError, match="source_status|official_source_url"):
        load_c3_registry_config(broken)


def test_c3_registry_flags_split_policy_review_for_rul_data(tmp_path):
    text = Path("configs/c_stage_c3_public_dataset_registry.yaml").read_text(
        encoding="utf-8"
    )
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        text.replace(
            "split_policy: unit_run_split_required",
            "split_policy: time_split",
            1,
        ),
        encoding="utf-8",
    )
    config = load_c3_registry_config(broken)

    result = run_c3_public_dataset_registry(config)
    by_id = {item.dataset_id: item for item in result.readiness}

    assert by_id["nasa_cmapss"].readiness == "split_policy_review"
    assert "unit_or_run_split_required_for_rul" in by_id["nasa_cmapss"].reasons


def test_c3_registry_flags_process_fault_leakage_review(tmp_path):
    text = Path("configs/c_stage_c3_public_dataset_registry.yaml").read_text(
        encoding="utf-8"
    )
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        text.replace(
            (
                'leakage_risks: "Process fault trajectory, fault injection timing, '
                'and operating condition leakage must be guarded."'
            ),
            'leakage_risks: "needs split review"',
            1,
        ),
        encoding="utf-8",
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
    config = load_c3_registry_config("configs/c_stage_c3_public_dataset_registry.yaml")
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
