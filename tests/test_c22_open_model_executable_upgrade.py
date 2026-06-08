from pathlib import Path

import pytest

from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId
from b08_model_core.experiments.c22_open_model_executable_upgrade import (
    C22ConfigError,
    C22ModelRole,
    build_c22_core_attempts,
    load_c22_config,
)


def test_c22_default_config_is_offline_safe():
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    assert config.stage == "C2_2_open_model_executable_upgrade"
    assert config.upstream_c21_config == Path(
        "configs/c_stage_c21_executable_open_model_evaluation.yaml"
    )
    assert config.allow_network is False
    assert config.allow_download is False
    assert config.strict_model_success is False
    assert config.cache_dir == Path("hf_cache")


def test_c22_model_targets_capture_roles_and_versions():
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    assert config.model_targets["ttm"].role == C22ModelRole.ANCHOR
    assert config.model_targets["chronos"].role == C22ModelRole.PRIORITY_REAL_EXECUTION
    assert config.model_targets["chronos"].target == "chronos_2"
    assert config.model_targets["chronos"].fallback == "chronos_bolt"
    assert config.model_targets["timesfm"].target == "timesfm_2_5"
    assert config.model_targets["moirai_uni2ts"].target == "moirai_2_0_current_uni2ts"
    assert config.model_targets["moment"].tasks == (
        C21TaskId.REPRESENTATION,
        C21TaskId.IMPUTATION,
    )
    assert config.model_targets["units"].tasks == (
        C21TaskId.REPRESENTATION,
        C21TaskId.IMPUTATION,
    )


def test_c22_core_attempts_exclude_watchlist_targets():
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    attempts = build_c22_core_attempts(config)
    pairs = {(attempt.model_id, attempt.task_id) for attempt in attempts}
    assert ("chronos", C21TaskId.FORECASTING) in pairs
    assert ("timesfm", C21TaskId.FORECASTING) in pairs
    assert ("moment", C21TaskId.REPRESENTATION) in pairs
    assert ("units", C21TaskId.IMPUTATION) in pairs
    assert not any(model_id == "sundial" for model_id, _ in pairs)
    assert len(pairs) == 8


def test_c22_rejects_download_without_network(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        "allow_download: false",
        "allow_download: true",
    )
    with pytest.raises(C22ConfigError, match="allow_download requires allow_network=true"):
        load_c22_config(config_path)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("record_failure: true", "record_failure: false", "record_failure=false is not supported"),
        (
            "continue_on_model_failure: true",
            "continue_on_model_failure: false",
            "continue_on_model_failure=false is not supported",
        ),
        (
            "reuse_existing_cache: true",
            "reuse_existing_cache: false",
            "reuse_existing_cache=false is not supported",
        ),
    ],
)
def test_c22_rejects_c21_bridge_unsupported_policy_states(tmp_path, old, new, message):
    config_path = _write_modified_config(tmp_path, old, new)
    with pytest.raises(C22ConfigError, match=message):
        load_c22_config(config_path)


def test_c22_rejects_bad_stage(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        "stage: C2_2_open_model_executable_upgrade",
        "stage: C2_1_executable_open_model_evaluation",
    )
    with pytest.raises(
        C22ConfigError,
        match="C2.2 stage must be C2_2_open_model_executable_upgrade",
    ):
        load_c22_config(config_path)


def test_c22_rejects_non_positive_window_value(tmp_path):
    config_path = _write_modified_config(tmp_path, "context_length: 90", "context_length: 0")
    with pytest.raises(C22ConfigError, match="context_length must be a positive integer"):
        load_c22_config(config_path)


def test_c22_rejects_non_positive_timeout(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        "timeout_seconds_per_model: 900",
        "timeout_seconds_per_model: 0",
    )
    with pytest.raises(
        C22ConfigError,
        match="timeout_seconds_per_model must be a positive number",
    ):
        load_c22_config(config_path)


def test_c22_rejects_unknown_role(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        "role: priority_real_execution",
        "role: experimental",
        count=1,
    )
    with pytest.raises(
        C22ConfigError,
        match="model_targets.chronos.role is unknown: experimental",
    ):
        load_c22_config(config_path)


def test_c22_rejects_unknown_task(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        "tasks: [representation, imputation]",
        "tasks: [representation, classification]",
        count=1,
    )
    with pytest.raises(
        C22ConfigError,
        match="model_targets.moment.tasks contains unknown task: classification",
    ):
        load_c22_config(config_path)


def _write_modified_config(
    tmp_path: Path,
    old: str,
    new: str,
    *,
    count: int = -1,
) -> Path:
    config_path = tmp_path / "modified_c22.yaml"
    text = Path("configs/c_stage_c22_open_model_executable_upgrade.yaml").read_text(
        encoding="utf-8"
    )
    assert old in text
    config_path.write_text(text.replace(old, new, count), encoding="utf-8")
    return config_path
