# C3.4 Open Model Expansion Decision Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add C3.4 as a default-safe decision review stage that decides whether C3.3 TTM evidence is strong enough to design one second forecasting open model candidate.

**Architecture:** Add a new C-stage experiment module instead of changing C3.3 behavior. C3.4 loads a default offline config, validates C3.3 evidence status against an explicit mapping table, renders a decision report, and never imports or runs open model adapters.

**Tech Stack:** Python dataclasses, YAML config loading via `yaml.safe_load`, existing CLI argparse pattern, pytest, Markdown reports.

---

## File Structure

- Create: `configs/c_stage_c34_open_model_expansion_decision_review.yaml`
  - Default contract-only C3.4 decision review config.
- Create: `configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml`
  - Explicit local-evidence review example. It records reviewed C3.3 evidence, but still does not run adapters or inspect cache.
- Create: `src/b08_model_core/experiments/c34_open_model_expansion_decision_review.py`
  - Owns C3.4 config dataclasses, validation, C3.3-to-C3.4 status mapping, report rendering, and runner.
- Modify: `src/b08_model_core/cli.py`
  - Import C3.4 loader/runner/renderer and register `experiment c-stage-c34`.
- Create: `tests/test_c34_open_model_expansion_decision_review.py`
  - C3.4 config, mapping, report, and CLI tests.
- Modify: `tests/test_experiment_scaffold.py`
  - README/details C3.4 command and doc entry checks.
- Modify: `README.md`
  - Add C3.4 section after C3.3 and doc links.
- Modify: `details.md`
  - Update current stage, daily log, and next plan from C3.4 to C3.5 or evidence remediation.

## Shared Constants And Field Rules

C3.4 accepted C3.3 evidence statuses:

```python
CONTRACT_READY = "contract_ready_single_candidate_local_execution_blocked"
TTM_READY = "local_execution_ttm_forecasting_ready"
TTM_MISSING_DEPENDENCY = "local_execution_ttm_missing_dependency"
TTM_MISSING_OR_BLOCKED_WEIGHTS = "local_execution_ttm_missing_or_blocked_weights"
TTM_UNSUPPORTED_WINDOW_SHAPE = "local_execution_ttm_unsupported_window_shape"
TTM_RUNTIME_FAILED = "local_execution_ttm_runtime_failed"
INSUFFICIENT_WINDOWS = "blocked_insufficient_fu13_like_windows"
```

C3.4 decision statuses:

```python
HOLD = "hold_candidate_expansion_pending_ttm_local_evidence"
READY = "candidate_expansion_design_ready"
BLOCKED = "blocked_candidate_expansion_due_to_ttm_evidence_gap"
```

Adapter evidence validation:

- Default contract-only uses `adapter_evidence: not_applicable_default_contract`; it must not require runtime, shape, network, or download fields.
- Ready evidence requires:
  - `dependency_status`: non-empty string.
  - `weight_status`: non-empty string.
  - `adapter_status`: non-empty string.
  - `runtime_seconds`: number, `int` or `float`, `>= 0`; bool is invalid.
  - `input_shape`: non-empty mapping.
  - `output_shape`: non-empty mapping.
  - `actual_network_used`: boolean or string sentinel such as `unknown_not_reported`; bool preferred.
  - `download_allowed_not_verified`: boolean.
- Missing dependency / missing weights / runtime failed requires:
  - `failure_reason`: non-empty string.
  - `dependency_status`: non-empty string.
  - `weight_status`: non-empty string.
- Unsupported window shape additionally requires at least one non-empty `input_shape` or `output_shape`.
- Insufficient windows requires `blocked_reason` or `failure_reason`; no adapter evidence fields are required.
- Unknown C3.3 status is config error.

Candidate review rows are review-only for:

- `chronos_bolt_route`
- `timesfm_2_5_route`
- `moirai_uni2ts_route`

Each row should include candidate id, display name, C2.2 source, readiness status `review_only_not_promoted`, promotion blocker, and next design requirement.

## Task 1: C3.4 Config Contract And Default Report

**Files:**
- Create: `configs/c_stage_c34_open_model_expansion_decision_review.yaml`
- Create: `src/b08_model_core/experiments/c34_open_model_expansion_decision_review.py`
- Create: `tests/test_c34_open_model_expansion_decision_review.py`

