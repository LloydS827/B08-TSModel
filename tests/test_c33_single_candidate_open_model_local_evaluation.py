from pathlib import Path

import numpy as np
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


def test_c33_rejects_wrong_c32_prerequisite_status(tmp_path):
    data = yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
    data["prerequisites"]["c32_local_status"] = "blocked"
    with pytest.raises(C33ConfigError, match="c32_local_status"):
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


def test_c33_local_runner_records_successful_ttm_adapter_evidence():
    config = load_c33_config(_LOCAL_CONFIG)
    fake_adapter = _RunOnlyFakeTtmAdapter()

    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_LOCAL_CONFIG,
        adapter_factory=lambda: fake_adapter,
    )
    text = render_c33_report(result)

    assert result.status == "local_execution_ttm_forecasting_ready"
    assert result.baseline_reference_result is not None
    assert result.baseline_reference_result.train_window_count == 42
    assert result.baseline_reference_result.test_window_count == 18
    assert result.adapter_result is not None
    assert result.adapter_failure is None
    assert result.adapter_result.status == _adapter_status().AVAILABLE_AND_RAN
    assert result.adapter_result.adapter_status == _adapter_status().AVAILABLE_AND_RAN
    assert result.adapter_result.dependency_status == "available"
    assert result.adapter_result.weight_status == "available"
    assert result.adapter_result.download_allowed_not_verified is False
    assert result.ttm_metrics is not None
    assert result.ttm_metrics["mae"] == 1.0
    assert result.ttm_metrics["count"] > 0
    assert result.ttm_residual_ranking
    assert not hasattr(result, "forecasting_reference_result")
    assert not hasattr(result, "ttm_adapter_result")
    assert not hasattr(result, "ttm_forecasting_metrics")
    assert fake_adapter.contexts
    context = fake_adapter.contexts[-1]
    assert context.cache_dir == config.local_execution.model_cache_dir
    assert context.allow_network is False
    assert context.allow_download is False
    assert context.timeout_seconds_per_model == 300.0
    assert context.metadata == {
        "stage": "C3_3_single_candidate_open_model_local_evaluation",
        "candidate": "ttm",
    }
    assert "Baseline Forecasting Reference" in text
    assert "TTM Adapter Execution" in text
    assert "TTM Forecasting Metrics" in text
    assert "Separated Metric Interpretation" in text
    assert "- status: available_and_ran" in text
    assert "adapter_status" in text
    assert "download_allowed_not_verified" in text


def test_c33_local_runner_maps_missing_dependency_status():
    result = _run_local_with_adapter(
        _RunOnlyFakeTtmAdapter(
            run_result=_adapter_failure(
                model_id="ttm",
                status=_adapter_status().MISSING_DEPENDENCY,
                failure_stage="execute",
                failure_reason="missing dependency",
                dependency_status="missing:tsfm_public",
                weight_status="not_checked",
            )
        )
    )

    assert result.status == "local_execution_ttm_missing_dependency"
    assert result.adapter_result is None
    assert result.adapter_failure is not None
    assert result.adapter_failure.dependency_status == "missing:tsfm_public"
    assert result.ttm_metrics is None


def test_c33_local_runner_maps_missing_or_blocked_weights_status():
    result = _run_local_with_adapter(
        _RunOnlyFakeTtmAdapter(
            run_result=_adapter_failure(
                model_id="ttm",
                status=_adapter_status().MISSING_OR_BLOCKED_WEIGHTS,
                failure_stage="execute",
                failure_reason="cache miss and downloads disabled",
                dependency_status="available",
                weight_status="missing_or_blocked",
            )
        )
    )

    assert result.status == "local_execution_ttm_missing_or_blocked_weights"
    assert result.adapter_result is None
    assert result.adapter_failure is not None
    assert result.adapter_failure.weight_status == "missing_or_blocked"
    assert result.ttm_metrics is None


def test_c33_local_runner_converts_adapter_exception_to_runtime_failed_evidence():
    result = _run_local_with_adapter(
        _RunOnlyFakeTtmAdapter(run_exception=RuntimeError("adapter exploded"))
    )

    assert result.status == "local_execution_ttm_runtime_failed"
    assert result.adapter_result is None
    assert result.adapter_failure is not None
    assert result.adapter_failure.status == _adapter_status().RUNTIME_FAILED
    assert result.adapter_failure.failure_stage == "execute"
    assert result.adapter_failure.failure_reason == "adapter exploded"
    assert result.adapter_failure.error_type == "RuntimeError"
    assert result.adapter_failure.error_detail == "adapter exploded"
    assert result.ttm_metrics is None


def test_c33_local_runner_maps_unsupported_window_shape_status():
    result = _run_local_with_adapter(
        _RunOnlyFakeTtmAdapter(
            run_result=_adapter_failure(
                model_id="ttm",
                status=_adapter_status().UNSUPPORTED_WINDOW_SHAPE,
                failure_stage="execute",
                failure_reason="shape mismatch",
                dependency_status="available",
                weight_status="available",
            )
        )
    )

    assert result.status == "local_execution_ttm_unsupported_window_shape"
    assert result.adapter_result is None
    assert result.adapter_failure is not None
    assert result.ttm_metrics is None


def test_c33_local_runner_structures_adapter_factory_exception():
    config = load_c33_config(_LOCAL_CONFIG)

    def broken_factory():
        raise RuntimeError("factory exploded")

    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_LOCAL_CONFIG,
        adapter_factory=broken_factory,
    )

    assert result.status == "local_execution_ttm_runtime_failed"
    assert result.adapter_result is None
    assert result.adapter_failure is not None
    assert result.adapter_failure.failure_stage == "construct"
    assert result.adapter_failure.failure_reason == "factory exploded"
    assert result.adapter_failure.error_type == "RuntimeError"
    assert result.adapter_failure.error_detail == "factory exploded"


