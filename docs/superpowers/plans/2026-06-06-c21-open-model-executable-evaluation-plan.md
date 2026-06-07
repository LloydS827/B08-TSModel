# C2.1 Open Model Executable Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 C2.1 开源模型真实执行评测闭环，让 TTM、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、MOMENT、UniTS 六个核心模型在统一 adapter contract、统一 FU13 窗口、统一指标和统一报告口径下进入真实执行尝试。

**Architecture:** 新增 `c21_executable_open_model_evaluation` 窄实验模块，复用 C2 六模型 registry 和现有窗口 / baseline 能力；新增 `adapters/open_models/` 保存最小 adapter contract 与六模型 adapter。默认配置离线安全，真实联网下载只通过 opt-in 配置或显式 override 进入；模型失败结构化记录，不破坏默认 workflow。

**Tech Stack:** Python 3.11, pandas, numpy, PyYAML, pytest, existing `b08_model_core` modules, optional open model dependencies, Markdown reports.

---

## Scope Guard

本计划实现已批准规格：

`docs/superpowers/specs/2026-06-06-c21-open-model-executable-evaluation-design.md`

必须做到：

- 六个核心模型都进入 C2.1 registry、adapter readiness table 和 model-task result matrix。
- 每个核心模型都完成声明的 C2.1 主任务真实执行尝试：
  - TTM: forecasting
  - Chronos / Chronos-Bolt: forecasting
  - TimesFM: forecasting
  - Moirai / Uni2TS: forecasting
  - MOMENT: representation 与 imputation
  - UniTS: representation 与 imputation
- 默认配置 `configs/c_stage_c21_executable_open_model_evaluation.yaml` 必须保持 `allow_network: false` 和 `allow_download: false`。
- 允许本机 opt-in 联网执行，但默认 pytest、默认 CLI 文档和默认配置不能依赖联网、外部权重或本机 cache。
- `timeout_seconds_per_model` 在实现中按 **每个 model-task attempt** 执行；报告字段仍可写 `timeout_seconds_per_model` 以保持 spec 名称，但 tests 要覆盖真实超时 enforcement，而不是只捕获 adapter 自己抛出的 `TimeoutError`。
- C2 status-only 入口 `experiment c-stage-c2` 继续可用。

必须避免：

- 不接入 C3 公开数据集。
- 不进入 B 阶段自研训练。
- 不做生产告警、RUL、自动维修建议或模型选型终局结论。
- 不把外部模型权重、cache 或私有本机路径提交到 Git。
- 不用 fake success 替代真实 adapter attempt；测试 fake adapter 只用于 runner 行为验证。

## File Structure

Create:

- `configs/c_stage_c21_executable_open_model_evaluation.yaml`
  - 默认离线安全 C2.1 配置。引用 C2 配置、FU13 数据路径、窗口参数、六模型主任务矩阵、cache/no-network 策略和输出报告路径。

- `src/b08_model_core/adapters/open_models/__init__.py`
  - 导出 C2.1 adapter contract 与 factory。

- `src/b08_model_core/adapters/open_models/base.py`
  - Adapter context、readiness、task output、error/result dataclasses、base adapter class、failure helpers。

- `src/b08_model_core/adapters/open_models/ttm.py`
  - TTM forecasting adapter；尽量复用现有 TTM adapter / real-data forecasting 路径。

- `src/b08_model_core/adapters/open_models/chronos.py`
  - Chronos / Chronos-Bolt forecasting adapter；依赖缺失或接口不匹配时结构化失败。

- `src/b08_model_core/adapters/open_models/timesfm.py`
  - TimesFM forecasting adapter；依赖缺失或接口不匹配时结构化失败。

- `src/b08_model_core/adapters/open_models/moirai_uni2ts.py`
  - Moirai / Uni2TS probabilistic forecasting adapter；依赖缺失或接口不匹配时结构化失败。

- `src/b08_model_core/adapters/open_models/moment.py`
  - MOMENT representation / imputation adapter；依赖缺失或接口不匹配时结构化失败。

- `src/b08_model_core/adapters/open_models/units.py`
  - UniTS representation / imputation adapter；依赖缺失或接口不匹配时结构化失败。

- `src/b08_model_core/experiments/c21_executable_open_model_evaluation.py`
  - C2.1 config loader、task matrix、runner、baseline builders、result schema、cache manifest、report renderer。

- `tests/test_c21_executable_open_model_evaluation.py`
  - C2.1 config、task matrix、runner、report、CLI、strict mode、offline default、failure isolation tests。

- `tests/test_open_model_adapters.py`
  - Adapter contract、factory、fake adapters、dependency failure and unsupported task behavior tests。

Modify:

- `src/b08_model_core/cli.py`
  - 增加 `uv run b08-model-core experiment c-stage-c21 --config configs/c_stage_c21_executable_open_model_evaluation.yaml --output reports/c_stage_c21_executable_open_model_evaluation.md`。

