# C3 Public Dataset Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the C3 public dataset registry entrypoint: a machine-readable registry config, validation/reporting module, CLI command, and focused tests that do not download data.

**Architecture:** C3 is a narrow experiment module like C2/C2.1/C2.2. `configs/c_stage_c3_public_dataset_registry.yaml` stores candidate public dataset metadata. `src/b08_model_core/experiments/c3_public_dataset_registry.py` loads and validates the registry, derives readiness categories, and renders `reports/c_stage_c3_public_dataset_registry.md`. `src/b08_model_core/cli.py` exposes `experiment c-stage-c3`.

**Tech Stack:** Python dataclasses, `yaml.safe_load`, existing CLI patterns, Markdown report rendering, `pytest`.

---

## File Structure

**Precondition:** execute this plan on branch `codex/c3-public-dataset-registry`, branched from current `main` after the C3 design spec commit.

- Create: `configs/c_stage_c3_public_dataset_registry.yaml`
  - Default C3 registry config with initial five datasets: FU13, NASA C-MAPSS, NASA IMS Bearing, PRONOSTIA / FEMTO-ST, Tennessee Eastman Process.
  - No data download paths and no raw public data references.

- Create: `src/b08_model_core/experiments/c3_public_dataset_registry.py`
  - C3 dataclasses, config loader, validation rules, readiness classification, report renderer, and run function.

- Modify: `src/b08_model_core/cli.py`
  - Add `experiment c-stage-c3 --config --output`.

- Create: `tests/test_c3_public_dataset_registry.py`
  - Focused tests for default config, required fields, safety rules, readiness classification, report rendering, and CLI behavior.

- Modify: `README.md`
  - Add a short C3 command section only. Keep README as project entrance; do not duplicate registry details.

- Modify: `details.md`
  - Add one short daily ledger sentence if needed. Do not expand beyond the current three-section format.

---

## Task 1: Registry Config And Loader

**Files:**
- Create: `configs/c_stage_c3_public_dataset_registry.yaml`
- Create: `src/b08_model_core/experiments/c3_public_dataset_registry.py`
- Test: `tests/test_c3_public_dataset_registry.py`

- [ ] **Step 1: Write failing config loader tests**

Add tests:

```python
from pathlib import Path

import pytest

from b08_model_core.experiments.c3_public_dataset_registry import (
    C3DatasetRole,
    C3RegistryConfigError,
    load_c3_registry_config,
)


def test_c3_default_registry_config_has_initial_dataset_set():
    config = load_c3_registry_config("configs/c_stage_c3_public_dataset_registry.yaml")

    assert config.stage == "C3_public_dataset_registry"
    assert config.outputs.report == Path("reports/c_stage_c3_public_dataset_registry.md")
    assert tuple(item.dataset_id for item in config.datasets) == (
        "fu13_internal",
        "nasa_cmapss",
        "ims_bearing",
        "pronostia_femto",
        "tennessee_eastman_process",
    )
    assert config.datasets[0].dataset_role == C3DatasetRole.INTERNAL_ANCHOR
    assert all(item.invalid_claims for item in config.datasets)


def test_c3_registry_rejects_missing_required_dataset_field(tmp_path):
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        '''
stage: C3_public_dataset_registry
latest_source_calibration:
  enabled: true
  policy: watchlist_only
outputs:
  report: reports/c_stage_c3_public_dataset_registry.md
datasets:
  - dataset_id: missing_display_name
''',
        encoding="utf-8",
    )

    with pytest.raises(C3RegistryConfigError, match="display_name"):
        load_c3_registry_config(broken)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run python -m pytest tests/test_c3_public_dataset_registry.py::test_c3_default_registry_config_has_initial_dataset_set tests/test_c3_public_dataset_registry.py::test_c3_registry_rejects_missing_required_dataset_field -q
```

Expected: FAIL because module/config do not exist.

- [ ] **Step 3: Create default config**