- [ ] **Step 1: Write failing tests for default config and report**

Add tests:

```python
from pathlib import Path

import pytest
import yaml

from b08_model_core.experiments.c34_open_model_expansion_decision_review import (
    C34ConfigError,
    load_c34_config,
    render_c34_report,
    run_c34_open_model_expansion_decision_review,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs/c_stage_c34_open_model_expansion_decision_review.yaml"


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def test_c34_default_config_is_offline_decision_review_only():
    config = load_c34_config(DEFAULT_CONFIG)

    assert config.stage == "C3_4_open_model_expansion_decision_review"
    assert config.safety_policy.allow_network is False
    assert config.safety_policy.allow_download is False
    assert config.safety_policy.allow_model_cache is False
    assert config.safety_policy.allow_local_execution is False
    assert config.safety_policy.allow_training is False
    assert config.safety_policy.allow_write_processed is False
    assert config.c33_evidence.source == "default_contract"
    assert config.c33_evidence.status == "contract_ready_single_candidate_local_execution_blocked"
    assert config.c33_evidence.adapter_evidence == "not_applicable_default_contract"
    assert config.decision_policy.leaderboard_allowed is False
    assert config.decision_policy.rul_open_model_allowed is False
    assert config.decision_policy.second_candidate_execution_allowed is False


def test_c34_default_runner_holds_candidate_expansion():
    config = load_c34_config(DEFAULT_CONFIG)
    result = run_c34_open_model_expansion_decision_review(config, DEFAULT_CONFIG)
    text = render_c34_report(result)

    assert result.status == "hold_candidate_expansion_pending_ttm_local_evidence"
    assert "C3.3 Evidence Gate" in text
    assert "Candidate Expansion Review" in text
    assert "review_only_not_promoted" in text
    assert "No leaderboard" in text
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c34_open_model_expansion_decision_review.py -q
```

Expected: FAIL because C3.4 module/config do not exist.

- [ ] **Step 3: Add default config**

Create `configs/c_stage_c34_open_model_expansion_decision_review.yaml`:

```yaml
stage: C3_4_open_model_expansion_decision_review
safety_policy:
  allow_network: false
  allow_download: false
  allow_model_cache: false
  allow_local_execution: false
  allow_training: false
  allow_write_processed: false
prerequisites:
  c33_design_doc: docs/superpowers/specs/2026-06-22-c33-single-candidate-open-model-local-evaluation-design.md
  c33_default_status: contract_ready_single_candidate_local_execution_blocked
  c32_local_status: local_execution_baseline_reference_ready
  c22_watchlist_source: configs/c_stage_c22_open_model_executable_upgrade.yaml
c33_evidence:
  source: default_contract
  status: contract_ready_single_candidate_local_execution_blocked
  candidate: ttm
  task: fu13_like_forecasting
  adapter_evidence: not_applicable_default_contract
decision_policy:
  require_ttm_status: local_execution_ttm_forecasting_ready
  required_adapter_fields:
    - dependency_status
    - weight_status
    - adapter_status
    - runtime_seconds
    - input_shape
    - output_shape
    - actual_network_used
    - download_allowed_not_verified
  leaderboard_allowed: false
  rul_open_model_allowed: false
  second_candidate_execution_allowed: false
candidate_review:
  - candidate_id: chronos_bolt_route
    display_name: Chronos / Chronos-Bolt
    c22_source: chronos
    readiness_status: review_only_not_promoted
    promotion_blocker: package, license, cache, API shape, and resource review required
    next_design_requirement: design one FU13-like forecasting adapter/cache path before execution
  - candidate_id: timesfm_2_5_route
    display_name: TimesFM 2.5
    c22_source: timesfm
    readiness_status: review_only_not_promoted
    promotion_blocker: package, weights, license, resource, and forecasting API review required
    next_design_requirement: verify deterministic PyTorch cache path and FU13-like shape contract
  - candidate_id: moirai_uni2ts_route
    display_name: Moirai / Uni2TS
    c22_source: moirai_uni2ts
    readiness_status: review_only_not_promoted
    promotion_blocker: dependency, checkpoint compatibility, probabilistic output shape review required
    next_design_requirement: resolve Uni2TS dependency and output shape before local execution design
outputs:
  report: reports/c_stage_c34_open_model_expansion_decision_review.md
```