- `pyproject.toml`
  - 只在核对包名后新增 optional extras；不得把开源模型依赖加入默认 dependencies。若包名或版本无法稳定解析，本轮只保留 adapter dependency checks，不新增对应 extra。

- `README.md`
  - 增加 C2.1 命令和边界说明：默认离线、联网 opt-in、失败结构化、不代表生产能力。

- `details.md`
  - 增加 2026-06-06 C2.1 计划 / 执行入口台账行。

Do not modify:

- `docs/research/**`，除非实现后有单独文档入口任务。
- `data/**`
- `hf_cache/**`
- `reports/real_*.md`
- C2 status-only 行为，除非为复用 registry 做向后兼容的小型 helper。

## Shared Contracts

### C2.1 Primary Task Matrix

Tests must encode this matrix exactly:

| model_id | required C2.1 attempts |
| --- | --- |
| `ttm` | `forecasting` |
| `chronos` | `forecasting` |
| `timesfm` | `forecasting` |
| `moirai_uni2ts` | `forecasting` |
| `moment` | `representation`, `imputation` |
| `units` | `representation`, `imputation` |

Default success is attempt completeness plus report generation, not all models succeeding. Strict success is every required attempt status equals `available_and_ran`.

### C2.1 Status Semantics

Use these model-task statuses:

| status | meaning |
| --- | --- |
| `available_and_ran` | adapter 真实执行成功，并输出可计算指标 |
| `missing_dependency` | Python 包或运行时依赖缺失 |
| `missing_or_blocked_weights` | 权重缺失、下载被禁用、下载失败或 cache 不可用 |
| `unsupported_task` | adapter 或官方接口不支持当前任务 |
| `unsupported_window_shape` | 当前窗口、变量数、horizon、mask 或 token 形式不被模型支持 |
| `runtime_failed` | 真实执行时出现异常，已捕获并记录 |
| `timeout` | 单个 model-task attempt 超过 `timeout_seconds_per_model` |
| `license_or_interface_needs_review` | 许可证或官方接口边界不足以安全执行 |
| `skipped_by_config` | 配置主动跳过；核心模型主任务默认不应出现 |

## Task 1: C2.1 Config, Loader, And Primary Task Matrix

**Files:**

- Create: `configs/c_stage_c21_executable_open_model_evaluation.yaml`
- Create: `src/b08_model_core/experiments/c21_executable_open_model_evaluation.py`
- Create: `tests/test_c21_executable_open_model_evaluation.py`

- [ ] **Step 1: Write failing config and task matrix tests**

Add tests:

```python
from pathlib import Path

from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21TaskId,
    REQUIRED_C21_TASKS,
    load_c21_executable_config,
    build_c21_attempts,
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
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py -q
```

Expected: FAIL because `c21_executable_open_model_evaluation` and config do not exist.

- [ ] **Step 3: Create default C2.1 config**

Create `configs/c_stage_c21_executable_open_model_evaluation.yaml`:

```yaml
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
  timeout_seconds_per_model: 900
model_cache_policy:
  cache_dir: hf_cache
  reuse_existing_cache: true
  write_cache_manifest: true
outputs:
  report: reports/c_stage_c21_executable_open_model_evaluation.md
  cache_manifest: reports/c_stage_c21_model_cache_manifest.md
```

- [ ] **Step 4: Implement minimal config loader and task matrix**

