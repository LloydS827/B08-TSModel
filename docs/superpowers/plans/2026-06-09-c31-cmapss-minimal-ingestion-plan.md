# C3.1 C-MAPSS Minimal Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the C3.1 NASA PCoE #6 classic C-MAPSS minimal ingestion, schema validation, split/leakage guard, CLI report, and documentation path without downloading or committing public data by default.

**Architecture:** Add one focused C3.1 experiment module that mirrors the existing C3 registry pattern: config loader, dataclasses/enums, runner, parser/mapping helpers, split checks, and report renderer. Keep public data outside Git by default; tests use only synthetic fixtures created under `tmp_path`.

**Tech Stack:** Python 3.11+, stdlib dataclasses/enums/pathlib, `yaml.safe_load`, `pandas`, existing `b08_model_core.cli`, existing `b08_model_core.tasks.schema.validate_observation_frame`, `pytest`, `uv`.

---

## File Structure

- Create: `configs/c_stage_c31_cmapss_minimal_ingestion.yaml`
  - Default offline C3.1 config.
  - Records NASA PCoE #6 source URLs, calibration URLs, license review state, expected 12 classic files, mapping policy, split policy, and output report path.
  - Default behavior must be no network, no download, no local raw read, no processed write.

- Create: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
  - Owns C3.1 config loading, validation, expected-file checks, synthetic-friendly C-MAPSS parser, mapping dry-run, RUL target metadata construction, split/leakage guard, runner, and Markdown report renderer.
  - This file may be moderately large for the first implementation, but keep boundaries clear with small helpers and dataclasses.

- Modify: `src/b08_model_core/cli.py`
  - Add `experiment c-stage-c31 --config --output`.
  - Load C3.1 config, run C3.1 runner, render report.
  - Return 0 for structured `blocked`/preflight report states; return 1 only for config syntax/unsafe policy errors or IO errors that match existing CLI behavior.

- Create: `tests/test_c31_cmapss_minimal_ingestion.py`
  - Primary TDD coverage for config, default blocked/preflight behavior, unsafe policy rejection, synthetic parser/mapping, RUL target metadata, split/leakage guard, and report sections.
  - Synthetic C-MAPSS files must be written in `tmp_path`; do not commit real C-MAPSS data.

- Modify: `tests/test_experiment_scaffold.py`
  - Add README/details and CLI help regression assertions for C3.1.

- Modify: `README.md`
  - Add a C3.1 section after C3 with command shape and default no-network/no-download/no-raw/no-processed boundary.

- Modify: `details.md`
  - Update current stage and 2026-06-09 ledger row after implementation.
  - Keep exactly the existing three-section structure.

---

## Shared Naming And Status Contract

Implement these stable names unless a test reveals a local style conflict:

```python
class C31CmapssConfigError(ValueError):
    ...

class C31LicenseDecision(StrEnum):
    APPROVED_FOR_SCHEMA_VALIDATION = "approved_for_schema_validation"
    APPROVED_FOR_RESEARCH_TRAINING = "approved_for_research_training"
    BLOCKED_BY_LICENSE_REVIEW = "blocked_by_license_review"
    NEEDS_REVIEW = "needs_review"

class C31TopLevelStatus(StrEnum):
    BLOCKED = "blocked"
    READY_FOR_LOCAL_MAPPING = "ready_for_local_mapping"
    SCHEMA_VALIDATED_PENDING_TRAINING_USE_REVIEW = "schema_validated_pending_training_use_review"
    SCHEMA_VALIDATED_READY_FOR_C32 = "schema_validated_ready_for_c32"

class C31BlockedReason(StrEnum):
    BLOCKED_BY_SOURCE_REVIEW = "blocked_by_source_review"
    BLOCKED_BY_LICENSE_REVIEW = "blocked_by_license_review"
    BLOCKED_BY_DOWNLOAD_POLICY = "blocked_by_download_policy"
    BLOCKED_BY_MISSING_RAW_FILES = "blocked_by_missing_raw_files"
    BLOCKED_BY_RAW_SCHEMA_MISMATCH = "blocked_by_raw_schema_mismatch"
    BLOCKED_BY_MAPPING_SCHEMA = "blocked_by_mapping_schema"
    BLOCKED_BY_LEAKAGE_GUARD = "blocked_by_leakage_guard"
    BLOCKED_BY_LABEL_SEMANTICS = "blocked_by_label_semantics"
```

Expected classic C-MAPSS files:

```python
EXPECTED_CMAPSS_SUBSETS = ("FD001", "FD002", "FD003", "FD004")
EXPECTED_CMAPSS_FILE_ROLES = ("train", "test", "RUL")
```

Trajectory identity:

```python
trajectory_id = f"cmapss_{subset}_{file_role}_unit_{unit_id}"
device_id = trajectory_id
batch_id = trajectory_id
```

Pseudo timestamp:

```python
timestamp = pandas.Timestamp("2000-01-01T00:00:00Z") + pandas.to_timedelta(cycle_index, unit="s")
```

RUL target metadata:

```python
train_rul_at_cycle = train_last_cycle - cycle_index
test_rul_at_cycle = test_final_rul + (test_last_observed_cycle - cycle_index)
```

No capped RUL in C3.1.

---

## Task 1: C3.1 Config Loader And Safety Policy

**Files:**
- Create: `configs/c_stage_c31_cmapss_minimal_ingestion.yaml`
- Create: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
- Test: `tests/test_c31_cmapss_minimal_ingestion.py`

- [ ] **Step 1: Write failing tests for default config and safety policy**

Add these tests to `tests/test_c31_cmapss_minimal_ingestion.py`:

```python
from pathlib import Path

import pytest
import yaml

from b08_model_core.experiments.c31_cmapss_minimal_ingestion import (
    C31CmapssConfigError,
    C31LicenseDecision,
    C31TopLevelStatus,
    expected_cmapss_files,
    load_c31_cmapss_config,
    run_c31_cmapss_minimal_ingestion,
)

_DEFAULT_CONFIG = Path("configs/c_stage_c31_cmapss_minimal_ingestion.yaml")


def _load_default_yaml() -> dict:
    return yaml.safe_load(_DEFAULT_CONFIG.read_text(encoding="utf-8"))


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _modified_config(tmp_path: Path, update) -> Path:
    data = _load_default_yaml()
    update(data)
    return _write_yaml(tmp_path / "c31.yaml", data)


def test_c31_default_config_is_offline_and_lists_classic_cmapss_files():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)

    assert config.stage == "C3_1_cmapss_minimal_ingestion"
    assert config.dataset_id == "nasa_cmapss"
    assert config.download_policy.allow_network is False
    assert config.download_policy.allow_download is False
    assert config.download_policy.allow_local_raw_data is False
    assert config.download_policy.allow_write_processed is False
    assert config.license_review.decision == C31LicenseDecision.NEEDS_REVIEW
    assert len(config.download_policy.expected_files) == 12
    assert set(expected_cmapss_files()) == set(config.download_policy.expected_files)
    assert config.outputs.report == Path("reports/c_stage_c31_cmapss_minimal_ingestion.md")


def test_c31_default_runner_blocks_without_reading_raw_data():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)

    result = run_c31_cmapss_minimal_ingestion(config, config_path=_DEFAULT_CONFIG)

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_license_review" in [reason.value for reason in result.blocked_reasons]
    assert result.raw_files_present == ()
    assert result.raw_files_missing == tuple(config.download_policy.expected_files)


def test_c31_blocks_unapproved_source_even_when_license_is_schema_approved(tmp_path):
    path = _modified_config(
        tmp_path,
        lambda data: data["license_review"].update(
            {
                "decision": "approved_for_schema_validation",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "needs_review",
            }
        ),
    )
    config = load_c31_cmapss_config(path)

    result = run_c31_cmapss_minimal_ingestion(config, config_path=path)

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_source_review" in [reason.value for reason in result.blocked_reasons]


@pytest.mark.parametrize(
    "update,match",
    [
        (
            lambda data: data["download_policy"].update({"allow_network": False, "allow_download": True}),
            "allow_download",
        ),
        (
            lambda data: data["download_policy"].update(
                {"allow_network": True, "allow_download": True, "allow_local_raw_data": False}
            ),
            "allow_local_raw_data",
        ),
        (
            lambda data: data["download_policy"].update({"allow_write_processed": True, "allow_local_raw_data": False}),
            "allow_write_processed",
        ),
    ],
)
def test_c31_rejects_unsafe_download_policy_combinations(tmp_path, update, match):
    path = _modified_config(tmp_path, update)

    with pytest.raises(C31CmapssConfigError, match=match):
        load_c31_cmapss_config(path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py -q
```

Expected: FAIL because `c31_cmapss_minimal_ingestion` module/config do not exist.

- [ ] **Step 3: Add default C3.1 config**

Create `configs/c_stage_c31_cmapss_minimal_ingestion.yaml`:

```yaml
stage: C3_1_cmapss_minimal_ingestion
dataset_id: nasa_cmapss
source:
  primary_source_name: NASA PCoE #6 Turbofan Engine Degradation Simulation Data Set
  primary_source_url: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
  download_target_url: https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip
  source_status: needs_review
  citation: "Saxena, A., Goebel, K., Simon, D., and Eklund, N. Damage propagation modeling for aircraft engine run-to-failure simulation. 2008."
  calibration_sources:
    - name: NASA Open Data Portal C-MAPSS Aircraft Engine Simulator Data
      url: https://data.nasa.gov/dataset/c-mapss-aircraft-engine-simulator-data
      handling: calibration_note_only
    - name: NASA NTRS C-MAPSS-2
      url: https://ntrs.nasa.gov/citations/20205001125
      handling: watchlist_only
license_review:
  decision: needs_review
  license_status: needs_review
  redistribution_status: needs_review
  training_use_status: needs_review
  citation_required: true
download_policy:
  allow_network: false
  allow_download: false
  allow_local_raw_data: false
  allow_write_processed: false
  raw_dir: data/public/cmapss/raw
  processed_dir: data/processed/cmapss
  checksum_policy: record_if_downloaded
  expected_files:
    - train_FD001.txt
    - test_FD001.txt
    - RUL_FD001.txt
    - train_FD002.txt
    - test_FD002.txt
    - RUL_FD002.txt
    - train_FD003.txt
    - test_FD003.txt
    - RUL_FD003.txt
    - train_FD004.txt
    - test_FD004.txt
    - RUL_FD004.txt
mapping_policy:
  subsets: [FD001, FD002, FD003, FD004]
  pseudo_timestamp_start: "2000-01-01T00:00:00Z"
  file_roles: [train, test, RUL]
  sensor_count: 21
  setting_count: 3
  use_capped_rul: false
split_policy:
  split_unit: trajectory_id
  validation_source: train_trajectories
  forbidden_leakage_modes:
    - trajectory_id_overlap
    - target_columns_in_input_features
    - window_adjacency_across_splits
outputs:
  report: reports/c_stage_c31_cmapss_minimal_ingestion.md
  processed_dir: data/processed/cmapss
```

- [ ] **Step 4: Implement minimal config dataclasses, loader, policy validation, expected files, and default runner**

In `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`, implement:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class C31CmapssConfigError(ValueError):
    """Raised when the C3.1 C-MAPSS config is invalid."""


class C31LicenseDecision(StrEnum):
    APPROVED_FOR_SCHEMA_VALIDATION = "approved_for_schema_validation"
    APPROVED_FOR_RESEARCH_TRAINING = "approved_for_research_training"
    BLOCKED_BY_LICENSE_REVIEW = "blocked_by_license_review"
    NEEDS_REVIEW = "needs_review"


class C31TopLevelStatus(StrEnum):
    BLOCKED = "blocked"
    READY_FOR_LOCAL_MAPPING = "ready_for_local_mapping"
    SCHEMA_VALIDATED_PENDING_TRAINING_USE_REVIEW = "schema_validated_pending_training_use_review"
    SCHEMA_VALIDATED_READY_FOR_C32 = "schema_validated_ready_for_c32"


class C31BlockedReason(StrEnum):
    BLOCKED_BY_SOURCE_REVIEW = "blocked_by_source_review"
    BLOCKED_BY_LICENSE_REVIEW = "blocked_by_license_review"
    BLOCKED_BY_DOWNLOAD_POLICY = "blocked_by_download_policy"
    BLOCKED_BY_MISSING_RAW_FILES = "blocked_by_missing_raw_files"
    BLOCKED_BY_RAW_SCHEMA_MISMATCH = "blocked_by_raw_schema_mismatch"
    BLOCKED_BY_MAPPING_SCHEMA = "blocked_by_mapping_schema"
    BLOCKED_BY_LEAKAGE_GUARD = "blocked_by_leakage_guard"
    BLOCKED_BY_LABEL_SEMANTICS = "blocked_by_label_semantics"


EXPECTED_CMAPSS_SUBSETS = ("FD001", "FD002", "FD003", "FD004")


def expected_cmapss_files() -> tuple[str, ...]:
    files: list[str] = []
    for subset in EXPECTED_CMAPSS_SUBSETS:
        files.extend((f"train_{subset}.txt", f"test_{subset}.txt", f"RUL_{subset}.txt"))
    return tuple(files)
```

Add frozen dataclasses for source, calibration source, license review, download policy, mapping policy, split policy, outputs, config, and result.

Loader requirements:
- Wrap malformed YAML in `C31CmapssConfigError`.
- Require `stage == "C3_1_cmapss_minimal_ingestion"`.
- Require `dataset_id == "nasa_cmapss"`.
- Validate all four safety flag combinations from the spec.
- Reject unsafe combinations from the spec.
- Validate expected files exactly match `expected_cmapss_files()` for default/full config.

Runner requirements for Task 1:
- Do not read `raw_dir` when `allow_local_raw_data` is false.
- Return `C31TopLevelStatus.BLOCKED` with `blocked_by_source_review` when `source.source_status` is not `verified`, even if license review is otherwise approved.
- Return `C31TopLevelStatus.BLOCKED` when license decision is `needs_review` or `blocked_by_license_review`.
- Set `raw_files_present=()` and `raw_files_missing=tuple(expected_files)` when local raw data is not allowed.

- [ ] **Step 5: Run tests to verify Task 1 passes**

Run:

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py -q
```

Expected: PASS for Task 1 tests.

