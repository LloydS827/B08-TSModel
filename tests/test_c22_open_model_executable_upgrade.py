from pathlib import Path

import pytest

from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus
from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21ModelTaskResult,
    C21RunResult,
    C21TaskId,
)
from b08_model_core.experiments.c22_open_model_executable_upgrade import (
    C22ConfigError,
    C22ModelRole,
    C22RunResult,
    C22TargetResult,
    REQUIRED_C22_MODEL_TARGET_IDS,
    REQUIRED_C22_WATCHLIST_TARGET_IDS,
    build_c22_core_attempts,
    build_c21_config_from_c22,
    build_frontier_watchlist_audit,
    load_c22_config,
    render_c22_cache_manifest,
    render_c22_report,
    run_c22_open_model_executable_upgrade,
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
    assert config.timeout_seconds_per_model == 900


def test_c22_model_targets_capture_roles_and_versions():
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    assert tuple(config.model_targets) == REQUIRED_C22_MODEL_TARGET_IDS
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


def test_c22_default_watchlist_contains_exact_frontier_targets():
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    assert config.frontier_watchlist.targets == REQUIRED_C22_WATCHLIST_TARGET_IDS


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


def test_build_c21_config_from_c22_populates_bridge_settings(tmp_path):
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    config.cache_dir = tmp_path / "cache"

    c21_config = build_c21_config_from_c22(config)

    assert c21_config.stage == "C2_1_executable_open_model_evaluation"
    assert c21_config.upstream_c2_config == Path(
        "configs/c_stage_c2_open_model_evaluation.yaml"
    )
    assert c21_config.dataset_path == config.dataset_path
    assert c21_config.fu13_config_path == config.fu13_config_path
    assert c21_config.dataset_boundary == config.dataset_boundary
    assert c21_config.max_windows == config.max_windows
    assert c21_config.allow_network is False
    assert c21_config.allow_download is False
    assert c21_config.cache_dir == config.cache_dir


def test_c22_runner_wraps_c21_results_with_target_metadata(tmp_path):
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    config.cache_dir = tmp_path / "empty_cache"

    def fake_c21_runner(c21_config, adapter_factory=None):
        return C21RunResult(
            run_id="c21-fake",
            config_path="c21",
            upstream_c2_config="c2",
            dataset_boundary="internal_fu13_no_raw_data_committed",
            config_allows_network=False,
            config_allows_download=False,
            cache_dir=c21_config.cache_dir,
            tested_windows=2,
            task_results=[
                C21ModelTaskResult(
                    model_id="chronos",
                    display_name="Chronos / Chronos-Bolt",
                    task_id=C21TaskId.FORECASTING,
                    status=OpenModelAdapterStatus.MISSING_DEPENDENCY,
                    metrics={},
                    baseline_metrics={"baseline": "RobustStageForecaster"},
                    failure_stage="inspect",
                    failure_reason="dependency modules are unavailable",
                    error_type="MissingDependency",
                    error_detail="chronos",
                    dependency_status="missing:chronos",
                    weight_status="not_checked",
                    input_shape={"windows": 2},
                    output_shape={},
                    runtime_seconds=0.0,
                    adapter_name="ChronosOpenModelAdapter",
                    model_ref="amazon/chronos-2",
                    cache_dir=c21_config.cache_dir,
                    actual_network_used=False,
                )
            ],
            invalid_claims=["不得解释为生产告警"],
        )

    result = run_c22_open_model_executable_upgrade(config, c21_runner=fake_c21_runner)

    assert result.tested_windows == 2
    assert result.config_allows_network is False
    assert result.config_allows_download is False
    assert result.watchlist_audit
    chronos = result.target_results[0]
    assert chronos.model_id == "chronos"
    assert chronos.role == C22ModelRole.PRIORITY_REAL_EXECUTION
    assert chronos.target == "chronos_2"
    assert chronos.fallback == "chronos_bolt"
    assert chronos.target_metadata["target_model_ref"] == "amazon/chronos-2"
    assert chronos.target_metadata["target_package_hint"]
    assert chronos.target_metadata["target_task_fit"]
    assert chronos.cache_dir == config.cache_dir
    assert chronos.actual_network_used is False


def test_c22_runner_offline_behavior_is_stable_with_existing_cache(tmp_path):
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    config.cache_dir = tmp_path / "existing_cache"
    config.cache_dir.mkdir()

    def fake_c21_runner(c21_config, adapter_factory=None):
        return C21RunResult(
            run_id="c21-fake",
            config_path="c21",
            upstream_c2_config="c2",
            dataset_boundary="boundary",
            config_allows_network=False,
            config_allows_download=False,
            cache_dir=c21_config.cache_dir,
            tested_windows=0,
            task_results=[],
            invalid_claims=[],
        )

    result = run_c22_open_model_executable_upgrade(config, c21_runner=fake_c21_runner)
    manifest = render_c22_cache_manifest(result)

    assert "existing_cache" in manifest
    assert "network_allowed" in manifest
    assert result.config_allows_network is False
    assert result.config_allows_download is False


def test_c22_runner_passes_adapter_factory_to_c21_runner(tmp_path):
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    config.cache_dir = tmp_path / "cache"
    adapter_factory = object()
    captured = {}

    def fake_c21_runner(c21_config, adapter_factory=None):
        captured["adapter_factory"] = adapter_factory
        return C21RunResult(
            run_id="c21-fake",
            config_path="c21",
            upstream_c2_config="c2",
            dataset_boundary=config.dataset_boundary,
            config_allows_network=config.allow_network,
            config_allows_download=config.allow_download,
            cache_dir=c21_config.cache_dir,
            tested_windows=0,
            task_results=[],
            invalid_claims=[],
        )

    run_c22_open_model_executable_upgrade(
        config,
        adapter_factory=adapter_factory,
        c21_runner=fake_c21_runner,
    )

    assert captured["adapter_factory"] is adapter_factory


def test_c22_strict_helper_considers_only_core_target_results():
    failing_result = C22RunResult(
        run_id="c22-test",
        config_path="cfg",
        upstream_c21_config="c21",
        dataset_boundary="boundary",
        config_allows_network=False,
        config_allows_download=False,
        cache_dir="hf_cache",
        tested_windows=0,
        target_results=[
            C22TargetResult(
                model_id="chronos",
                role=C22ModelRole.PRIORITY_REAL_EXECUTION,
                target="chronos_2",
                fallback="chronos_bolt",
                task_id=C21TaskId.FORECASTING,
                status=OpenModelAdapterStatus.MISSING_DEPENDENCY,
            )
        ],
        watchlist_audit=[],
        invalid_claims=[],
    )
    watchlist_only_result = C22RunResult(
        run_id="c22-test",
        config_path="cfg",
        upstream_c21_config="c21",
        dataset_boundary="boundary",
        config_allows_network=False,
        config_allows_download=False,
        cache_dir="hf_cache",
        tested_windows=0,
        target_results=[],
        watchlist_audit=[
            build_frontier_watchlist_audit(
                load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
            )[0]
        ],
        invalid_claims=[],
    )

    assert failing_result.has_priority_or_core_failure is True
    assert watchlist_only_result.has_priority_or_core_failure is False


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


@pytest.mark.parametrize("timeout_value", ["0", "0.5"])
def test_c22_rejects_non_positive_or_non_integer_timeout(tmp_path, timeout_value):
    config_path = _write_modified_config(
        tmp_path,
        "timeout_seconds_per_model: 900",
        f"timeout_seconds_per_model: {timeout_value}",
    )
    with pytest.raises(
        C22ConfigError,
        match="timeout_seconds_per_model must be a positive integer",
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


def test_c22_rejects_wrong_task_set_for_model(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        "tasks: [forecasting]",
        "tasks: [representation]",
        count=1,
    )
    with pytest.raises(
        C22ConfigError,
        match="model_targets.ttm.tasks must match C2.1 required tasks",
    ):
        load_c22_config(config_path)


def test_c22_rejects_missing_required_task_for_model(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        "tasks: [representation, imputation]",
        "tasks: [representation]",
        count=1,
    )
    with pytest.raises(
        C22ConfigError,
        match="model_targets.moment.tasks must match C2.1 required tasks",
    ):
        load_c22_config(config_path)


def test_c22_rejects_duplicate_task_for_model(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        "tasks: [representation, imputation]",
        "tasks: [representation, representation]",
        count=1,
    )
    with pytest.raises(
        C22ConfigError,
        match="model_targets.moment.tasks must match C2.1 required tasks",
    ):
        load_c22_config(config_path)


def test_c22_rejects_missing_required_model_target(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        """  chronos:
    role: priority_real_execution
    target: chronos_2
    fallback: chronos_bolt
    tasks: [forecasting]
""",
        "",
    )
    with pytest.raises(C22ConfigError, match="model_targets must contain exactly"):
        load_c22_config(config_path)


def test_c22_rejects_extra_model_target(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        """frontier_watchlist:
""",
        """  sundial:
    role: core_run_review
    target: sundial_watchlist
    tasks: [forecasting]
frontier_watchlist:
""",
    )
    with pytest.raises(C22ConfigError, match="model_targets must contain exactly"):
        load_c22_config(config_path)


def test_c22_rejects_missing_watchlist_target(tmp_path):
    config_path = _write_modified_config(tmp_path, "    - sundial\n", "")
    with pytest.raises(C22ConfigError, match="frontier_watchlist.targets must contain exactly"):
        load_c22_config(config_path)


def test_c22_rejects_empty_watchlist_targets(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        """  targets:
    - time_moe
    - sundial
    - timer_s1_timer_xl
    - kairos
    - toto
    - ibm_flowstate_tspulse
    - tabpfn_ts
""",
        "  targets: []\n",
    )
    with pytest.raises(C22ConfigError, match="frontier_watchlist.targets must contain exactly"):
        load_c22_config(config_path)


def test_c22_rejects_extra_watchlist_target(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        """outputs:
""",
        """    - extra_frontier_model
outputs:
""",
    )
    with pytest.raises(C22ConfigError, match="frontier_watchlist.targets must contain exactly"):
        load_c22_config(config_path)


def test_c22_rejects_duplicate_watchlist_target(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        "    - sundial\n",
        "    - sundial\n    - sundial\n",
    )
    with pytest.raises(C22ConfigError, match="frontier_watchlist.targets must contain exactly"):
        load_c22_config(config_path)


def test_c22_rejects_watchlist_audit_only_false(tmp_path):
    config_path = _write_modified_config(tmp_path, "  audit_only: true", "  audit_only: false")
    with pytest.raises(C22ConfigError, match="frontier_watchlist.audit_only must be true"):
        load_c22_config(config_path)


def test_c22_rejects_watchlist_promotion_enabled(tmp_path):
    config_path = _write_modified_config(
        tmp_path,
        "  promote_to_real_execution: false",
        "  promote_to_real_execution: true",
    )
    with pytest.raises(
        C22ConfigError,
        match="frontier_watchlist.promote_to_real_execution must be false",
    ):
        load_c22_config(config_path)


def test_c22_watchlist_audit_records_all_expected_targets():
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    audit = build_frontier_watchlist_audit(config)
    by_id = {item.model_or_route: item for item in audit}
    assert set(by_id) == {
        "time_moe",
        "sundial",
        "timer_s1_timer_xl",
        "kairos",
        "toto",
        "ibm_flowstate_tspulse",
        "tabpfn_ts",
    }
    assert all(item.status == "audit_only" for item in audit)
    assert all(item.default_c22_action == "watchlist_audit_only" for item in audit)
    assert by_id["sundial"].promotion_condition


def test_c22_report_contains_decision_sections():
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    result = C22RunResult(
        run_id="c22-test",
        config_path="cfg",
        upstream_c21_config=config.upstream_c21_config,
        dataset_boundary=config.dataset_boundary,
        config_allows_network=False,
        config_allows_download=False,
        cache_dir="hf_cache",
        tested_windows=0,
        target_results=[],
        watchlist_audit=build_frontier_watchlist_audit(config),
        invalid_claims=["不得解释为生产告警"],
    )
    text = render_c22_report(result, config)
    assert "C2.2 Open Model Executable Evaluation Upgrade Report" in text
    assert "Versioned Model Target Matrix" in text
    assert "Priority Real Execution Results" in text
    assert "Core Model-Task Result Matrix" in text
    assert "Frontier Watchlist Audit" in text
    assert "Failure Taxonomy" in text
    assert "C2.2 -> C3 Handoff" in text
    assert "C2.2 -> B Decision Notes" in text
    assert "不得解释为生产告警" in text
    assert "time_moe" in text
    assert "Chronos-2" in text
    assert "TimesFM 2.5" in text
    assert "invalid claims" in text.lower()


def test_c22_report_renders_target_result_rows_and_failure_taxonomy():
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    result = C22RunResult(
        run_id="c22-test",
        config_path="cfg",
        upstream_c21_config=config.upstream_c21_config,
        dataset_boundary=config.dataset_boundary,
        config_allows_network=False,
        config_allows_download=False,
        cache_dir="hf_cache",
        tested_windows=0,
        target_results=[
            C22TargetResult(
                model_id="chronos",
                role=C22ModelRole.PRIORITY_REAL_EXECUTION,
                target="chronos_2",
                fallback="chronos_bolt",
                task_id=C21TaskId.FORECASTING,
                status="runtime_failed",
                metrics={"mae": None},
                baseline_metrics={"baseline": "not_run"},
                failure_stage="execute",
                failure_reason="dependency missing",
                dependency_status="missing",
                weight_status="not_checked",
                adapter_name="ChronosAdapter",
                model_ref="amazon/chronos-2",
                cache_dir="hf_cache/chronos",
                actual_network_used=False,
            )
        ],
        watchlist_audit=[],
        invalid_claims=[],
    )
    text = render_c22_report(result, config)
    assert "| chronos | Chronos-2 | forecasting | chronos_2 | runtime_failed |" in text
    assert "| chronos | forecasting | runtime_failed | execute | dependency missing |" in text
    assert "| chronos | forecasting | chronos_2 | chronos_bolt | ChronosAdapter | hf_cache/chronos | not_checked | false | amazon/chronos-2 |" in text


def test_c22_report_sanitizes_metadata_and_bullets():
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    result = C22RunResult(
        run_id="c22-test",
        config_path="cfg\n- forged: yes|pipe",
        upstream_c21_config=config.upstream_c21_config,
        dataset_boundary=config.dataset_boundary,
        config_allows_network=False,
        config_allows_download=False,
        cache_dir="hf_cache",
        tested_windows=0,
        target_results=[],
        watchlist_audit=[],
        invalid_claims=["claim\n- forged|claim"],
    )
    text = render_c22_report(result, config)
    assert "- config_path: cfg - forged: yes\\|pipe" in text
    assert "- claim - forged\\|claim" in text
    assert "\n- forged: yes|pipe" not in text
    assert "\n- forged|claim" not in text


def test_c22_cache_manifest_records_offline_and_cache_boundary():
    config = load_c22_config("configs/c_stage_c22_open_model_executable_upgrade.yaml")
    result = C22RunResult(
        run_id="c22-test",
        config_path="cfg",
        upstream_c21_config=config.upstream_c21_config,
        dataset_boundary=config.dataset_boundary,
        config_allows_network=False,
        config_allows_download=False,
        cache_dir="hf_cache",
        tested_windows=0,
        target_results=[
            C22TargetResult(
                model_id="timesfm",
                role=C22ModelRole.PRIORITY_REAL_EXECUTION,
                target="timesfm_2_5",
                fallback=None,
                task_id=C21TaskId.FORECASTING,
                status="available_and_ran",
                adapter_name="TimesFMAdapter",
                cache_dir="hf_cache/timesfm",
                actual_network_used=False,
            )
        ],
        watchlist_audit=[],
        invalid_claims=[],
    )
    text = render_c22_cache_manifest(result)
    assert "| network_allowed | false |" in text
    assert "| download_allowed | false |" in text
    assert "| cache_dir | hf_cache |" in text
    assert "actual_network_used" in text
    assert "| timesfm | forecasting | timesfm_2_5 | not_available | TimesFMAdapter | hf_cache/timesfm | not_available | false | not_available |" in text


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