Create `src/b08_model_core/experiments/c21_executable_open_model_evaluation.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class C21ConfigError(ValueError):
    pass


class C21TaskId(StrEnum):
    FORECASTING = "forecasting"
    REPRESENTATION = "representation"
    IMPUTATION = "imputation"


REQUIRED_C21_TASKS = {
    "ttm": (C21TaskId.FORECASTING,),
    "chronos": (C21TaskId.FORECASTING,),
    "timesfm": (C21TaskId.FORECASTING,),
    "moirai_uni2ts": (C21TaskId.FORECASTING,),
    "moment": (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION),
    "units": (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION),
}


@dataclass
class C21ExecutionConfig:
    stage: str
    upstream_c2_config: Path
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
    cache_dir: str | None
    reuse_existing_cache: bool
    write_cache_manifest: bool
    report_path: Path
    cache_manifest_path: Path


@dataclass(frozen=True)
class C21ModelTaskAttempt:
    model_id: str
    task_id: C21TaskId


def load_c21_executable_config(path: str | Path) -> C21ExecutionConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise C21ConfigError("C2.1 config must be a mapping")
    dataset = _load_mapping(raw, "dataset")
    window = _load_mapping(raw, "window")
    policy = _load_mapping(raw, "execution_policy")
    cache = _load_mapping(raw, "model_cache_policy")
    outputs = _load_mapping(raw, "outputs")
    stage = _load_required_string(raw, "stage")
    if stage != "C2_1_executable_open_model_evaluation":
        raise C21ConfigError("C2.1 stage must be C2_1_executable_open_model_evaluation")
    return C21ExecutionConfig(
        stage=stage,
        upstream_c2_config=Path(_load_required_string(raw, "upstream_c2_config")),
        dataset_path=Path(_load_required_string(dataset, "fu13_observations")),
        fu13_config_path=Path(_load_required_string(dataset, "fu13_config")),
        dataset_boundary=_load_required_string(dataset, "boundary"),
        window_mode=_load_window_mode(window),
        context_length=_load_positive_int(window, "context_length"),
        prediction_length=_load_positive_int(window, "prediction_length"),
        max_windows=_load_positive_int(window, "max_windows"),
        mask_ratio=_load_mask_ratio(window, "mask_ratio"),
        seed=_load_nonnegative_int(window, "seed"),
        allow_network=_load_bool(policy, "allow_network", False),
        allow_download=_load_bool(policy, "allow_download", False),
        strict_model_success=_load_bool(policy, "strict_model_success", False),
        record_failure=_load_bool(policy, "record_failure", True),
        do_not_over_claim=_load_bool(policy, "do_not_over_claim", True),
        continue_on_model_failure=_load_bool(policy, "continue_on_model_failure", True),
        timeout_seconds_per_model=_load_positive_number(policy, "timeout_seconds_per_model"),
        cache_dir=cache.get("cache_dir"),
        reuse_existing_cache=_load_bool(cache, "reuse_existing_cache", True),
        write_cache_manifest=_load_bool(cache, "write_cache_manifest", True),
        report_path=Path(_load_required_string(outputs, "report")),
        cache_manifest_path=Path(_load_required_string(outputs, "cache_manifest")),
    )


def build_c21_attempts(config: C21ExecutionConfig) -> list[C21ModelTaskAttempt]:
    return [
        C21ModelTaskAttempt(model_id=model_id, task_id=task_id)
        for model_id, task_ids in REQUIRED_C21_TASKS.items()
        for task_id in task_ids
    ]
```

Implementation notes:

- Add `_load_mapping`, `_load_required_string`, `_load_window_mode`, `_load_positive_int`, `_load_nonnegative_int`, `_load_positive_number`, `_load_mask_ratio`, and `_load_bool` helpers, following the defensive style in `c2_open_model_evaluation.py`.
- Validate `window_mode` is `stage-local` or `cross-stage`.
- Validate positive `context_length`, `prediction_length`, `max_windows`, and positive numeric `timeout_seconds_per_model`.
- Validate `mask_ratio` is in `(0, 1]`.
- Keep paths relative as configured.

- [ ] **Step 5: Run focused tests and verify they pass**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py -q
```

Expected: PASS for Task 1 tests.

- [ ] **Step 6: Commit Task 1**

```bash
git add configs/c_stage_c21_executable_open_model_evaluation.yaml \
  src/b08_model_core/experiments/c21_executable_open_model_evaluation.py \
  tests/test_c21_executable_open_model_evaluation.py
git commit -m "feat: add c21 executable config"
```

## Task 2: Adapter Contract And Fake Adapter Test Harness

**Files:**

- Create: `src/b08_model_core/adapters/open_models/__init__.py`
- Create: `src/b08_model_core/adapters/open_models/base.py`
- Create: `tests/test_open_model_adapters.py`

- [ ] **Step 1: Write failing adapter contract tests**

Add tests:

```python
import numpy as np

from b08_model_core.adapters.open_models.base import (
    AdapterExecutionContext,
    AdapterFailure,
    AdapterReadiness,
    AdapterTaskOutput,
    OpenModelAdapter,
    OpenModelAdapterStatus,
)
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class FakeAdapter(OpenModelAdapter):
    model_id = "fake"
    supported_tasks = (C21TaskId.FORECASTING,)

    def inspect_environment(self, context):
        return AdapterReadiness(
            model_id=self.model_id,
            dependency_status="available",
            weight_status="not_required",
            adapter_status=OpenModelAdapterStatus.READY,
        )

    def load(self, context):
        return self

    def run_forecasting(self, windows, context):
        return AdapterTaskOutput(
            model_id=self.model_id,
            task_id=C21TaskId.FORECASTING,
            status=OpenModelAdapterStatus.AVAILABLE_AND_RAN,
            predictions=np.zeros((1, 1, 1)),
            metrics={"runtime_seconds": 0.01},
            input_shape={"windows": len(windows)},
            output_shape={"predictions": [1, 1, 1]},
        )


def test_fake_adapter_contract_returns_readiness_and_output():
    adapter = FakeAdapter()
    context = AdapterExecutionContext(
        allow_network=False,
        allow_download=False,
        cache_dir="hf_cache",
        timeout_seconds_per_model=900,
    )
    readiness = adapter.inspect_environment(context)
    assert readiness.adapter_status == OpenModelAdapterStatus.READY
    output = adapter.run_forecasting([], context)
    assert output.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert output.metrics["runtime_seconds"] == 0.01


