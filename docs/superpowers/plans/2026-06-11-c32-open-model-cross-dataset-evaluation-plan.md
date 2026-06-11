# C3.2 Open Model Cross-Dataset Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a default-safe C3.2 cross-dataset evaluation contract/report scaffold that moves the project beyond C3.1 without running models, reading raw data, or claiming benchmark results.

**Architecture:** Follow existing C-stage experiment patterns: YAML config -> dataclass loader/validator -> pure runner -> Markdown renderer -> CLI command -> docs/tests. The default runner only evaluates contract readiness and safety policy. Explicit local raw/model execution remains a future branch.

**Tech Stack:** Python dataclasses, `yaml.safe_load`, existing `b08_model_core.cli` command structure, `pytest`, Markdown docs.

---

## File Structure

- Create `configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml`
  - Default-safe C3.2 config.
  - Records C3.1 prerequisite evidence, dataset views, task contracts, model candidates, metrics, safety policy and report output.
- Create `src/b08_model_core/experiments/c32_open_model_cross_dataset_evaluation.py`
  - Defines config/result dataclasses, loader validation, pure contract runner, and Markdown renderer.
  - Must not read C-MAPSS raw files, FU13 real files, model cache paths, or instantiate adapters.
- Modify `src/b08_model_core/cli.py`
  - Adds `experiment c-stage-c32 --config --output`.
  - Imports and calls C3.2 loader/runner/renderer.
- Create `tests/test_c32_open_model_cross_dataset_evaluation.py`
  - Unit and CLI tests for config validation, default safety, readiness, negative no-touch behavior, and report content.
- Modify `tests/test_experiment_scaffold.py`
  - Adds README/details assertions for C3.2 workflow and verifies C2/C3/C3.1 help entries remain documented.
- Modify `README.md`
  - Adds C3.2 command and boundary section after C3.1.
- Modify `details.md`
  - Updates current stage and next plan from C3.2 design to C3.2 contract scaffold completed / next local execution design.

---

## Task 1: C3.2 Config Contract

**Files:**
- Create: `configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml`
- Create: `src/b08_model_core/experiments/c32_open_model_cross_dataset_evaluation.py`
- Test: `tests/test_c32_open_model_cross_dataset_evaluation.py`

- [ ] **Step 1: Write failing tests for config loading and safety**

Add tests:

```python
from pathlib import Path

import pytest
import yaml

from b08_model_core.experiments.c32_open_model_cross_dataset_evaluation import (
    C32ConfigError,
    load_c32_config,
)


_DEFAULT_CONFIG = Path("configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml")


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
    assert config.prerequisites.required_readiness_detail == "full_classic_cmapss_validated"
    assert config.prerequisites.reviewed_raw_file_count == 12
    assert config.prerequisites.leakage_guard_passed is True
```

Add tests for wrong stage, unsafe default flags, duplicate ids and missing required sections.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c32_open_model_cross_dataset_evaluation.py -q
```

Expected: FAIL because C3.2 module/config do not exist.

- [ ] **Step 3: Add default config**

Create YAML with these defaults:

```yaml
stage: C3_2_open_model_cross_dataset_evaluation
safety_policy:
  allow_network: false
  allow_download: false
  allow_local_raw_data: false
  allow_model_cache: false
  allow_training: false
  allow_write_processed: false
prerequisites:
  c31_review_doc: docs/reviews/2026-06-11-c31-cmapss-local-raw-mapping-review.md
  required_status: schema_validated_ready_for_c32
  required_readiness_detail: full_classic_cmapss_validated
  reviewed_raw_file_count: 12
  leakage_guard_passed: true
