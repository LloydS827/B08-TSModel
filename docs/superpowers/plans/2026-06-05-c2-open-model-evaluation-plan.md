# C2 开源模型系统评测 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 C2 开源模型系统评测入口，让 TTM、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS 六个核心模型全部进入同一套 audit、model-task attempt、报告和结构化失败记录。

**Architecture:** 复用 C1 的窄实验模块模式，在 `b08_model_core.experiments` 下新增 C2 模块：配置加载 -> registry -> audit runner -> task runner -> result schema -> Markdown report。第一版只做 C2 所需的薄 adapter/status checker 和 baseline 对照，不把 adapter 系统扩展成通用插件平台，不接入 C3 公开数据集，也不进入 B 阶段自研模型训练。

**Tech Stack:** Python 3.11, pandas, numpy, PyYAML, pytest, existing `b08_model_core` modules, Markdown docs.

---

## Scope Guard

本计划实现已批准规格：

`docs/superpowers/specs/2026-06-05-c2-open-model-evaluation-design.md`

必须做到：

- 六个核心模型固定纳入 C2：`ttm`、`moment`、`chronos`、`timesfm`、`moirai_uni2ts`、`units`。
- 每个核心模型都有 audit record。
- 每个核心模型至少有一个 model-task attempt，状态为成功或结构化失败。
- 候选模型失败默认不让 CLI 返回非零；配置、数据窗口或报告错误才返回非零。
- 报告包含 audit table、result matrix、failure taxonomy、invalid claims、C2 -> C3 handoff、C2 -> B decision notes。

必须避免：

- 不默认联网下载模型权重。
- 不要求真实 FU13 私有数据、外部网络或本机模型 cache 才能跑测试。
- 不把 TSPulse / FlowState 纳入 C2 核心验收。
- 不实现公开数据集下载、schema mapping、B 阶段训练、自研 backbone、生产告警、RUL 或维修建议。

## File Structure

Create:

- `configs/c_stage_c2_open_model_evaluation.yaml`
  - C2 执行配置。引用 C1 配置、FU13 数据路径、窗口参数、六个核心模型、任务映射、cache/no-network 策略和输出报告路径。

- `src/b08_model_core/experiments/c2_open_model_evaluation.py`
  - C2 config loader、model registry、audit/result dataclasses、status enums、audit runner、task runner、report renderer 和 C2 主入口。
  - 可以复用 C1 的 `apply_deterministic_mask`、`simple_statistical_embedding`、`reconstruction_metrics` 和 report cell formatting 思路；不要反向修改 C1 行为。

- `tests/test_c2_open_model_evaluation.py`
  - TDD 测试：config、registry、audit status、model-task status、report、CLI、candidate failure 默认成功、strict mode、数据错误。

Modify:

- `src/b08_model_core/cli.py`
  - 增加 `uv run b08-model-core experiment c-stage-c2 --config ... --output ...`。

- `README.md`
  - 增加一段 C2 命令和阶段说明。只补入口，不重写 README 结构。

- `details.md`
  - 增加 2026-06-05 C2 计划/执行入口 ledger 行。若文件不存在则跳过；当前仓库存在。

Do not modify:

- `docs/index.html`
- `docs/research/**`
- 历史归档文档
- `data/**`
- `hf_cache/**`

## Shared Status Semantics

Audit status:

| status | meaning |
| --- | --- |
| `audit_passed` | 来源、许可证边界、依赖、权重策略和任务接口已记录，未发现阻断。 |
| `needs_license_review` | 许可证或使用边界需要人工核对。 |
| `needs_dependency_review` | 依赖、安装方式或运行环境需要核对。 |
| `needs_interface_review` | 官方接口、adapter contract 或输入输出形状需要核对。 |
| `audit_failed` | 审计过程本身失败，原因必须记录。 |

Model-task status:

| status | meaning |
| --- | --- |
| `available_and_ran` | 依赖、权重、输入形状和任务头可用，模型完成运行。 |
| `missing_dependency` | Python 包或运行时依赖缺失。 |
| `missing_or_blocked_weights` | 权重缺失、下载被禁用、下载失败或 cache 不可用。 |
| `unsupported_task` | adapter 或官方接口不支持当前任务。 |
| `unsupported_window_shape` | 当前窗口、变量数、horizon、mask 或 token 形式不被模型支持。 |
| `runtime_failed` | 运行时异常，已捕获并写入报告。 |
| `license_or_interface_needs_review` | 许可证或接口边界不足以安全执行，需要人工核对。 |
| `skipped_by_config` | C2 配置主动跳过；默认核心模型不应出现该状态。 |

## Task 1: C2 Config, Registry, And Core Model Coverage

**Files:**

- Create: `configs/c_stage_c2_open_model_evaluation.yaml`
- Create: `src/b08_model_core/experiments/c2_open_model_evaluation.py`
- Create: `tests/test_c2_open_model_evaluation.py`

- [ ] **Step 1: Write failing config and registry tests**

Create `tests/test_c2_open_model_evaluation.py` with these initial tests:

```python
from pathlib import Path

import pytest

from b08_model_core.experiments.c2_open_model_evaluation import (
    C2OpenModelConfigError,
    CORE_MODEL_IDS,
    C2TaskId,
    load_c2_open_model_config,
    build_c2_model_registry,
)


def test_c2_config_lists_all_six_core_models():
    config = load_c2_open_model_config("configs/c_stage_c2_open_model_evaluation.yaml")
    assert config.stage == "C2_open_model_evaluation"
    assert config.upstream_c1_config == Path("configs/c_stage_c1_execution.yaml")
    assert config.allow_download is False
    assert config.strict_model_success is False
    assert [model.model_id for model in config.core_models] == list(CORE_MODEL_IDS)


def test_c2_registry_generates_attempt_for_every_core_model():
    config = load_c2_open_model_config("configs/c_stage_c2_open_model_evaluation.yaml")
    registry = build_c2_model_registry(config)
    assert set(registry.by_model_id) == set(CORE_MODEL_IDS)
    assert set(attempt.model_id for attempt in registry.attempts) == set(CORE_MODEL_IDS)
    assert registry.by_model_id["ttm"].display_name == "TTM / TinyTimeMixer"
    assert C2TaskId.FORECASTING in registry.by_model_id["chronos"].primary_tasks
    assert C2TaskId.REPRESENTATION in registry.by_model_id["moment"].primary_tasks
    assert C2TaskId.IMPUTATION in registry.by_model_id["units"].primary_tasks


def test_c2_registry_rejects_missing_core_model(tmp_path):
    config = load_c2_open_model_config("configs/c_stage_c2_open_model_evaluation.yaml")
    config.core_models = [model for model in config.core_models if model.model_id != "timesfm"]
    with pytest.raises(C2OpenModelConfigError, match="missing core models"):
        build_c2_model_registry(config)


def test_c2_registry_rejects_core_model_without_primary_task():
    config = load_c2_open_model_config("configs/c_stage_c2_open_model_evaluation.yaml")
    config.by_model_id["moment"].primary_tasks = []
    with pytest.raises(C2OpenModelConfigError, match="at least one primary task"):
        build_c2_model_registry(config)
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
uv run --extra dev python -m pytest tests/test_c2_open_model_evaluation.py -q
```

Expected: FAIL because `b08_model_core.experiments.c2_open_model_evaluation` does not exist.

- [ ] **Step 3: Create the C2 default config**

Create `configs/c_stage_c2_open_model_evaluation.yaml`:

```yaml
stage: C2_open_model_evaluation
upstream_c1_config: configs/c_stage_c1_execution.yaml
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
core_models:
  - model_id: ttm
    display_name: TTM / TinyTimeMixer
    source_kind: official_repo
    source_ref: docs/research/open-source-model-paper-matrix.md#ttm--tinytimemixer
    model_card_ref: ibm-granite/granite-timeseries-ttm-r2
    license_note: needs_review
    dependency_modules: [tsfm_public, torch, transformers, huggingface_hub]
    primary_tasks: [forecasting]
    supported_tasks: [forecasting]
  - model_id: moment
    display_name: MOMENT
    source_kind: official_repo
    source_ref: docs/research/open-source-model-paper-matrix.md#moment
    model_card_ref: needs_review
    license_note: needs_review
    dependency_modules: [momentfm]
    primary_tasks: [representation, imputation]
    supported_tasks: [forecasting, representation, imputation]
  - model_id: chronos
    display_name: Chronos / Chronos-Bolt
    source_kind: official_repo
    source_ref: docs/research/open-source-model-paper-matrix.md#chronos--chronos-bolt
    model_card_ref: needs_review
    license_note: needs_review
    dependency_modules: [chronos]
    primary_tasks: [forecasting]
    supported_tasks: [forecasting]
  - model_id: timesfm
    display_name: TimesFM
    source_kind: official_repo
    source_ref: docs/research/open-source-model-paper-matrix.md#timesfm
    model_card_ref: needs_review
    license_note: needs_review
    dependency_modules: [timesfm]
    primary_tasks: [forecasting]
    supported_tasks: [forecasting]
  - model_id: moirai_uni2ts
    display_name: Moirai / Uni2TS
    source_kind: official_repo
    source_ref: docs/research/open-source-model-paper-matrix.md#moirai--uni2ts
    model_card_ref: needs_review
    license_note: needs_review
    dependency_modules: [uni2ts]
    primary_tasks: [forecasting]
    supported_tasks: [forecasting]
  - model_id: units
    display_name: UniTS
    source_kind: official_repo
    source_ref: docs/research/open-source-model-paper-matrix.md#units
    model_card_ref: needs_review
    license_note: needs_review
    dependency_modules: []
    primary_tasks: [representation, imputation]
    supported_tasks: [forecasting, representation, imputation]
task_policy:
  forecasting: [ttm, chronos, timesfm, moirai_uni2ts]
  representation: [moment, units]
  imputation: [moment, units]
model_cache_policy:
  allow_download: false
  cache_dir: hf_cache
execution_policy:
  strict_model_success: false
  no_network_by_default: true
  record_failure: true
  do_not_over_claim: true
outputs:
  report: reports/c_stage_c2_open_model_evaluation.md
```

- [ ] **Step 4: Implement minimal config loader and registry**

Create `src/b08_model_core/experiments/c2_open_model_evaluation.py` with:

- `CORE_MODEL_IDS = ("ttm", "moment", "chronos", "timesfm", "moirai_uni2ts", "units")`
- `C2TaskId(StrEnum)` values: `FORECASTING`, `REPRESENTATION`, `IMPUTATION`
- `C2AuditStatus(StrEnum)` and `C2ModelTaskStatus(StrEnum)` from shared status semantics
- dataclasses:
  - `C2ModelSpec`
  - `C2ExecutionConfig`
  - `C2ModelTaskAttempt`
  - `C2ModelRegistry`
- `load_c2_open_model_config(path)`
- `build_c2_model_registry(config)`

Implementation notes:

- Convert YAML `primary_tasks` and `supported_tasks` to `C2TaskId`.
- Add `C2ExecutionConfig.by_model_id` property or fill it during load.
- Reject missing core ids and extra core ids in `core_models`; extension candidates are out of C2 core and should not be accepted in this config.
- Generate attempts from `task_policy`; if a core model appears in `core_models` but not in `task_policy`, add attempts from its `primary_tasks`.
- Keep all paths relative as provided; do not resolve to private absolute paths.

- [ ] **Step 5: Run the focused test**

Run:

```bash
uv run --extra dev python -m pytest tests/test_c2_open_model_evaluation.py -q
```

Expected: PASS for the Task 1 tests.

- [ ] **Step 6: Commit Task 1**

```bash
git add configs/c_stage_c2_open_model_evaluation.yaml src/b08_model_core/experiments/c2_open_model_evaluation.py tests/test_c2_open_model_evaluation.py
git commit -m "feat: add c2 model registry"
```

## Task 2: Model Audit Records And Structured Audit Status

**Files:**

- Modify: `src/b08_model_core/experiments/c2_open_model_evaluation.py`
- Modify: `tests/test_c2_open_model_evaluation.py`