- [ ] **Step 6: Run focused regression**

Run:

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py tests/test_c3_public_dataset_registry.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```bash
git add configs/c_stage_c31_cmapss_minimal_ingestion.yaml src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py tests/test_c31_cmapss_minimal_ingestion.py
git commit -m "feat: add c31 cmapss config boundary"
```

---

## Task 2: Synthetic C-MAPSS Parser, Canonical Mapping, And RUL Metadata

**Files:**
- Modify: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`

- [ ] **Step 1: Write failing tests for synthetic parser and mapping**

Append helper and tests:

```python
def _write_synthetic_subset(raw_dir: Path, subset: str = "FD001") -> None:
    sensor_values_1 = " ".join(str(100 + index) for index in range(1, 22))
    sensor_values_2 = " ".join(str(200 + index) for index in range(1, 22))
    train_rows = [
        f"1 1 0.1 0.2 0.3 {sensor_values_1}",
        f"1 2 0.1 0.2 0.3 {sensor_values_2}",
        f"2 1 0.4 0.5 0.6 {sensor_values_1}",
    ]
    test_rows = [
        f"1 1 0.7 0.8 0.9 {sensor_values_1}",
        f"1 2 0.7 0.8 0.9 {sensor_values_2}",
    ]
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"train_{subset}.txt").write_text("\\n".join(train_rows) + "\\n", encoding="utf-8")
    (raw_dir / f"test_{subset}.txt").write_text("\\n".join(test_rows) + "\\n", encoding="utf-8")
    (raw_dir / f"RUL_{subset}.txt").write_text("5\\n", encoding="utf-8")


def _approved_local_mapping_config(tmp_path: Path) -> Path:
    raw_dir = tmp_path / "raw"
    _write_synthetic_subset(raw_dir)

    def update(data: dict) -> None:
        data["source"]["source_status"] = "verified"
        data["license_review"].update(
            {
                "decision": "approved_for_schema_validation",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "needs_review",
            }
        )
        data["download_policy"].update(
            {
                "allow_local_raw_data": True,
                "raw_dir": str(raw_dir),
                "expected_files": ["train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt"],
            }
        )
        data["mapping_policy"]["subsets"] = ["FD001"]

    return _modified_config(tmp_path, update)


def test_c31_maps_synthetic_subset_to_canonical_observations(tmp_path):
    config = load_c31_cmapss_config(_approved_local_mapping_config(tmp_path))

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.mapping_summary is not None
    assert result.mapping_summary.observation_rows == 5 * 24
    assert result.mapping_summary.trajectory_count == 3
    assert result.mapping_summary.required_schema_valid is True
    assert "cmapss_FD001_train_unit_1" in result.mapping_summary.trajectory_ids
    assert "cmapss_FD001_test_unit_1" in result.mapping_summary.trajectory_ids
    assert result.mapping_summary.pseudo_timestamp_rule == "2000-01-01T00:00:00Z + cycle_index seconds"


def test_c31_rul_targets_use_uncapped_train_and_test_formulas(tmp_path):
    config = load_c31_cmapss_config(_approved_local_mapping_config(tmp_path))

    result = run_c31_cmapss_minimal_ingestion(config)
    by_key = {
        (target.trajectory_id, target.cycle_index): target.rul
        for target in result.rul_targets
    }

    assert by_key[("cmapss_FD001_train_unit_1", 1)] == 1
    assert by_key[("cmapss_FD001_train_unit_1", 2)] == 0
    assert by_key[("cmapss_FD001_test_unit_1", 1)] == 6
    assert by_key[("cmapss_FD001_test_unit_1", 2)] == 5
    assert result.mapping_summary.uses_capped_rul is False


def test_c31_blocks_when_approved_local_raw_files_are_missing(tmp_path):
    raw_dir = tmp_path / "missing_raw"

    def update(data: dict) -> None:
        data["source"]["source_status"] = "verified"
        data["license_review"].update(
            {
                "decision": "approved_for_schema_validation",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "needs_review",
            }
        )
        data["download_policy"].update(
            {
                "allow_local_raw_data": True,
                "raw_dir": str(raw_dir),
                "expected_files": ["train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt"],
            }
        )
        data["mapping_policy"]["subsets"] = ["FD001"]

    config = load_c31_cmapss_config(_modified_config(tmp_path, update))

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_missing_raw_files" in [reason.value for reason in result.blocked_reasons]
    assert result.raw_files_missing == ("train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt")


