from pathlib import Path

import pytest
import yaml

from b08_model_core.cli import main
from b08_model_core.experiments.c31_cmapss_minimal_ingestion import (
    C31CmapssConfigError,
    C31LicenseDecision,
    C31TopLevelStatus,
    expected_cmapss_files,
    load_c31_cmapss_config,
    render_c31_cmapss_report,
    run_c31_cmapss_minimal_ingestion,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG = _REPO_ROOT / "configs/c_stage_c31_cmapss_minimal_ingestion.yaml"


def _load_default_yaml() -> dict:
    return yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def _modified_config(tmp_path: Path, update) -> Path:
    data = _load_default_yaml()
    update(data)
    return _write_yaml(tmp_path / "c31.yaml", data)


def test_c31_default_config_is_offline_and_lists_classic_cmapss_files():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)

    assert config.stage == "C3_1_cmapss_minimal_ingestion"
    assert config.dataset_id == "nasa_cmapss"
    assert config.download_policy.allow_network is False
    assert config.download_policy.allow_download is False
    assert config.download_policy.allow_local_raw_data is False
    assert config.download_policy.allow_write_processed is False
    assert config.source.source_status == "verified"
    assert (
        config.license_review.decision
        == C31LicenseDecision.APPROVED_FOR_RESEARCH_TRAINING
    )
    assert config.license_review.license_status == "verified"
    assert config.license_review.redistribution_status == "allowed"
    assert config.license_review.training_use_status == "research_only"
    assert config.license_evidence.record_url == "https://zenodo.org/records/15346912"
    assert config.license_evidence.doi == "10.5281/zenodo.15346912"
    assert config.license_evidence.license_id == "cc-by-4.0"
    assert config.license_evidence.file_key == "CMAPSSData.zip"
    assert config.license_evidence.file_size_bytes == 12425978
    assert len(config.download_policy.expected_files) == 12
    assert config.download_policy.expected_files == expected_cmapss_files()
    assert config.outputs.report == Path("reports/c_stage_c31_cmapss_minimal_ingestion.md")


def test_c31_rejects_duplicate_yaml_mapping_keys(tmp_path):
    text = _DEFAULT_CONFIG.read_text(encoding="utf-8").replace(
        "  allow_network: false\n  allow_download: false\n",
        "  allow_network: false\n  allow_network: false\n  allow_download: false\n",
    )
    path = tmp_path / "duplicate_key.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(C31CmapssConfigError, match="duplicate|YAML|allow_network"):
        load_c31_cmapss_config(path)


def test_c31_wraps_malformed_yaml_errors(tmp_path):
    path = tmp_path / "malformed.yaml"
    path.write_text(
        """
stage: C3_1_cmapss_minimal_ingestion
dataset_id: nasa_cmapss
download_policy:
  expected_files: [train_FD001.txt
""",
        encoding="utf-8",
    )

    with pytest.raises(C31CmapssConfigError, match="YAML"):
        load_c31_cmapss_config(path)


def test_c31_default_runner_blocks_without_reading_raw_data():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)

    result = run_c31_cmapss_minimal_ingestion(config, config_path=_DEFAULT_CONFIG)

    assert result.status == C31TopLevelStatus.BLOCKED
    reasons = [reason.value for reason in result.blocked_reasons]
    assert "blocked_by_license_review" not in reasons
    assert reasons == ["blocked_by_download_policy"]
    assert result.c32_go_no_go == "No-Go: local raw mapping review not executed"
    assert result.raw_files_present == ()
    assert result.raw_files_missing == tuple(config.download_policy.expected_files)


def test_c31_report_contains_required_sections_for_default_config():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)
    result = run_c31_cmapss_minimal_ingestion(config, config_path=_DEFAULT_CONFIG)

    text = render_c31_cmapss_report(result)

    required_sections = (
        "# C3.1 NASA C-MAPSS Minimal Ingestion Report",
        "## C3.1 Summary",
        "## Source And License Preflight",
        "## Source Calibration Notes",
        "## Download Boundary And Local Paths",
        "## Expected C-MAPSS Files",
        "## Raw File Presence / Download Status",
        "## Schema Mapping Dry-Run",
        "## Canonical Observation Compatibility",
        "## RUL / Degradation Target Metadata",
        "## Split Policy And Leakage Guard",
        "## Supported Tasks And Metrics",
        "## Invalid Claims",
        "## C3.2 Go / No-Go",
    )
    for section in required_sections:
        assert section in text
    assert "不下载公开数据，不提交公开数据或派生 parquet，不运行模型训练。" in text
    assert "blocked" in text
    assert "blocked_by_download_policy" in text


