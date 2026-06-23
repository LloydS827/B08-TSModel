from pathlib import Path

import pytest
import yaml

from b08_model_core.experiments.c34_open_model_expansion_decision_review import (
    C34ConfigError,
    load_c34_config,
    render_c34_report,
    run_c34_open_model_expansion_decision_review,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    REPO_ROOT / "configs/c_stage_c34_open_model_expansion_decision_review.yaml"
)
LOCAL_CONFIG = (
    REPO_ROOT / "configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml"
)


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def _load_default_config_data() -> dict:
    return yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))


def _ready_c33_evidence() -> dict:
    return {
        "source": "explicit_local_reviewed",
        "status": "local_execution_ttm_forecasting_ready",
        "candidate": "ttm",
        "task": "fu13_like_forecasting",
        "adapter_evidence": {
            "dependency_status": "available",
            "weight_status": "available",
            "adapter_status": "available_and_ran",
            "runtime_seconds": 0.01,
            "input_shape": {"windows": 18, "X": [32, 8]},
            "output_shape": {"predictions": [18, 8, 8]},
            "actual_network_used": False,
            "download_allowed_not_verified": False,
        },
    }


def test_c34_default_config_is_offline_decision_review_only():
    config = load_c34_config(DEFAULT_CONFIG)

    assert config.stage == "C3_4_open_model_expansion_decision_review"
    assert config.safety_policy.allow_network is False
    assert config.safety_policy.allow_download is False
    assert config.safety_policy.allow_model_cache is False
    assert config.safety_policy.allow_local_execution is False
    assert config.safety_policy.allow_training is False
    assert config.safety_policy.allow_write_processed is False
    assert config.c33_evidence.source == "default_contract"
    assert (
        config.c33_evidence.status
        == "contract_ready_single_candidate_local_execution_blocked"
    )
    assert config.c33_evidence.adapter_evidence == "not_applicable_default_contract"
    assert config.decision_policy.leaderboard_allowed is False
    assert config.decision_policy.rul_open_model_allowed is False
    assert config.decision_policy.second_candidate_execution_allowed is False


def test_c34_default_runner_holds_candidate_expansion():
    config = load_c34_config(DEFAULT_CONFIG)
    result = run_c34_open_model_expansion_decision_review(config, DEFAULT_CONFIG)
    text = render_c34_report(result)

    assert result.status == "hold_candidate_expansion_pending_ttm_local_evidence"
    assert "C3.3 Evidence Gate" in text
    assert "Candidate Expansion Review" in text
    assert "review_only_not_promoted" in text
    assert "No leaderboard" in text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", "generated_report"),
        ("candidate", "chronos"),
        ("task", "rul_forecasting"),
    ],
)
def test_c34_rejects_wrong_default_c33_evidence_contract(
    tmp_path: Path,
    field: str,
    value: str,
):
    data = _load_default_config_data()
    data["c33_evidence"][field] = value
    config_path = _write_yaml(tmp_path / "c34.yaml", data)

    with pytest.raises(C34ConfigError):
        load_c34_config(config_path)


def test_c34_rejects_unexpected_default_c33_evidence_status(tmp_path: Path):
    data = _load_default_config_data()
    data["c33_evidence"]["status"] = "unexpected_status"
    config_path = _write_yaml(tmp_path / "c34.yaml", data)

    with pytest.raises(C34ConfigError):
        load_c34_config(config_path)


def test_c34_rejects_wrong_required_ttm_status(tmp_path: Path):
    data = _load_default_config_data()
    data["decision_policy"]["require_ttm_status"] = "contract_ready"
    config_path = _write_yaml(tmp_path / "c34.yaml", data)

    with pytest.raises(C34ConfigError):
        load_c34_config(config_path)