def test_c31_blocks_malformed_raw_shape(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "train_FD001.txt").write_text("1 1 0.1\\n", encoding="utf-8")
    (raw_dir / "test_FD001.txt").write_text("1 1 0.7\\n", encoding="utf-8")
    (raw_dir / "RUL_FD001.txt").write_text("5\\n", encoding="utf-8")

    def update(data: dict) -> None:
        data["source"]["source_status"] = "verified"
        data["license_review"].update(
            {
                "decision": "approved_for_schema_validation",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "needs_review",
            }
        )
        data["download_policy"].update(
            {
                "allow_local_raw_data": True,
                "raw_dir": str(raw_dir),
                "expected_files": ["train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt"],
            }
        )
        data["mapping_policy"]["subsets"] = ["FD001"]

    config = load_c31_cmapss_config(_modified_config(tmp_path, update))

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_raw_schema_mismatch" in [reason.value for reason in result.blocked_reasons]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py -q
```

Expected: FAIL because mapping summary and RUL target construction are missing.

- [ ] **Step 3: Implement parser and canonical mapping**

In `c31_cmapss_minimal_ingestion.py`, add:
- `C31MappedObservationSummary`
- `C31RulTarget`
- `_parse_cmapss_data_file(path, subset, file_role)`
- `_parse_rul_file(path)`
- `_map_cmapss_rows_to_observations(config)`

Parsing shape:
- Data rows must contain 26 whitespace-separated columns: `unit`, `cycle`, `setting_1..setting_3`, `sensor_01..sensor_21`.
- RUL rows must contain one integer per test unit in file order.
- Malformed rows should produce `blocked_by_raw_schema_mismatch` through runner, not crash in default report path.
- Missing expected raw files when local raw reads are allowed should produce `blocked_by_missing_raw_files`.

Canonical mapping:
- For each raw train/test row, create 24 observation rows: 3 settings + 21 sensors.
- Required B08 observation columns:
  - `timestamp`: `pd.Timestamp("2000-01-01T00:00:00Z") + pd.to_timedelta(cycle_index, unit="s")`
  - `device_id`: `trajectory_id`
  - `batch_id`: `trajectory_id`
  - `stage`: subset id, e.g. `FD001`
  - `sensor_id`: `setting_1..setting_3` or `sensor_01..sensor_21`
  - `value`: float reading
  - `unit`: `"normalized"`
  - `domain`: `"operational_condition"` for settings, `"turbofan_sensor"` for sensors
  - `quality_flag`: `"good"`
  - `degradation_label`: `"run_to_failure_known"` for train, `"partial_trajectory_with_rul_target"` for test
  - `failure_proxy`: `False`
- Use `validate_observation_frame` to set `required_schema_valid`.
- Do not write parquet in this task.

RUL metadata:
- Train: group by train trajectory, `max_cycle - cycle_index`.
- Test: use RUL file values in ascending test unit order; `test_final_rul + (last_observed_cycle - cycle_index)`.
- Store targets separately in `result.rul_targets`; do not add RUL as observation input feature.

- [ ] **Step 4: Run tests to verify Task 2 passes**

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py tests/test_c31_cmapss_minimal_ingestion.py
git commit -m "feat: map c31 cmapss synthetic fixtures"
```

---

## Task 3: Split And Leakage Guard

**Files:**
- Modify: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`

- [ ] **Step 1: Write failing tests for split/leakage behavior**

Append tests:

```python
def test_c31_partial_subset_validated_is_not_c32_ready(tmp_path):
    config = load_c31_cmapss_config(_approved_local_mapping_config(tmp_path))

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.readiness_detail == "partial_subset_validated"
    assert result.status == C31TopLevelStatus.READY_FOR_LOCAL_MAPPING
    assert result.c32_go_no_go == "No-Go: partial subset only"


def test_c31_full_schema_validation_pending_training_use_review(tmp_path):
    raw_dir = tmp_path / "raw"
    for subset in ("FD001", "FD002", "FD003", "FD004"):
        _write_synthetic_subset(raw_dir, subset=subset)

    def update(data: dict) -> None:
        data["source"]["source_status"] = "verified"
        data["license_review"].update(
            {
                "decision": "approved_for_schema_validation",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "needs_review",
            }
        )
        data["download_policy"].update({"allow_local_raw_data": True, "raw_dir": str(raw_dir)})

    config = load_c31_cmapss_config(_modified_config(tmp_path, update))

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.readiness_detail == "full_classic_cmapss_validated"
    assert result.status == C31TopLevelStatus.SCHEMA_VALIDATED_PENDING_TRAINING_USE_REVIEW
    assert result.c32_go_no_go == "No-Go: pending training-use review"


def test_c31_full_schema_validation_ready_for_c32_when_research_training_approved(tmp_path):
    raw_dir = tmp_path / "raw"
    for subset in ("FD001", "FD002", "FD003", "FD004"):
        _write_synthetic_subset(raw_dir, subset=subset)

    def update(data: dict) -> None:
        data["source"]["source_status"] = "verified"
        data["license_review"].update(
            {
                "decision": "approved_for_research_training",
                "license_status": "verified",
                "redistribution_status": "not_allowed",
                "training_use_status": "research_only",
            }
        )
        data["download_policy"].update({"allow_local_raw_data": True, "raw_dir": str(raw_dir)})

    config = load_c31_cmapss_config(_modified_config(tmp_path, update))

    result = run_c31_cmapss_minimal_ingestion(config)

    assert result.status == C31TopLevelStatus.SCHEMA_VALIDATED_READY_FOR_C32
    assert result.c32_go_no_go == "Go: schema validated and research training/evaluation use approved"