- [ ] **Step 4: Implement minimal C3.4 module**

Create dataclasses:

```python
@dataclass(frozen=True)
class C34SafetyPolicy:
    allow_network: bool
    allow_download: bool
    allow_model_cache: bool
    allow_local_execution: bool
    allow_training: bool
    allow_write_processed: bool

@dataclass(frozen=True)
class C34Prerequisites:
    c33_design_doc: Path
    c33_default_status: str
    c32_local_status: str
    c22_watchlist_source: Path

@dataclass(frozen=True)
class C34C33Evidence:
    source: str
    status: str
    candidate: str
    task: str
    adapter_evidence: str | dict[str, Any]

@dataclass(frozen=True)
class C34DecisionPolicy:
    require_ttm_status: str
    required_adapter_fields: tuple[str, ...]
    leaderboard_allowed: bool
    rul_open_model_allowed: bool
    second_candidate_execution_allowed: bool

@dataclass(frozen=True)
class C34CandidateReview:
    candidate_id: str
    display_name: str
    c22_source: str
    readiness_status: str
    promotion_blocker: str
    next_design_requirement: str
```

Implement:

- `load_c34_config(path)`.
- Strict stage validation.
- Safety policy validation: all flags must be false.
- Decision policy validation: required adapter fields must exactly match the shared constant, all allow flags false.
- Default evidence validation: `adapter_evidence` must equal `not_applicable_default_contract`.
- Candidate review validation: exactly three candidate ids listed above, each readiness `review_only_not_promoted`.
- `run_c34_open_model_expansion_decision_review(config, config_path)` returns status from mapping.
- `render_c34_report(result)`.

Report sections:

- Summary
- Safety Policy
- C3.3 Evidence Gate
- Decision Policy
- Candidate Expansion Review
- Metric Separation
- Go / No-Go
- Invalid Claims
- Next Step

- [ ] **Step 5: Run tests and verify pass**

Run:

```bash
uv run python -m pytest tests/test_c34_open_model_expansion_decision_review.py -q
```

Expected: PASS for Task 1 tests.

- [ ] **Step 6: Commit**

```bash
git add configs/c_stage_c34_open_model_expansion_decision_review.yaml \
  src/b08_model_core/experiments/c34_open_model_expansion_decision_review.py \
  tests/test_c34_open_model_expansion_decision_review.py
git commit -m "feat: add c34 decision review contract"
```

## Task 2: C3.3 Evidence Mapping And Local Evidence Example

**Files:**
- Create: `configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml`
- Modify: `src/b08_model_core/experiments/c34_open_model_expansion_decision_review.py`
- Modify: `tests/test_c34_open_model_expansion_decision_review.py`

- [ ] **Step 1: Write failing tests for accepted status mapping**

Add tests:

```python
def test_c34_ready_c33_evidence_allows_candidate_expansion_design(tmp_path):
    data = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    data["c33_evidence"] = {
        "source": "explicit_local_reviewed",
        "status": "local_execution_ttm_forecasting_ready",
        "candidate": "ttm",
        "task": "fu13_like_forecasting",
        "adapter_evidence": {
            "dependency_status": "available",
            "weight_status": "available",
            "adapter_status": "available_and_ran",
            "runtime_seconds": 0.01,
            "input_shape": {"windows": 18, "X": [32, 8]},
            "output_shape": {"predictions": [18, 8, 8]},
            "actual_network_used": False,
            "download_allowed_not_verified": False,
        },
    }
    config = load_c34_config(_write_yaml(tmp_path / "ready.yaml", data))
    result = run_c34_open_model_expansion_decision_review(config, tmp_path / "ready.yaml")

    assert result.status == "candidate_expansion_design_ready"
    assert "C3.5 second forecasting candidate design" in render_c34_report(result)


@pytest.mark.parametrize(
    "c33_status",
    [
        "local_execution_ttm_missing_dependency",
        "local_execution_ttm_missing_or_blocked_weights",
        "local_execution_ttm_runtime_failed",
    ],
)
def test_c34_blocker_c33_evidence_blocks_candidate_expansion(tmp_path, c33_status):
    data = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    data["c33_evidence"] = {
        "source": "explicit_local_reviewed",
        "status": c33_status,
        "candidate": "ttm",
        "task": "fu13_like_forecasting",
        "adapter_evidence": {
            "failure_reason": "cache miss",
            "dependency_status": "available",
            "weight_status": "missing_or_blocked",
        },
    }
    config = load_c34_config(_write_yaml(tmp_path / "blocked.yaml", data))
    result = run_c34_open_model_expansion_decision_review(config, tmp_path / "blocked.yaml")

    assert result.status == "blocked_candidate_expansion_due_to_ttm_evidence_gap"
```