dataset_views:
  - dataset_id: cmapss_classic_rul
    display_name: NASA C-MAPSS Classic RUL
    status: eligible_but_local_raw_required
    source: c31_local_raw_mapping_review
    local_path: data/public/cmapss/raw
    task_families: [rul_regression]
    default_action: skipped_local_raw_disabled
    comparable_scope: public_rul_degradation_only
  - dataset_id: fu13_real_forecasting_evidence
    display_name: FU13 Real Forecasting Evidence
    status: documented_evidence_only
    source: existing_fu13_pipeline
    local_path: data/processed/fu13_real_observations.parquet
    task_families: [forecasting_residual]
    default_action: skipped_real_data_not_read_by_default
    comparable_scope: internal_forecasting_evidence_only
  - dataset_id: fu13_like_simulated_forecasting
    display_name: FU13-like Simulated Forecasting
    status: contract_ready_no_scoring
    source: simulation_scaffold
    local_path: ""
    task_families: [forecasting_residual]
    default_action: contract_only_no_metrics
    comparable_scope: sandbox_contract_reference
task_contracts:
  - task_id: rul_regression
    status: blocked_in_default
    compatible_dataset_views: [cmapss_classic_rul]
    required_metrics: [rul_mae, rul_rmse, nasa_score]
    default_action: skipped_local_raw_disabled
  - task_id: forecasting_residual
    status: contract_ready_no_scoring
    compatible_dataset_views:
      - fu13_real_forecasting_evidence
      - fu13_like_simulated_forecasting
    required_metrics: [forecasting_mae, forecasting_rmse, residual_ranking]
    default_action: contract_only_no_metrics
  - task_id: representation_diagnostics
    status: planned_not_executed
    compatible_dataset_views:
      - fu13_real_forecasting_evidence
      - fu13_like_simulated_forecasting
    required_metrics: [embedding_probe_placeholder]
    default_action: skipped_planned_task
model_candidates:
  - model_id: baseline
    role: required_baseline
    status: contract_ready_no_scoring
    task_ids: [rul_regression, forecasting_residual]
    default_action: contract_only_no_model_run
  - model_id: ttm
    role: optional_open_model
    status: skipped_model_cache_disabled
    task_ids: [forecasting_residual]
    default_action: skipped_no_cache_or_dependencies
  - model_id: chronos
    role: optional_open_model
    status: skipped_model_cache_disabled
    task_ids: [forecasting_residual]
    default_action: skipped_no_cache_or_dependencies
  - model_id: timesfm
    role: optional_open_model
    status: skipped_model_cache_disabled
    task_ids: [forecasting_residual]
    default_action: skipped_no_cache_or_dependencies
  - model_id: moirai
    role: optional_open_model
    status: skipped_model_cache_disabled
    task_ids: [forecasting_residual]
    default_action: skipped_no_cache_or_dependencies
  - model_id: moment
    role: representation_candidate
    status: planned_not_executed
    task_ids: [representation_diagnostics]
    default_action: skipped_planned_task
  - model_id: units
    role: representation_candidate
    status: planned_not_executed
    task_ids: [representation_diagnostics]
    default_action: skipped_planned_task
metric_contract:
  rul_metrics: [rul_mae, rul_rmse, nasa_score]
  forecasting_metrics: [forecasting_mae, forecasting_rmse, residual_ranking]
  cross_dataset_summary: readiness_matrix_only
  leaderboard_allowed: false
outputs:
  report: reports/c_stage_c32_open_model_cross_dataset_evaluation.md
```

- [ ] **Step 4: Implement loader/validator dataclasses**

In the C3.2 module:

- `C32ConfigError`
- `C32SafetyPolicy`
- `C32Prerequisites`
- `C32DatasetView`
- `C32TaskContract`
- `C32ModelCandidate`
- `C32MetricContract`
- `C32Outputs`
- `C32Config`
- `load_c32_config(path)`

Validation rules:

- Stage must equal `C3_2_open_model_cross_dataset_evaluation`.
- Safety defaults must all be false in the default config.
- Required sections must exist and be mappings/lists as appropriate.
- Dataset/task/model ids must be unique and non-empty.
- Task contracts must reference known dataset ids.
- Model candidates must reference known task ids.
- Metric contract must set `leaderboard_allowed: false`.

- [ ] **Step 5: Run Task 1 tests**

Run:

```bash
uv run python -m pytest tests/test_c32_open_model_cross_dataset_evaluation.py -q
```

Expected: config tests pass; runner/CLI tests not yet written.

- [ ] **Step 6: Commit Task 1**

```bash
git add configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml \
  src/b08_model_core/experiments/c32_open_model_cross_dataset_evaluation.py \
  tests/test_c32_open_model_cross_dataset_evaluation.py