Create `configs/c_stage_c3_public_dataset_registry.yaml`:

```yaml
stage: C3_public_dataset_registry
latest_source_calibration:
  enabled: true
  policy: watchlist_only
  note: "Only records whether new 2025-2026 candidates should enter watchlist; no dataset download in C3 first loop."
outputs:
  report: reports/c_stage_c3_public_dataset_registry.md
datasets:
  - dataset_id: fu13_internal
    display_name: FU13 Internal Device Data
    dataset_role: internal_anchor
    source_type: internal
    official_source_url: internal_no_public_url
    source_status: needs_review
    license_status: needs_review
    redistribution_status: needs_review
    training_use_status: needs_review
    task_families: [forecasting, imputation, representation, weak_label]
    label_semantics: "quality_flag, stage, and failure_proxy are weak or operational labels; no confirmed production fault/RUL labels."
    schema_mapping_status: mapped
    canonical_mapping_notes: "Already mapped to B08 canonical observations for FU13 pipeline validation."
    split_policy: time_or_cycle_split_required
    leakage_risks: "cycle reconstruction and stage metadata must not leak target labels into probes."
    allowed_metrics: [forecasting_mae, forecasting_rmse, mask_reconstruction_error, linear_probe_macro_f1]
    go_no_go_prerequisites:
      - internal_source_and_training_boundary_confirmed
      - weak_label_semantics_documented
    invalid_claims:
      - 不得解释为生产告警
      - 不得解释为 RUL 精确估计
      - 不得解释为自动维修建议
    next_action: "Confirm internal use boundary and keep as C3 anchor."
    risk_level: medium
```

Then add the four open benchmark candidate entries with the same required fields. Keep source/license/training fields as `needs_review` unless already proven by current repo evidence.

- [ ] **Step 4: Implement minimal loader**

Create dataclasses and loader:

```python
class C3RegistryConfigError(ValueError):
    pass

class C3DatasetRole(StrEnum):
    INTERNAL_ANCHOR = "internal_anchor"
    OPEN_BENCHMARK_CANDIDATE = "open_benchmark_candidate"
    WATCHLIST_CANDIDATE = "watchlist_candidate"

@dataclass(frozen=True)
class C3DatasetEntry:
    dataset_id: str
    display_name: str
    dataset_role: C3DatasetRole
    source_type: str
    official_source_url: str
    source_status: str
    license_status: str
    redistribution_status: str
    training_use_status: str
    task_families: tuple[str, ...]
    label_semantics: str
    schema_mapping_status: str
    canonical_mapping_notes: str
    split_policy: str
    leakage_risks: str
    allowed_metrics: tuple[str, ...]
    go_no_go_prerequisites: tuple[str, ...]
    invalid_claims: tuple[str, ...]
    next_action: str
    risk_level: str
```

Validation rules:
- `stage` must be `C3_public_dataset_registry`.
- dataset ids must be unique.
- all required fields must be present and non-empty.
- list fields must be non-empty lists.
- enum-like fields must match allowed values from the C3 spec:
  - `dataset_role`: `internal_anchor`, `open_benchmark_candidate`, `watchlist_candidate`
  - `source_type`: `internal`, `official_public`, `paper_hosted`, `repository`, `unknown`
  - `source_status`: `verified`, `needs_review`, `unavailable`, `deprecated`
  - `license_status`: `verified`, `needs_review`, `restricted`, `unknown`
  - `redistribution_status`: `allowed`, `not_allowed`, `needs_review`, `unknown`
  - `training_use_status`: `allowed`, `research_only`, `needs_review`, `not_allowed`, `unknown`
  - `schema_mapping_status`: `mapped`, `partial`, `planned`, `blocked`, `needs_review`
  - `risk_level`: `low`, `medium`, `high`

- [ ] **Step 5: Run tests to verify pass**

Run:

```bash
uv run python -m pytest tests/test_c3_public_dataset_registry.py::test_c3_default_registry_config_has_initial_dataset_set tests/test_c3_public_dataset_registry.py::test_c3_registry_rejects_missing_required_dataset_field -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add configs/c_stage_c3_public_dataset_registry.yaml \
  src/b08_model_core/experiments/c3_public_dataset_registry.py \
  tests/test_c3_public_dataset_registry.py
git commit -m "feat: add c3 public dataset registry config"
```

---

## Task 2: Validation Rules, Readiness Classification, And Report Renderer

**Files:**
- Modify: `src/b08_model_core/experiments/c3_public_dataset_registry.py`
- Modify: `tests/test_c3_public_dataset_registry.py`

- [ ] **Step 1: Write failing validation and report tests**

Add tests:

```python
def test_c3_registry_rejects_invalid_enum_value(tmp_path):
    text = Path("configs/c_stage_c3_public_dataset_registry.yaml").read_text(encoding="utf-8")
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        text.replace("license_status: needs_review", "license_status: verifed", 1),
        encoding="utf-8",
    )

    with pytest.raises(C3RegistryConfigError, match="license_status"):
        load_c3_registry_config(broken)


def test_c3_registry_does_not_allow_unknown_training_use_as_ready():
    config = load_c3_registry_config("configs/c_stage_c3_public_dataset_registry.yaml")
    result = run_c3_public_dataset_registry(config)

    by_id = {item.dataset_id: item for item in result.readiness}

    assert by_id["nasa_cmapss"].readiness == "needs_source_license_review"
    assert "training_use_status=needs_review" in by_id["nasa_cmapss"].reasons
    assert by_id["nasa_cmapss"].readiness != "ready_for_next_mapping"


def test_c3_registry_enforces_source_and_training_safety_rules(tmp_path):
    text = Path("configs/c_stage_c3_public_dataset_registry.yaml").read_text(encoding="utf-8")
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        text.replace("source_status: needs_review", "source_status: verified", 1)
            .replace("official_source_url: internal_no_public_url", "official_source_url: needs_review", 1)
            .replace("training_use_status: needs_review", "training_use_status: unknown", 1),
        encoding="utf-8",
    )

    with pytest.raises(C3RegistryConfigError, match="source_status|training_use_status"):
        load_c3_registry_config(broken)


def test_c3_registry_flags_split_policy_review_for_rul_and_process_data(tmp_path):
    text = Path("configs/c_stage_c3_public_dataset_registry.yaml").read_text(encoding="utf-8")
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        text.replace("split_policy: unit_run_split_required", "split_policy: time_split", 1),
        encoding="utf-8",
    )
    config = load_c3_registry_config(broken)

    result = run_c3_public_dataset_registry(config)
    by_id = {item.dataset_id: item for item in result.readiness}

    assert by_id["nasa_cmapss"].readiness == "split_policy_review"
    assert "unit_or_run_split_required_for_rul" in by_id["nasa_cmapss"].reasons


def test_c3_registry_flags_process_fault_leakage_review(tmp_path):
    text = Path("configs/c_stage_c3_public_dataset_registry.yaml").read_text(encoding="utf-8")
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        text.replace(
            "leakage_risks: \"Process fault trajectory, fault injection timing, and operating condition leakage must be guarded.\"",
            "leakage_risks: \"needs split review\"",
            1,
        ),
        encoding="utf-8",
    )
    config = load_c3_registry_config(broken)

    result = run_c3_public_dataset_registry(config)
    by_id = {item.dataset_id: item for item in result.readiness}

    assert by_id["tennessee_eastman_process"].readiness == "split_policy_review"
    assert "fault_or_condition_leakage_guard_required" in by_id["tennessee_eastman_process"].reasons


def test_c3_registry_report_contains_required_sections():
    config = load_c3_registry_config("configs/c_stage_c3_public_dataset_registry.yaml")
    result = run_c3_public_dataset_registry(config)
    text = render_c3_registry_report(result)

    assert "C3 Public Dataset Registry Report" in text
    assert "Dataset Readiness Table" in text
    assert "Source And License Audit" in text
    assert "Task And Metric Mapping" in text
    assert "Split Policy And Leakage Guard" in text
    assert "Latest Source Calibration Notes" in text
    assert "Invalid Claims" in text
    assert "不下载公开数据原始文件" in text
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run python -m pytest tests/test_c3_public_dataset_registry.py -q
```