Also add tests:

- unsupported window shape requires `input_shape` or `output_shape`.
- insufficient windows maps to hold and requires `blocked_reason` or `failure_reason`.
- unknown C3.3 status raises `C34ConfigError`.

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c34_open_model_expansion_decision_review.py -q
```

Expected: FAIL until mapping validation exists.

- [ ] **Step 3: Implement evidence mapping validation**

Implementation requirements:

- Keep accepted statuses in a tuple or dict constant.
- Map:
  - contract-ready -> HOLD.
  - ready -> READY.
  - missing dependency / missing weights / unsupported shape / runtime failed -> BLOCKED.
  - insufficient windows -> HOLD.
- Reject unknown statuses.
- Ready status must require exact adapter fields. Missing any of the required fields raises `C34ConfigError`.
- `runtime_seconds` must be int/float and not bool.
- `download_allowed_not_verified` must be bool.
- `actual_network_used` must be bool or non-empty string.
- `input_shape` and `output_shape` must be non-empty mappings for ready status.
- Blocker status must require failure evidence as described above.

- [ ] **Step 4: Add explicit local evidence example config**

Create `configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml` using a blocker example by default so it does not imply local success:

```yaml
stage: C3_4_open_model_expansion_decision_review
safety_policy:
  allow_network: false
  allow_download: false
  allow_model_cache: false
  allow_local_execution: false
  allow_training: false
  allow_write_processed: false
prerequisites:
  c33_design_doc: docs/superpowers/specs/2026-06-22-c33-single-candidate-open-model-local-evaluation-design.md
  c33_default_status: contract_ready_single_candidate_local_execution_blocked
  c32_local_status: local_execution_baseline_reference_ready
  c22_watchlist_source: configs/c_stage_c22_open_model_executable_upgrade.yaml
c33_evidence:
  source: explicit_local_reviewed
  status: local_execution_ttm_missing_or_blocked_weights
  candidate: ttm
  task: fu13_like_forecasting
  adapter_evidence:
    failure_reason: cache miss and downloads disabled
    dependency_status: available
    weight_status: missing_or_blocked
decision_policy:
  require_ttm_status: local_execution_ttm_forecasting_ready
  required_adapter_fields:
    - dependency_status
    - weight_status
    - adapter_status
    - runtime_seconds
    - input_shape
    - output_shape
    - actual_network_used
    - download_allowed_not_verified
  leaderboard_allowed: false
  rul_open_model_allowed: false
  second_candidate_execution_allowed: false
candidate_review:
  - candidate_id: chronos_bolt_route
    display_name: Chronos / Chronos-Bolt
    c22_source: chronos
    readiness_status: review_only_not_promoted
    promotion_blocker: package, license, cache, API shape, and resource review required
    next_design_requirement: design one FU13-like forecasting adapter/cache path before execution
  - candidate_id: timesfm_2_5_route
    display_name: TimesFM 2.5
    c22_source: timesfm
    readiness_status: review_only_not_promoted
    promotion_blocker: package, weights, license, resource, and forecasting API review required
    next_design_requirement: verify deterministic PyTorch cache path and FU13-like shape contract
  - candidate_id: moirai_uni2ts_route
    display_name: Moirai / Uni2TS
    c22_source: moirai_uni2ts
    readiness_status: review_only_not_promoted
    promotion_blocker: dependency, checkpoint compatibility, probabilistic output shape review required
    next_design_requirement: resolve Uni2TS dependency and output shape before local execution design
outputs:
  report: reports/c_stage_c34_review_c33_local_ttm_evidence.md
```

- [ ] **Step 5: Add local example load test**

```python
LOCAL_CONFIG = REPO_ROOT / "configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml"


