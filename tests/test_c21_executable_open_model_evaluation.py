from pathlib import Path

import pytest

from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus
from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21ConfigError,
    C21ModelTaskResult,
    C21RunResult,
    C21TaskId,
    REQUIRED_C21_TASKS,
    build_c21_attempts,
    load_c21_executable_config,
    render_c21_cache_manifest,
    render_c21_report,
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


def test_c21_report_contains_required_decision_sections():
    result = C21RunResult(
        run_id="c21-test",
        config_path="configs/c_stage_c21_executable_open_model_evaluation.yaml",
        upstream_c2_config="configs/c_stage_c2_open_model_evaluation.yaml",
        dataset_boundary="internal_fu13_no_raw_data_committed",
        config_allows_network=False,
        config_allows_download=False,
        cache_dir="hf_cache",
        tested_windows=2,
        task_results=[
            C21ModelTaskResult(
                model_id="chronos",
                display_name="Chronos / Chronos-Bolt",
                task_id=C21TaskId.FORECASTING,
                status=OpenModelAdapterStatus.MISSING_DEPENDENCY,
                metrics={},
                baseline_metrics={"mae": 1.0},
                failure_stage="inspect",
                failure_reason="dependency modules are unavailable",
                error_type="MissingDependency",
                error_detail="chronos",
                dependency_status="missing:chronos",
                weight_status="not_checked",
                input_shape={"windows": 2},
                output_shape={},
                runtime_seconds=0.0,
                adapter_name="ChronosAdapter",
                model_ref="needs_review",
                cache_dir="hf_cache",
                actual_network_used="false",
            )
        ],
        invalid_claims=["不得解释为生产告警"],
    )
    text = render_c21_report(result)
    assert "C2.1 Executable Open Model Evaluation Report" in text
    assert "Adapter Readiness Table" in text
    assert "Model-Task Result Matrix" in text
    assert "Failure Taxonomy" in text
    assert "C2 -> C3 Handoff" in text
    assert "C2 -> B Decision Notes" in text
    assert "不得解释为生产告警" in text


def test_c21_report_mentions_all_six_core_models():
    result = _sample_c21_run_result_with_all_required_attempts()
    text = render_c21_report(result)
    for model_id in ["ttm", "chronos", "timesfm", "moirai_uni2ts", "moment", "units"]:
        assert model_id in text


def test_c21_adapter_readiness_table_mentions_all_six_core_models():
    result = _sample_c21_run_result_with_all_required_attempts()
    text = render_c21_report(result)
    readiness_section = text.split("## Adapter Readiness Table", 1)[1].split(
        "## Model-Task Result Matrix",
        1,
    )[0]
    for model_id in ["ttm", "chronos", "timesfm", "moirai_uni2ts", "moment", "units"]:
        assert model_id in readiness_section


def test_c21_report_contains_all_required_model_task_rows():
    result = _sample_c21_run_result_with_all_required_attempts()
    text = render_c21_report(result)
    for model_id, task_id in [
        ("ttm", "forecasting"),
        ("chronos", "forecasting"),
        ("timesfm", "forecasting"),
        ("moirai_uni2ts", "forecasting"),
        ("moment", "representation"),
        ("moment", "imputation"),
        ("units", "representation"),
        ("units", "imputation"),
    ]:
        matching_lines = [
            line
            for line in text.splitlines()
            if f"| {model_id} |" in line and f"| {task_id} |" in line
        ]
        assert matching_lines, f"missing report row for {model_id}/{task_id}"


def test_c21_cache_manifest_records_network_and_weight_boundary():
    result = C21RunResult(
        run_id="c21-test",
        config_path="cfg",
        upstream_c2_config="c2",
        dataset_boundary="boundary",
        config_allows_network=False,
        config_allows_download=False,
        cache_dir="hf_cache",
        tested_windows=1,
        task_results=[],
        invalid_claims=[],
    )
    text = render_c21_cache_manifest(result)
    assert "download_allowed" in text
    assert "actual_network_used" in text


def _sample_c21_run_result_with_all_required_attempts() -> C21RunResult:
    task_results = [
        C21ModelTaskResult(
            model_id=model_id,
            display_name=model_id,
            task_id=task_id,
            status=OpenModelAdapterStatus.MISSING_DEPENDENCY,
            metrics={},
            baseline_metrics={"baseline": "not_run"},
            failure_stage="inspect",
            failure_reason="dependency modules are unavailable",
            error_type="MissingDependency",
            error_detail=model_id,
            dependency_status=f"missing:{model_id}",
            weight_status="not_checked",
            input_shape={"windows": 2},
            output_shape={},
            runtime_seconds=0.0,
            adapter_name=f"{model_id}Adapter",
            model_ref="needs_review",
            cache_dir="hf_cache",
            actual_network_used=False,
        )
        for model_id, task_ids in REQUIRED_C21_TASKS.items()
        for task_id in task_ids
    ]
    assert len(task_results) == 8
    return C21RunResult(
        run_id="c21-test",
        config_path="configs/c_stage_c21_executable_open_model_evaluation.yaml",
        upstream_c2_config="configs/c_stage_c2_open_model_evaluation.yaml",
        dataset_boundary="internal_fu13_no_raw_data_committed",
        config_allows_network=False,
        config_allows_download=False,
        cache_dir="hf_cache",
        tested_windows=2,
        task_results=task_results,
        invalid_claims=["do not treat as production alert decision"],
    )
