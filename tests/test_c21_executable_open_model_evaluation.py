from pathlib import Path

import pytest

from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21ConfigError,
    C21TaskId,
    REQUIRED_C21_TASKS,
    build_c21_attempts,
    load_c21_executable_config,
)


def test_c21_default_config_is_offline_safe():
    config = load_c21_executable_config(
        "configs/c_stage_c21_executable_open_model_evaluation.yaml"
    )
    assert config.stage == "C2_1_executable_open_model_evaluation"
    assert config.upstream_c2_config == Path("configs/c_stage_c2_open_model_evaluation.yaml")
    assert config.allow_network is False
    assert config.allow_download is False
    assert config.strict_model_success is False


def test_c21_required_task_matrix_includes_all_declared_attempts():
    assert REQUIRED_C21_TASKS == {
        "ttm": (C21TaskId.FORECASTING,),
        "chronos": (C21TaskId.FORECASTING,),
        "timesfm": (C21TaskId.FORECASTING,),
        "moirai_uni2ts": (C21TaskId.FORECASTING,),
        "moment": (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION),
        "units": (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION),
    }


def test_c21_attempts_include_moment_and_units_two_primary_tasks():
    config = load_c21_executable_config(
        "configs/c_stage_c21_executable_open_model_evaluation.yaml"
    )
    attempts = build_c21_attempts(config)
    pairs = {(attempt.model_id, attempt.task_id) for attempt in attempts}
    assert ("moment", C21TaskId.REPRESENTATION) in pairs
    assert ("moment", C21TaskId.IMPUTATION) in pairs
    assert ("units", C21TaskId.REPRESENTATION) in pairs
    assert ("units", C21TaskId.IMPUTATION) in pairs
    assert len(pairs) == 8


@pytest.mark.parametrize("timeout_value", [".nan", ".inf"])
def test_c21_config_rejects_non_finite_timeout(tmp_path, timeout_value):
    config_path = tmp_path / "c21_non_finite_timeout.yaml"
    config_path.write_text(
        f"""
stage: C2_1_executable_open_model_evaluation
upstream_c2_config: configs/c_stage_c2_open_model_evaluation.yaml
dataset:
  fu13_observations: data/processed/fu13_real_observations.parquet
  fu13_config: configs/fu13_real_data_schema.yaml
  boundary: internal_fu13_no_raw_data_committed
window:
  window_mode: cross-stage
  context_length: 90
  prediction_length: 16
  max_windows: 40
  mask_ratio: 0.2
  seed: 7
execution_policy:
  allow_network: false
  allow_download: false
  strict_model_success: false
  record_failure: true
  do_not_over_claim: true
  continue_on_model_failure: true
  timeout_seconds_per_model: {timeout_value}
model_cache_policy:
  cache_dir: hf_cache
  reuse_existing_cache: true
  write_cache_manifest: true
outputs:
  report: reports/c_stage_c21_executable_open_model_evaluation.md
  cache_manifest: reports/c_stage_c21_model_cache_manifest.md
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(C21ConfigError, match="timeout_seconds_per_model must be finite"):
        load_c21_executable_config(config_path)