git commit -m "feat: add c32 evaluation config contract"
```

---

## Task 2: Runner, Report, And CLI

**Files:**
- Modify: `src/b08_model_core/experiments/c32_open_model_cross_dataset_evaluation.py`
- Modify: `src/b08_model_core/cli.py`
- Test: `tests/test_c32_open_model_cross_dataset_evaluation.py`

- [ ] **Step 1: Write failing runner/report tests**

Add tests:

```python
from b08_model_core.experiments.c32_open_model_cross_dataset_evaluation import (
    render_c32_report,
    run_c32_open_model_cross_dataset_evaluation,
)


def test_c32_runner_returns_contract_ready_local_execution_blocked():
    config = load_c32_config(_DEFAULT_CONFIG)
    result = run_c32_open_model_cross_dataset_evaluation(config, config_path=_DEFAULT_CONFIG)

    assert result.status == "contract_ready_local_execution_blocked"
    assert result.go_no_go_decision == "Go for C3.2 local execution design"
    assert result.invalid_claims
    assert all(item.status for item in result.dataset_results)
    assert all(item.default_action for item in result.model_results)


def test_c32_report_records_no_scoring_and_no_production_claims():
    config = load_c32_config(_DEFAULT_CONFIG)
    result = run_c32_open_model_cross_dataset_evaluation(config, config_path=_DEFAULT_CONFIG)
    text = render_c32_report(result)

    assert "C3.2 Open Model Cross-Dataset Evaluation Report" in text
    assert "contract_ready_local_execution_blocked" in text
    assert "schema_validated_ready_for_c32" in text
    assert "full_classic_cmapss_validated" in text
    assert "readiness_matrix_only" in text
    assert "No model training, scoring, or leaderboard is executed" in text
    assert "Do not claim production RUL" in text
```

- [ ] **Step 2: Write failing no-touch test**

Use impossible paths to prove default runner does not inspect local data/cache paths:

```python
def test_c32_default_runner_does_not_touch_raw_real_or_cache_paths(tmp_path):
    data = yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
    data["dataset_views"][0]["local_path"] = str(tmp_path / "missing_cmapss_raw")
    data["dataset_views"][1]["local_path"] = str(tmp_path / "missing_fu13_real.parquet")
    data["model_cache_policy"] = {"cache_dir": str(tmp_path / "missing_model_cache")}
    config_path = tmp_path / "c32_no_touch.yaml"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    config = load_c32_config(config_path)
    result = run_c32_open_model_cross_dataset_evaluation(config, config_path=config_path)

    assert result.status == "contract_ready_local_execution_blocked"
```

If the implementation accidentally inspects paths, this test will fail.

- [ ] **Step 3: Implement runner result dataclasses**

Add:

- `C32DatasetResult`
- `C32TaskResult`
- `C32ModelResult`
- `C32RunResult`
- `run_c32_open_model_cross_dataset_evaluation(config, config_path)`

The runner should:

- Copy config contract rows into result rows.
- Set status `contract_ready_local_execution_blocked`.
- Set decision `Go for C3.2 local execution design`.
- Include invalid claims:
  - no production RUL
  - no production alarms
  - no maintenance recommendations
  - no benchmark leaderboard
  - no self-developed model superiority
- Never call `Path.exists()` on configured local raw, real data, or cache paths.
- Never import or instantiate open model adapters.

- [ ] **Step 4: Implement Markdown renderer**

Report sections:

- Title and scope
- Summary
- Safety Policy
- C3.1 Prerequisites
- Dataset View Matrix
- Task Compatibility
- Model Candidate Status
- Metric Contract
- Go / No-Go
- Invalid Claims
- Next Step

- [ ] **Step 5: Add CLI command**

In `src/b08_model_core/cli.py`:

- Import `load_c32_config`, `run_c32_open_model_cross_dataset_evaluation`, `render_c32_report`.
- Add parser:

```python
c_stage_c32 = experiment_sub.add_parser("c-stage-c32")
c_stage_c32.add_argument("--config", required=True)
c_stage_c32.add_argument("--output", required=True)
```

- Add dispatch branch after C3.1 or C3:

```python
if args.command == "experiment" and args.experiment_command == "c-stage-c32":
    try:
        config = load_c32_config(args.config)
        result = run_c32_open_model_cross_dataset_evaluation(config, config_path=args.config)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_c32_report(result), encoding="utf-8")
    except (FileNotFoundError, ValueError, OSError, PermissionError):
        return 1
    return 0
