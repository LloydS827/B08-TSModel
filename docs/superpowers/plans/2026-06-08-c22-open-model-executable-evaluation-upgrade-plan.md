# C2.2 Open Model Executable Evaluation Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build C2.2 as a narrow upgrade on top of C2.1 that adds versioned model targets, priority/core/watchlist layering, frontier watchlist audit, C2.2 report output, and a CLI entry while preserving C2/C2.1 behavior.

**Architecture:** C2.2 will reuse the C2.1 adapter contract, failure taxonomy, cache policy, and runner mechanics. A new `c22_open_model_executable_upgrade` experiment module will load a C2.2 config, map versioned targets to C2.1 attempts, wrap C2.1 execution results with C2.2 metadata, generate watchlist audit records, and render a decision report. C2.2 defaults remain offline/no-download; real network/download behavior is opt-in only.

**Tech Stack:** Python 3.11, dataclasses, StrEnum, pathlib, PyYAML, pandas/parquet fixtures, pytest, existing `b08_model_core` C2.1 adapter and experiment modules.

---

## Scope Guard

This plan implements the approved spec:

`docs/superpowers/specs/2026-06-08-c22-open-model-executable-evaluation-upgrade-design.md`

Must do:

- Add default offline-safe C2.2 config.
- Add C2.2 experiment module and focused tests.
- Add versioned model target metadata for TTM, Chronos-2, TimesFM 2.5, Moirai 2.0 / Uni2TS, MOMENT, and UniTS.
- Add frontier watchlist audit for Time-MoE, Sundial, Timer-S1 / Timer-XL, Kairos, Toto, IBM FlowState / TSPulse, and TabPFN-TS.
- Add `experiment c-stage-c22` CLI.
- Preserve C2 and C2.1 entry points.
- Keep default pytest independent of network, external weights, and local cache.

Must not do:

- Do not implement C3 public dataset registry.
- Do not implement B-stage self-training.
- Do not add model weights, cache files, private paths, or generated real reports to Git.
- Do not make watchlist models required real execution attempts.
- Do not add optional extras unless package names and versions are verified and a test proves default dependencies remain unchanged.

## File Structure

Create:

- `configs/c_stage_c22_open_model_executable_upgrade.yaml`
  - Default offline-safe C2.2 config. Stores upstream C2.1 config, FU13 dataset/window policy, execution/cache policy, versioned model targets, watchlist targets, and output paths.

- `src/b08_model_core/experiments/c22_open_model_executable_upgrade.py`
  - C2.2 config loader, target/watchlist schema, C2.1 config bridge, runner wrapper, watchlist audit builder, report/cache manifest renderers, and strict-mode helpers.

- `tests/test_c22_open_model_executable_upgrade.py`
  - Focused tests for config, target matrix, watchlist audit, report sections, runner wrapping, CLI, strict mode, and regression boundaries.

Modify:

- `src/b08_model_core/cli.py`
  - Add `experiment c-stage-c22` parser and execution branch.

- `src/b08_model_core/adapters/open_models/base.py`
  - Add optional versioned target metadata fields if needed by C2.2 report. Keep backward compatible defaults.

- `src/b08_model_core/adapters/open_models/chronos.py`
  - Ensure Chronos-2 primary target and Chronos-Bolt fallback are represented.

- `src/b08_model_core/adapters/open_models/timesfm.py`
  - Ensure TimesFM 2.5 target is represented.

- `src/b08_model_core/adapters/open_models/moirai_uni2ts.py`
  - Update target to Moirai 2.0 / current Uni2TS, with fallback notes if current runtime remains 1.x-shaped.

- `src/b08_model_core/adapters/open_models/moment.py`
  - Add representation/imputation target metadata if needed.

- `src/b08_model_core/adapters/open_models/units.py`
  - Add representation/imputation/multi-task target metadata if needed.

- `README.md`
  - Add final C2.2 CLI command and maintain offline/no-download boundary.

- `details.md`
  - Add C2.2 execution entry once implemented.

Do not modify:

- `data/**`
- `hf_cache/**`
- `reports/real_*.md`
- Existing C2/C2.1 behavior except for safe imports or helpers required by C2.2.

## Shared Names And Contracts

Use these exact names unless an implementation blocker is discovered:

- Config: `configs/c_stage_c22_open_model_executable_upgrade.yaml`
- Experiment module: `src/b08_model_core/experiments/c22_open_model_executable_upgrade.py`
- CLI: `uv run b08-model-core experiment c-stage-c22 --config ... --output ...`
- Report: `reports/c_stage_c22_open_model_executable_upgrade.md`
- Cache manifest: `reports/c_stage_c22_model_cache_manifest.md`
- Stage string: `C2_2_open_model_executable_upgrade`