def test_c33_local_runner_structures_malformed_success_prediction_shape():
    result = _run_local_with_adapter(
        _RunOnlyFakeTtmAdapter(prediction_mode="malformed_shape")
    )

    assert result.status == "local_execution_ttm_unsupported_window_shape"
    assert result.adapter_result is None
    assert result.adapter_failure is not None
    assert result.adapter_failure.failure_stage == "metrics"
    assert result.adapter_failure.status == _adapter_status().UNSUPPORTED_WINDOW_SHAPE
    assert result.ttm_metrics is None


def test_c33_local_runner_records_download_allowed_not_verified(tmp_path):
    data = yaml.safe_load(_LOCAL_CONFIG.read_text(encoding="utf-8"))
    data["safety_policy"]["allow_network"] = True
    data["safety_policy"]["allow_download"] = True
    config = load_c33_config(_write_yaml(tmp_path / "local.yaml", data))

    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=tmp_path / "local.yaml",
        adapter_factory=lambda: _RunOnlyFakeTtmAdapter(actual_network_used=None),
    )
    text = render_c33_report(result)

    assert result.adapter_result is not None
    assert result.adapter_result.actual_network_used is None
    assert result.adapter_result.download_allowed_not_verified is True
    assert "- download_allowed_not_verified: True" in text


def test_c33_local_runner_blocks_when_fu13_like_windows_are_insufficient(tmp_path):
    data = yaml.safe_load(_LOCAL_CONFIG.read_text(encoding="utf-8"))
    data["local_execution"]["fu13_like"]["days"] = 1
    data["local_execution"]["fu13_like"]["context_length"] = 10_000
    config = load_c33_config(_write_yaml(tmp_path / "local.yaml", data))

    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=tmp_path / "local.yaml",
        adapter_factory=lambda: _RunOnlyFakeTtmAdapter(),
    )

    assert result.status == "blocked_insufficient_fu13_like_windows"
    assert result.baseline_reference_result is None
    assert result.adapter_result is None
    assert result.adapter_failure is None
    assert result.local_execution_blocked_reason == "insufficient FU13-like windows"


def _run_local_with_adapter(fake_adapter: "_RunOnlyFakeTtmAdapter"):
    config = load_c33_config(_LOCAL_CONFIG)
    return run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_LOCAL_CONFIG,
        adapter_factory=lambda: fake_adapter,
    )


class _RunOnlyFakeTtmAdapter:
    def __init__(
        self,
        *,
        run_result: object | None = None,
        run_exception: Exception | None = None,
        actual_network_used: bool | None = False,
        prediction_mode: str = "truth_plus_one",
    ) -> None:
        self.run_result = run_result
        self.run_exception = run_exception
        self.actual_network_used = actual_network_used
        self.prediction_mode = prediction_mode
        self.contexts = []

    def run_forecasting(self, windows, context):
        AdapterTaskOutput, status, task_id = _adapter_output_types()
        self.contexts.append(context)
        if self.run_exception is not None:
            raise self.run_exception
        if self.run_result is not None:
            return self.run_result
        if self.prediction_mode == "malformed_shape":
            predictions = np.asarray([1.0])
        else:
            predictions = np.stack([window.y + 1.0 for window in windows], axis=0)
        return AdapterTaskOutput(
            model_id="ttm",
            task_id=task_id.FORECASTING,
            status=status.AVAILABLE_AND_RAN,
            predictions=predictions,
            metrics={"runtime_seconds": 0.01},
            input_shape={
                "windows": len(windows),
                "X": list(np.asarray(windows[0].X).shape),
                "y": list(np.asarray(windows[0].y).shape),
            },
            output_shape={"predictions": list(predictions.shape)},
            runtime_seconds=0.01,
            adapter_name="RunOnlyFakeTtmAdapter",
            model_ref="fake-ttm",
            cache_dir=context.cache_dir,
            actual_network_used=self.actual_network_used,
            metadata={"weight_status": "available"},
        )


def _adapter_status():
    from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus

    return OpenModelAdapterStatus


def _adapter_output_types():
    from b08_model_core.adapters.open_models.base import AdapterTaskOutput
    from b08_model_core.experiments.c21_executable_open_model_evaluation import (
        C21TaskId,
    )

    return AdapterTaskOutput, _adapter_status(), C21TaskId


def _adapter_failure(**kwargs):
    from b08_model_core.adapters.open_models.base import AdapterFailure
    from b08_model_core.experiments.c21_executable_open_model_evaluation import (
        C21TaskId,
    )

    return AdapterFailure(task_id=C21TaskId.FORECASTING, **kwargs)


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


def test_c33_local_report_uses_local_execution_wording():
    config = load_c33_config(_LOCAL_CONFIG)
    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_LOCAL_CONFIG,
        adapter_factory=lambda: _RunOnlyFakeTtmAdapter(),
    )
    text = render_c33_report(result)

    assert "Adapter execution: explicit local TTM run" in text
    assert "Default adapter execution: disabled" not in text
    assert "Use the explicit local config in the next task" not in text


def test_c33_contract_report_keeps_contract_only_wording():
    config = load_c33_config(_DEFAULT_CONFIG)
    result = run_c33_single_candidate_open_model_local_evaluation(
        config,
        config_path=_DEFAULT_CONFIG,
    )
    text = render_c33_report(result)

    assert "Adapter execution: disabled in contract-only config" in text
    assert (
        "Use an explicit local config to record TTM adapter/cache/dependency evidence."
        in text
    )
