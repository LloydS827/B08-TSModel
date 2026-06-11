from pathlib import Path

import pytest
import yaml

from b08_model_core.experiments.c32_open_model_cross_dataset_evaluation import (
    C32ConfigError,
    load_c32_config,
)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG = (
    _REPO_ROOT / "configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml"
)


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def _modified_default(tmp_path: Path, update) -> Path:
    data = yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
    update(data)
    return _write_yaml(tmp_path / "c32_broken.yaml", data)


def test_c32_default_config_is_contract_first_and_offline_safe():
    config = load_c32_config(_DEFAULT_CONFIG)

    assert config.stage == "C3_2_open_model_cross_dataset_evaluation"
    assert config.outputs.report == Path(
        "reports/c_stage_c32_open_model_cross_dataset_evaluation.md"
    )
    assert config.safety_policy.allow_network is False
    assert config.safety_policy.allow_download is False
    assert config.safety_policy.allow_local_raw_data is False
    assert config.safety_policy.allow_model_cache is False
    assert config.safety_policy.allow_training is False
    assert config.safety_policy.allow_write_processed is False
    assert config.prerequisites.c31_review_doc == Path(
        "docs/reviews/2026-06-11-c31-cmapss-local-raw-mapping-review.md"
    )
    assert config.prerequisites.required_status == "schema_validated_ready_for_c32"
    assert (
        config.prerequisites.required_readiness_detail
        == "full_classic_cmapss_validated"
    )
    assert config.prerequisites.reviewed_raw_file_count == 12
    assert config.prerequisites.leakage_guard_passed is True
    assert config.metric_contract.leaderboard_allowed is False
    assert config.model_cache_policy.cache_dir == Path("hf_cache")


def test_c32_rejects_wrong_stage(tmp_path):
    broken = _modified_default(tmp_path, lambda data: data.update({"stage": "wrong"}))

    with pytest.raises(C32ConfigError, match="stage"):
        load_c32_config(broken)


def test_c32_rejects_unsafe_default_policy(tmp_path):
    def make_unsafe(data):
        data["safety_policy"]["allow_download"] = True

    broken = _modified_default(tmp_path, make_unsafe)

    with pytest.raises(C32ConfigError, match="allow_download"):
        load_c32_config(broken)


def test_c32_rejects_duplicate_dataset_ids(tmp_path):
    def duplicate_dataset(data):
        data["dataset_views"][1]["dataset_id"] = data["dataset_views"][0][
            "dataset_id"
        ]

    broken = _modified_default(tmp_path, duplicate_dataset)

    with pytest.raises(C32ConfigError, match="duplicate dataset_id"):
        load_c32_config(broken)


def test_c32_rejects_unknown_task_dataset_reference(tmp_path):
    def unknown_dataset(data):
        data["task_contracts"][0]["compatible_dataset_views"] = ["missing_dataset"]

    broken = _modified_default(tmp_path, unknown_dataset)

    with pytest.raises(C32ConfigError, match="unknown dataset"):
        load_c32_config(broken)


def test_c32_rejects_duplicate_task_ids(tmp_path):
    def duplicate_task(data):
        data["task_contracts"][1]["task_id"] = data["task_contracts"][0]["task_id"]

    broken = _modified_default(tmp_path, duplicate_task)

    with pytest.raises(C32ConfigError, match="duplicate task_id"):
        load_c32_config(broken)


def test_c32_rejects_unknown_model_task_reference(tmp_path):
    def unknown_task(data):
        data["model_candidates"][0]["task_ids"] = ["missing_task"]

    broken = _modified_default(tmp_path, unknown_task)

    with pytest.raises(C32ConfigError, match="unknown task"):
        load_c32_config(broken)
