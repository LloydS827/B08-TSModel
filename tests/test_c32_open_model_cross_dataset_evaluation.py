from pathlib import Path

import pytest
import yaml

from b08_model_core.cli import main
from b08_model_core.experiments.c32_open_model_cross_dataset_evaluation import (
    C32ConfigError,
    load_c32_config,
    render_c32_report,
    run_c32_open_model_cross_dataset_evaluation,
)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG = (
    _REPO_ROOT / "configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml"
)
_LOCAL_EXECUTION_CONFIG = (
    _REPO_ROOT / "configs/local/c_stage_c32_explicit_local_execution.example.yaml"
)


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def _modified_default(tmp_path: Path, update) -> Path:
    data = yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
    update(data)
    return _write_yaml(tmp_path / "c32_broken.yaml", data)


def test_c32_default_config_is_contract_first_and_offline_safe():
    config = load_c32_config(_DEFAULT_CONFIG)

    assert config.stage == "C3_2_open_model_cross_dataset_evaluation"
    assert config.outputs.report == Path(
        "reports/c_stage_c32_open_model_cross_dataset_evaluation.md"
    )
    assert config.safety_policy.allow_network is False
    assert config.safety_policy.allow_download is False
    assert config.safety_policy.allow_local_raw_data is False
    assert config.safety_policy.allow_model_cache is False
    assert config.safety_policy.allow_training is False
    assert config.safety_policy.allow_write_processed is False
    assert config.prerequisites.c31_review_doc == Path(
        "docs/reviews/2026-06-11-c31-cmapss-local-raw-mapping-review.md"
    )
    assert config.prerequisites.required_status == "schema_validated_ready_for_c32"
    assert (
        config.prerequisites.required_readiness_detail
        == "full_classic_cmapss_validated"
    )
    assert config.prerequisites.reviewed_raw_file_count == 12
    assert config.prerequisites.leakage_guard_passed is True
    assert config.metric_contract.leaderboard_allowed is False
    assert config.model_cache_policy.cache_dir == Path("hf_cache")
    assert config.local_execution is None


def test_c32_local_execution_example_is_explicit_opt_in():
    config = load_c32_config(_LOCAL_EXECUTION_CONFIG)

    assert config.safety_policy.allow_local_execution is True
    assert config.safety_policy.allow_local_raw_data is True
    assert config.safety_policy.allow_network is False
    assert config.safety_policy.allow_download is False
    assert config.safety_policy.allow_model_cache is False
    assert config.safety_policy.allow_training is False
    assert config.safety_policy.allow_write_processed is False
    assert config.local_execution is not None
    assert config.local_execution.enabled is True
    assert config.local_execution.cmapss.subsets == (
        "FD001",
        "FD002",
        "FD003",
        "FD004",
    )
    assert config.local_execution.fu13_like.context_length == 32
    assert config.local_execution.fu13_like.prediction_length == 8
    assert config.local_execution.fu13_like.max_windows == 60
    assert config.local_execution.cmapss.raw_dir == (
        _REPO_ROOT / "data/public/cmapss/raw"
    )
    assert config.outputs.report == Path("reports/c_stage_c32_explicit_local_execution.md")


def test_c32_local_execution_example_report_path_is_ignored():
    config = load_c32_config(_LOCAL_EXECUTION_CONFIG)

    assert config.outputs.report.parent == Path("reports")


def test_c32_rejects_local_execution_without_required_flags(tmp_path):
    data = yaml.safe_load(_LOCAL_EXECUTION_CONFIG.read_text(encoding="utf-8"))
    data["safety_policy"]["allow_local_raw_data"] = False
    broken = _write_yaml(tmp_path / "broken_local.yaml", data)

    with pytest.raises(C32ConfigError, match="allow_local_raw_data"):
        load_c32_config(broken)


def test_c32_rejects_local_execution_with_training_enabled(tmp_path):
    data = yaml.safe_load(_LOCAL_EXECUTION_CONFIG.read_text(encoding="utf-8"))
    data["safety_policy"]["allow_training"] = True
    broken = _write_yaml(tmp_path / "broken_training.yaml", data)

    with pytest.raises(C32ConfigError, match="allow_training"):
        load_c32_config(broken)


def test_c32_rejects_local_execution_with_negative_seed(tmp_path):
    data = yaml.safe_load(_LOCAL_EXECUTION_CONFIG.read_text(encoding="utf-8"))
    data["local_execution"]["fu13_like"]["seed"] = -1
    broken = _write_yaml(tmp_path / "broken_seed.yaml", data)

    with pytest.raises(C32ConfigError, match="seed"):
        load_c32_config(broken)


