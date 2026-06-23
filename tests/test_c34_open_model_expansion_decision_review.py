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


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def _load_default_config_data() -> dict:
    return yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))


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


def test_c34_rejects_wrong_required_ttm_status(tmp_path: Path):
    data = _load_default_config_data()
    data["decision_policy"]["require_ttm_status"] = "contract_ready"
    config_path = _write_yaml(tmp_path / "c34.yaml", data)

    with pytest.raises(C34ConfigError):
        load_c34_config(config_path)