def test_c34_ready_c33_evidence_allows_candidate_expansion_design(tmp_path):
    data = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    data["c33_evidence"] = _ready_c33_evidence()
    config = load_c34_config(_write_yaml(tmp_path / "ready.yaml", data))
    result = run_c34_open_model_expansion_decision_review(config, tmp_path / "ready.yaml")
    text = render_c34_report(result)

    assert result.status == "candidate_expansion_design_ready"
    assert (
        "Candidate expansion stays blocked until local TTM forecasting evidence "
        "reaches the required status"
    ) not in text
    assert "C3.5 second forecasting candidate design may proceed" in text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("adapter_status", "runtime_failed"),
        ("dependency_status", "missing:tsfm_public"),
        ("weight_status", "missing_or_blocked"),
    ],
)
def test_c34_ready_c33_evidence_rejects_contradictory_adapter_statuses(
    tmp_path: Path,
    field: str,
    value: str,
):
    data = _load_default_config_data()
    data["c33_evidence"] = _ready_c33_evidence()
    data["c33_evidence"]["adapter_evidence"][field] = value

    with pytest.raises(C34ConfigError):
        load_c34_config(_write_yaml(tmp_path / "contradictory_ready.yaml", data))


@pytest.mark.parametrize(
    ("shape_field", "shape_value"),
    [
        ("output_shape", {}),
        ("output_shape", {"predictions": []}),
        ("input_shape", {"windows": 18, "X": []}),
    ],
)
def test_c34_ready_c33_evidence_rejects_empty_shapes(
    tmp_path: Path,
    shape_field: str,
    shape_value: dict,
):
    data = _load_default_config_data()
    data["c33_evidence"] = _ready_c33_evidence()
    data["c33_evidence"]["adapter_evidence"][shape_field] = shape_value

    with pytest.raises(C34ConfigError):
        load_c34_config(_write_yaml(tmp_path / "empty_shape_ready.yaml", data))


@pytest.mark.parametrize(
    "c33_status",
    [
        "local_execution_ttm_missing_dependency",
        "local_execution_ttm_missing_or_blocked_weights",
        "local_execution_ttm_runtime_failed",
    ],
)
def test_c34_blocker_c33_evidence_blocks_candidate_expansion(tmp_path, c33_status):
    data = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    data["c33_evidence"] = {
        "source": "explicit_local_reviewed",
        "status": c33_status,
        "candidate": "ttm",
        "task": "fu13_like_forecasting",
        "adapter_evidence": {
            "failure_reason": "cache miss",
            "dependency_status": "available",
            "weight_status": "missing_or_blocked",
        },
    }
    config = load_c34_config(_write_yaml(tmp_path / "blocked.yaml", data))
    result = run_c34_open_model_expansion_decision_review(config, tmp_path / "blocked.yaml")

    assert result.status == "blocked_candidate_expansion_due_to_ttm_evidence_gap"


def test_c34_unsupported_window_shape_requires_shape_and_blocks(tmp_path: Path):
    data = _load_default_config_data()
    data["c33_evidence"] = {
        "source": "explicit_local_reviewed",
        "status": "local_execution_ttm_unsupported_window_shape",
        "candidate": "ttm",
        "task": "fu13_like_forecasting",
        "adapter_evidence": {
            "failure_reason": "window rank mismatch",
            "dependency_status": "available",
            "weight_status": "available",
            "input_shape": {"windows": 18, "X": [32, 8]},
        },
    }

    config = load_c34_config(_write_yaml(tmp_path / "unsupported_shape.yaml", data))
    result = run_c34_open_model_expansion_decision_review(
        config,
        tmp_path / "unsupported_shape.yaml",
    )

    assert result.status == "blocked_candidate_expansion_due_to_ttm_evidence_gap"

    data["c33_evidence"]["adapter_evidence"].pop("input_shape")
    with pytest.raises(C34ConfigError):
        load_c34_config(_write_yaml(tmp_path / "missing_shape.yaml", data))