def test_c31_split_guard_blocks_overlapping_trajectory_ids(tmp_path):
    config = load_c31_cmapss_config(_approved_local_mapping_config(tmp_path))

    result = run_c31_cmapss_minimal_ingestion(
        config,
        split_assignments={
            "train": {"cmapss_FD001_train_unit_1"},
            "validation": {"cmapss_FD001_train_unit_1"},
            "test": {"cmapss_FD001_test_unit_1"},
        },
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [reason.value for reason in result.blocked_reasons]
    assert result.leakage_summary is not None
    assert result.leakage_summary.trajectory_overlap_count == 1


def test_c31_input_feature_guard_blocks_rul_target_leakage(tmp_path):
    config = load_c31_cmapss_config(_approved_local_mapping_config(tmp_path))

    result = run_c31_cmapss_minimal_ingestion(config, input_feature_columns=("sensor_01", "rul"))

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [reason.value for reason in result.blocked_reasons]
    assert result.leakage_summary.target_columns_in_input == ("rul",)


def test_c31_window_adjacency_guard_blocks_cross_split_adjacent_cycles(tmp_path):
    config = load_c31_cmapss_config(_approved_local_mapping_config(tmp_path))

    result = run_c31_cmapss_minimal_ingestion(
        config,
        split_assignments={
            "train": {"cmapss_FD001_train_unit_1"},
            "validation": {"cmapss_FD001_train_unit_2"},
            "test": {"cmapss_FD001_test_unit_1"},
        },
        window_assignments=[
            {
                "trajectory_id": "cmapss_FD001_train_unit_1",
                "start_cycle": 1,
                "end_cycle": 2,
                "split": "train",
            },
            {
                "trajectory_id": "cmapss_FD001_train_unit_1",
                "start_cycle": 2,
                "end_cycle": 3,
                "split": "validation",
            },
        ],
    )

    assert result.status == C31TopLevelStatus.BLOCKED
    assert "blocked_by_leakage_guard" in [reason.value for reason in result.blocked_reasons]
    assert result.leakage_summary.window_adjacency_leakage_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py -q
```

Expected: FAIL because split/leakage status handling is missing.

- [ ] **Step 3: Implement readiness and leakage guard**

Add:
- `C31LeakageSummary`
- `C31ReadinessDetail` as strings or enum values:
  - `full_classic_cmapss_validated`
  - `partial_subset_validated`
- `_default_split_assignments(trajectory_ids)`:
  - test trajectories to `test`
  - train trajectories split by trajectory id; with tiny fixtures, assign all train trajectories to `train` unless explicit assignments are passed.
- `_check_leakage(split_assignments, input_feature_columns, window_assignments)`:
  - zero overlap across split sets.
  - zero target input columns from `{"rul", "RUL", "target_rul", "remaining_useful_life"}`.
  - zero adjacent or overlapping windows from the same `trajectory_id` across different splits. Treat windows as leaking when they share a trajectory and their cycle ranges overlap or touch at a boundary, for example `train [1, 2]` and `validation [2, 3]`.
- Status rules:
  - Any leakage failure -> `blocked` + `blocked_by_leakage_guard`.
  - Full expected files + schema valid + license decision `approved_for_schema_validation` -> `schema_validated_pending_training_use_review`.
  - Full expected files + schema valid + license decision `approved_for_research_training` -> `schema_validated_ready_for_c32`.
  - Partial subset valid -> `ready_for_local_mapping`, not C3.2 ready.

- [ ] **Step 4: Run tests to verify Task 3 passes**

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py tests/test_c31_cmapss_minimal_ingestion.py
git commit -m "feat: add c31 cmapss leakage guard"
```

---

## Task 4: Report Renderer And CLI Entry

**Files:**
- Modify: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`

- [ ] **Step 1: Write failing tests for report and CLI**

Add tests:

```python
from b08_model_core.cli import main
from b08_model_core.experiments.c31_cmapss_minimal_ingestion import render_c31_cmapss_report


def test_c31_report_contains_required_sections_for_default_config():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)
    result = run_c31_cmapss_minimal_ingestion(config, config_path=_DEFAULT_CONFIG)

    text = render_c31_cmapss_report(result)

    assert "C3.1 NASA C-MAPSS Minimal Ingestion Report" in text
    assert "Source And License Preflight" in text
    assert "Source Calibration Notes" in text
    assert "Download Boundary And Local Paths" in text
    assert "Expected C-MAPSS Files" in text
    assert "Schema Mapping Dry-Run" in text
    assert "RUL / Degradation Target Metadata" in text
    assert "Split Policy And Leakage Guard" in text
    assert "C3.2 Go / No-Go" in text
    assert "不下载公开数据" in text
    assert "不运行模型训练" in text
    assert "blocked_by_license_review" in text