Expected: FAIL because validation/report functions are incomplete.

- [ ] **Step 3: Implement validation and result dataclasses**

Add:

```python
@dataclass(frozen=True)
class C3DatasetReadiness:
    dataset_id: str
    readiness: str
    reasons: tuple[str, ...]
    next_action: str

@dataclass(frozen=True)
class C3RegistryRunResult:
    stage: str
    config_path: str | Path
    datasets: tuple[C3DatasetEntry, ...]
    readiness: tuple[C3DatasetReadiness, ...]
    latest_source_calibration: dict[str, Any]
    invalid_claims: tuple[str, ...]
```

Readiness categories:
- `ready_for_next_mapping`: source/license/redistribution/training/schema fields are not `unknown`, `needs_review`, `restricted`, `not_allowed`, or `blocked`, and split/leakage policy checks pass.
- `needs_source_license_review`: source/license/training/redistribution has `needs_review` or `unknown`.
- `task_mapping_review`: task family or allowed metric is outside allowed local vocabulary.
- `split_policy_review`: RUL/run-to-failure data does not declare unit/run split, or process monitoring / fault classification data does not declare fault trajectory or condition leakage guard.
- `watchlist_only`: `dataset_role == watchlist_candidate`.

Allowed task families:
`forecasting`, `imputation`, `representation`, `weak_label`, `fault_classification`, `rul`, `run_to_failure`, `anomaly_detection`, `process_monitoring`.

Safety and leakage rules:
- reject invalid enum-like values at load time; typo values must not silently become ready.
- if `official_source_url` is `needs_review`, `source_status` cannot be `verified`.
- if `training_use_status` is `unknown` and `next_action` implies ready/training-ready, reject the config.
- if `license_status` is `unknown` and `next_action` implies ready/training-ready, reject the config.
- for `rul` or `run_to_failure`, `split_policy` must contain `unit` or `run`; otherwise classify as `split_policy_review`.
- for `process_monitoring` or `fault_classification`, `leakage_risks` must mention `fault`, `trajectory`, `condition`, `工况`, or `故障`; otherwise classify as `split_policy_review`.

- [ ] **Step 4: Implement report renderer**

Render sections exactly from spec:
- Registry Summary
- Dataset Readiness Table
- Source And License Audit
- Task And Metric Mapping
- Canonical Schema Mapping Status
- Split Policy And Leakage Guard
- Latest Source Calibration Notes
- Go / No-Go For Next C3 Loop
- Invalid Claims

Include boundary line: `不下载公开数据原始文件，不提交公开数据或派生 parquet，不运行模型训练。`

- [ ] **Step 5: Run tests to verify pass**

Run:

```bash
uv run python -m pytest tests/test_c3_public_dataset_registry.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/b08_model_core/experiments/c3_public_dataset_registry.py tests/test_c3_public_dataset_registry.py
git commit -m "feat: render c3 public dataset registry report"
```

---

## Task 3: CLI Integration