def test_c34_insufficient_windows_holds_and_requires_reason(tmp_path: Path):
    data = _load_default_config_data()
    data["c33_evidence"] = {
        "source": "explicit_local_reviewed",
        "status": "blocked_insufficient_fu13_like_windows",
        "candidate": "ttm",
        "task": "fu13_like_forecasting",
        "adapter_evidence": {"blocked_reason": "need at least one evaluation window"},
    }

    config = load_c34_config(_write_yaml(tmp_path / "insufficient.yaml", data))
    result = run_c34_open_model_expansion_decision_review(
        config,
        tmp_path / "insufficient.yaml",
    )

    assert result.status == "hold_candidate_expansion_pending_ttm_local_evidence"

    data["c33_evidence"]["adapter_evidence"] = {}
    with pytest.raises(C34ConfigError):
        load_c34_config(_write_yaml(tmp_path / "missing_reason.yaml", data))


def test_c34_unknown_c33_status_is_config_error(tmp_path: Path):
    data = _load_default_config_data()
    data["c33_evidence"]["status"] = "local_execution_ttm_surprise"
    config_path = _write_yaml(tmp_path / "unknown.yaml", data)

    with pytest.raises(C34ConfigError):
        load_c34_config(config_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actual_network_used", None),
        ("download_allowed_not_verified", "false"),
    ],
)
def test_c34_ready_c33_evidence_rejects_invalid_adapter_fields(
    tmp_path: Path,
    field: str,
    value,
):
    data = _load_default_config_data()
    adapter_evidence = {
        "dependency_status": "available",
        "weight_status": "available",
        "adapter_status": "available_and_ran",
        "runtime_seconds": 0.01,
        "input_shape": {"windows": 18, "X": [32, 8]},
        "output_shape": {"predictions": [18, 8, 8]},
        "actual_network_used": False,
        "download_allowed_not_verified": False,
    }
    if value is None:
        adapter_evidence.pop(field)
    else:
        adapter_evidence[field] = value
    data["c33_evidence"] = {
        "source": "explicit_local_reviewed",
        "status": "local_execution_ttm_forecasting_ready",
        "candidate": "ttm",
        "task": "fu13_like_forecasting",
        "adapter_evidence": adapter_evidence,
    }

    with pytest.raises(C34ConfigError):
        load_c34_config(_write_yaml(tmp_path / "invalid_ready.yaml", data))


def test_c34_ready_c33_evidence_rejects_extra_adapter_field(tmp_path: Path):
    data = _load_default_config_data()
    data["c33_evidence"] = {
        "source": "explicit_local_reviewed",
        "status": "local_execution_ttm_forecasting_ready",
        "candidate": "ttm",
        "task": "fu13_like_forecasting",
        "adapter_evidence": {
            "dependency_status": "available",
            "weight_status": "available",
            "adapter_status": "available_and_ran",
            "runtime_seconds": 0.01,
            "input_shape": {"windows": 18, "X": [32, 8]},
            "output_shape": {"predictions": [18, 8, 8]},
            "actual_network_used": False,
            "download_allowed_not_verified": False,
            "report_path": "reports/generated.md",
        },
    }

    with pytest.raises(C34ConfigError):
        load_c34_config(_write_yaml(tmp_path / "extra_ready.yaml", data))


def test_c34_runner_has_no_adapter_or_report_execution_hook():
    config = load_c34_config(DEFAULT_CONFIG)
    result = run_c34_open_model_expansion_decision_review(config, DEFAULT_CONFIG)

    assert result.status == "hold_candidate_expansion_pending_ttm_local_evidence"
    assert not hasattr(result, "adapter_result")
    assert not hasattr(result, "model_cache_manifest")


def test_c34_local_evidence_example_is_review_only_blocker():
    config = load_c34_config(LOCAL_CONFIG)
    result = run_c34_open_model_expansion_decision_review(config, LOCAL_CONFIG)

    assert result.status == "blocked_candidate_expansion_due_to_ttm_evidence_gap"
    assert config.safety_policy.allow_model_cache is False
    assert config.safety_policy.allow_local_execution is False
