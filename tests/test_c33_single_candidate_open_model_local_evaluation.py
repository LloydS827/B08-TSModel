from pathlib import Path

import pytest
import yaml

from b08_model_core.experiments.c33_single_candidate_open_model_local_evaluation import (
    C33ConfigError,
    load_c33_config,
    render_c33_report,
    run_c33_single_candidate_open_model_local_evaluation,
)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG = (
    _REPO_ROOT
    / "configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml"
)
_LOCAL_CONFIG = (
    _REPO_ROOT
    / "configs/local/c_stage_c33_ttm_fu13_like_local_evaluation.example.yaml"
)


def test_c33_default_config_is_contract_only_and_offline_safe():
    config = load_c33_config(_DEFAULT_CONFIG)

    assert config.stage == "C3_3_single_candidate_open_model_local_evaluation"
    assert config.safety_policy.allow_network is False
    assert config.safety_policy.allow_download is False
    assert config.safety_policy.allow_model_cache is False
    assert config.safety_policy.allow_local_execution is False
    assert config.safety_policy.allow_training is False
    assert config.safety_policy.allow_write_processed is False
    assert config.candidate.model_id == "ttm"
    assert config.candidate.task_id == "forecasting_residual"
    assert config.candidate.dataset_view == "fu13_like_simulated_forecasting"
    assert config.metric_contract.leaderboard_allowed is False
    assert config.local_execution is None


def test_c33_local_config_is_explicit_opt_in_cache_first():
    config = load_c33_config(_LOCAL_CONFIG)

    assert config.safety_policy.allow_local_execution is True
    assert config.safety_policy.allow_model_cache is True
    assert config.safety_policy.allow_network is False
    assert config.safety_policy.allow_download is False
    assert config.safety_policy.allow_training is False
    assert config.safety_policy.allow_write_processed is False
    assert config.local_execution is not None
    assert config.local_execution.enabled is True
    assert config.local_execution.model_cache_dir == _REPO_ROOT / "hf_cache"
    assert config.local_execution.fu13_like.context_length == 32
    assert config.local_execution.fu13_like.prediction_length == 8
    assert config.local_execution.fu13_like.max_windows == 60


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def test_c33_rejects_wrong_stage(tmp_path):
    data = yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
    data["stage"] = "wrong"
    with pytest.raises(C33ConfigError, match="stage"):
        load_c33_config(_write_yaml(tmp_path / "broken.yaml", data))


def test_c33_rejects_non_ttm_candidate(tmp_path):
    data = yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
    data["candidate"]["model_id"] = "chronos"
    with pytest.raises(C33ConfigError, match="candidate.model_id"):
        load_c33_config(_write_yaml(tmp_path / "broken.yaml", data))


def test_c33_rejects_download_without_network(tmp_path):
    data = yaml.safe_load(_LOCAL_CONFIG.read_text(encoding="utf-8"))
    data["safety_policy"]["allow_download"] = True
    data["safety_policy"]["allow_network"] = False
    with pytest.raises(C33ConfigError, match="allow_network"):
        load_c33_config(_write_yaml(tmp_path / "broken.yaml", data))


def test_c33_rejects_local_execution_without_model_cache(tmp_path):
    data = yaml.safe_load(_LOCAL_CONFIG.read_text(encoding="utf-8"))
    data["safety_policy"]["allow_model_cache"] = False
    with pytest.raises(C33ConfigError, match="allow_model_cache"):
        load_c33_config(_write_yaml(tmp_path / "broken.yaml", data))


def test_c33_contract_runner_renders_default_report():
    config = load_c33_config(_DEFAULT_CONFIG)
    result = run_c33_single_candidate_open_model_local_evaluation(
        config, config_path=_DEFAULT_CONFIG
    )
    text = render_c33_report(result)

    assert result.status == "contract_ready_single_candidate_local_execution_blocked"
    assert "C3.2 Anchor" in text
    assert "Candidate Contract" in text
    assert "ttm" in text
    assert "Leaderboard allowed: False" in text
    assert "No-Go" in text


def test_c33_contract_runner_does_not_call_adapter_factory():
    config = load_c33_config(_DEFAULT_CONFIG)

    def forbidden_factory():
        raise AssertionError("default C3.3 contract path touched adapter factory")

    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_DEFAULT_CONFIG,
        adapter_factory=forbidden_factory,
    )

    assert result.status == "contract_ready_single_candidate_local_execution_blocked"