**Files:**
- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_c3_public_dataset_registry.py`

- [ ] **Step 1: Write failing CLI test**

Add:

```python
def test_cli_c_stage_c3_writes_registry_report(tmp_path):
    output = tmp_path / "c3_registry.md"

    exit_code = main([
        "experiment",
        "c-stage-c3",
        "--config",
        "configs/c_stage_c3_public_dataset_registry.yaml",
        "--output",
        str(output),
    ])

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "C3 Public Dataset Registry Report" in text
    assert "fu13_internal" in text
    assert "nasa_cmapss" in text
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run python -m pytest tests/test_c3_public_dataset_registry.py::test_cli_c_stage_c3_writes_registry_report -q
```

Expected: FAIL because CLI does not know `c-stage-c3`.

- [ ] **Step 3: Add CLI imports and parser**

In `src/b08_model_core/cli.py`, import:

```python
from b08_model_core.experiments.c3_public_dataset_registry import (
    load_c3_registry_config,
    render_c3_registry_report,
    run_c3_public_dataset_registry,
)
```

Add parser near other C-stage commands:

```python
c_stage_c3 = experiment_sub.add_parser("c-stage-c3")
c_stage_c3.add_argument("--config", required=True)
c_stage_c3.add_argument("--output", required=True)
```

Add branch:

```python
if args.command == "experiment" and args.experiment_command == "c-stage-c3":
    try:
        config = load_c3_registry_config(args.config)
        result = run_c3_public_dataset_registry(config, config_path=args.config)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_c3_registry_report(result), encoding="utf-8")
    except (FileNotFoundError, ValueError, OSError, PermissionError):
        return 1
    return 0
```

- [ ] **Step 4: Run CLI test to verify pass**

Run:

```bash
uv run python -m pytest tests/test_c3_public_dataset_registry.py::test_cli_c_stage_c3_writes_registry_report -q
```

Expected: PASS.

- [ ] **Step 5: Run focused C3 tests**

Run:

```bash
uv run python -m pytest tests/test_c3_public_dataset_registry.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/b08_model_core/cli.py tests/test_c3_public_dataset_registry.py
git commit -m "feat: add c3 registry cli"
```

---

## Task 4: README / details Update And Regression

**Files:**
- Modify: `README.md`
- Modify: `details.md`
- Modify: `tests/test_experiment_scaffold.py` if needed for documentation contract

- [ ] **Step 1: Write or update doc contract test if needed**

If no existing test checks the new C3 entry, add to `tests/test_experiment_scaffold.py`:

```python
def test_c3_public_dataset_registry_workflow_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "c-stage-c3" in readme
    assert "configs/c_stage_c3_public_dataset_registry.yaml" in readme
    assert "reports/c_stage_c3_public_dataset_registry.md" in readme
    assert "不下载公开数据" in readme
    assert "C3" in details
```

- [ ] **Step 2: Run doc test to verify failure**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c3_public_dataset_registry_workflow_is_documented -q
```

Expected: FAIL until README/details mention the C3 entry.

- [ ] **Step 3: Update README**

Add a short C3 section under C-stage entries:

    ### C3. 公开数据 registry 与跨数据验证准备

    ```bash
    uv run b08-model-core experiment c-stage-c3 \
      --config configs/c_stage_c3_public_dataset_registry.yaml \
      --output reports/c_stage_c3_public_dataset_registry.md
    ```

    C3 第一轮只验证公开数据 registry、来源/许可证/任务/schema/split 边界和报告，不下载公开数据、不提交数据文件、不运行模型训练。

- [ ] **Step 4: Update details**

In `details.md`, keep the three-section format. Add one 2026-06-09 ledger row or extend the current next-step plan to mention C3 registry implementation entry. Do not add a fourth section.

- [ ] **Step 5: Run docs and all focused C3 tests**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py tests/test_c3_public_dataset_registry.py -q
```

Expected: PASS.

- [ ] **Step 6: Run full tests**

Run:

```bash
uv run python -m pytest -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add README.md details.md tests/test_experiment_scaffold.py
git commit -m "docs: document c3 registry workflow"
```

---

## Final Verification

After all tasks and reviews:

```bash
git diff --check
uv run python -m pytest -q
git status --short --branch
```

Expected:
- no diff check output
- full test suite passes
- working tree clean on `codex/c3-public-dataset-registry`

Then use `superpowers:finishing-a-development-branch`.