def test_c31_report_renders_source_license_decision_details():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)
    result = run_c31_cmapss_minimal_ingestion(config, config_path=_DEFAULT_CONFIG)

    text = render_c31_cmapss_report(result)

    assert "NASA PCoE #6 Turbofan Engine Degradation Simulation Data Set" in text
    assert (
        "https://www.nasa.gov/intelligent-systems-division/"
        "discovery-and-systems-health/pcoe/pcoe-data-set-repository/"
    ) in text
    assert (
        "https://phm-datasets.s3.amazonaws.com/NASA/"
        "6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
    ) in text
    assert "Saxena, A., Goebel, K., Simon, D., and Eklund, N." in text
    assert "| license_decision | approved_for_research_training |" in text
    assert "| redistribution_status | allowed |" in text
    assert "| training_use_status | research_only |" in text
    assert (
        "Local raw opt-in: eligible for a separate explicit opt-in review, "
        "but disabled in the default configuration."
    ) in text


def test_c31_report_renders_license_evidence_and_next_gate():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)
    result = run_c31_cmapss_minimal_ingestion(config, config_path=_DEFAULT_CONFIG)

    text = render_c31_cmapss_report(result)

    assert "https://zenodo.org/records/15346912" in text
    assert "10.5281/zenodo.15346912" in text
    assert "Creative Commons Attribution 4.0 International" in text
    assert "cc-by-4.0" in text
    assert "CMAPSSData.zip" in text
    assert "12425978" in text
    assert "| license_decision | approved_for_research_training |" in text
    assert "| redistribution_status | allowed |" in text
    assert "| training_use_status | research_only |" in text
    assert (
        "Local raw opt-in: eligible for a separate explicit opt-in review, "
        "but disabled in the default configuration."
    ) in text
    assert (
        "Current default C3.2 gate: No-Go until local raw mapping review validates "
        "full schema, RUL metadata, and leakage guard."
    ) in text
    assert "blocked_by_license_review" not in text