def test_base_adapter_returns_unsupported_task_for_missing_method():
    adapter = FakeAdapter()
    context = AdapterExecutionContext(False, False, "hf_cache", 900)
    failure = adapter.run_representation([], context)
    assert isinstance(failure, AdapterFailure)
    assert failure.status == OpenModelAdapterStatus.UNSUPPORTED_TASK
    assert failure.failure_stage == "execute"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: FAIL because `adapters.open_models` does not exist.

- [ ] **Step 3: Implement adapter contract**

Create `base.py` with:

- `OpenModelAdapterStatus(StrEnum)` matching C2.1 statuses.
- `AdapterExecutionContext` dataclass.
- `AdapterReadiness` dataclass.
- `AdapterTaskOutput` dataclass.
- `AdapterFailure` dataclass.
- `OpenModelAdapter` base class with default `unsupported_task` methods.
- `dependency_status(modules, dependency_checker)` helper.

Important defaults:

- Base `run_forecasting`, `run_representation`, `run_imputation` return `AdapterFailure(status=UNSUPPORTED_TASK)`.
- Do not import optional model packages in `base.py`.
- `timeout_seconds_per_model` is documented as per model-task attempt.
- `OpenModelAdapterStatus.READY` is readiness-only and should appear only in readiness objects; model-task results must use C2.1 task statuses such as `available_and_ran`, `missing_dependency`, `unsupported_task`, or `timeout`.

- [ ] **Step 4: Export contract**

In `src/b08_model_core/adapters/open_models/__init__.py`, export base contract classes only. Do not import concrete optional model adapters here, because imports may trigger missing optional dependency errors.

- [ ] **Step 5: Run adapter tests**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add src/b08_model_core/adapters/open_models tests/test_open_model_adapters.py
git commit -m "feat: add c21 open model adapter contract"
```

## Task 3: C2.1 Result Schema, Report Renderer, And Cache Manifest

**Files:**

- Modify: `src/b08_model_core/experiments/c21_executable_open_model_evaluation.py`
- Modify: `tests/test_c21_executable_open_model_evaluation.py`

- [ ] **Step 1: Write failing result and report tests**

Add tests:

```python
from b08_model_core.adapters.open_models.base import OpenModelAdapterStatus
from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21ModelTaskResult,
    C21RunResult,
    C21TaskId,
    render_c21_report,
    render_c21_cache_manifest,
)


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
    readiness_section = text.split("## Adapter Readiness Table", 1)[1].split("## Model-Task Result Matrix", 1)[0]
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
            line for line in text.splitlines()
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
```

- [ ] **Step 2: Run focused tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py -q
```

Expected: FAIL because result dataclasses and renderers do not exist.

- [ ] **Step 3: Implement result dataclasses and renderers**

Add:

- `C21ModelTaskResult`
- `C21RunResult`
- `render_c21_report(result)`
- `render_c21_cache_manifest(result)`
- `_cell(value)` and `_value(value)` helpers, matching existing C1/C2 report style.

Report must include:

- Report Metadata
- Executive Summary
- Adapter Readiness Table
- Model-Task Result Matrix
- Forecasting Comparison
- Representation And Imputation Results
- Failure Taxonomy
- Cache Manifest
- C2 -> C3 Handoff
- C2 -> B Decision Notes
- Invalid Claims

- [ ] **Step 4: Run report tests**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py -q
```

Expected: PASS for config and report tests.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/b08_model_core/experiments/c21_executable_open_model_evaluation.py \
  tests/test_c21_executable_open_model_evaluation.py
git commit -m "feat: add c21 report schema"
```

## Task 4: Runner With Fake Adapter Registry, Baselines, Failure Isolation, And Strict Mode

**Files:**

- Modify: `src/b08_model_core/experiments/c21_executable_open_model_evaluation.py`
- Modify: `tests/test_c21_executable_open_model_evaluation.py`

- [ ] **Step 1: Write failing runner tests with fake adapters**

Add fake adapter classes inside tests:

```python
import time

import pandas as pd
import pytest

from b08_model_core.adapters.open_models.base import AdapterFailure, AdapterTaskOutput, OpenModelAdapterStatus
from b08_model_core.experiments.c21_executable_open_model_evaluation import (
    C21TaskId,
    run_c21_executable_evaluation,
)


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
```