Core model roles:

| model_id | role | target |
| --- | --- | --- |
| `ttm` | `anchor` | `ttm_current_local_adapter` |
| `chronos` | `priority_real_execution` | `chronos_2` |
| `timesfm` | `priority_real_execution` | `timesfm_2_5` |
| `moirai_uni2ts` | `core_run_review` | `moirai_2_0_current_uni2ts` |
| `moment` | `core_interface` | `moment_current_interface` |
| `units` | `core_interface` | `units_current_interface` |

Watchlist target ids:

```python
[
    "time_moe",
    "sundial",
    "timer_s1_timer_xl",
    "kairos",
    "toto",
    "ibm_flowstate_tspulse",
    "tabpfn_ts",
]
```

## Task 1: C2.2 Config, Loader, And Target Matrix

**Files:**

- Create: `configs/c_stage_c22_open_model_executable_upgrade.yaml`
- Create: `src/b08_model_core/experiments/c22_open_model_executable_upgrade.py`
- Create: `tests/test_c22_open_model_executable_upgrade.py`

- [ ] **Step 1: Write failing config tests**

Add to `tests/test_c22_open_model_executable_upgrade.py`:

```python
from pathlib import Path

import pytest

from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId
from b08_model_core.experiments.c22_open_model_executable_upgrade import (
    C22ConfigError,
    C22ModelRole,
    load_c22_config,
    build_c22_core_attempts,
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
    assert config.model_targets["moment"].tasks == (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION)
    assert config.model_targets["units"].tasks == (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION)


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
    config_path = tmp_path / "bad_c22.yaml"
    text = Path("configs/c_stage_c22_open_model_executable_upgrade.yaml").read_text(encoding="utf-8")
    config_path.write_text(
        text.replace("allow_download: false", "allow_download: true"),
        encoding="utf-8",
    )
    with pytest.raises(C22ConfigError, match="allow_download requires allow_network=true"):
        load_c22_config(config_path)
```

- [ ] **Step 2: Run focused test and verify it fails**

Run:

```bash
uv run python -m pytest tests/test_c22_open_model_executable_upgrade.py -q
```

Expected: FAIL because `c22_open_model_executable_upgrade` and config do not exist.

- [ ] **Step 3: Create default C2.2 config**

Create `configs/c_stage_c22_open_model_executable_upgrade.yaml` with:

```yaml
stage: C2_2_open_model_executable_upgrade
upstream_c21_config: configs/c_stage_c21_executable_open_model_evaluation.yaml
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
  timeout_seconds_per_model: 900
model_cache_policy:
  cache_dir: hf_cache
  reuse_existing_cache: true
  write_cache_manifest: true
model_targets:
  ttm:
    role: anchor
    target: ttm_current_local_adapter
    tasks: [forecasting]
  chronos:
    role: priority_real_execution
    target: chronos_2
    fallback: chronos_bolt
    tasks: [forecasting]
  timesfm:
    role: priority_real_execution
    target: timesfm_2_5
    tasks: [forecasting]
  moirai_uni2ts:
    role: core_run_review
    target: moirai_2_0_current_uni2ts
    fallback: moirai_1_x_interface
    tasks: [forecasting]
  moment:
    role: core_interface
    target: moment_current_interface
    tasks: [representation, imputation]
  units:
    role: core_interface
    target: units_current_interface
    tasks: [representation, imputation]
frontier_watchlist:
  audit_only: true
  promote_to_real_execution: false
  targets:
    - time_moe
    - sundial
    - timer_s1_timer_xl
    - kairos
    - toto
    - ibm_flowstate_tspulse
    - tabpfn_ts
outputs:
  report: reports/c_stage_c22_open_model_executable_upgrade.md
  cache_manifest: reports/c_stage_c22_model_cache_manifest.md
```

- [ ] **Step 4: Implement minimal config loader and matrix**