def test_c34_local_evidence_example_is_review_only_blocker():
    config = load_c34_config(LOCAL_CONFIG)
    result = run_c34_open_model_expansion_decision_review(config, LOCAL_CONFIG)

    assert result.status == "blocked_candidate_expansion_due_to_ttm_evidence_gap"
    assert config.safety_policy.allow_model_cache is False
    assert config.safety_policy.allow_local_execution is False
```

Add a review-only boundary test. Keep it simple: monkeypatch any C3.3 loader/parser symbol only if the C3.4 implementation imports one. Prefer proving by design that the C3.4 module has no adapter imports and that `run_c34_open_model_expansion_decision_review()` accepts no adapter factory:

```python
def test_c34_runner_has_no_adapter_or_report_execution_hook():
    config = load_c34_config(DEFAULT_CONFIG)

    result = run_c34_open_model_expansion_decision_review(config, DEFAULT_CONFIG)

    assert result.status == "hold_candidate_expansion_pending_ttm_local_evidence"
    assert not hasattr(result, "adapter_result")
    assert not hasattr(result, "model_cache_manifest")
```

- [ ] **Step 6: Run tests and verify pass**

Run:

```bash
uv run python -m pytest tests/test_c34_open_model_expansion_decision_review.py -q
```

Expected: all C3.4 tests pass.

- [ ] **Step 7: Commit**

```bash
git add configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml \
  src/b08_model_core/experiments/c34_open_model_expansion_decision_review.py \
  tests/test_c34_open_model_expansion_decision_review.py
git commit -m "feat: map c34 c33 evidence decisions"
```

## Task 3: CLI, README, Details, And Scaffold Tests

**Files:**
- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_c34_open_model_expansion_decision_review.py`
- Modify: `tests/test_experiment_scaffold.py`
- Modify: `README.md`
- Modify: `details.md`

- [ ] **Step 1: Write failing CLI and docs tests**

Add C3.4 CLI tests:

```python
from b08_model_core.cli import main


def test_c34_cli_writes_default_decision_report(tmp_path):
    output = tmp_path / "c34_report.md"
    exit_code = main([
        "experiment",
        "c-stage-c34",
        "--config",
        str(DEFAULT_CONFIG),
        "--output",
        str(output),
    ])

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "C3.4 Open Model Expansion Decision Review Report" in text
    assert "hold_candidate_expansion_pending_ttm_local_evidence" in text
```

Add scaffold tests:

```python
def test_readme_documents_c34_decision_review_workflow():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    section_header = "### C3.4. Open model expansion decision review"
    next_header = "\n## 项目边界"

    assert section_header in readme
    c34_section = readme.split(section_header, 1)[1].split(next_header, 1)[0]
    assert "c-stage-c34" in c34_section
    assert "configs/c_stage_c34_open_model_expansion_decision_review.yaml" in c34_section
    assert "configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml" in c34_section
    assert "不运行第二候选 open model" in c34_section
    assert "不生成 leaderboard" in c34_section


def test_details_records_c34_completion_and_next_step():
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "C3.4 open model expansion decision review implemented" in details
    assert "C3.5 second forecasting candidate design" in details
    assert "hold_candidate_expansion_pending_ttm_local_evidence" in details
```

- [ ] **Step 2: Run tests and verify fail**

Run:

```bash
uv run python -m pytest tests/test_c34_open_model_expansion_decision_review.py tests/test_experiment_scaffold.py -q
```

Expected: FAIL because CLI/docs not wired.

- [ ] **Step 3: Register CLI command**

In `src/b08_model_core/cli.py`:

- Import:

```python
from b08_model_core.experiments.c34_open_model_expansion_decision_review import (
    C34ConfigError,
    load_c34_config,
    render_c34_report,
    run_c34_open_model_expansion_decision_review,
)
```

- Add parser:

```python
c_stage_c34 = experiment_sub.add_parser("c-stage-c34")
c_stage_c34.add_argument("--config", required=True)
c_stage_c34.add_argument("--output", required=True)
```

- Add handler near C3.3 handler:

```python
if args.command == "experiment" and args.experiment_command == "c-stage-c34":
    try:
        config = load_c34_config(args.config)
        result = run_c34_open_model_expansion_decision_review(config, args.config)
    except C34ConfigError as exc:
        print(f"C3.4 config error: {exc}", file=sys.stderr)
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_c34_report(result), encoding="utf-8")
    return 0
```

If `sys` is not imported, add it at top. Match existing CLI error style if different.

