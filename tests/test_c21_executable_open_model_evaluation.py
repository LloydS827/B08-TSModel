from pathlib import Path
import time

import pandas as pd
import pytest

from b08_model_core.adapters.open_models.base import (
    AdapterFailure,
    AdapterReadiness,
    AdapterTaskOutput,
    OpenModelAdapterStatus,
)
import b08_model_core.experiments.c21_executable_open_model_evaluation as c21_eval
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
    run_c21_executable_evaluation,
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


class AlwaysRunsForecastingAdapter:
    model_id = "ttm"
    display_name = "TTM / TinyTimeMixer"

    def inspect_environment(self, context):
        return None

    def load(self, context):
        return self

    def run_forecasting(self, windows, context):
        y = [window.y for window in windows]
        return AdapterTaskOutput(
            model_id=self.model_id,
            task_id=C21TaskId.FORECASTING,
            status=OpenModelAdapterStatus.AVAILABLE_AND_RAN,
            predictions=y,
            metrics={"runtime_seconds": 0.01},
            input_shape={"windows": len(windows)},
            output_shape={"predictions": len(y)},
        )


class MissingDependencyAdapter:
    model_id = "chronos"
    display_name = "Chronos / Chronos-Bolt"

    def inspect_environment(self, context):
        return AdapterFailure(
            model_id=self.model_id,
            task_id=C21TaskId.FORECASTING,
            status=OpenModelAdapterStatus.MISSING_DEPENDENCY,
            failure_stage="inspect",
            failure_reason="dependency modules are unavailable",
            error_type="MissingDependency",
            error_detail="chronos",
        )


class TimeoutAdapter:
    model_id = "timesfm"
    display_name = "TimesFM"

    def inspect_environment(self, context):
        return None

    def load(self, context):
        return self

    def run_forecasting(self, windows, context):
        time.sleep(0.05)
        return AdapterTaskOutput(
            model_id=self.model_id,
            task_id=C21TaskId.FORECASTING,
            status=OpenModelAdapterStatus.AVAILABLE_AND_RAN,
            predictions=[window.y for window in windows],
            metrics={"runtime_seconds": 0.05},
            input_shape={"windows": len(windows)},
            output_shape={"predictions": len(windows)},
        )


class LaterRunsForecastingAdapter(AlwaysRunsForecastingAdapter):
    model_id = "moirai_uni2ts"
    display_name = "Moirai / Uni2TS"


class LoadFailureAdapter(AlwaysRunsForecastingAdapter):
    model_id = "timesfm"
    display_name = "TimesFM"

    def load(self, context):
        return AdapterFailure(
            model_id=self.model_id,
            task_id=C21TaskId.FORECASTING,
            status=OpenModelAdapterStatus.MISSING_OR_BLOCKED_WEIGHTS,
            failure_stage="load",
            failure_reason="weights unavailable in offline cache",
            error_type="MissingWeights",
            error_detail="timesfm",
            weight_status="missing:timesfm",
        )


class NonReadyReadinessAdapter(AlwaysRunsForecastingAdapter):
    model_id = "chronos"
    display_name = "Chronos / Chronos-Bolt"

    def inspect_environment(self, context):
        return AdapterReadiness(
            model_id=self.model_id,
            dependency_status="missing:chronos",
            weight_status="not_checked",
            adapter_status=OpenModelAdapterStatus.MISSING_DEPENDENCY,
            adapter_name=self.__class__.__name__,
            model_ref="chronos-bolt",
            cache_dir=context.cache_dir,
            actual_network_used=False,
            known_limitations=("dependency modules are unavailable",),
        )


def test_runner_continues_when_one_model_fails(tmp_path):
    config = _write_c21_fixture_config(tmp_path, strict_model_success=False)
    _write_fixture_observations(tmp_path / "observations.parquet")
    result = run_c21_executable_evaluation(
        config,
        adapter_factory={
            "ttm": AlwaysRunsForecastingAdapter(),
            "chronos": MissingDependencyAdapter(),
        },
    )
    statuses = {(item.model_id, item.status) for item in result.task_results}
    assert ("ttm", OpenModelAdapterStatus.AVAILABLE_AND_RAN) in statuses
    assert ("chronos", OpenModelAdapterStatus.MISSING_DEPENDENCY) in statuses
    assert len({(item.model_id, item.task_id) for item in result.task_results}) == 8


def test_strict_mode_detects_required_attempt_failures(tmp_path):
    config = _write_c21_fixture_config(tmp_path, strict_model_success=True)
    _write_fixture_observations(tmp_path / "observations.parquet")
    result = run_c21_executable_evaluation(
        config,
        adapter_factory={"chronos": MissingDependencyAdapter()},
    )
    assert result.has_required_attempt_failure is True


def test_runner_maps_timeout_per_model_task_attempt(tmp_path):
    config = _write_c21_fixture_config(
        tmp_path,
        strict_model_success=False,
        timeout_seconds_per_model=0.01,
    )
    _write_fixture_observations(tmp_path / "observations.parquet")
    result = run_c21_executable_evaluation(
        config,
        adapter_factory={
            "timesfm": TimeoutAdapter(),
            "moirai_uni2ts": LaterRunsForecastingAdapter(),
        },
    )
    timesfm = next(item for item in result.task_results if item.model_id == "timesfm")
    moirai = next(item for item in result.task_results if item.model_id == "moirai_uni2ts")
    assert timesfm.status == OpenModelAdapterStatus.TIMEOUT
    assert timesfm.failure_stage == "execute"
    assert moirai.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN


def test_runner_preserves_load_failure_without_executing_task(tmp_path):
    config = _write_c21_fixture_config(tmp_path, strict_model_success=False)
    _write_fixture_observations(tmp_path / "observations.parquet")
    result = run_c21_executable_evaluation(
        config,
        adapter_factory={"timesfm": LoadFailureAdapter()},
    )
    timesfm = next(item for item in result.task_results if item.model_id == "timesfm")
    assert timesfm.status == OpenModelAdapterStatus.MISSING_OR_BLOCKED_WEIGHTS
    assert timesfm.failure_stage == "load"
    assert timesfm.failure_reason == "weights unavailable in offline cache"


def test_runner_maps_non_ready_readiness_to_inspect_failure(tmp_path):
    config = _write_c21_fixture_config(tmp_path, strict_model_success=False)
    _write_fixture_observations(tmp_path / "observations.parquet")
    result = run_c21_executable_evaluation(
        config,
        adapter_factory={"chronos": NonReadyReadinessAdapter()},
    )
    chronos = next(item for item in result.task_results if item.model_id == "chronos")
    assert chronos.status == OpenModelAdapterStatus.MISSING_DEPENDENCY
    assert chronos.failure_stage == "inspect"
    assert chronos.dependency_status == "missing:chronos"
    assert chronos.weight_status == "not_checked"


def test_attempt_timeout_restores_outer_timer_after_elapsed(monkeypatch):
    events = []
    monotonic_values = iter([100.0, 100.25])

    def fake_setitimer(which, seconds, interval=0.0):
        events.append(("setitimer", which, seconds, interval))
        if len([event for event in events if event[0] == "setitimer"]) == 1:
            return (1.0, 0.0)
        return (0.0, 0.0)

    monkeypatch.setattr(c21_eval.signal, "getsignal", lambda signum: "old-handler")
    monkeypatch.setattr(
        c21_eval.signal,
        "signal",
        lambda signum, handler: events.append(("signal", signum, handler)),
    )
    monkeypatch.setattr(c21_eval.signal, "setitimer", fake_setitimer)
    monkeypatch.setattr(c21_eval.time, "monotonic", lambda: next(monotonic_values))

    with c21_eval._attempt_timeout(0.5):
        pass

    assert [event[:3] for event in events] == [
        ("setitimer", c21_eval.signal.ITIMER_REAL, 0.0),
        ("signal", c21_eval.signal.SIGALRM, events[1][2]),
        ("setitimer", c21_eval.signal.ITIMER_REAL, 0.5),
        ("setitimer", c21_eval.signal.ITIMER_REAL, 0.0),
        ("signal", c21_eval.signal.SIGALRM, "old-handler"),
        ("setitimer", c21_eval.signal.ITIMER_REAL, 0.75),
    ]
    assert events[-1] == ("setitimer", c21_eval.signal.ITIMER_REAL, 0.75, 0.0)


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


def _write_c21_fixture_config(
    tmp_path: Path,
    *,
    strict_model_success: bool = False,
    timeout_seconds_per_model: float = 1.0,
):
    config_path = tmp_path / "c21_fixture.yaml"
    config_path.write_text(
        f"""
stage: C2_1_executable_open_model_evaluation
upstream_c2_config: configs/c_stage_c2_open_model_evaluation.yaml
dataset:
  fu13_observations: {tmp_path / "observations.parquet"}
  fu13_config: {tmp_path / "fu13_schema.yaml"}
  boundary: fixture_internal_fu13
window:
  window_mode: cross-stage
  context_length: 8
  prediction_length: 2
  max_windows: 4
  mask_ratio: 0.2
  seed: 7
execution_policy:
  allow_network: false
  allow_download: false
  strict_model_success: {str(strict_model_success).lower()}
  record_failure: true
  do_not_over_claim: true
  continue_on_model_failure: true
  timeout_seconds_per_model: {timeout_seconds_per_model}
model_cache_policy:
  cache_dir: {tmp_path / "hf_cache"}
  reuse_existing_cache: true
  write_cache_manifest: true
outputs:
  report: {tmp_path / "c21_report.md"}
  cache_manifest: {tmp_path / "c21_cache_manifest.md"}
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "fu13_schema.yaml").write_text("fixture: true\n", encoding="utf-8")
    return load_c21_executable_config(config_path)


def _write_fixture_observations(path: Path) -> None:
    timestamps = pd.date_range("2026-01-01", periods=12, freq="min")
    rows = []
    for sensor_index, sensor_id in enumerate(["sensor_a", "sensor_b"]):
        for index, timestamp in enumerate(timestamps):
            rows.append(
                {
                    "device_id": "device_fixture",
                    "batch_id": "batch_fixture",
                    "stage": "heating" if index < 6 else "holding",
                    "timestamp": timestamp,
                    "sensor_id": sensor_id,
                    "domain": "thermal",
                    "value": float(index + sensor_index),
                    "degradation_label": "normal",
                }
            )
    pd.DataFrame(rows).to_parquet(path)