Create `src/b08_model_core/experiments/c22_open_model_executable_upgrade.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21ExecutionConfig,
    C21ModelTaskAttempt,
    C21TaskId,
)


class C22ConfigError(ValueError):
    pass


class C22ModelRole(StrEnum):
    ANCHOR = "anchor"
    PRIORITY_REAL_EXECUTION = "priority_real_execution"
    CORE_RUN_REVIEW = "core_run_review"
    CORE_INTERFACE = "core_interface"


@dataclass(frozen=True)
class C22ModelTarget:
    model_id: str
    role: C22ModelRole
    target: str
    tasks: tuple[C21TaskId, ...]
    fallback: str | None = None


@dataclass(frozen=True)
class C22WatchlistConfig:
    audit_only: bool
    promote_to_real_execution: bool
    targets: tuple[str, ...]


@dataclass
class C22ExecutionConfig:
    stage: str
    upstream_c21_config: Path
    dataset_path: Path
    fu13_config_path: Path
    dataset_boundary: str
    window_mode: str
    context_length: int
    prediction_length: int
    max_windows: int
    mask_ratio: float
    seed: int
    allow_network: bool
    allow_download: bool
    strict_model_success: bool
    record_failure: bool
    do_not_over_claim: bool
    continue_on_model_failure: bool
    timeout_seconds_per_model: float
    cache_dir: Path
    reuse_existing_cache: bool
    write_cache_manifest: bool
    model_targets: dict[str, C22ModelTarget]
    frontier_watchlist: C22WatchlistConfig
    report_path: Path
    cache_manifest_path: Path


def load_c22_config(path: str | Path) -> C22ExecutionConfig:
    raw = _load_mapping(Path(path))
    stage = _required_string(raw, "stage")
    if stage != "C2_2_open_model_executable_upgrade":
        raise C22ConfigError("C2.2 stage must be C2_2_open_model_executable_upgrade")
    execution_policy = _load_mapping(raw, "execution_policy")
    model_cache_policy = _load_mapping(raw, "model_cache_policy")
    allow_network = _required_bool(execution_policy, "allow_network")
    allow_download = _required_bool(execution_policy, "allow_download")
    if allow_download and not allow_network:
        raise C22ConfigError("allow_download requires allow_network=true")
    dataset = _load_mapping(raw, "dataset")
    window = _load_mapping(raw, "window")
    outputs = _load_mapping(raw, "outputs")
    return C22ExecutionConfig(
        stage=stage,
        upstream_c21_config=Path(_required_string(raw, "upstream_c21_config")),
        dataset_path=Path(_required_string(dataset, "fu13_observations")),
        fu13_config_path=Path(_required_string(dataset, "fu13_config")),
        dataset_boundary=_required_string(dataset, "boundary"),
        window_mode=_required_string(window, "window_mode"),
        context_length=_positive_int(window, "context_length"),
        prediction_length=_positive_int(window, "prediction_length"),
        max_windows=_positive_int(window, "max_windows"),
        mask_ratio=float(window["mask_ratio"]),
        seed=int(window["seed"]),
        allow_network=allow_network,
        allow_download=allow_download,
        strict_model_success=_required_bool(execution_policy, "strict_model_success"),
        record_failure=_required_bool(execution_policy, "record_failure"),
        do_not_over_claim=_required_bool(execution_policy, "do_not_over_claim"),
        continue_on_model_failure=_required_bool(execution_policy, "continue_on_model_failure"),
        timeout_seconds_per_model=float(execution_policy["timeout_seconds_per_model"]),
        cache_dir=Path(_required_string(model_cache_policy, "cache_dir")),
        reuse_existing_cache=_required_bool(model_cache_policy, "reuse_existing_cache"),
        write_cache_manifest=_required_bool(model_cache_policy, "write_cache_manifest"),
        model_targets=_load_model_targets(_load_mapping(raw, "model_targets")),
        frontier_watchlist=_load_watchlist(_load_mapping(raw, "frontier_watchlist")),
        report_path=Path(_required_string(outputs, "report")),
        cache_manifest_path=Path(_required_string(outputs, "cache_manifest")),
    )


def build_c22_core_attempts(config: C22ExecutionConfig) -> list[C21ModelTaskAttempt]:
    return [
        C21ModelTaskAttempt(model_id=model_id, task_id=task_id)
        for model_id, target in config.model_targets.items()
        for task_id in target.tasks
    ]
```

Also add private helper functions `_load_mapping`, `_required_string`, `_required_bool`, `_positive_int`, `_load_model_targets`, and `_load_watchlist`. Keep them small and follow the validation style in C2.1.

- [ ] **Step 5: Run focused tests and verify they pass**

Run:

```bash
uv run python -m pytest tests/test_c22_open_model_executable_upgrade.py -q
```

Expected: PASS for the config/target tests added in this task.

- [ ] **Step 6: Commit Task 1**

Run:

```bash
git add configs/c_stage_c22_open_model_executable_upgrade.yaml \
  src/b08_model_core/experiments/c22_open_model_executable_upgrade.py \
  tests/test_c22_open_model_executable_upgrade.py
git commit -m "feat: add c22 config and target matrix"
```

## Task 2: Frontier Watchlist Audit And C2.2 Report Renderer

**Files:**

- Modify: `src/b08_model_core/experiments/c22_open_model_executable_upgrade.py`
- Modify: `tests/test_c22_open_model_executable_upgrade.py`

- [ ] **Step 1: Write failing watchlist and report tests**

Append tests:

```python
from b08_model_core.experiments.c22_open_model_executable_upgrade import (
    C22RunResult,
    build_frontier_watchlist_audit,
    render_c22_cache_manifest,
    render_c22_report,
)


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
        target_results=[],
        watchlist_audit=[],
        invalid_claims=[],
    )
    text = render_c22_cache_manifest(result)
    assert "network_allowed" in text
    assert "download_allowed" in text
    assert "cache_dir" in text
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c22_open_model_executable_upgrade.py -q
```

Expected: FAIL because watchlist audit, run result, and render functions do not exist.

- [ ] **Step 3: Implement watchlist audit dataclass and builder**

Add to `c22_open_model_executable_upgrade.py`:

```python
from dataclasses import field


@dataclass(frozen=True)
class C22FrontierWatchlistAudit:
    model_or_route: str
    latest_known_version_or_paper: str
    primary_tasks: tuple[str, ...]
    repository_or_model_card: str
    package_availability: str
    weight_availability: str
    license_status: str
    resource_requirement: str
    input_output_fit: str
    fu13_task_fit: str
    status: str
    default_c22_action: str
    promotion_condition: str


@dataclass
class C22TargetResult:
    model_id: str
    role: C22ModelRole
    target: str
    fallback: str | None
    task_id: C21TaskId
    status: Any
    metrics: dict[str, Any] = field(default_factory=dict)
    baseline_metrics: dict[str, Any] = field(default_factory=dict)
    failure_stage: str = ""
    failure_reason: str = ""
    dependency_status: str = ""
    weight_status: str = ""
    adapter_name: str = ""
    model_ref: str | None = None
    runtime_seconds: float | None = None
    target_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class C22RunResult:
    run_id: str
    config_path: str | Path
    upstream_c21_config: str | Path
    dataset_boundary: str
    config_allows_network: bool
    config_allows_download: bool
    cache_dir: str | Path
    tested_windows: int
    target_results: list[C22TargetResult]
    watchlist_audit: list[C22FrontierWatchlistAudit]
    invalid_claims: list[str]
    c3_handoff_notes: list[str] = field(default_factory=lambda: [
        "C2.2 promotes only models with executable evidence or clear promotion conditions to C3.",
        "Watchlist audit entries require re-check before cross-dataset validation.",
    ])
    b_decision_notes: list[str] = field(default_factory=lambda: [
        "C2.2 is not a B-stage self-training Go decision.",
        "Model failures must be interpreted as dependency/weight/interface/task/resource evidence before capability claims.",
    ])
```

Implement `build_frontier_watchlist_audit(config)` using a static dictionary for the seven target ids. Keep values concise and stable. For unknown ids, return a `needs_research_review` record instead of failing unless config validation already blocks unknown ids.

- [ ] **Step 4: Implement report and cache manifest renderers**

Add:

```python
def render_c22_report(result: C22RunResult, config: C22ExecutionConfig) -> str:
    ...


def render_c22_cache_manifest(result: C22RunResult) -> str:
    ...
```

Required sections:

- `# C2.2 Open Model Executable Evaluation Upgrade Report`
- `## Report Metadata`
- `## Executive Summary`
- `## Versioned Model Target Matrix`
- `## Priority Real Execution Results`
- `## Core Model-Task Result Matrix`
- `## Frontier Watchlist Audit`
- `## Failure Taxonomy`
- `## Cache / Download Manifest`
- `## C2.2 -> C3 Handoff`
- `## C2.2 -> B Decision Notes`
- `## Invalid Claims`

Use small `_cell()` / `_value()` helpers patterned after C2.1 to keep Markdown table output stable.

- [ ] **Step 5: Run focused tests and verify they pass**

Run:

```bash
uv run python -m pytest tests/test_c22_open_model_executable_upgrade.py -q
```

Expected: PASS for Tasks 1-2 tests.

- [ ] **Step 6: Commit Task 2**

Run:

```bash
git add src/b08_model_core/experiments/c22_open_model_executable_upgrade.py \
  tests/test_c22_open_model_executable_upgrade.py
git commit -m "feat: add c22 watchlist audit report"
```

## Task 3: C2.2 Runner Wrapper And C2.1 Result Integration

**Files:**

- Modify: `src/b08_model_core/experiments/c22_open_model_executable_upgrade.py`
- Modify: `tests/test_c22_open_model_executable_upgrade.py`

- [ ] **Step 1: Write failing runner integration tests**

Append tests:

```python
from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus
from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21ModelTaskResult,
    C21RunResult,
)
from b08_model_core.experiments.c22_open_model_executable_upgrade import (
    run_c22_open_model_executable_upgrade,
)


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
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c22_open_model_executable_upgrade.py -q
```

Expected: FAIL because `run_c22_open_model_executable_upgrade` does not exist.

- [ ] **Step 3: Implement C2.1 bridge config**

Add function:

```python
def build_c21_config_from_c22(config: C22ExecutionConfig) -> C21ExecutionConfig:
    return C21ExecutionConfig(
        stage="C2_1_executable_open_model_evaluation",
        upstream_c2_config=Path("configs/c_stage_c2_open_model_evaluation.yaml"),
        dataset_path=config.dataset_path,
        fu13_config_path=config.fu13_config_path,
        dataset_boundary=config.dataset_boundary,
        window_mode=config.window_mode,
        context_length=config.context_length,
        prediction_length=config.prediction_length,
        max_windows=config.max_windows,
        mask_ratio=config.mask_ratio,
        seed=config.seed,
        allow_network=config.allow_network,
        allow_download=config.allow_download,
        strict_model_success=config.strict_model_success,
        record_failure=config.record_failure,
        do_not_over_claim=config.do_not_over_claim,
        continue_on_model_failure=config.continue_on_model_failure,
        timeout_seconds_per_model=config.timeout_seconds_per_model,
        cache_dir=config.cache_dir,
        reuse_existing_cache=config.reuse_existing_cache,
        write_cache_manifest=config.write_cache_manifest,
        report_path=config.report_path,
        cache_manifest_path=config.cache_manifest_path,
    )
```

If C2.1 later exposes upstream C2 config from its own loader, prefer that. For now, keep the bridge explicit and tested.

- [ ] **Step 4: Implement runner wrapper**

Add:

```python
def run_c22_open_model_executable_upgrade(
    config: C22ExecutionConfig | str | Path,
    *,
    adapter_factory: Any = None,
    c21_runner: Any = None,
) -> C22RunResult:
    ...
```

Behavior:

- Load config if path is provided.
- Build a C2.1 config from C2.2.
- Use `c21_runner` injection when provided; otherwise call `run_c21_executable_evaluation`.
- Pass through `adapter_factory`.
- Convert C2.1 task results into `C22TargetResult` using `config.model_targets`.
- Add target metadata for:
  - `target_model_ref`
  - `fallback_model_ref`
  - `target_package_hint`
  - `target_task_fit`
  - `target_resource_note`
  - `target_license_note`
- Build watchlist audit.
- Return a `C22RunResult`.

Add `has_priority_or_core_failure` property or helper if needed for CLI strict mode. It should consider target results for anchor, priority, core run/review, and core interface roles. Watchlist audit-only entries must not cause strict failure.

- [ ] **Step 5: Run focused tests and verify they pass**

Run:

```bash
uv run python -m pytest tests/test_c22_open_model_executable_upgrade.py -q
```

Expected: PASS for Tasks 1-3 tests.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
git add src/b08_model_core/experiments/c22_open_model_executable_upgrade.py \
  tests/test_c22_open_model_executable_upgrade.py
git commit -m "feat: wrap c21 results for c22"
```

## Task 4: C2.2 CLI Entry And Default Report Writing

**Files:**

- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_c22_open_model_executable_upgrade.py`

- [ ] **Step 1: Write failing CLI tests**

Append helper and tests:

```python
import pandas as pd
from b08_model_core.cli import main


def _write_c22_fixture_config(tmp_path, strict_model_success=False):
    config_text = Path("configs/c_stage_c22_open_model_executable_upgrade.yaml").read_text(
        encoding="utf-8"
    )
    config_text = config_text.replace(
        "data/processed/fu13_real_observations.parquet",
        str(tmp_path / "observations.parquet"),
    )
    config_text = config_text.replace(
        "reports/c_stage_c22_open_model_executable_upgrade.md",
        str(tmp_path / "c22.md"),
    )
    config_text = config_text.replace(
        "reports/c_stage_c22_model_cache_manifest.md",
        str(tmp_path / "c22_cache_manifest.md"),
    )
    config_text = config_text.replace(
        "strict_model_success: false",
        f"strict_model_success: {str(strict_model_success).lower()}",
    )
    (tmp_path / "c22_fixture.yaml").write_text(config_text, encoding="utf-8")


def _write_fixture_observations(path):
    rows = []
    for t in range(120):
        for sensor in ["LeakElec", "Temp"]:
            rows.append(
                {
                    "timestamp": pd.Timestamp("2026-01-01") + pd.Timedelta(minutes=t),
                    "device_id": "FU13",
                    "batch_id": "cycle_1",
                    "stage": "melt",
                    "sensor_id": sensor,
                    "value": float(t),
                    "unit": "a.u.",
                    "domain": "test",
                    "quality_flag": "good",
                    "degradation_label": "normal",
                    "failure_proxy": "",
                }
            )
    pd.DataFrame(rows).to_parquet(path, index=False)


def test_cli_c_stage_c22_writes_report_and_cache_manifest(tmp_path):
    _write_c22_fixture_config(tmp_path, strict_model_success=False)
    _write_fixture_observations(tmp_path / "observations.parquet")
    output = tmp_path / "c22.md"
    exit_code = main(
        [
            "experiment",
            "c-stage-c22",
            "--config",
            str(tmp_path / "c22_fixture.yaml"),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "C2.2 Open Model Executable Evaluation Upgrade Report" in text
    assert "Versioned Model Target Matrix" in text
    assert "Frontier Watchlist Audit" in text
    assert "- config_allows_network: false" in text
    assert "- config_allows_download: false" in text
    cache_manifest = (tmp_path / "c22_cache_manifest.md").read_text(encoding="utf-8")
    assert "download_allowed" in cache_manifest


def test_cli_c_stage_c22_strict_mode_returns_nonzero_but_writes_report(tmp_path):
    _write_c22_fixture_config(tmp_path, strict_model_success=True)
    _write_fixture_observations(tmp_path / "observations.parquet")
    output = tmp_path / "c22.md"
    exit_code = main(
        [
            "experiment",
            "c-stage-c22",
            "--config",
            str(tmp_path / "c22_fixture.yaml"),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 1
    assert output.exists()
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c22_open_model_executable_upgrade.py -q
```

Expected: FAIL because CLI does not recognize `c-stage-c22`.

- [ ] **Step 3: Add CLI imports and parser branch**

Modify `src/b08_model_core/cli.py`:

- Import:

```python
from b08_model_core.experiments.c22_open_model_executable_upgrade import (
    load_c22_config,
    render_c22_cache_manifest,
    render_c22_report,
    run_c22_open_model_executable_upgrade,
)
```

- Add parser:

```python
c_stage_c22 = experiment_sub.add_parser("c-stage-c22")
c_stage_c22.add_argument("--config", required=True)
c_stage_c22.add_argument("--output", required=True)
```

- Add branch after C2.1:

```python
if args.command == "experiment" and args.experiment_command == "c-stage-c22":
    try:
        from b08_model_core.adapters.open_models import build_open_model_adapter

        config = load_c22_config(args.config)
        config.report_path = Path(args.output)
        result = run_c22_open_model_executable_upgrade(
            config,
            adapter_factory=build_open_model_adapter,
        )
        result.config_path = args.config
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_c22_report(result, config), encoding="utf-8")
        if config.write_cache_manifest:
            config.cache_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            config.cache_manifest_path.write_text(
                render_c22_cache_manifest(result),
                encoding="utf-8",
            )
    except (FileNotFoundError, ValueError, OSError, PermissionError):
        return 1
    if config.strict_model_success and result.has_priority_or_core_failure:
        return 1
    return 0
```

- [ ] **Step 4: Run CLI-focused tests and verify they pass**

Run:

```bash
uv run python -m pytest tests/test_c22_open_model_executable_upgrade.py -q
```

Expected: PASS.