def test_c32_treats_missing_local_execution_enabled_as_contract_only(tmp_path):
    data = yaml.safe_load(_LOCAL_EXECUTION_CONFIG.read_text(encoding="utf-8"))
    data["safety_policy"]["allow_local_raw_data"] = False
    data["safety_policy"]["allow_local_execution"] = False
    data["local_execution"].pop("enabled")
    path = _write_yaml(tmp_path / "c32_local_disabled.yaml", data)

    config = load_c32_config(path)

    assert config.local_execution is None
    assert config.safety_policy.allow_local_execution is False
    assert config.safety_policy.allow_local_raw_data is False


def test_c32_rejects_wrong_stage(tmp_path):
    broken = _modified_default(tmp_path, lambda data: data.update({"stage": "wrong"}))

    with pytest.raises(C32ConfigError, match="stage"):
        load_c32_config(broken)


def test_c32_rejects_unsafe_default_policy(tmp_path):
    def make_unsafe(data):
        data["safety_policy"]["allow_download"] = True

    broken = _modified_default(tmp_path, make_unsafe)

    with pytest.raises(C32ConfigError, match="allow_download"):
        load_c32_config(broken)


def test_c32_rejects_duplicate_dataset_ids(tmp_path):
    def duplicate_dataset(data):
        data["dataset_views"][1]["dataset_id"] = data["dataset_views"][0][
            "dataset_id"
        ]

    broken = _modified_default(tmp_path, duplicate_dataset)

    with pytest.raises(C32ConfigError, match="duplicate dataset_id"):
        load_c32_config(broken)


def test_c32_rejects_unknown_task_dataset_reference(tmp_path):
    def unknown_dataset(data):
        data["task_contracts"][0]["compatible_dataset_views"] = ["missing_dataset"]

    broken = _modified_default(tmp_path, unknown_dataset)

    with pytest.raises(C32ConfigError, match="unknown dataset"):
        load_c32_config(broken)


def test_c32_rejects_duplicate_task_ids(tmp_path):
    def duplicate_task(data):
        data["task_contracts"][1]["task_id"] = data["task_contracts"][0]["task_id"]

    broken = _modified_default(tmp_path, duplicate_task)

    with pytest.raises(C32ConfigError, match="duplicate task_id"):
        load_c32_config(broken)


def test_c32_rejects_unknown_model_task_reference(tmp_path):
    def unknown_task(data):
        data["model_candidates"][0]["task_ids"] = ["missing_task"]

    broken = _modified_default(tmp_path, unknown_task)

    with pytest.raises(C32ConfigError, match="unknown task"):
        load_c32_config(broken)


def test_c32_rejects_duplicate_model_ids(tmp_path):
    def duplicate_model(data):
        data["model_candidates"][1]["model_id"] = data["model_candidates"][0][
            "model_id"
        ]

    broken = _modified_default(tmp_path, duplicate_model)

    with pytest.raises(C32ConfigError, match="duplicate model_id"):
        load_c32_config(broken)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("required_status", "blocked"),
        ("required_readiness_detail", "not_ready"),
        ("reviewed_raw_file_count", 11),
        ("leakage_guard_passed", False),
    ],
)
def test_c32_rejects_wrong_c31_prerequisite_contract(tmp_path, field, value):
    def break_prerequisite(data):
        data["prerequisites"][field] = value

    broken = _modified_default(tmp_path, break_prerequisite)

    with pytest.raises(C32ConfigError, match=field):
        load_c32_config(broken)


def test_c32_rejects_leaderboard_allowed(tmp_path):
    def allow_leaderboard(data):
        data["metric_contract"]["leaderboard_allowed"] = True

    broken = _modified_default(tmp_path, allow_leaderboard)

    with pytest.raises(C32ConfigError, match="leaderboard_allowed"):
        load_c32_config(broken)


def test_c32_rejects_task_metric_missing_from_metric_contract(tmp_path):
    def unknown_metric(data):
        data["task_contracts"][0]["required_metrics"] = ["missing_metric"]

    broken = _modified_default(tmp_path, unknown_metric)

    with pytest.raises(C32ConfigError, match="unknown metric"):
        load_c32_config(broken)


@pytest.mark.parametrize(
    ("section", "id_field", "missing_id"),
    [
        ("dataset_views", "dataset_id", "cmapss_classic_rul"),
        ("task_contracts", "task_id", "rul_regression"),
        ("model_candidates", "model_id", "baseline"),
    ],
)
def test_c32_rejects_missing_required_contract_ids(
    tmp_path,
    section,
    id_field,
    missing_id,
):
    def remove_required_id(data):
        data[section] = [
            item for item in data[section] if item[id_field] != missing_id
        ]

    broken = _modified_default(tmp_path, remove_required_id)

    with pytest.raises(C32ConfigError, match=missing_id):
        load_c32_config(broken)