Use helper functions like existing C2 tests to write a small canonical observation parquet. Keep fixture windows small enough for fast tests.

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py -q
```

Expected: FAIL because runner does not exist.

- [ ] **Step 3: Implement runner skeleton**

Implement:

- `run_c21_executable_evaluation(config, adapter_factory=None) -> C21RunResult`
- Shared FU13 windows using `build_model_windows`.
- Forecasting baseline using `RobustStageForecaster` and `forecasting_metrics`.
- Representation baseline using `simple_statistical_embedding`.
- Imputation baseline using `apply_deterministic_mask` and `reconstruction_metrics`.
- `adapter_factory` injection for tests.
- Failure isolation: catch exceptions per model-task attempt and convert to `runtime_failed`.
- Timeout enforcement: wrap each model-task attempt in `_run_attempt_with_timeout(...)` using `config.timeout_seconds_per_model`. The wrapper must interrupt or stop waiting for adapter work that exceeds the configured seconds, return `timeout` with `failure_stage="execute"`, and then continue later attempts. A simple adapter-raised `TimeoutError` mapping is not enough.
- Preferred first implementation for timeout: on POSIX, use a small `_attempt_timeout(seconds)` context manager built on `signal.setitimer(signal.ITIMER_REAL, seconds)` and a custom internal exception. Wrap the synchronous adapter call in that context so an over-time call is interrupted and mapped to `timeout`. Always restore the previous timer/handler in `finally`. If signal-based timeout is unavailable in a future runtime, use a documented fallback, but keep the same tests and status behavior.
- Timeout mapping: convert both enforced timeout and adapter-raised `TimeoutError` to `timeout` with `failure_stage="execute"`.
- `has_required_attempt_failure` property on `C21RunResult`.

If an adapter is missing from factory, use real adapter factory from Task 5+; until then, return a `missing_dependency` or `license_or_interface_needs_review` structured failure for that model. Do not skip required attempts.

- [ ] **Step 4: Run focused runner tests**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py -q
```

Expected: PASS for runner tests.

- [ ] **Step 5: Commit Task 4**

```bash
git add src/b08_model_core/experiments/c21_executable_open_model_evaluation.py \
  tests/test_c21_executable_open_model_evaluation.py
git commit -m "feat: add c21 executable runner"
```

## Task 5: Real Adapter Factory And Dependency-First Model Adapters

**Files:**

- Create: concrete adapter files under `src/b08_model_core/adapters/open_models/`
- Modify: `tests/test_open_model_adapters.py`

- [ ] **Step 1: Write failing adapter factory tests**

Add tests:

```python
from b08_model_core.adapters.open_models import build_open_model_adapter


def test_adapter_factory_returns_all_c21_adapters_without_importing_optional_packages():
    for model_id in ["ttm", "chronos", "timesfm", "moirai_uni2ts", "moment", "units"]:
        adapter = build_open_model_adapter(model_id)
        assert adapter.model_id == model_id


def test_adapter_factory_rejects_unknown_model():
    with pytest.raises(ValueError, match="unknown open model adapter"):
        build_open_model_adapter("unknown")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: FAIL because factory and concrete adapter modules do not exist.

- [ ] **Step 3: Implement real adapter factory**

In `src/b08_model_core/adapters/open_models/__init__.py`, add lazy factory:

```python
def build_open_model_adapter(model_id: str):
    if model_id == "ttm":
        from b08_model_core.adapters.open_models.ttm import TTMOpenModelAdapter
        return TTMOpenModelAdapter()
    if model_id == "chronos":
        from b08_model_core.adapters.open_models.chronos import ChronosOpenModelAdapter
        return ChronosOpenModelAdapter()
    if model_id == "timesfm":
        from b08_model_core.adapters.open_models.timesfm import TimesFMOpenModelAdapter
        return TimesFMOpenModelAdapter()
    if model_id == "moirai_uni2ts":
        from b08_model_core.adapters.open_models.moirai_uni2ts import MoiraiUni2TSOpenModelAdapter
        return MoiraiUni2TSOpenModelAdapter()
    if model_id == "moment":
        from b08_model_core.adapters.open_models.moment import MomentOpenModelAdapter
        return MomentOpenModelAdapter()
    if model_id == "units":
        from b08_model_core.adapters.open_models.units import UniTSOpenModelAdapter
        return UniTSOpenModelAdapter()
    raise ValueError(f"unknown open model adapter: {model_id}")
```

Do not import optional dependency packages at module import time.

- [ ] **Step 4: Implement dependency-first concrete adapters**

For each concrete adapter:

- `inspect_environment` checks configured dependency modules using `dependency_available`.
- If dependency missing, return `AdapterFailure(status=MISSING_DEPENDENCY, failure_stage="inspect")`.
- If task unsupported, return `AdapterFailure(status=UNSUPPORTED_TASK, failure_stage="execute")`.
- If dependency is present, `load` attempts real import/model construction in a try/except and maps failures to `missing_or_blocked_weights`, `license_or_interface_needs_review`, or `runtime_failed`.

Initial adapter modes:

| file | class | required tasks |
| --- | --- | --- |
| `ttm.py` | `TTMOpenModelAdapter` | forecasting |
| `chronos.py` | `ChronosOpenModelAdapter` | forecasting |
| `timesfm.py` | `TimesFMOpenModelAdapter` | forecasting |
| `moirai_uni2ts.py` | `MoiraiUni2TSOpenModelAdapter` | forecasting |
| `moment.py` | `MomentOpenModelAdapter` | representation, imputation |
| `units.py` | `UniTSOpenModelAdapter` | representation, imputation |

For unknown or not-yet-verified official APIs, do not fake success. If import succeeds but interface is not implemented, return `license_or_interface_needs_review` or `runtime_failed` with `failure_stage="load"` or `"execute"` and a precise reason.

- [ ] **Step 5: Run adapter tests**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add src/b08_model_core/adapters/open_models tests/test_open_model_adapters.py
git commit -m "feat: add c21 open model adapters"
```