- [ ] **Step 1: Write failing audit tests**

Append tests:

```python
from b08_model_core.experiments.c2_open_model_evaluation import (
    C2AuditStatus,
    C2ModelAuditRecord,
    run_c2_model_audit,
)


def test_c2_audit_creates_record_for_every_core_model():
    config = load_c2_open_model_config("configs/c_stage_c2_open_model_evaluation.yaml")
    records = run_c2_model_audit(build_c2_model_registry(config))
    assert set(record.model_id for record in records) == set(CORE_MODEL_IDS)
    ttm = next(record for record in records if record.model_id == "ttm")
    assert ttm.source_ref
    assert ttm.model_card_ref
    assert ttm.license_note
    assert "forecasting" in ttm.supported_tasks
    assert ttm.audit_status in set(C2AuditStatus)


def test_c2_audit_records_dependency_review_when_dependency_missing():
    config = load_c2_open_model_config("configs/c_stage_c2_open_model_evaluation.yaml")
    config.by_model_id["chronos"].dependency_modules = ["definitely_missing_chronos_module"]
    records = run_c2_model_audit(build_c2_model_registry(config))
    chronos = next(record for record in records if record.model_id == "chronos")
    assert chronos.audit_status == C2AuditStatus.NEEDS_DEPENDENCY_REVIEW
    assert chronos.dependency_status.startswith("missing:")


def test_c2_audit_records_license_review_without_blocking_attempts():
    config = load_c2_open_model_config("configs/c_stage_c2_open_model_evaluation.yaml")
    config.by_model_id["timesfm"].license_note = "needs_review"
    registry = build_c2_model_registry(config)
    records = run_c2_model_audit(registry)
    timesfm = next(record for record in records if record.model_id == "timesfm")
    assert timesfm.audit_status in {
        C2AuditStatus.NEEDS_LICENSE_REVIEW,
        C2AuditStatus.NEEDS_DEPENDENCY_REVIEW,
    }
    assert any(attempt.model_id == "timesfm" for attempt in registry.attempts)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --extra dev python -m pytest tests/test_c2_open_model_evaluation.py -q
```

Expected: FAIL because audit dataclass/runner is not implemented.

- [ ] **Step 3: Implement audit dataclass and runner**

Add dataclass:

```python
@dataclass
class C2ModelAuditRecord:
    model_id: str
    display_name: str
    source_kind: str
    source_ref: str
    model_card_ref: str
    license_note: str
    dependency_status: str
    weights_status: str
    supported_tasks: list[str]
    input_constraints: str
    offline_feasibility: str
    audit_status: C2AuditStatus
```

Add `run_c2_model_audit(registry, dependency_checker=dependency_available)`.

Audit rules:

- Missing dependency -> `needs_dependency_review`.
- `license_note == "needs_review"` and dependencies present -> `needs_license_review`.
- Empty `source_ref`, empty `model_card_ref`, or no supported tasks -> `needs_interface_review`.
- Otherwise -> `audit_passed`.
- `weights_status` should be `"download_disabled"` when `allow_download` is false and a model has model-card/weight dependency; `"not_required_for_status_check"` is acceptable for status-only attempts.
- `offline_feasibility` should mention `no_network_by_default`.

- [ ] **Step 4: Run the audit tests**

Run:

```bash
uv run --extra dev python -m pytest tests/test_c2_open_model_evaluation.py -q
```

Expected: PASS for Task 1 and Task 2 tests.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/b08_model_core/experiments/c2_open_model_evaluation.py tests/test_c2_open_model_evaluation.py
git commit -m "feat: add c2 model audit records"
```

## Task 3: C2 Task Runner, Baselines, And Model-Task Attempts

**Files:**

- Modify: `src/b08_model_core/experiments/c2_open_model_evaluation.py`
- Modify: `tests/test_c2_open_model_evaluation.py`

- [ ] **Step 1: Write failing task-runner tests with fixture data**

Append tests and helpers:

```python
import numpy as np
import pandas as pd
import yaml

from b08_model_core.experiments.c2_open_model_evaluation import (
    C2ModelTaskStatus,
    run_c2_open_model_evaluation,
)