- [ ] **Step 5: Run C2/C2.1 regression CLI tests**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py tests/test_c2_open_model_evaluation.py -q
```

Expected: PASS. If `tests/test_c2_open_model_evaluation.py` does not exist, run:

```bash
uv run python -m pytest tests -k "c2 or c21" -q
```

Expected: PASS for available C2/C2.1 tests.

- [ ] **Step 6: Commit Task 4**

Run:

```bash
git add src/b08_model_core/cli.py tests/test_c22_open_model_executable_upgrade.py
git commit -m "feat: add c22 experiment cli"
```

## Task 5: Versioned Adapter Metadata

**Files:**

- Modify: `src/b08_model_core/adapters/open_models/base.py`
- Modify: `src/b08_model_core/adapters/open_models/chronos.py`
- Modify: `src/b08_model_core/adapters/open_models/timesfm.py`
- Modify: `src/b08_model_core/adapters/open_models/moirai_uni2ts.py`
- Modify: `src/b08_model_core/adapters/open_models/moment.py`
- Modify: `src/b08_model_core/adapters/open_models/units.py`
- Modify: `tests/test_open_model_adapters.py`
- Modify: `tests/test_c22_open_model_executable_upgrade.py` if C2.2 uses adapter metadata helper directly.

- [ ] **Step 1: Write failing adapter metadata tests**

Add to `tests/test_open_model_adapters.py`:

```python
def test_chronos_adapter_declares_chronos2_primary_and_bolt_fallback():
    adapter = ChronosOpenModelAdapter()
    assert adapter.model_ref == "amazon/chronos-2"
    assert adapter.target_model_ref == "amazon/chronos-2"
    assert adapter.fallback_model_ref == "amazon/chronos-bolt-base"
    assert "chronos" in adapter.target_package_hint
    assert "forecasting" in adapter.target_task_fit


def test_timesfm_adapter_declares_timesfm25_target():
    adapter = TimesFMOpenModelAdapter()
    assert adapter.model_ref == "google/timesfm-2.5-200m-pytorch"
    assert adapter.target_model_ref == "google/timesfm-2.5-200m-pytorch"
    assert adapter.fallback_model_ref is None
    assert "timesfm" in adapter.target_package_hint


def test_moirai_adapter_declares_moirai20_target_and_license_note():
    adapter = MoiraiUni2TSOpenModelAdapter()
    assert adapter.model_ref == "Salesforce/moirai-2.0-R-small"
    assert adapter.target_model_ref == "Salesforce/moirai-2.0-R-small"
    assert adapter.fallback_model_ref == "Salesforce/moirai-1.1-R-small"
    assert "uni2ts" in adapter.target_package_hint
    assert "license" in adapter.target_license_note.lower()


def test_moment_and_units_adapters_declare_interface_targets():
    moment = MomentOpenModelAdapter()
    units = UniTSOpenModelAdapter()
    assert "representation" in moment.target_task_fit
    assert "imputation" in moment.target_task_fit
    assert "representation" in units.target_task_fit
    assert "imputation" in units.target_task_fit
```

- [ ] **Step 2: Run adapter tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: FAIL because metadata fields are missing or Moirai still points to 1.1.

- [ ] **Step 3: Add backward-compatible metadata fields**

Modify `OpenModelAdapter` in `base.py`:

```python
class OpenModelAdapter:
    model_id = ""
    supported_tasks: tuple[C21TaskId, ...] = ()
    target_model_ref: str | None = None
    fallback_model_ref: str | None = None
    target_package_hint = ""
    target_license_note = ""
    target_resource_note = ""
    target_task_fit = ""
```

Do not require subclasses to set these fields.

- [ ] **Step 4: Update concrete adapter classes**

Set these minimum values:

```python
# chronos.py
model_ref = "amazon/chronos-2"
target_model_ref = "amazon/chronos-2"
fallback_model_ref = "amazon/chronos-bolt-base"
target_package_hint = "chronos-forecasting / chronos package"
target_task_fit = "forecasting"
target_resource_note = "depends on selected Chronos-2 or Chronos-Bolt model size"
target_license_note = "check official model card before promotion"
```

```python
# timesfm.py
model_ref = "google/timesfm-2.5-200m-pytorch"
target_model_ref = "google/timesfm-2.5-200m-pytorch"
fallback_model_ref = None
target_package_hint = "timesfm"
target_task_fit = "forecasting"
target_resource_note = "TimesFM 2.5 200M PyTorch local runtime required"
target_license_note = "check official model card before promotion"
```

```python
# moirai_uni2ts.py
model_ref = "Salesforce/moirai-2.0-R-small"
target_model_ref = "Salesforce/moirai-2.0-R-small"
fallback_model_ref = "Salesforce/moirai-1.1-R-small"
target_package_hint = "uni2ts"
target_task_fit = "probabilistic forecasting"
target_resource_note = "Uni2TS runtime and Moirai model weights required"
target_license_note = "license requires review before promotion"
```

For MOMENT and UniTS, keep current model refs if already present, but set `target_task_fit` to include representation and imputation.

- [ ] **Step 5: Ensure C2.2 runner uses adapter metadata when available**

In `run_c22_open_model_executable_upgrade`, when building `target_metadata`, prefer adapter metadata if available in C2.1 result or by instantiating `adapter_factory(model_id)` safely. If no adapter is available, fall back to static config target/fallback.

Minimum target metadata keys must include:

```python
{
    "target_model_ref": "...",
    "fallback_model_ref": "...",
    "target_package_hint": "...",
    "target_task_fit": "...",
    "target_resource_note": "...",
    "target_license_note": "...",
}
```

- [ ] **Step 6: Run adapter and C2.2 tests**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py tests/test_c22_open_model_executable_upgrade.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

Run:

```bash
git add src/b08_model_core/adapters/open_models/base.py \
  src/b08_model_core/adapters/open_models/chronos.py \
  src/b08_model_core/adapters/open_models/timesfm.py \
  src/b08_model_core/adapters/open_models/moirai_uni2ts.py \
  src/b08_model_core/adapters/open_models/moment.py \
  src/b08_model_core/adapters/open_models/units.py \
  tests/test_open_model_adapters.py \
  tests/test_c22_open_model_executable_upgrade.py