## Task 6: TTM Anchor Real Forecasting Adapter

**Files:**

- Modify: `src/b08_model_core/adapters/open_models/ttm.py`
- Modify: `tests/test_open_model_adapters.py`

- [ ] **Step 1: Write failing TTM adapter tests using monkeypatch**

Add tests that monkeypatch TTM adapter internals so tests do not require `granite-tsfm`:

```python
def test_ttm_adapter_runs_forecasting_when_runtime_is_injected(monkeypatch, model_windows):
    adapter = TTMOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(adapter, "_predict_with_ttm", lambda windows, context: np.stack([w.y for w in windows]))
    context = AdapterExecutionContext(False, False, "hf_cache", 900)
    output = adapter.run_forecasting(model_windows[:2], context)
    assert output.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert output.predictions.shape == np.stack([w.y for w in model_windows[:2]]).shape
```

If there is no shared `model_windows` fixture in this test file, create a tiny local helper using `ModelWindow`.

- [ ] **Step 2: Run TTM adapter test and verify it fails**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py::test_ttm_adapter_runs_forecasting_when_runtime_is_injected -q
```

Expected: FAIL because TTM real adapter path is not implemented.

- [ ] **Step 3: Implement TTM adapter**

Implementation requirements:

- Prefer reusing existing `b08_model_core.adapters.ttm_adapter` or foundation runner behavior.
- Honor `context.allow_download` and `context.cache_dir`.
- If dependencies missing, return `missing_dependency`.
- If weights unavailable and download disabled, return `missing_or_blocked_weights`.
- On success, return predictions and shape metadata.
- Do not require TTM dependency for default tests.

- [ ] **Step 4: Run TTM adapter tests**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 6**

```bash
git add src/b08_model_core/adapters/open_models/ttm.py tests/test_open_model_adapters.py
git commit -m "feat: add c21 ttm executable adapter"
```

## Task 7: Forecasting Open Model Adapters For Chronos, TimesFM, And Moirai / Uni2TS

**Files:**

- Modify: `src/b08_model_core/adapters/open_models/chronos.py`
- Modify: `src/b08_model_core/adapters/open_models/timesfm.py`
- Modify: `src/b08_model_core/adapters/open_models/moirai_uni2ts.py`
- Modify: `tests/test_open_model_adapters.py`

- [ ] **Step 1: Verify official import/package refs before coding concrete API calls**

Use official repositories, model cards, or package docs to verify current import/package names and first-call APIs for:

- Chronos / Chronos-Bolt
- TimesFM
- Moirai / Uni2TS

Record findings in implementation comments only where needed, not as broad docs. If official API cannot be verified or package is unavailable, implement adapter path that records `license_or_interface_needs_review` or `missing_dependency` precisely.

- [ ] **Step 2: Write failing tests for dependency and injected runtime paths**

For each forecasting adapter:

```python
def test_chronos_adapter_reports_missing_dependency(monkeypatch):
    adapter = ChronosOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: False)
    context = AdapterExecutionContext(False, False, "hf_cache", 900)
    failure = adapter.inspect_environment(context)
    assert failure.status == OpenModelAdapterStatus.MISSING_DEPENDENCY


def test_chronos_adapter_runs_forecasting_with_injected_runtime(monkeypatch, model_windows):
    adapter = ChronosOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(adapter, "_predict", lambda windows, context: np.stack([w.y for w in windows]))
    context = AdapterExecutionContext(False, False, "hf_cache", 900)
    output = adapter.run_forecasting(model_windows[:2], context)
    assert output.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
```

Repeat equivalent tests for TimesFM and Moirai / Uni2TS. Use DRY helper functions if appropriate.

- [ ] **Step 3: Run focused tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: FAIL for unimplemented forecasting adapter runtime paths.

- [ ] **Step 4: Implement Chronos, TimesFM, and Moirai / Uni2TS adapters**

Common behavior:

- Dependency check first.
- Honor `allow_network`, `allow_download`, and `cache_dir`.
- Convert FU13 windows to model input shape; if impossible, return `unsupported_window_shape`.
- If official load/predict API succeeds, return `available_and_ran` with predictions.
- If official API cannot be safely called after dependency import, return `license_or_interface_needs_review` with specific package/interface detail.
- Do not fake predictions when model runtime fails.

- [ ] **Step 5: Run adapter tests**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 7**

```bash
git add src/b08_model_core/adapters/open_models/chronos.py \
  src/b08_model_core/adapters/open_models/timesfm.py \
  src/b08_model_core/adapters/open_models/moirai_uni2ts.py \
  tests/test_open_model_adapters.py
