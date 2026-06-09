from pathlib import Path

import pytest
import yaml

from b08_model_core.experiments.c31_cmapss_minimal_ingestion import (
    C31CmapssConfigError,
    C31LicenseDecision,
    C31TopLevelStatus,
    expected_cmapss_files,
    load_c31_cmapss_config,
    run_c31_cmapss_minimal_ingestion,
)

_DEFAULT_CONFIG = Path("configs/c_stage_c31_cmapss_minimal_ingestion.yaml")


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
    assert config.license_review.decision == C31LicenseDecision.NEEDS_REVIEW
    assert len(config.download_policy.expected_files) == 12
    assert config.download_policy.expected_files == expected_cmapss_files()
    assert config.outputs.report == Path("reports/c_stage_c31_cmapss_minimal_ingestion.md")


def test_c31_default_runner_blocks_without_reading_raw_data():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)

    result = run_c31_cmapss_minimal_ingestion(config, config_path=_DEFAULT_CONFIG)

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_license_review" in [reason.value for reason in result.blocked_reasons]
    assert result.raw_files_present == ()
    assert result.raw_files_missing == tuple(config.download_policy.expected_files)


def test_c31_default_runner_does_not_inspect_raw_dir_when_local_raw_disabled(
    tmp_path,
    monkeypatch,
):
    sentinel_raw_dir = tmp_path / "sentinel_raw"
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


def test_c31_blocks_unapproved_source_even_when_license_is_schema_approved(tmp_path):
    path = _modified_config(
        tmp_path,
        lambda data: data["license_review"].update(
            {
                "decision": "approved_for_schema_validation",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "needs_review",
            }
        ),
    )
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

    with pytest.raises(C31CmapssConfigError, match="full classic"):
        load_c31_cmapss_config(path)