- [ ] **Step 4: Update README**

Update:

- C-stage summary line includes C3.4.
- Add section after C3.3:
  - Default command.
  - Local evidence review config command.
  - Explain default status `hold_candidate_expansion_pending_ttm_local_evidence`.
  - Explain C3.4 does not run second candidate, inspect cache, train, download, or generate leaderboard.
  - Explain ready gate requires C3.3 `local_execution_ttm_forecasting_ready` plus required adapter fields.
- Add spec/plan links in document entry list.

- [ ] **Step 5: Update details**

Update:

- Date to `2026-06-23`.
- Current stage to `C3.4 open model expansion decision review implemented`.
- Add current C3.4 default command and local evidence review command.
- Daily log row for 2026-06-23.
- Next plan:
  - If default / hold: run or review C3.3 explicit local TTM evidence before second candidate.
  - If ready evidence is recorded: C3.5 second forecasting candidate design, single candidate only.
  - Keep C-MAPSS RUL baseline-only and metrics separated.

- [ ] **Step 6: Run docs and C3.4 tests**

Run:

```bash
uv run python -m pytest tests/test_c34_open_model_expansion_decision_review.py tests/test_experiment_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 7: CLI smoke**

Run:

```bash
uv run b08-model-core experiment c-stage-c34 \
  --config configs/c_stage_c34_open_model_expansion_decision_review.yaml \
  --output /tmp/c_stage_c34_open_model_expansion_decision_review.md
rg -n "Status:|hold_candidate_expansion_pending_ttm_local_evidence|Candidate Expansion Review" \
  /tmp/c_stage_c34_open_model_expansion_decision_review.md
```

Expected: exit 0 and output contains the default hold status.

- [ ] **Step 8: Commit**

```bash
git add src/b08_model_core/cli.py \
  tests/test_c34_open_model_expansion_decision_review.py \
  tests/test_experiment_scaffold.py \
  README.md details.md
git commit -m "docs: document c34 decision review workflow"
```

## Task 4: Final Verification And Review Cleanup

**Files:**
- Modify only files needed for fixes found during verification.

- [ ] **Step 1: Run targeted C-stage tests**

Run:

```bash
uv run python -m pytest \
  tests/test_c33_single_candidate_open_model_local_evaluation.py \
  tests/test_c34_open_model_expansion_decision_review.py \
  tests/test_experiment_scaffold.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run broader C2/C3 regression tests**

Run:

```bash
uv run python -m pytest \
  tests/test_c22_open_model_executable_upgrade.py \
  tests/test_c32_local_execution.py \
  tests/test_c32_open_model_cross_dataset_evaluation.py \
  tests/test_c33_single_candidate_open_model_local_evaluation.py \
  tests/test_c34_open_model_expansion_decision_review.py \
  tests/test_experiment_scaffold.py \
  -q
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```bash
uv run python -m pytest -q
```

Expected: PASS. If a Torch import flake similar to the baseline run appears, reproduce the failing test alone and with related adapter tests before deciding whether it is environmental or caused by C3.4.

- [ ] **Step 4: Run default CLI smoke**

Run:

```bash
uv run b08-model-core experiment c-stage-c34 \
  --config configs/c_stage_c34_open_model_expansion_decision_review.yaml \
  --output /tmp/c_stage_c34_open_model_expansion_decision_review.md
rg -n "Status:|hold_candidate_expansion_pending_ttm_local_evidence|No-Go" \
  /tmp/c_stage_c34_open_model_expansion_decision_review.md
```

Expected: exit 0 and report states default hold decision.

- [ ] **Step 5: Diff hygiene**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intended changes.

- [ ] **Step 6: Request implementation review**

Dispatch a reviewer subagent with:

```text
Review branch codex/c34-decision-review against origin/main. Focus on C3.4 scope: default offline decision review only, no adapter/cache execution, exact C3.3 status mapping, README/details consistency, no leaderboard/RUL/open-model execution scope creep. Do not edit files.
```

Fix any Important or Critical findings. Minor findings may be fixed if low risk.

- [ ] **Step 7: Commit any review fixes**

If fixes are needed:

Stage only the files changed by the review fix, then commit:

```bash
git add path/to/changed_file
git commit -m "fix: align c34 decision review"
```

Run the targeted tests again after fixes.