git commit -m "feat: add c21 forecasting model adapters"
```

## Task 8: MOMENT And UniTS Representation / Imputation Adapters

**Files:**

- Modify: `src/b08_model_core/adapters/open_models/moment.py`
- Modify: `src/b08_model_core/adapters/open_models/units.py`
- Modify: `tests/test_open_model_adapters.py`

- [ ] **Step 1: Verify official import/package refs before coding concrete API calls**

Verify current official import/package names and task APIs for:

- MOMENT representation and imputation
- UniTS representation and imputation

If official API cannot be verified, adapter must still perform real import/load attempt where possible and record `license_or_interface_needs_review` or `runtime_failed` precisely. Do not mark success without real output.

- [ ] **Step 2: Write failing tests for both required tasks per adapter**

Add tests:

```python
def test_moment_adapter_attempts_representation_and_imputation_with_injected_runtime(monkeypatch, model_windows):
    adapter = MomentOpenModelAdapter()
    monkeypatch.setattr(adapter, "_dependency_available", lambda name: True)
    monkeypatch.setattr(adapter, "_embed", lambda windows, context: np.ones((len(windows), 4)))
    monkeypatch.setattr(adapter, "_impute", lambda windows, mask_policy, context: np.stack([w.X for w in windows]))
    context = AdapterExecutionContext(False, False, "hf_cache", 900)
    rep = adapter.run_representation(model_windows[:2], context)
    imp = adapter.run_imputation(model_windows[:2], {"mask_ratio": 0.2, "seed": 7}, context)
    assert rep.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
    assert imp.status == OpenModelAdapterStatus.AVAILABLE_AND_RAN
```

Repeat equivalent test for UniTS.

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: FAIL for unimplemented representation / imputation adapter paths.

- [ ] **Step 4: Implement MOMENT and UniTS adapters**

Common behavior:

- Dependency check first.
- Both `run_representation` and `run_imputation` must be implemented for each adapter.
- Use deterministic mask policy for imputation.
- Return embedding shape, finite value ratio, reconstruction output shape and runtime metadata when successful.
- If dependency exists but task API is incompatible, return `license_or_interface_needs_review` or `unsupported_window_shape` with precise detail.

- [ ] **Step 5: Run adapter tests**

Run:

```bash
uv run python -m pytest tests/test_open_model_adapters.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 8**

```bash
git add src/b08_model_core/adapters/open_models/moment.py \
  src/b08_model_core/adapters/open_models/units.py \
  tests/test_open_model_adapters.py
git commit -m "feat: add c21 representation adapters"
```

## Task 9: CLI Integration, Exit Policy, And Report Writing

**Files:**

- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_c21_executable_open_model_evaluation.py`

- [ ] **Step 1: Write failing CLI tests**

Add tests:

```python
from b08_model_core.cli import main


def test_cli_c_stage_c21_writes_report_when_models_fail_structurally(tmp_path, monkeypatch):
    config_path = _write_c21_fixture_config(tmp_path, strict_model_success=False)
    _write_fixture_observations(tmp_path / "observations.parquet")
    output = tmp_path / "c21.md"
    exit_code = main([
        "experiment",
        "c-stage-c21",
        "--config",
        str(config_path),
        "--output",
        str(output),
    ])
    assert exit_code == 0
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "C2.1 Executable Open Model Evaluation Report" in text
    assert "config_allows_network" in text
    assert "False" in text
    assert "config_allows_download" in text


def test_cli_c_stage_c21_strict_mode_returns_nonzero_but_writes_report(tmp_path):
    config_path = _write_c21_fixture_config(tmp_path, strict_model_success=True)
    _write_fixture_observations(tmp_path / "observations.parquet")
    output = tmp_path / "c21.md"
    exit_code = main([
        "experiment",
        "c-stage-c21",
        "--config",
        str(config_path),
        "--output",
        str(output),
    ])
    assert exit_code == 1
    assert output.exists()
```

- [ ] **Step 2: Run CLI tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py -q
```

Expected: FAIL because CLI command does not exist.

- [ ] **Step 3: Implement CLI command**

In `src/b08_model_core/cli.py`:

- Add `c-stage-c21` parser under `experiment`.
- Load config with `load_c21_executable_config`.
- Override `config.report_path` with CLI `--output`.
- Run `run_c21_executable_evaluation`.
- Write `render_c21_report(result)` to output.
- If config requests cache manifest, write `render_c21_cache_manifest(result)`.
- Return 1 for config/data/report errors.
- Return 1 in strict mode when `result.has_required_attempt_failure`.
- Return 0 otherwise.

- [ ] **Step 4: Run CLI tests**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 9**

```bash
git add src/b08_model_core/cli.py \
  src/b08_model_core/experiments/c21_executable_open_model_evaluation.py \
  tests/test_c21_executable_open_model_evaluation.py
git commit -m "feat: add c21 executable cli"
```