def test_c2_runner_outputs_attempt_for_every_core_model(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    result = run_c2_open_model_evaluation(load_c2_open_model_config(config_path))
    assert set(record.model_id for record in result.audit_records) == set(CORE_MODEL_IDS)
    assert set(attempt.model_id for attempt in result.task_results) == set(CORE_MODEL_IDS)
    assert any(attempt.task_id == C2TaskId.FORECASTING for attempt in result.task_results)
    assert any(attempt.task_id == C2TaskId.REPRESENTATION for attempt in result.task_results)
    assert any(attempt.task_id == C2TaskId.IMPUTATION for attempt in result.task_results)


def test_c2_runner_records_forecasting_and_representation_imputation_baselines(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    result = run_c2_open_model_evaluation(load_c2_open_model_config(config_path))
    ttm = _task_result(result, "ttm", C2TaskId.FORECASTING)
    moment_rep = _task_result(result, "moment", C2TaskId.REPRESENTATION)
    units_imp = _task_result(result, "units", C2TaskId.IMPUTATION)
    assert ttm.baseline_reference == "RobustStageForecaster"
    assert "mae" in ttm.baseline_metrics
    assert moment_rep.baseline_reference == "statistical_embedding"
    assert moment_rep.baseline_metrics["embedding_windows"] > 0
    assert units_imp.baseline_reference == "simple_reconstruction_baseline"
    assert units_imp.baseline_metrics["mae"] is not None


def test_c2_runner_candidate_failures_are_structured(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    result = run_c2_open_model_evaluation(load_c2_open_model_config(config_path))
    statuses = {attempt.status for attempt in result.task_results}
    assert C2ModelTaskStatus.MISSING_DEPENDENCY in statuses or C2ModelTaskStatus.UNSUPPORTED_TASK in statuses
    assert all(attempt.invalid_claims for attempt in result.task_results)
    assert result.failure_taxonomy


def test_c2_runner_returns_data_error_when_no_windows(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True, rows=8)
    with pytest.raises(ValueError, match="not enough windows"):
        run_c2_open_model_evaluation(load_c2_open_model_config(config_path))
```

Helpers:

```python
def _task_result(result, model_id, task_id):
    return next(item for item in result.task_results if item.model_id == model_id and item.task_id == task_id)


def _write_c2_fixture_config(tmp_path, *, force_model_failures=False, rows=120, strict_model_success=False):
    dataset = tmp_path / "fu13.parquet"
    _write_fu13_fixture(dataset, rows=rows)
    raw = yaml.safe_load(Path("configs/c_stage_c2_open_model_evaluation.yaml").read_text(encoding="utf-8"))
    raw["dataset"]["fu13_observations"] = str(dataset)
    raw["dataset"]["boundary"] = "test_fixture_no_private_data"
    raw["window"]["context_length"] = 24
    raw["window"]["prediction_length"] = 6
    raw["window"]["max_windows"] = 8
    raw["outputs"]["report"] = str(tmp_path / "report.md")
    raw["execution_policy"]["strict_model_success"] = strict_model_success
    if force_model_failures:
        for model in raw["core_models"]:
            model["force_missing_dependency"] = model["model_id"] in {"ttm", "chronos", "timesfm", "moirai_uni2ts", "moment"}
            model["force_unsupported_task"] = model["model_id"] == "units"
    path = tmp_path / "c2.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return path


def _write_fu13_fixture(path, *, rows=120):
    timestamps = pd.date_range("2026-05-01", periods=rows, freq="5s", tz="UTC")
    records = []
    for i, ts in enumerate(timestamps):
        stage = "溶解" if i < rows // 2 else "浇筑"
        quality = "good" if i % 17 else "unassigned_cycle"
        for sensor, domain, value in [
            ("LeakElec", "electrical", 10 + np.sin(i / 7)),
            ("O2Content", "atmosphere", -20 + np.cos(i / 9)),
        ]:
            records.append(
                {
                    "timestamp": ts,
                    "device_id": "FU13",
                    "batch_id": "cycle_0001",
                    "stage": stage,
                    "sensor_id": sensor,
                    "value": value,
                    "unit": "%",
                    "domain": domain,
                    "quality_flag": quality,
                    "degradation_label": "normal",
                    "failure_proxy": False,
                }
            )
    pd.DataFrame(records).to_parquet(path, index=False)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --extra dev python -m pytest tests/test_c2_open_model_evaluation.py -q
```

Expected: FAIL because runner/result schema is not implemented.

- [ ] **Step 3: Implement result dataclasses and runner**

Add dataclasses:

- `C2ModelTaskResult`
  - `model_id`
  - `display_name`
  - `task_id`
  - `status`
  - `dataset_boundary`
  - `window_policy`
  - `metrics`
  - `baseline_reference`
  - `baseline_metrics`
  - `failure_reason`
  - `error_detail`
  - `artifact_outputs`
  - `invalid_claims`
  - `decision_notes`

- `C2OpenModelEvaluationResult`
  - `audit_records`
  - `task_results`
  - `failure_taxonomy`
  - `c3_handoff_notes`
  - `b_decision_notes`
  - `invalid_claims`

Add `run_c2_open_model_evaluation(config)`.

Runner behavior:

- Load FU13 parquet and build windows using `build_model_windows`.
- Require at least 2 windows; otherwise raise `ValueError("not enough windows for C2 evaluation: ...")`.
- Build audit records first.
- For forecasting attempts:
  - Split windows 70/30.
  - Fit `RobustStageForecaster` and compute baseline metrics with `forecasting_metrics`.
  - For each forecasting model attempt, call `_model_task_status(model_spec, task_id, audit_record)`.
  - If `ttm` has dependencies and config permits actual inference, it may use existing `TTMForecastAdapter`; if not, structured status is enough for first implementation.
- For representation attempts:
  - Use C1 `simple_statistical_embedding(window.X)`.
  - Store `embedding_windows` and `embedding_features` in `baseline_metrics`.
- For imputation attempts:
  - Use C1 `apply_deterministic_mask` and `reconstruction_metrics`.
  - Store mask policy in artifact outputs.
- For all attempts:
  - Include inherited invalid claims:
    - `不得解释为生产告警`
    - `不得解释为 FU13 RUL`
    - `不得解释为自动维修建议`
    - `不得解释为模型选型终局`
    - `不得解释为自研训练 Go 结论`
  - Convert audit needs-review to model-task status if it prevents execution.
  - Add model/task failure to `failure_taxonomy`.

Status helper rules:

- `force_missing_dependency` in config -> `missing_dependency`.
- `force_unsupported_task` in config -> `unsupported_task`.
- Missing dependency modules -> `missing_dependency`.
- Task not in model supported tasks -> `unsupported_task`.
- License/interface needs review -> `license_or_interface_needs_review`.
- Otherwise, if no actual runtime is implemented for that model/task, record `license_or_interface_needs_review` or `unsupported_task` with clear reason. Do not fake `available_and_ran`.

- [ ] **Step 4: Run the focused tests**

Run:

```bash
uv run --extra dev python -m pytest tests/test_c2_open_model_evaluation.py -q
```

Expected: PASS for Task 1-3 tests.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/b08_model_core/experiments/c2_open_model_evaluation.py tests/test_c2_open_model_evaluation.py
git commit -m "feat: add c2 open model task runner"
```

## Task 4: Report Renderer And CLI Command

**Files:**

- Modify: `src/b08_model_core/experiments/c2_open_model_evaluation.py`
- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_c2_open_model_evaluation.py`

- [ ] **Step 1: Write failing report and CLI tests**

Append tests:

```python
from b08_model_core.cli import main
from b08_model_core.experiments.c2_open_model_evaluation import render_c2_open_model_report


def test_c2_report_contains_required_sections(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    result = run_c2_open_model_evaluation(load_c2_open_model_config(config_path))
    text = render_c2_open_model_report(result, config_path=str(config_path))
    assert "C2 Open Model Evaluation Report" in text
    assert "Model Audit Table" in text
    assert "Model-Task Result Matrix" in text
    assert "Failure Taxonomy" in text
    assert "C2 -> C3 Handoff" in text
    assert "C2 -> B Decision Notes" in text
    assert "Invalid Claims" in text
    for model_id in CORE_MODEL_IDS:
        assert model_id in text


def test_cli_c_stage_c2_writes_report_when_candidates_fail(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True, strict_model_success=False)
    output = tmp_path / "c2_report.md"
    result = main(["experiment", "c-stage-c2", "--config", str(config_path), "--output", str(output)])
    assert result == 0
    text = output.read_text(encoding="utf-8")
    assert "C2 Open Model Evaluation Report" in text
    assert "missing_dependency" in text or "unsupported_task" in text


def test_cli_c_stage_c2_strict_candidate_failure_returns_nonzero_but_writes_report(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True, strict_model_success=True)
    output = tmp_path / "c2_report.md"
    result = main(["experiment", "c-stage-c2", "--config", str(config_path), "--output", str(output)])
    assert result == 1
    assert output.exists()


def test_cli_c_stage_c2_returns_nonzero_for_missing_dataset(tmp_path):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw["dataset"]["fu13_observations"] = str(tmp_path / "missing.parquet")
    config_path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    output = tmp_path / "c2_report.md"
    result = main(["experiment", "c-stage-c2", "--config", str(config_path), "--output", str(output)])
    assert result == 1


def test_cli_c_stage_c2_returns_nonzero_when_report_cannot_be_written(tmp_path, monkeypatch):
    config_path = _write_c2_fixture_config(tmp_path, force_model_failures=True)

    def fail_write_text(self, *args, **kwargs):
        raise PermissionError("read-only report target")

    monkeypatch.setattr(Path, "write_text", fail_write_text)
    result = main(
        [
            "experiment",
            "c-stage-c2",
            "--config",
            str(config_path),
            "--output",
            str(tmp_path / "c2_report.md"),
        ]
    )
    assert result == 1
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run --extra dev python -m pytest tests/test_c2_open_model_evaluation.py -q
```

Expected: FAIL because report renderer and CLI are missing.

- [ ] **Step 3: Implement report renderer**

Add `render_c2_open_model_report(result, *, config_path=None) -> str`.

Report sections must include:

- `# C2 Open Model Evaluation Report`
- `## Report Metadata`
- `## C2 Scope`
- `## Model Audit Table`
- `## Model-Task Result Matrix`
- `## Forecasting Results`
- `## Representation And Imputation Results`
- `## Baseline Comparison`
- `## Failure Taxonomy`
- `## C2 -> C3 Handoff`
- `## C2 -> B Decision Notes`
- `## Invalid Claims`

Use local helper `_cell()` and `_value()` or copy the C1 implementation into C2 to keep the module independent. Preserve Chinese invalid-claim text without escaping away readability.

- [ ] **Step 4: Add CLI parser and command branch**

Modify `src/b08_model_core/cli.py`:

- Import:
  - `C2ModelTaskStatus`
  - `load_c2_open_model_config`
  - `render_c2_open_model_report`
  - `run_c2_open_model_evaluation`
- Add parser:

```python
c_stage_c2 = experiment_sub.add_parser("c-stage-c2")
c_stage_c2.add_argument("--config", required=True)
c_stage_c2.add_argument("--output", required=True)
```

- Add command branch:

```python
if args.command == "experiment" and args.experiment_command == "c-stage-c2":
    try:
        config = load_c2_open_model_config(args.config)
        config.report_path = Path(args.output)
        result = run_c2_open_model_evaluation(config)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_c2_open_model_report(result, config_path=args.config), encoding="utf-8")
    except (FileNotFoundError, ValueError, OSError, PermissionError):
        return 1
    if config.strict_model_success and _has_c2_candidate_model_failure(result.task_results):
        return 1
    return 0
```

Add `_has_c2_candidate_model_failure(task_results)` near `_has_candidate_model_failure`.

Failure statuses:

- `missing_dependency`
- `missing_or_blocked_weights`
- `unsupported_task`
- `unsupported_window_shape`
- `runtime_failed`
- `license_or_interface_needs_review`

- [ ] **Step 5: Run focused and CLI tests**

Run:

```bash
uv run --extra dev python -m pytest tests/test_c2_open_model_evaluation.py -q
uv run --extra dev python -m pytest tests/test_c1_evidence.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add src/b08_model_core/experiments/c2_open_model_evaluation.py src/b08_model_core/cli.py tests/test_c2_open_model_evaluation.py
git commit -m "feat: add c2 open model report cli"
```

## Task 5: Documentation, Smoke Verification, And Whole-Suite Check

**Files:**

- Modify: `README.md`
- Modify: `details.md`
- Modify if needed: `tests/test_c2_open_model_evaluation.py`

- [ ] **Step 1: Write a documentation assertion if existing tests cover README command examples**

If no existing README command test exists, do not add a broad docs parser. Keep verification manual with `rg` in Step 4.

- [ ] **Step 2: Update README with the C2 command**

Add a short C2 subsection near the C1 command:

Add this prose:

> C2 是开源时序基础模型系统评测入口。它固定审计并尝试 TTM / TinyTimeMixer、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS 六个核心模型；模型失败默认写入结构化状态，不等同于阶段失败。

Add this command block:

```bash
uv run b08-model-core experiment c-stage-c2 \
  --config configs/c_stage_c2_open_model_evaluation.yaml \
  --output reports/c_stage_c2_open_model_evaluation.md
```

Mention that `reports/c_stage_c2_open_model_evaluation.md` is ignored local output.

- [ ] **Step 3: Update details ledger**

Add one row to `details.md`:

```markdown
| 2026-06-05 | C2 开源模型系统评测计划已形成并进入执行入口：核心配置为 `configs/c_stage_c2_open_model_evaluation.yaml`，命令为 `uv run b08-model-core experiment c-stage-c2 --config configs/c_stage_c2_open_model_evaluation.yaml --output reports/c_stage_c2_open_model_evaluation.md`；该阶段固定覆盖 TTM、MOMENT、Chronos / Chronos-Bolt、TimesFM、Moirai / Uni2TS、UniTS，成功标准是 audit + model-task attempt + 结构化失败记录，不要求全部模型成功运行。 |
```

- [ ] **Step 4: Verify documentation references**

Run:

```bash
rg -n "c-stage-c2|c_stage_c2_open_model_evaluation|TTM|MOMENT|Chronos|TimesFM|Moirai|UniTS" README.md details.md
```

Expected: command and six-model wording appear.

- [ ] **Step 5: Run full test suite**

Run:

```bash
uv run --extra dev python -m pytest -q
```

Expected: PASS.

- [ ] **Step 6: Run optional local smoke when FU13 parquet exists**

Run only if `data/processed/fu13_real_observations.parquet` exists:

```bash
uv run b08-model-core experiment c-stage-c2 \
  --config configs/c_stage_c2_open_model_evaluation.yaml \
  --output reports/c_stage_c2_open_model_evaluation.md
```

Expected:

- Exit 0 when candidate model failures are structured and report writes successfully.
- Report contains all six core model ids or display names.
- If optional model dependencies/cache are absent, report contains `missing_dependency`, `missing_or_blocked_weights`, `unsupported_task`, or `license_or_interface_needs_review`.

- [ ] **Step 7: Commit Task 5**

```bash
git add README.md details.md tests/test_c2_open_model_evaluation.py
git commit -m "docs: document c2 open model evaluation workflow"
```

## Final Verification

After all tasks:

- [ ] Run:

```bash
uv run --extra dev python -m pytest -q
```

- [ ] Run C2 CLI against fixture through tests:

```bash
uv run --extra dev python -m pytest tests/test_c2_open_model_evaluation.py -q
```

- [ ] If local FU13 parquet exists, run:

```bash
uv run b08-model-core experiment c-stage-c2 \
  --config configs/c_stage_c2_open_model_evaluation.yaml \
  --output reports/c_stage_c2_open_model_evaluation.md
```

- [ ] Confirm working tree is clean except ignored local reports:

```bash
git status --short --branch
```

- [ ] Use superpowers:requesting-code-review after implementation is complete and before finishing the branch.