def test_c32_rejects_unknown_model_candidate_id(tmp_path):
    def fake_model(data):
        data["model_candidates"][0]["model_id"] = "fake_model"

    broken = _modified_default(tmp_path, fake_model)

    with pytest.raises(C32ConfigError, match="fake_model"):
        load_c32_config(broken)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("dataset_views", "status", "scored_and_ranked"),
        ("task_contracts", "default_action", "model_scored"),
        ("model_candidates", "status", "training_executed"),
    ],
)
def test_c32_rejects_overclaiming_status_and_action_values(
    tmp_path,
    section,
    field,
    value,
):
    def overclaim(data):
        data[section][0][field] = value

    broken = _modified_default(tmp_path, overclaim)

    with pytest.raises(C32ConfigError, match=value):
        load_c32_config(broken)


def test_c32_rejects_overclaiming_model_cache_default_action(tmp_path):
    def overclaim(data):
        data["model_cache_policy"]["default_action"] = "training_executed"

    broken = _modified_default(tmp_path, overclaim)

    with pytest.raises(C32ConfigError, match="training_executed"):
        load_c32_config(broken)


def test_c32_runner_returns_contract_ready_local_execution_blocked():
    config = load_c32_config(_DEFAULT_CONFIG)
    result = run_c32_open_model_cross_dataset_evaluation(
        config, config_path=_DEFAULT_CONFIG
    )

    assert result.status == "contract_ready_local_execution_blocked"
    assert result.go_no_go_decision == "Go for C3.2 local execution design"
    assert result.invalid_claims == (
        "no production RUL",
        "no production alarms",
        "no maintenance recommendations",
        "no benchmark leaderboard",
        "no self-developed model superiority",
    )
    assert [item.dataset_id for item in result.dataset_results] == [
        item.dataset_id for item in config.dataset_views
    ]
    assert all(item.status for item in result.dataset_results)
    assert all(item.default_action for item in result.model_results)


def test_c32_report_records_no_scoring_and_no_production_claims():
    config = load_c32_config(_DEFAULT_CONFIG)
    result = run_c32_open_model_cross_dataset_evaluation(
        config, config_path=_DEFAULT_CONFIG
    )
    text = render_c32_report(result)

    assert "C3.2 Open Model Cross-Dataset Evaluation Report" in text
    assert "Status: contract_ready_local_execution_blocked" in text
    assert "Decision: Go for C3.2 local execution design" in text
    assert "Safety Policy" in text
    assert "C3.1 Prerequisites" in text
    assert "Dataset View Matrix" in text
    assert "Task Compatibility" in text
    assert "Model Candidate Status" in text
    assert "Metric Contract" in text
    assert "Go / No-Go" in text
    assert "Invalid Claims" in text
    assert "Next Step" in text
    assert "schema_validated_ready_for_c32" in text
    assert "full_classic_cmapss_validated" in text
    assert "readiness_matrix_only" in text
    assert "No model training, scoring, or leaderboard is executed" in text
    assert "Do not claim production RUL" in text


def _patch_forbidden_path_probes(
    monkeypatch,
    sentinel_paths: set[Path],
) -> None:
    sentinel_strings = {str(path) for path in sentinel_paths}

    def is_sentinel_or_child(path) -> bool:
        candidate = str(path)
        return any(
            candidate == sentinel
            or candidate.startswith(f"{sentinel}/")
            for sentinel in sentinel_strings
        )

    def fail_if_sentinel_path_is_touched(method_name):
        original = getattr(Path, method_name)

        def wrapped(self, *args, **kwargs):
            if is_sentinel_or_child(self):
                raise AssertionError(
                    f"C3.2 default path touched {method_name}: {self}"
                )
            return original(self, *args, **kwargs)

        return wrapped

    for method_name in (
        "exists",
        "is_file",
        "is_dir",
        "stat",
        "iterdir",
        "glob",
        "rglob",
        "open",
    ):
        monkeypatch.setattr(
            Path, method_name, fail_if_sentinel_path_is_touched(method_name)
        )

    import os

    original_os_stat = os.stat
    original_os_scandir = os.scandir

    def guarded_os_stat(path, *args, **kwargs):
        if is_sentinel_or_child(path):
            raise AssertionError(f"C3.2 default path touched os.stat: {path}")
        return original_os_stat(path, *args, **kwargs)

    def guarded_os_scandir(path="."):
        if is_sentinel_or_child(path):
            raise AssertionError(f"C3.2 default path touched os.scandir: {path}")
        return original_os_scandir(path)

    monkeypatch.setattr(os, "stat", guarded_os_stat)
    monkeypatch.setattr(os, "scandir", guarded_os_scandir)