## Task 10: Optional Dependencies Boundary And Documentation Updates

**Files:**

- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `details.md`
- Modify: `tests/test_experiment_scaffold.py` or create focused tests if needed

- [ ] **Step 1: Decide optional dependency extras after adapter API verification**

If official packages can be pinned without breaking `uv sync --extra dev`, add only optional extras, for example:

```toml
[project.optional-dependencies]
foundation-open-models = [
  # only verified, installable packages here
]
```

If package names are uncertain or resolver conflicts with existing deps, do not add them in this task. Adapter dependency checks and opt-in local install instructions are enough for C2.1 first pass.

- [ ] **Step 2: Write/update tests for default dependency safety**

Add or update a test that confirms:

- C2.1 default config has `allow_network is False`.
- C2.1 default config has `allow_download is False`.
- `uv run python -m pytest -q` does not require optional open model packages.

- [ ] **Step 3: Update README**

Add a short section near C2 stage commands:

```markdown
### C2.1 open model executable evaluation

默认 C2.1 配置离线运行，不隐式下载外部模型权重：

uv run b08-model-core experiment c-stage-c21 \
  --config configs/c_stage_c21_executable_open_model_evaluation.yaml \
  --output reports/c_stage_c21_executable_open_model_evaluation.md

联网真实执行必须使用显式 opt-in 配置或 override，并记录 cache / 权重 / 失败原因。
```

Keep wording clear that C2.1 is not production alarm, RUL, maintenance advice, or B-stage self-training Go.

- [ ] **Step 4: Update details.md**

Add a 2026-06-06 ledger row:

```markdown
| 2026-06-06 | C2.1 开源模型真实执行评测进入设计/计划阶段：目标是在默认离线安全边界下建立六模型 executable adapter 尝试、统一 task matrix、结构化失败和 C2 -> C3 / C2 -> B 决策报告；联网下载只允许 opt-in，不改变默认可复现路径。 |
```

- [ ] **Step 5: Run docs/config focused tests**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py tests/test_experiment_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 10**

```bash
git add pyproject.toml README.md details.md tests/test_c21_executable_open_model_evaluation.py tests/test_experiment_scaffold.py
git commit -m "docs: document c21 executable evaluation workflow"
```

If `pyproject.toml` or `tests/test_experiment_scaffold.py` were not changed, omit them from `git add`.

## Task 11: Full Verification And C2 Regression

**Files:**

- No new files expected.

- [ ] **Step 1: Run C2.1 focused tests**

Run:

```bash
uv run python -m pytest tests/test_c21_executable_open_model_evaluation.py tests/test_open_model_adapters.py -q
```

Expected: PASS.

- [ ] **Step 2: Run C2 regression tests**

Run:

```bash
uv run python -m pytest tests/test_c2_open_model_evaluation.py -q
```

Expected: PASS. This protects existing `experiment c-stage-c2`.

- [ ] **Step 3: Run full test suite**

Run:

```bash
uv run python -m pytest -q
```

Expected: PASS.

- [ ] **Step 4: Run default C2.1 CLI smoke on fixture or real local data**

If `data/processed/fu13_real_observations.parquet` exists locally, run:

```bash
uv run b08-model-core experiment c-stage-c21 \
  --config configs/c_stage_c21_executable_open_model_evaluation.yaml \
  --output reports/c_stage_c21_executable_open_model_evaluation.md
```

Expected:

- Exit code 0 unless config/data/report error occurs.
- Report is written.
- Default config records no implicit network/download.
- Missing optional model dependencies are structured failures, not crashes.

If local real data is absent, run the CLI through the fixture path in tests only and record that real-data smoke was not run.

- [ ] **Step 5: Check git status and ignored outputs**

Run:

```bash
git status --short --ignored=matching reports/c_stage_c21_executable_open_model_evaluation.md reports/c_stage_c21_model_cache_manifest.md hf_cache data/processed
```

Expected: generated reports/cache/data are ignored unless explicitly whitelisted.

- [ ] **Step 6: Final commit if needed**

If Task 11 required fixes:

```bash
git add <changed-files>
git commit -m "fix: harden c21 executable evaluation"
```

Otherwise no commit is needed.

## Optional Local Network Smoke

This is not part of default pytest or required CI. Run only on a machine where opt-in network/model downloads are intended:

```bash
uv run b08-model-core experiment c-stage-c21 \
  --config configs/local/c_stage_c21_executable_open_model_evaluation.network.yaml \
  --output reports/c_stage_c21_executable_open_model_evaluation_network.md
```

Expected:

- Report records `config_allows_network=true`.
- Any downloads or cache usage are recorded.
- Model failures remain structured.
- Generated network report is local/ignored unless explicitly approved.

If optional dependencies are not installed, first install only verified extras or model-specific packages. Do not add uncertain package names to `pyproject.toml` without resolver verification.