```

- [ ] **Step 6: Add CLI test**

```python
from b08_model_core.cli import main


def test_cli_c_stage_c32_writes_contract_report(tmp_path):
    output = tmp_path / "c32_report.md"
    exit_code = main(
        [
            "experiment",
            "c-stage-c32",
            "--config",
            "configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "C3.2 Open Model Cross-Dataset Evaluation Report" in text
    assert "contract_ready_local_execution_blocked" in text
```

- [ ] **Step 7: Run Task 2 tests**

```bash
uv run python -m pytest tests/test_c32_open_model_cross_dataset_evaluation.py -q
uv run b08-model-core experiment c-stage-c32 \
  --config configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml \
  --output /tmp/c32_contract_report.md
rg -n "Status:|Decision:|No model training|leaderboard|schema_validated_ready_for_c32" /tmp/c32_contract_report.md
```

Expected: tests pass, CLI exits 0, report contains contract-ready/no-scoring lines.

- [ ] **Step 8: Commit Task 2**

```bash
git add src/b08_model_core/experiments/c32_open_model_cross_dataset_evaluation.py \
  src/b08_model_core/cli.py \
  tests/test_c32_open_model_cross_dataset_evaluation.py
git commit -m "feat: add c32 evaluation contract report"
```

---

## Task 3: README And Details

**Files:**
- Modify: `README.md`
- Modify: `details.md`
- Modify: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Write failing docs regression tests**

Extend `test_c31_cmapss_minimal_ingestion_workflow_is_documented` or add a new test:

```python
def test_c32_cross_dataset_evaluation_workflow_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "### C3.2. Open model cross-dataset evaluation" in readme
    assert "c-stage-c32" in readme
    assert "configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml" in readme
    assert "allow_local_raw_data: false" in readme
    assert "allow_model_cache: false" in readme
    assert "不运行模型训练" in readme
    assert "不生成 leaderboard" in readme
    assert "C3.2" in details
    assert "contract_ready_local_execution_blocked" in details
    assert "local execution design" in details
```

- [ ] **Step 2: Run docs test to verify it fails**

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c32_cross_dataset_evaluation_workflow_is_documented -q
```

Expected: FAIL because README/details do not yet include C3.2 section.

- [ ] **Step 3: Update README**

Add a C3.2 section after C3.1:

```markdown
### C3.2. Open model cross-dataset evaluation

```bash
uv run b08-model-core experiment c-stage-c32 \
  --config configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml \
  --output reports/c_stage_c32_open_model_cross_dataset_evaluation.md
```

Default C3.2 only renders the cross-dataset evaluation contract...
```

Mention:

- C-MAPSS + FU13 / FU13-like scope.
- Default status `contract_ready_local_execution_blocked`.
- Default does not download, read raw, read real data, inspect model cache, run adapters, train, score, or produce leaderboard.
- Next branch should be explicit local execution design.

- [ ] **Step 4: Update details.md**

Update:

- Current stage: C3.2 contract scaffold.
- Daily row for 2026-06-11 or same date continuation.
- Next plan:
  1. C3.2 explicit local execution design.
  2. C-MAPSS RUL baseline first.
  3. FU13-like forecasting reference second.
  4. Keep metrics separated and no leaderboard.

- [ ] **Step 5: Run docs tests**

```bash
uv run python -m pytest tests/test_experiment_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add README.md details.md tests/test_experiment_scaffold.py
git commit -m "docs: document c32 evaluation workflow"
```

---

## Task 4: Final Verification, PR, Merge, Cleanup

**Files:**
- No source edits expected unless verification finds a bug.

- [ ] **Step 1: Run targeted tests**

```bash
uv run python -m pytest tests/test_c32_open_model_cross_dataset_evaluation.py -q
uv run python -m pytest tests/test_experiment_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full suite**

```bash
uv run python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run C3.2 CLI**

```bash
uv run b08-model-core experiment c-stage-c32 \
  --config configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml \
  --output /tmp/c32_contract_report.md
rg -n "Status:|Decision:|contract_ready_local_execution_blocked|No model training|Do not claim" /tmp/c32_contract_report.md
```

Expected:

- exit 0
- status `contract_ready_local_execution_blocked`
- no training/scoring/leaderboard/prod claims

- [ ] **Step 4: Run regression CLI help checks**

```bash
uv run b08-model-core experiment c-stage-c2 --help >/tmp/c32_help_c2.txt
uv run b08-model-core experiment c-stage-c21 --help >/tmp/c32_help_c21.txt
uv run b08-model-core experiment c-stage-c22 --help >/tmp/c32_help_c22.txt
uv run b08-model-core experiment c-stage-c3 --help >/tmp/c32_help_c3.txt
uv run b08-model-core experiment c-stage-c31 --help >/tmp/c32_help_c31.txt
uv run b08-model-core experiment c-stage-c32 --help >/tmp/c32_help_c32.txt
```

Expected: all exit 0.

- [ ] **Step 5: Safety audit**

```bash
git diff --check HEAD
git status --short
git ls-files data/public data/processed reports/c_stage_c32_open_model_cross_dataset_evaluation.md
```

Expected:

- no diff whitespace errors
- tracked status clean after commits
- no tracked raw/processed/generated report files

- [ ] **Step 6: Subagent review**

Dispatch one code review subagent with these checks:

- C3.2 default CLI does not touch raw/real/cache paths or adapters.
- Safety policy is validated.
- Report does not overclaim training/scoring/leaderboard.
- README/details reflect the new stage.

Fix blocking issues, re-run relevant tests, and commit fixes.

- [ ] **Step 7: Push and create PR**

```bash
git push -u origin codex/c32-open-model-cross-dataset-eval
gh pr create --base main --head codex/c32-open-model-cross-dataset-eval \
  --title "Add C3.2 cross-dataset evaluation contract scaffold" \
  --body-file /tmp/c32_pr_body.md
```

PR body should include summary, safety boundary, and verification commands.

- [ ] **Step 8: Merge PR remotely**

```bash
gh pr view <PR> --json mergeStateStatus,isDraft,statusCheckRollup
gh pr merge <PR> --squash --delete-branch \
  --subject "Add C3.2 cross-dataset evaluation contract scaffold" \
  --body "Add a default-safe C3.2 contract/report scaffold and document the next local execution step."
```

If `gh pr merge` reports local checkout/worktree issues but PR state is `MERGED`, treat the remote state as authoritative and continue cleanup.

- [ ] **Step 9: Cleanup local branch/worktree**

From feature worktree first:

```bash
git status --short
```

From main workspace:

```bash
git fetch origin --prune
git merge --ff-only origin/main
git worktree remove .worktrees/c32-open-model-cross-dataset-eval
git branch -D codex/c32-open-model-cross-dataset-eval
git branch -r --list 'origin/codex/c32-open-model-cross-dataset-eval'
git status --short --branch
git worktree list
```

Expected:

- main fast-forwarded to PR merge commit
- feature worktree removed
- local and remote feature branches gone

- [ ] **Step 10: Final summary**

Summarize in Chinese:

- What C3.2 now does.
- What it explicitly does not do.
- Verification evidence.
- PR URL and merge status.
- Next stage: explicit local execution for C-MAPSS RUL baseline + FU13-like forecasting reference, with metrics separated and no leaderboard.