def test_c32_default_loader_runner_and_cli_do_not_touch_raw_real_or_cache_paths(
    tmp_path,
    monkeypatch,
):
    data = yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
    sentinel_cmapss_raw = tmp_path / "sentinel_cmapss_raw"
    sentinel_fu13_real = tmp_path / "sentinel_fu13_real.parquet"
    sentinel_model_cache = tmp_path / "sentinel_model_cache"
    sentinel_paths = {
        sentinel_cmapss_raw,
        sentinel_fu13_real,
        sentinel_model_cache,
    }
    data["dataset_views"][0]["local_path"] = str(sentinel_cmapss_raw)
    data["dataset_views"][1]["local_path"] = str(sentinel_fu13_real)
    data["model_cache_policy"]["cache_dir"] = str(sentinel_model_cache)
    config_path = _write_yaml(tmp_path / "c32_no_touch.yaml", data)

    _patch_forbidden_path_probes(monkeypatch, sentinel_paths)

    config = load_c32_config(config_path)
    result = run_c32_open_model_cross_dataset_evaluation(
        config, config_path=config_path
    )

    assert result.status == "contract_ready_local_execution_blocked"

    output = tmp_path / "c32_report.md"
    exit_code = main(
        [
            "experiment",
            "c-stage-c32",
            "--config",
            str(config_path),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    assert output.exists()


def test_c32_default_runner_does_not_import_open_model_adapters(monkeypatch):
    import builtins
    import importlib

    forbidden = (
        "b08_model_core.adapters.open_models",
        "b08_model_core.adapters.ttm_adapter",
    )
    original_import = builtins.__import__
    original_import_module = importlib.import_module

    def guarded_import(name, *args, **kwargs):
        if name.startswith(forbidden):
            raise AssertionError(f"C3.2 default runner imported adapters: {name}")
        return original_import(name, *args, **kwargs)

    def guarded_import_module(name, *args, **kwargs):
        if name.startswith(forbidden):
            raise AssertionError(
                f"C3.2 default runner imported adapter module: {name}"
            )
        return original_import_module(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(importlib, "import_module", guarded_import_module)
    config = load_c32_config(_DEFAULT_CONFIG)

    result = run_c32_open_model_cross_dataset_evaluation(
        config, config_path=_DEFAULT_CONFIG
    )

    assert result.status == "contract_ready_local_execution_blocked"


def test_c32_default_cli_import_and_run_does_not_import_model_adapters(
    monkeypatch,
    tmp_path,
):
    import builtins
    import importlib
    import sys

    for module_name in tuple(sys.modules):
        if module_name.startswith(
            (
                "b08_model_core.cli",
                "b08_model_core.adapters",
                "b08_model_core.experiments.forecasting",
                "b08_model_core.evaluation.benchmark",
            )
        ):
            sys.modules.pop(module_name, None)

    original_import = builtins.__import__
    original_import_module = importlib.import_module

    def is_forbidden(name: str) -> bool:
        return name.startswith(
            (
                "b08_model_core.adapters",
                "b08_model_core.experiments.forecasting",
                "b08_model_core.evaluation.benchmark",
            )
        )

    def guarded_import(name, *args, **kwargs):
        if is_forbidden(name):
            raise AssertionError(f"C3.2 default CLI imported adapter path: {name}")
        return original_import(name, *args, **kwargs)

    def guarded_import_module(name, *args, **kwargs):
        if is_forbidden(name):
            raise AssertionError(f"C3.2 default CLI imported adapter module: {name}")
        return original_import_module(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(importlib, "import_module", guarded_import_module)

    from b08_model_core.cli import main

    output = tmp_path / "c32_cli_no_adapter_report.md"
    exit_code = main(
        [
            "experiment",
            "c-stage-c32",
            "--config",
            str(_DEFAULT_CONFIG),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    assert "contract_ready_local_execution_blocked" in output.read_text(encoding="utf-8")


def test_cli_c_stage_c32_writes_contract_report(tmp_path):
    output = tmp_path / "c32_report.md"
    exit_code = main(
        [
            "experiment",
            "c-stage-c32",
            "--config",
            str(_DEFAULT_CONFIG),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "C3.2 Open Model Cross-Dataset Evaluation Report" in text
    assert "contract_ready_local_execution_blocked" in text