git commit -m "feat: add c22 versioned adapter metadata"
```

## Task 6: README, Details, And Full Verification

**Files:**

- Modify: `README.md`
- Modify: `details.md`
- Modify: `tests/test_c22_open_model_executable_upgrade.py` if a documentation consistency test is useful.

- [ ] **Step 1: Update README command section**

In `README.md`, update the C2.2 section to include the actual command:

```bash
uv run b08-model-core experiment c-stage-c22 \
  --config configs/c_stage_c22_open_model_executable_upgrade.yaml \
  --output reports/c_stage_c22_open_model_executable_upgrade.md
```

Keep the text that says default C2.2 is offline/no-download and watchlist is audit-only.

- [ ] **Step 2: Update details stage ledger**

In `details.md`, add a new 2026-06-08 row in the recent ledger:

```markdown
| 2026-06-08 | C2.2 升级版开源模型真实执行与审计进入实现入口：新增默认离线安全配置 `configs/c_stage_c22_open_model_executable_upgrade.yaml`、CLI `experiment c-stage-c22`、版本化核心模型目标矩阵和 frontier watchlist audit；默认不联网、不下载权重，真实执行只通过显式 opt-in 配置进入。 |
```

Update the “下一阶段计划” wording if needed so it says C2.2 has an implementation entry, not only a proposed plan.

- [ ] **Step 3: Run C2.2 focused tests**

Run:

```bash
uv run python -m pytest tests/test_c22_open_model_executable_upgrade.py -q
```

Expected: PASS.

- [ ] **Step 4: Run open model adapter tests**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: PASS.

- [ ] **Step 5: Run C2/C2.1 regression tests**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py -q
```

Expected: PASS.

Then run available C2 tests:

```bash
uv run python -m pytest tests -k "c2_open_model or c_stage_c2 or c21 or c22" -q
```

Expected: PASS for selected tests.

- [ ] **Step 6: Run full test suite**

Run:

```bash
uv run python -m pytest -q
```

Expected: PASS. If failures occur, apply `superpowers:systematic-debugging` before fixing.

- [ ] **Step 7: Inspect git status and ignored outputs**

Run:

```bash
git status --short --branch
git diff --check
```

Expected:

- Only intended source/config/test/docs changes are present.
- No `data/real/`, `data/processed/*.parquet`, `hf_cache/`, `reports/real_*.md`, model cache, or downloaded weights are staged.
- `git diff --check` has no output.

- [ ] **Step 8: Commit Task 6**

Run:

```bash
git add README.md details.md tests/test_c22_open_model_executable_upgrade.py
git commit -m "docs: document c22 executable upgrade workflow"
```

If tests or source files required final fixes, include only those directly related files in the commit and mention the test command in the commit body if useful.

## Final Review And Branch Completion

After all tasks are complete:

- Run the full verification commands from Task 6 again if any review fixes changed code.
- Dispatch final code review per `superpowers:subagent-driven-development`.
- Use `superpowers:finishing-a-development-branch` to decide PR/merge/cleanup path.

Do not mark the implementation complete until:

- C2.2 CLI writes report and cache manifest.
- Default C2.2 config is offline/no-download.
- Watchlist audit exists and is audit-only.
- C2 and C2.1 regression tests pass.
- Full test suite passes or any inability to run it is explicitly documented with reason.
