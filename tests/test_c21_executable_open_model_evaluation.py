from pathlib import Path

from b08_model_core.experiments.c21_executable_open_model_evaluation import (
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