def test_cli_c_stage_c31_writes_default_preflight_report(tmp_path):
    output = tmp_path / "c31.md"

    exit_code = main(
        [
            "experiment",
            "c-stage-c31",
            "--config",
            "configs/c_stage_c31_cmapss_minimal_ingestion.yaml",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "C3.1 NASA C-MAPSS Minimal Ingestion Report" in text
    assert "blocked" in text
    assert "blocked_by_download_policy" in text


def test_c31_default_runner_reports_input_feature_leakage_while_preflight_blocked():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)

    result = run_c31_cmapss_minimal_ingestion(
        config,
        config_path=_DEFAULT_CONFIG,
        input_feature_columns=("sensor_01", "rul"),
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_download_policy" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.target_columns_in_input == ("rul",)


def test_c31_default_runner_reports_explicit_split_overlap_while_preflight_blocked():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)

    result = run_c31_cmapss_minimal_ingestion(
        config,
        config_path=_DEFAULT_CONFIG,
        split_assignments={
            "train": {"cmapss_FD001_train_unit_1"},
            "validation": {"cmapss_FD001_train_unit_1"},
        },
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.trajectory_overlap_count == 1


def test_c31_default_runner_does_not_inspect_raw_dir_when_local_raw_disabled(
    tmp_path,
    monkeypatch,
):
    sentinel_raw_dir = Path("data/public/cmapss/raw/sentinel_raw")
    path = _modified_config(
        tmp_path,
        lambda data: data["download_policy"].update({"raw_dir": str(sentinel_raw_dir)}),
    )
    config = load_c31_cmapss_config(path)

    def fail_if_raw_path(method_name: str):
        def guard(path: Path, *args, **kwargs):
            if path == sentinel_raw_dir or path.is_relative_to(sentinel_raw_dir):
                raise AssertionError(
                    f"unexpected raw_dir inspection via {method_name}: {path}"
                )
            return originals[method_name](path, *args, **kwargs)

        return guard

    originals = {
        "exists": Path.exists,
        "is_file": Path.is_file,
        "iterdir": Path.iterdir,
        "glob": Path.glob,
        "stat": Path.stat,
    }
    for method_name in originals:
        monkeypatch.setattr(Path, method_name, fail_if_raw_path(method_name))

    result = run_c31_cmapss_minimal_ingestion(config, config_path=path)

    assert result.status == C31TopLevelStatus.BLOCKED


def test_c31_source_license_block_does_not_inspect_raw_dir_when_local_raw_enabled(
    tmp_path,
    monkeypatch,
):
    sentinel_raw_dir = Path("data/public/cmapss/raw/sentinel_raw")

    def update(data: dict) -> None:
        data["license_review"].update(
            {
                "decision": "needs_review",
                "license_status": "needs_review",
                "redistribution_status": "needs_review",
                "training_use_status": "needs_review",
            }
        )
        data["download_policy"].update(
            {
                "allow_local_raw_data": True,
                "raw_dir": str(sentinel_raw_dir),
            }
        )

    path = _modified_config(tmp_path, update)
    config = load_c31_cmapss_config(path)

    def fail_if_raw_path(method_name: str):
        def guard(path: Path, *args, **kwargs):
            if path == sentinel_raw_dir or path.is_relative_to(sentinel_raw_dir):
                raise AssertionError(
                    f"unexpected raw_dir inspection via {method_name}: {path}"
                )
            return originals[method_name](path, *args, **kwargs)

        return guard

    originals = {
        "exists": Path.exists,
        "is_file": Path.is_file,
        "iterdir": Path.iterdir,
        "glob": Path.glob,
        "stat": Path.stat,
    }
    for method_name in originals:
        monkeypatch.setattr(Path, method_name, fail_if_raw_path(method_name))

    result = run_c31_cmapss_minimal_ingestion(config, config_path=path)

    assert result.status == C31TopLevelStatus.BLOCKED
    assert [reason.value for reason in result.blocked_reasons] == [
        "blocked_by_license_review"
    ]


def test_c31_blocks_unapproved_source_even_when_license_is_schema_approved(tmp_path):
    def update(data: dict) -> None:
        data["source"]["source_status"] = "needs_review"
        data["license_review"].update(
            {
                "decision": "approved_for_schema_validation",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "needs_review",
            }
        )

    path = _modified_config(tmp_path, update)
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config, config_path=path)

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_source_review" in [reason.value for reason in result.blocked_reasons]


@pytest.mark.parametrize(
    "update,match",
    [
        (
            lambda data: data["download_policy"].update({"allow_network": False, "allow_download": True}),
            "allow_download",
        ),
        (
            lambda data: data["download_policy"].update(
                {"allow_network": True, "allow_download": True, "allow_local_raw_data": False}
            ),
            "allow_local_raw_data",
        ),
        (
            lambda data: data["download_policy"].update({"allow_write_processed": True, "allow_local_raw_data": False}),
            "allow_write_processed",
        ),
    ],
)
def test_c31_rejects_unsafe_download_policy_combinations(tmp_path, update, match):
    path = _modified_config(tmp_path, update)

    with pytest.raises(C31CmapssConfigError, match=match):
        load_c31_cmapss_config(path)


@pytest.mark.parametrize(
    "update,match",
    [
        (
            lambda data: data["download_policy"].update({"raw_dir": "data/public"}),
            "raw_dir",
        ),
        (
            lambda data: data["download_policy"].update(
                {"processed_dir": "data/processed"}
            ),
            "processed_dir",
        ),
        (
            lambda data: data["outputs"].update({"processed_dir": "reports/cmapss"}),
            "outputs.processed_dir",
        ),
    ],
)
def test_c31_rejects_paths_outside_local_data_boundaries(tmp_path, update, match):
    path = _modified_config(tmp_path, update)

    with pytest.raises(C31CmapssConfigError, match=match):
        load_c31_cmapss_config(path)


@pytest.mark.parametrize(
    "update,match",
    [
        (
            lambda data: data["license_review"].update({"license_status": "allowed"}),
            "license_status",
        ),
        (
            lambda data: data["license_review"].update(
                {"training_use_status": "verified"}
            ),
            "training_use_status",
        ),
    ],
)
def test_c31_rejects_license_fields_with_wrong_semantics(tmp_path, update, match):
    path = _modified_config(tmp_path, update)

    with pytest.raises(C31CmapssConfigError, match=match):
        load_c31_cmapss_config(path)


def test_c31_rejects_non_positive_license_evidence_file_size(tmp_path):
    path = _modified_config(
        tmp_path,
        lambda data: data["license_evidence"].update({"file_size_bytes": 0}),
    )

    with pytest.raises(C31CmapssConfigError, match="file_size_bytes"):
        load_c31_cmapss_config(path)


def test_c31_rejects_research_training_approval_with_needs_review_statuses(tmp_path):
    path = _modified_config(
        tmp_path,
        lambda data: data["license_review"].update(
            {
                "decision": "approved_for_research_training",
                "license_status": "needs_review",
                "redistribution_status": "needs_review",
                "training_use_status": "needs_review",
            }
        ),
    )

    with pytest.raises(C31CmapssConfigError, match="approved_for_research_training"):
        load_c31_cmapss_config(path)


def test_c31_rejects_schema_validation_approval_with_unverified_license(tmp_path):
    path = _modified_config(
        tmp_path,
        lambda data: data["license_review"].update(
            {
                "decision": "approved_for_schema_validation",
                "license_status": "needs_review",
                "redistribution_status": "not_allowed",
                "training_use_status": "needs_review",
            }
        ),
    )

    with pytest.raises(C31CmapssConfigError, match="approved_for_schema_validation"):
        load_c31_cmapss_config(path)


def test_c31_rejects_duplicate_mapping_subsets(tmp_path):
    def update(data: dict) -> None:
        data["mapping_policy"].update({"subsets": ["FD001", "FD001"]})
        data["download_policy"]["expected_files"] = [
            "train_FD001.txt",
            "test_FD001.txt",
            "RUL_FD001.txt",
            "train_FD001.txt",
            "test_FD001.txt",
            "RUL_FD001.txt",
        ]

    path = _modified_config(tmp_path, update)

    with pytest.raises(C31CmapssConfigError, match="subsets"):
        load_c31_cmapss_config(path)


def test_c31_rejects_duplicate_mapping_file_roles(tmp_path):
    def update(data: dict) -> None:
        data["mapping_policy"].update(
            {"subsets": ["FD001"], "file_roles": ["train", "train", "RUL"]}
        )
        data["download_policy"]["expected_files"] = [
            "train_FD001.txt",
            "train_FD001.txt",
            "RUL_FD001.txt",
        ]

    path = _modified_config(tmp_path, update)

    with pytest.raises(C31CmapssConfigError, match="file_roles"):
        load_c31_cmapss_config(path)


@pytest.mark.parametrize(
    "file_roles,expected_files",
    [
        (["train", "RUL"], ["train_FD001.txt", "RUL_FD001.txt"]),
        (["train", "test"], ["train_FD001.txt", "test_FD001.txt"]),
    ],
)
def test_c31_rejects_incomplete_mapping_file_roles(
    tmp_path,
    file_roles,
    expected_files,
):
    def update(data: dict) -> None:
        data["mapping_policy"].update(
            {"subsets": ["FD001"], "file_roles": file_roles}
        )
        data["download_policy"]["expected_files"] = expected_files

    path = _modified_config(tmp_path, update)

    with pytest.raises(C31CmapssConfigError, match="file_roles"):
        load_c31_cmapss_config(path)


def test_c31_rejects_full_classic_expected_files_when_subset_order_is_reordered(tmp_path):
    def update(data: dict) -> None:
        data["mapping_policy"].update(
            {"subsets": ["FD002", "FD001", "FD003", "FD004"]}
        )
        data["download_policy"]["expected_files"] = [
            "train_FD002.txt",
            "test_FD002.txt",
            "RUL_FD002.txt",
            "train_FD001.txt",
            "test_FD001.txt",
            "RUL_FD001.txt",
            "train_FD003.txt",
            "test_FD003.txt",
            "RUL_FD003.txt",
            "train_FD004.txt",
            "test_FD004.txt",
            "RUL_FD004.txt",
        ]

    path = _modified_config(
        tmp_path,
        update,
    )

    with pytest.raises(C31CmapssConfigError, match="full classic"):
        load_c31_cmapss_config(path)


def test_c31_rejects_full_classic_expected_files_when_file_role_order_is_reordered(tmp_path):
    def update(data: dict) -> None:
        data["mapping_policy"].update({"file_roles": ["test", "train", "RUL"]})
        data["download_policy"]["expected_files"] = [
            "test_FD001.txt",
            "train_FD001.txt",
            "RUL_FD001.txt",
            "test_FD002.txt",
            "train_FD002.txt",
            "RUL_FD002.txt",
            "test_FD003.txt",
            "train_FD003.txt",
            "RUL_FD003.txt",
            "test_FD004.txt",
            "train_FD004.txt",
            "RUL_FD004.txt",
        ]

    path = _modified_config(
        tmp_path,
        update,
    )

    with pytest.raises(C31CmapssConfigError, match="file_roles"):
        load_c31_cmapss_config(path)


@pytest.mark.parametrize(
    "update,match",
    [
        (
            lambda data: data["download_policy"].update({"checksum_policy": "skip"}),
            "checksum_policy",
        ),
        (
            lambda data: data["mapping_policy"].update({"sensor_count": 20}),
            "sensor_count",
        ),
        (
            lambda data: data["mapping_policy"].update({"setting_count": 4}),
            "setting_count",
        ),
        (
            lambda data: data["mapping_policy"].update({"use_capped_rul": True}),
            "use_capped_rul",
        ),
        (
            lambda data: data["split_policy"].update({"split_unit": "unit_id"}),
            "split_unit",
        ),
        (
            lambda data: data["split_policy"].update({"validation_source": "random"}),
            "validation_source",
        ),
        (
            lambda data: data["split_policy"].update(
                {
                    "forbidden_leakage_modes": [
                        "target_columns_in_input_features",
                        "trajectory_id_overlap",
                        "window_adjacency_across_splits",
                    ]
                }
            ),
            "forbidden_leakage_modes",
        ),
    ],
)
def test_c31_rejects_config_contract_drift(tmp_path, update, match):
    path = _modified_config(tmp_path, update)

    with pytest.raises(C31CmapssConfigError, match=match):
        load_c31_cmapss_config(path)


def _write_synthetic_subset(
    raw_dir: Path,
    subset: str = "FD001",
    malformed: bool = False,
) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    if malformed:
        (raw_dir / f"train_{subset}.txt").write_text("1 1 0.1\n", encoding="utf-8")
        (raw_dir / f"test_{subset}.txt").write_text("1 1 0.7\n", encoding="utf-8")
        (raw_dir / f"RUL_{subset}.txt").write_text("5\n", encoding="utf-8")
        return

    sensor_values_1 = " ".join(str(100 + index) for index in range(1, 22))
    sensor_values_2 = " ".join(str(200 + index) for index in range(1, 22))
    train_rows = [
        f"1 1 0.1 0.2 0.3 {sensor_values_1}",
        f"1 2 0.1 0.2 0.3 {sensor_values_2}",
        f"2 1 0.4 0.5 0.6 {sensor_values_1}",
    ]
    test_rows = [
        f"1 1 0.7 0.8 0.9 {sensor_values_1}",
        f"1 2 0.7 0.8 0.9 {sensor_values_2}",
    ]
    (raw_dir / f"train_{subset}.txt").write_text(
        "\n".join(train_rows) + "\n", encoding="utf-8"
    )
    (raw_dir / f"test_{subset}.txt").write_text(
        "\n".join(test_rows) + "\n", encoding="utf-8"
    )
    (raw_dir / f"RUL_{subset}.txt").write_text("5\n", encoding="utf-8")


def _configure_approved_fd001_mapping(data: dict, raw_dir: Path) -> None:
    data["source"]["source_status"] = "verified"
    data["license_review"].update(
        {
            "decision": "approved_for_schema_validation",
            "license_status": "verified",
            "redistribution_status": "not_allowed",
            "training_use_status": "needs_review",
        }
    )
    data["download_policy"].update(
        {
            "allow_local_raw_data": True,
            "raw_dir": str(raw_dir),
            "expected_files": [
                "train_FD001.txt",
                "test_FD001.txt",
                "RUL_FD001.txt",
            ],
        }
    )
    data["mapping_policy"]["subsets"] = ["FD001"]


def _approved_local_mapping_config(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)

    return _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )


def _research_approved_full_config(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_full")
    for subset in ("FD001", "FD002", "FD003", "FD004"):
        _write_synthetic_subset(raw_dir, subset=subset)

    def update(data: dict) -> None:
        data["source"]["source_status"] = "verified"
        data["license_review"].update(
            {
                "decision": "approved_for_research_training",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "research_only",
            }
        )
        data["download_policy"].update(
            {"allow_local_raw_data": True, "raw_dir": str(raw_dir)}
        )

    return _modified_config(tmp_path, update)


def _assert_blocked_by_raw_schema_mismatch(result) -> None:
    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_raw_schema_mismatch" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.mapping_summary is None
    assert result.rul_targets == ()


def test_c31_maps_synthetic_subset_to_canonical_observations(tmp_path, monkeypatch):
    config = load_c31_cmapss_config(
        _approved_local_mapping_config(tmp_path, monkeypatch)
    )

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.status == C31TopLevelStatus.READY_FOR_LOCAL_MAPPING
    assert result.mapping_summary is not None
    assert result.mapping_summary.observation_rows == 5 * 24
    assert result.mapping_summary.trajectory_count == 3
    assert result.mapping_summary.required_schema_valid is True
    assert "cmapss_FD001_train_unit_1" in result.mapping_summary.trajectory_ids
    assert "cmapss_FD001_test_unit_1" in result.mapping_summary.trajectory_ids
    assert (
        result.mapping_summary.pseudo_timestamp_rule
        == "2000-01-01T00:00:00Z + cycle_index seconds"
    )


def test_c31_partial_subset_validated_is_not_c32_ready(tmp_path, monkeypatch):
    config = load_c31_cmapss_config(
        _approved_local_mapping_config(tmp_path, monkeypatch)
    )

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.readiness_detail == "partial_subset_validated"
    assert result.status == C31TopLevelStatus.READY_FOR_LOCAL_MAPPING
    assert result.c32_go_no_go == "No-Go: partial subset only"


def test_c31_full_schema_validation_pending_training_use_review(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_full")
    for subset in ("FD001", "FD002", "FD003", "FD004"):
        _write_synthetic_subset(raw_dir, subset=subset)

    def update(data: dict) -> None:
        data["source"]["source_status"] = "verified"
        data["license_review"].update(
            {
                "decision": "approved_for_schema_validation",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "needs_review",
            }
        )
        data["download_policy"].update(
            {"allow_local_raw_data": True, "raw_dir": str(raw_dir)}
        )

    config = load_c31_cmapss_config(_modified_config(tmp_path, update))

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.readiness_detail == "full_classic_cmapss_validated"
    assert (
        result.status
        == C31TopLevelStatus.SCHEMA_VALIDATED_PENDING_TRAINING_USE_REVIEW
    )
    assert result.c32_go_no_go == "No-Go: pending training-use review"


def test_c31_full_schema_validation_ready_for_c32_when_research_training_approved(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_full")
    for subset in ("FD001", "FD002", "FD003", "FD004"):
        _write_synthetic_subset(raw_dir, subset=subset)

    def update(data: dict) -> None:
        data["source"]["source_status"] = "verified"
        data["license_review"].update(
            {
                "decision": "approved_for_research_training",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "research_only",
            }
        )
        data["download_policy"].update(
            {"allow_local_raw_data": True, "raw_dir": str(raw_dir)}
        )

    config = load_c31_cmapss_config(_modified_config(tmp_path, update))

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.readiness_detail == "full_classic_cmapss_validated"
    assert result.status == C31TopLevelStatus.SCHEMA_VALIDATED_READY_FOR_C32
    assert (
        result.c32_go_no_go
        == "Go: schema validated and research training/evaluation use approved"
    )


def test_c31_report_marks_local_raw_mapping_complete_when_c32_ready(
    tmp_path,
    monkeypatch,
):
    config = load_c31_cmapss_config(_research_approved_full_config(tmp_path, monkeypatch))

    result = run_c31_cmapss_minimal_ingestion(config)
    text = render_c31_cmapss_report(result)

    assert result.status == C31TopLevelStatus.SCHEMA_VALIDATED_READY_FOR_C32
    assert "Local raw mapping review: completed for configured raw files." in text
    assert "Local raw opt-in: blocked until license" not in text
    assert "Current default C3.2 gate" not in text


def test_c31_report_does_not_mark_local_raw_mapping_complete_when_leakage_blocked(
    tmp_path,
    monkeypatch,
):
    config = load_c31_cmapss_config(_research_approved_full_config(tmp_path, monkeypatch))

    result = run_c31_cmapss_minimal_ingestion(
        config,
        split_assignments={"train": ()},
    )
    text = render_c31_cmapss_report(result)

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert "Local raw mapping review: completed for configured raw files." not in text
    assert "Local raw mapping review: blocked by schema, RUL, or leakage checks." in text


def test_c31_full_schema_validation_blocks_incomplete_explicit_split(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_full")
    for subset in ("FD001", "FD002", "FD003", "FD004"):
        _write_synthetic_subset(raw_dir, subset=subset)

    def update(data: dict) -> None:
        data["source"]["source_status"] = "verified"
        data["license_review"].update(
            {
                "decision": "approved_for_research_training",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "research_only",
            }
        )
        data["download_policy"].update(
            {"allow_local_raw_data": True, "raw_dir": str(raw_dir)}
        )

    config = load_c31_cmapss_config(_modified_config(tmp_path, update))

    result = run_c31_cmapss_minimal_ingestion(
        config,
        split_assignments={"train": ()},
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert result.status != C31TopLevelStatus.SCHEMA_VALIDATED_READY_FOR_C32
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.missing_split_trajectory_count == 12


def test_c31_full_schema_validation_blocks_generator_input_feature_leakage(
    tmp_path,
    monkeypatch,
):
    config = load_c31_cmapss_config(
        _research_approved_full_config(tmp_path, monkeypatch)
    )

    def input_features():
        yield "sensor_01"
        yield "rul"

    result = run_c31_cmapss_minimal_ingestion(
        config,
        input_feature_columns=input_features(),
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert result.status != C31TopLevelStatus.SCHEMA_VALIDATED_READY_FOR_C32
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.target_columns_in_input == ("rul",)


def test_c31_full_schema_validation_blocks_generator_malformed_window(
    tmp_path,
    monkeypatch,
):
    config = load_c31_cmapss_config(
        _research_approved_full_config(tmp_path, monkeypatch)
    )

    def windows():
        yield {
            "trajectory_id": "cmapss_FD001_train_unit_1",
            "start_cycle": 3,
            "end_cycle": 2,
            "split": "train",
        }

    result = run_c31_cmapss_minimal_ingestion(
        config,
        window_assignments=windows(),
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert result.status != C31TopLevelStatus.SCHEMA_VALIDATED_READY_FOR_C32
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.malformed_window_count == 1


def test_c31_full_schema_validation_accepts_generator_split_assignments(
    tmp_path,
    monkeypatch,
):
    config = load_c31_cmapss_config(
        _research_approved_full_config(tmp_path, monkeypatch)
    )

    def train_trajectories():
        for subset in ("FD001", "FD002", "FD003", "FD004"):
            yield f"cmapss_{subset}_train_unit_1"
            yield f"cmapss_{subset}_train_unit_2"

    def test_trajectories():
        for subset in ("FD001", "FD002", "FD003", "FD004"):
            yield f"cmapss_{subset}_test_unit_1"

    result = run_c31_cmapss_minimal_ingestion(
        config,
        split_assignments={
            "train": train_trajectories(),
            "test": test_trajectories(),
        },
    )

    assert result.status == C31TopLevelStatus.SCHEMA_VALIDATED_READY_FOR_C32
    assert "blocked_by_leakage_guard" not in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.missing_split_trajectory_count == 0
    assert result.leakage_summary.unknown_split_trajectory_count == 0


def test_c31_split_guard_blocks_overlapping_trajectory_ids(tmp_path, monkeypatch):
    config = load_c31_cmapss_config(
        _approved_local_mapping_config(tmp_path, monkeypatch)
    )

    result = run_c31_cmapss_minimal_ingestion(
        config,
        split_assignments={
            "train": {"cmapss_FD001_train_unit_1"},
            "validation": {"cmapss_FD001_train_unit_1"},
            "test": {"cmapss_FD001_test_unit_1"},
        },
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.mapping_summary is not None
    assert result.rul_targets != ()
    assert result.leakage_summary.trajectory_overlap_count == 1


def test_c31_input_feature_guard_blocks_rul_target_leakage(tmp_path, monkeypatch):
    config = load_c31_cmapss_config(
        _approved_local_mapping_config(tmp_path, monkeypatch)
    )

    result = run_c31_cmapss_minimal_ingestion(
        config,
        input_feature_columns=("sensor_01", "rul"),
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.target_columns_in_input == ("rul",)


def test_c31_window_adjacency_guard_blocks_cross_split_adjacent_cycles(
    tmp_path,
    monkeypatch,
):
    config = load_c31_cmapss_config(
        _approved_local_mapping_config(tmp_path, monkeypatch)
    )

    result = run_c31_cmapss_minimal_ingestion(
        config,
        split_assignments={
            "train": {"cmapss_FD001_train_unit_1"},
            "validation": {"cmapss_FD001_train_unit_2"},
            "test": {"cmapss_FD001_test_unit_1"},
        },
        window_assignments=[
            {
                "trajectory_id": "cmapss_FD001_train_unit_1",
                "start_cycle": 1,
                "end_cycle": 2,
                "split": "train",
            },
            {
                "trajectory_id": "cmapss_FD001_train_unit_1",
                "start_cycle": 2,
                "end_cycle": 3,
                "split": "validation",
            },
        ],
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.window_adjacency_leakage_count == 1


def test_c31_window_adjacency_guard_blocks_strictly_adjacent_cycles(
    tmp_path,
    monkeypatch,
):
    config = load_c31_cmapss_config(
        _approved_local_mapping_config(tmp_path, monkeypatch)
    )

    result = run_c31_cmapss_minimal_ingestion(
        config,
        window_assignments=[
            {
                "trajectory_id": "cmapss_FD001_train_unit_1",
                "start_cycle": 1,
                "end_cycle": 2,
                "split": "train",
            },
            {
                "trajectory_id": "cmapss_FD001_train_unit_1",
                "start_cycle": 3,
                "end_cycle": 4,
                "split": "validation",
            },
        ],
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.window_adjacency_leakage_count == 1


def test_c31_window_guard_blocks_missing_required_window_fields(tmp_path, monkeypatch):
    config = load_c31_cmapss_config(
        _approved_local_mapping_config(tmp_path, monkeypatch)
    )

    result = run_c31_cmapss_minimal_ingestion(
        config,
        window_assignments=[
            {
                "trajectory_id": "cmapss_FD001_train_unit_1",
                "start_cycle": 1,
                "end_cycle": 2,
            }
        ],
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.malformed_window_count == 1


def test_c31_window_guard_blocks_reversed_cycle_range(tmp_path, monkeypatch):
    config = load_c31_cmapss_config(
        _approved_local_mapping_config(tmp_path, monkeypatch)
    )

    result = run_c31_cmapss_minimal_ingestion(
        config,
        window_assignments=[
            {
                "trajectory_id": "cmapss_FD001_train_unit_1",
                "start_cycle": 3,
                "end_cycle": 2,
                "split": "train",
            }
        ],
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.malformed_window_count == 1


def test_c31_window_guard_blocks_bool_cycle_values(tmp_path, monkeypatch):
    config = load_c31_cmapss_config(
        _approved_local_mapping_config(tmp_path, monkeypatch)
    )

    result = run_c31_cmapss_minimal_ingestion(
        config,
        window_assignments=[
            {
                "trajectory_id": "cmapss_FD001_train_unit_1",
                "start_cycle": True,
                "end_cycle": 2,
                "split": "train",
            }
        ],
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.leakage_summary.malformed_window_count == 1


def test_c31_rul_targets_use_uncapped_train_and_test_formulas(tmp_path, monkeypatch):
    config = load_c31_cmapss_config(
        _approved_local_mapping_config(tmp_path, monkeypatch)
    )

    result = run_c31_cmapss_minimal_ingestion(config)
    by_key = {
        (target.trajectory_id, target.cycle_index): target.rul
        for target in result.rul_targets
    }

    assert by_key[("cmapss_FD001_train_unit_1", 1)] == 1
    assert by_key[("cmapss_FD001_train_unit_1", 2)] == 0
    assert by_key[("cmapss_FD001_test_unit_1", 1)] == 6
    assert by_key[("cmapss_FD001_test_unit_1", 2)] == 5
    assert result.mapping_summary.uses_capped_rul is False


def test_c31_rul_targets_align_test_units_by_file_order(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    test_path = raw_dir / "test_FD001.txt"
    lines = test_path.read_text(encoding="utf-8").splitlines()
    unit_2_line = lines[0].replace("1 1", "2 1", 1)
    test_path.write_text(
        "\n".join([*lines, unit_2_line]) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "RUL_FD001.txt").write_text("10\n20\n", encoding="utf-8")
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)
    by_key = {
        (target.trajectory_id, target.cycle_index): target.rul
        for target in result.rul_targets
    }

    assert by_key[("cmapss_FD001_test_unit_1", 1)] == 11
    assert by_key[("cmapss_FD001_test_unit_1", 2)] == 10
    assert by_key[("cmapss_FD001_test_unit_2", 1)] == 20


def test_c31_blocks_when_approved_local_raw_files_are_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")

    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_missing_raw_files" in [
        reason.value for reason in result.blocked_reasons
    ]
    assert result.raw_files_missing == (
        "train_FD001.txt",
        "test_FD001.txt",
        "RUL_FD001.txt",
    )
    assert result.mapping_summary is None
    assert result.rul_targets == ()


def test_c31_blocks_malformed_raw_shape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir, malformed=True)
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


@pytest.mark.parametrize("filename", ["train_FD001.txt", "test_FD001.txt"])
def test_c31_blocks_duplicate_unit_cycle_rows(tmp_path, monkeypatch, filename):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    data_path = raw_dir / filename
    lines = data_path.read_text(encoding="utf-8").splitlines()
    data_path.write_text("\n".join([*lines, lines[0]]) + "\n", encoding="utf-8")
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


def test_c31_blocks_test_units_when_first_seen_order_is_not_ascending(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    test_path = raw_dir / "test_FD001.txt"
    lines = test_path.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace("1 1", "2 1", 1)
    test_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (raw_dir / "RUL_FD001.txt").write_text("20\n10\n", encoding="utf-8")
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


def test_c31_blocks_test_units_when_unit_block_is_not_contiguous(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    test_path = raw_dir / "test_FD001.txt"
    lines = test_path.read_text(encoding="utf-8").splitlines()
    unit_2_line = lines[0].replace("1 1", "2 1", 1)
    test_path.write_text(
        "\n".join([lines[0], unit_2_line, lines[1]]) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "RUL_FD001.txt").write_text("10\n20\n", encoding="utf-8")
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


def test_c31_blocks_test_units_when_unit_ids_skip_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    test_path = raw_dir / "test_FD001.txt"
    lines = test_path.read_text(encoding="utf-8").splitlines()
    unit_3_line = lines[0].replace("1 1", "3 1", 1)
    test_path.write_text(
        "\n".join([*lines, unit_3_line]) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "RUL_FD001.txt").write_text("10\n30\n", encoding="utf-8")
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


@pytest.mark.parametrize("filename", ["train_FD001.txt", "test_FD001.txt"])
def test_c31_blocks_invalid_utf8_raw_data_files(tmp_path, monkeypatch, filename):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    (raw_dir / filename).write_bytes(b"\xff\xfe\xfa")
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


def test_c31_blocks_invalid_utf8_rul_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    (raw_dir / "RUL_FD001.txt").write_bytes(b"\xff\xfe\xfa")
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


def test_c31_blocks_rul_row_count_mismatch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    (raw_dir / "RUL_FD001.txt").write_text("5\n6\n", encoding="utf-8")
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


def test_c31_blocks_extreme_cycle_timestamp_overflow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    train_path = raw_dir / "train_FD001.txt"
    train_path.write_text(
        train_path.read_text(encoding="utf-8").replace(
            "1 1 0.1",
            "1 999999999999999999999999999999 0.1",
            1,
        ),
        encoding="utf-8",
    )
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


@pytest.mark.parametrize(
    "raw_prefix",
    [
        "0 1",
        "1 0",
        "-1 1",
        "1 -1",
    ],
)
def test_c31_blocks_non_positive_unit_or_cycle(tmp_path, monkeypatch, raw_prefix):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    train_path = raw_dir / "train_FD001.txt"
    train_path.write_text(
        train_path.read_text(encoding="utf-8").replace("1 1", raw_prefix, 1),
        encoding="utf-8",
    )
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


def test_c31_blocks_negative_rul(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    (raw_dir / "RUL_FD001.txt").write_text("-1\n", encoding="utf-8")
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)


@pytest.mark.parametrize(
    "old_value,new_value",
    [
        ("0.1", "nan"),
        ("101", "inf"),
    ],
)
def test_c31_blocks_non_finite_raw_values(
    tmp_path,
    monkeypatch,
    old_value,
    new_value,
):
    monkeypatch.chdir(tmp_path)
    raw_dir = Path("data/public/cmapss/raw/synthetic_fd001")
    _write_synthetic_subset(raw_dir)
    train_path = raw_dir / "train_FD001.txt"
    train_path.write_text(
        train_path.read_text(encoding="utf-8").replace(old_value, new_value, 1),
        encoding="utf-8",
    )
    path = _modified_config(
        tmp_path,
        lambda data: _configure_approved_fd001_mapping(data, raw_dir),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config)

    _assert_blocked_by_raw_schema_mismatch(result)