def test_cli_c_stage_c31_writes_default_preflight_report(tmp_path):
    output = tmp_path / "c31.md"

    exit_code = main(
        [
            "experiment",
            "c-stage-c31",
            "--config",
            "configs/c_stage_c31_cmapss_minimal_ingestion.yaml",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "C3.1 NASA C-MAPSS Minimal Ingestion Report" in text
    assert "blocked" in text
    assert "blocked_by_license_review" in text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py -q
```

Expected: FAIL because renderer and CLI entry are missing.

- [ ] **Step 3: Implement report renderer**

`render_c31_cmapss_report(result)` must include these sections exactly:
- `# C3.1 NASA C-MAPSS Minimal Ingestion Report`
- `## C3.1 Summary`
- `## Source And License Preflight`
- `## Source Calibration Notes`
- `## Download Boundary And Local Paths`
- `## Expected C-MAPSS Files`
- `## Raw File Presence / Download Status`
- `## Schema Mapping Dry-Run`
- `## Canonical Observation Compatibility`
- `## RUL / Degradation Target Metadata`
- `## Split Policy And Leakage Guard`
- `## Supported Tasks And Metrics`
- `## Invalid Claims`
- `## C3.2 Go / No-Go`

Report text must state:

```text
不下载公开数据，不提交公开数据或派生 parquet，不运行模型训练。
```

For default config, report must show `blocked` and `blocked_by_license_review`.

- [ ] **Step 4: Add CLI command**

In `src/b08_model_core/cli.py`:

Imports:

```python
from b08_model_core.experiments.c31_cmapss_minimal_ingestion import (
    load_c31_cmapss_config,
    render_c31_cmapss_report,
    run_c31_cmapss_minimal_ingestion,
)
```

Parser:

```python
c_stage_c31 = experiment_sub.add_parser("c-stage-c31")
c_stage_c31.add_argument("--config", required=True)
c_stage_c31.add_argument("--output", required=True)
```

Handler:

```python
if args.command == "experiment" and args.experiment_command == "c-stage-c31":
    try:
        config = load_c31_cmapss_config(args.config)
        result = run_c31_cmapss_minimal_ingestion(config, config_path=args.config)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_c31_cmapss_report(result), encoding="utf-8")
    except (FileNotFoundError, ValueError, OSError, PermissionError):
        return 1
    return 0
```

- [ ] **Step 5: Run Task 4 tests**

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py -q
```

Expected: PASS.

- [ ] **Step 6: Run CLI smoke**

```bash
tmpdir=$(mktemp -d)
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output "$tmpdir/c31.md"
rg -n "C3.1 NASA C-MAPSS Minimal Ingestion Report|blocked_by_license_review|不下载公开数据" "$tmpdir/c31.md"
```

Expected: command exits 0 and `rg` finds all three patterns.

- [ ] **Step 7: Commit Task 4**

```bash
git add src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py src/b08_model_core/cli.py tests/test_c31_cmapss_minimal_ingestion.py
git commit -m "feat: add c31 cmapss cli report"
```

---

## Task 5: README, Details, Regression, And Data Safety Checks

**Files:**
- Modify: `README.md`
- Modify: `details.md`
- Modify: `tests/test_experiment_scaffold.py`
- Test: `tests/test_c31_cmapss_minimal_ingestion.py`

- [ ] **Step 1: Write failing documentation regression test**

In `tests/test_experiment_scaffold.py`, add:

```python
def test_c31_cmapss_minimal_ingestion_workflow_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "c-stage-c31" in readme
    assert "configs/c_stage_c31_cmapss_minimal_ingestion.yaml" in readme
    assert "reports/c_stage_c31_cmapss_minimal_ingestion.md" in readme
    assert "allow_network: false" in readme
    assert "allow_download: false" in readme
    assert "allow_local_raw_data: false" in readme
    assert "不下载公开数据" in readme
    assert "不运行模型训练" in readme
    assert "C3.1" in details
    assert "NASA C-MAPSS" in details


def test_c31_cli_help_is_available():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "experiment",
            "c-stage-c31",
            "--help",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert "--config" in result.stdout
    assert "--output" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c31_cmapss_minimal_ingestion_workflow_is_documented -q
```

Expected: FAIL until README/details are updated.

- [ ] **Step 3: Update README**

Add after the C3 section:

````markdown
### C3.1. NASA C-MAPSS 最小接入与 schema validation

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output reports/c_stage_c31_cmapss_minimal_ingestion.md
```

C3.1 锁定 NASA PCoE #6 经典 C-MAPSS，验证 source/license preflight、最小下载边界、schema mapping dry-run、RUL target metadata、split/leakage guard 和 C3.2 Go / No-Go。默认配置保持：

```yaml
allow_network: false
allow_download: false
allow_local_raw_data: false
allow_write_processed: false
```

默认路径不下载公开数据、不读取本机 raw files、不写 processed data、不运行模型训练。只有显式 opt-in 且 source/license/training-use 边界被记录后，才允许读取 ignored 本机数据目录或生成 ignored 派生产物。
````

Ensure Markdown fences are nested correctly: use four backticks around the outer snippet if editing via patch.

- [ ] **Step 4: Update details**

Keep exactly three sections:
1. 当前阶段
2. 每日更新
3. 下一步计划

Update wording so:
- Current stage says C3.1 implementation entry exists and next is execution/review of C3.1 report.
- 2026-06-09 row includes C3.1 implementation.
- Next plan says next loop should run C3.1 default preflight, then optional source/license review and local synthetic/real raw mapping only when approved.

- [ ] **Step 5: Run documentation test**

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c31_cmapss_minimal_ingestion_workflow_is_documented -q
```

Expected: PASS.

- [ ] **Step 6: Run focused C3.1 and documentation tests**

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py tests/test_experiment_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 7: Run CLI help regression for C-stage entries**

```bash
uv run b08-model-core experiment c-stage-c1 --help >/tmp/c31_help_c1.txt
uv run b08-model-core experiment c-stage-c2 --help >/tmp/c31_help_c2.txt
uv run b08-model-core experiment c-stage-c21 --help >/tmp/c31_help_c21.txt
uv run b08-model-core experiment c-stage-c22 --help >/tmp/c31_help_c22.txt
uv run b08-model-core experiment c-stage-c3 --help >/tmp/c31_help_c3.txt
uv run b08-model-core experiment c-stage-c31 --help >/tmp/c31_help_c31.txt
```

Expected: all commands exit 0.

- [ ] **Step 8: Check no public data artifacts were added**

```bash
git status --short
find data reports -maxdepth 4 \( -name '*FD00*.txt' -o -name '*.zip' -o -name '*.parquet' -o -name 'c_stage_c31_cmapss_minimal_ingestion.md' \) -print 2>/dev/null
```

Expected:
- `git status --short` shows only source/docs/test/config changes.
- `find` prints nothing relevant from tracked paths. Temporary reports should only be in `/tmp` or ignored locations.

- [ ] **Step 9: Run final focused suite**

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py tests/test_c3_public_dataset_registry.py tests/test_experiment_scaffold.py -q
git diff --check
```

Expected: all tests PASS; `git diff --check` exits 0.

- [ ] **Step 10: Commit Task 5**

```bash
git add README.md details.md tests/test_experiment_scaffold.py
git commit -m "docs: document c31 cmapss workflow"
```

---

## Final Verification Before Branch Completion

After all tasks and reviews pass:

- [ ] Run full test suite:

```bash
uv run python -m pytest -q
```

Expected: all tests pass.

- [ ] Run C3.1 CLI smoke:

```bash
tmpdir=$(mktemp -d)
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output "$tmpdir/c31.md"
rg -n "C3.1 NASA C-MAPSS Minimal Ingestion Report|blocked_by_license_review|不下载公开数据" "$tmpdir/c31.md"
```

Expected: exit 0; report contains all patterns.

- [ ] Run C-stage help smoke:

```bash
uv run b08-model-core experiment c-stage-c1 --help >/tmp/c31_help_c1.txt
uv run b08-model-core experiment c-stage-c2 --help >/tmp/c31_help_c2.txt
uv run b08-model-core experiment c-stage-c21 --help >/tmp/c31_help_c21.txt
uv run b08-model-core experiment c-stage-c22 --help >/tmp/c31_help_c22.txt
uv run b08-model-core experiment c-stage-c3 --help >/tmp/c31_help_c3.txt
uv run b08-model-core experiment c-stage-c31 --help >/tmp/c31_help_c31.txt
```

Expected: all exit 0.

- [ ] Confirm Git has no public data artifacts:

```bash
git status --short
git ls-files | rg '(^data/public|FD00[1-4]|Turbofan|cmapss.*\\.(zip|txt|parquet)$)' || true
```

Expected: no public raw/zip/parquet artifacts tracked.

---

## Implementation Notes For Subagents

- You are not alone in the codebase. Do not revert changes made by other agents.
- Use TDD: write failing tests, run them red, implement minimal code, run green, then commit.
- Keep default workflow usable. Default `c-stage-c31` must not use network, download data, read local raw files, or write processed data.
- Synthetic fixtures are allowed only inside tests under `tmp_path`.
- Do not add real C-MAPSS files, generated parquet, zip files, cache, or local reports to Git.
- Keep C1/C2/C2.1/C2.2/C3 commands working.
