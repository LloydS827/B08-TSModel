# Real Data Validation and Experiment Scaffold Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Harden the next-stage bridge from the simulated FU13 sandbox to real-data validation and first forecasting experiments.

**Architecture:** This is a model-core sandbox extension, not a production ingestion system. Real-data exports are normalized into the existing canonical observation schema, validated with explicit failure reasons, then used by a lightweight forecasting experiment scaffold that never downloads external model weights.

**Tech Stack:** Python 3.11+, pandas, pydantic, PyYAML, pyarrow, pytest, existing `b08_model_core` CLI, existing optional adapter metadata.

---

## Current State

The first implementation pass already created the real-data and experiment files. This plan is the authoritative hardening and verification plan for the current repository state.

Existing files to modify:

- `configs/real_data_schema_map.template.yaml`
- `docs/reviews/real-data-schema-map.md`
- `pyproject.toml`
- `src/b08_model_core/real_data/schema_map.py`
- `src/b08_model_core/real_data/validation_report.py`
- `src/b08_model_core/experiments/forecasting.py`
- `src/b08_model_core/cli.py`
- `tests/test_real_data_schema_map.py`
- `tests/test_cli_real_data_validate.py`
- `tests/test_experiment_scaffold.py`

## Canonical Observation Schema

Every normalized real-data row must contain these columns in this order:

```python
[
    "timestamp",
    "device_id",
    "batch_id",
    "stage",
    "sensor_id",
    "value",
    "unit",
    "domain",
    "quality_flag",
    "degradation_label",
    "failure_proxy",
]
```

Required behavior:

- `timestamp` is parsed with `errors="coerce"` and invalid values are counted.
- `value` is parsed numeric with `errors="coerce"` and invalid values are counted.
- `stage` is mapped by `stage_map`; unmapped source stages are reported.
- `sensor_id`, `domain`, and `unit` come from sensor mapping; unknown sensors are reported.
- wide-format exports report `missing_sensor_columns` when configured sensor columns are absent.
- duplicate points are counted by `timestamp/device_id/batch_id/stage/sensor_id`.
- CLI writes a report for both valid and invalid inputs.
- CLI returns `0` when `schema_valid=True`, and `1` when validation completes but detects invalid data.

## Task 1: Schema Normalization Contract

**Files:**
- Modify: `src/b08_model_core/real_data/schema_map.py`
- Modify: `tests/test_real_data_schema_map.py`

- [x] **Step 1: Verify long-format test exists**

Required test shape:

```python
def test_long_real_data_map_normalizes_to_observation_schema(tmp_path):
    raw = pd.DataFrame({
        "ts": ["2026-01-01 00:00:00"],
        "equipment": ["FU13"],
        "lot": ["B001"],
        "phase": ["vacuum"],
        "tag": ["p1"],
        "reading": [1.2],
    })
    normalized = normalize_real_data_frame(raw, load_schema_map(schema_path))
    assert REQUIRED_OBSERVATION_COLUMNS <= set(normalized.columns)
    assert validate_observation_frame(normalized).valid
```

- [x] **Step 2: Verify wide-format test exists**

Required assertion:

```python
assert len(normalized) == 2
assert set(normalized["sensor_id"]) == {"PumpShake1", "OutletOxygen"}
```

- [x] **Step 3: Run task tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_real_data_schema_map.py::test_long_real_data_map_normalizes_to_observation_schema tests/test_real_data_schema_map.py::test_wide_real_data_map_normalizes_sensor_columns -v
```

Expected: PASS.

- [x] **Step 4: Commit if this task changed files**

```bash
git add src/b08_model_core/real_data/schema_map.py tests/test_real_data_schema_map.py
git commit -m "test: cover real data schema normalization"
```

## Task 2: Real-Data Failure Reporting

**Files:**
- Modify: `src/b08_model_core/real_data/schema_map.py`
- Modify: `src/b08_model_core/real_data/validation_report.py`
- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_real_data_schema_map.py`
- Modify: `tests/test_cli_real_data_validate.py`

- [x] **Step 1: Verify invalid-data test exists**

Required test data:

```python
raw = pd.DataFrame({
    "ts": ["bad timestamp", "2026-01-01 00:00:00", "2026-01-01 00:00:00"],
    "equipment": ["FU13", "FU13", "FU13"],
    "lot": ["B001", "B001", "B001"],
    "phase": ["unknown_stage", "vacuum", "vacuum"],
    "tag": ["unknown_tag", "p1", "p1"],
    "reading": ["oops", 1.2, 1.2],
})
```

Required assertions:

```python
assert report.schema_valid is False
assert report.timestamp_parse_errors == 1
assert report.non_numeric_values == 1
assert report.duplicate_points == 1
assert report.unknown_sensors == {"unknown_tag"}
assert report.unmapped_stages == {"unknown_stage"}
```

- [x] **Step 2: Verify missing wide sensor columns are invalid**

Required assertion:

```python
assert report.schema_valid is False
assert report.missing_sensor_columns == {"o2"}
```

- [x] **Step 3: Verify invalid CLI behavior**

Required behavior:

```python
assert result.returncode == 1
assert "schema_valid: False" in report_text
assert "unknown_sensors" in report_text
assert "unmapped_stages" in report_text
assert "missing_sensor_columns" in report_text
assert "non_numeric_values" in report_text
```

- [x] **Step 4: Run task tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_real_data_schema_map.py::test_validation_report_flags_common_real_data_mapping_errors tests/test_real_data_schema_map.py::test_validation_report_flags_missing_wide_sensor_columns tests/test_cli_real_data_validate.py::test_cli_invalid_real_data_returns_nonzero_but_writes_report -v
```

Expected: PASS with no warnings.

- [x] **Step 5: Commit if this task changed files**

```bash
git add src/b08_model_core/real_data/schema_map.py src/b08_model_core/real_data/validation_report.py src/b08_model_core/cli.py tests/test_real_data_schema_map.py tests/test_cli_real_data_validate.py
git commit -m "feat: report real data validation failures"
```

## Task 3: Forecasting Experiment Scaffold

**Files:**
- Modify: `src/b08_model_core/experiments/forecasting.py`
- Modify: `src/b08_model_core/evaluation/open_source_matrix.py`
- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_experiment_scaffold.py`

- [x] **Step 1: Verify command test exists**

Required command:

```bash
.venv/bin/python -m b08_model_core.cli experiment forecasting \
  --dataset <dataset.parquet> \
  --output <report.md> \
  --max-windows 40
```

Required report assertions:

```python
assert "Forecasting Experiment" in text
assert "RobustStageForecaster" in text
assert "FlowState" in text
assert "TTM" in text
assert "TimesFM" in text
assert "Chronos" in text
assert "Moirai" in text
assert "skipped_optional_dependency" in text
```

- [x] **Step 2: Verify forecast-first candidate matrix**

Required assertion:

```python
assert {"FlowState", "TTM", "TimesFM", "Chronos", "Moirai"} <= {candidate.name for candidate in candidate_matrix()}
```

- [x] **Step 3: Enforce no heavyweight imports**

Implementation must not import `torch`, `transformers`, `timesfm`, `chronos`, `uni2ts`, or model weights directly. Optional adapters may use `importlib.util.find_spec`.

- [x] **Step 4: Run task tests**

```bash
.venv/bin/python -m pytest tests/test_experiment_scaffold.py -v
```

Expected: PASS.

- [x] **Step 5: Commit if this task changed files**

```bash
git add src/b08_model_core/experiments/forecasting.py src/b08_model_core/evaluation/open_source_matrix.py src/b08_model_core/cli.py tests/test_experiment_scaffold.py
git commit -m "feat: add forecasting experiment scaffold"
```

## Task 4: Documentation and Review Surface

**Files:**
- Modify: `README.md`
- Modify: `docs/index.html`
- Modify: `docs/reviews/real-data-schema-map.md`
- Modify: `configs/real_data_schema_map.template.yaml`

- [x] **Step 1: Verify command documentation**

README must include:

```bash
.venv/bin/b08-model-core real-data validate --input path/to/real_export.csv --schema-map configs/real_data_schema_map.template.yaml --output reports/real_data_validation.md
.venv/bin/b08-model-core experiment forecasting --dataset data/simulated/furnace_fu13_45d.parquet --output reports/forecasting_experiment.md
```

- [x] **Step 2: Verify docs index link**

`docs/index.html` must link to:

```text
reviews/real-data-schema-map.md
```

- [x] **Step 3: Run exact HTML link checker**

```bash
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
root = Path('.').resolve()
class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs=[]
    def handle_starttag(self, tag, attrs):
        for k,v in attrs:
            if k == 'href' and v and not v.startswith(('http://','https://','mailto:','#')):
                self.hrefs.append(v.split('#',1)[0])
errors=[]
for html in sorted(Path('docs').glob('*.html')):
    p=P(); p.feed(html.read_text(encoding='utf-8'))
    for href in p.hrefs:
        target = (html.parent / unquote(href)).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(f'{html}: outside root: {href}')
            continue
        if not target.exists():
            errors.append(f'{html}: missing link target: {href} -> {target}')
if errors:
    print('\n'.join(errors)); raise SystemExit(1)
print('HTML link check passed')
PY
```

Expected: `HTML link check passed`.

- [x] **Step 4: Commit if this task changed files**

```bash
git add README.md docs/index.html docs/reviews/real-data-schema-map.md configs/real_data_schema_map.template.yaml
git commit -m "docs: add real data validation workflow"
```

## Task 5: Final Verification Gate

**Files:**
- No new files.

- [x] **Step 1: Run full tests**

```bash
.venv/bin/python -m pytest -v
```

Expected: all tests pass.

- [x] **Step 2: Run sample commands**

Create a temporary CSV and run:

```bash
.venv/bin/b08-model-core real-data validate --input <tmp.csv> --schema-map configs/real_data_schema_map.template.yaml --output <tmp-report.md>
.venv/bin/b08-model-core experiment forecasting --dataset data/simulated/furnace_fu13_45d.parquet --output <tmp-forecast.md> --max-windows 40
```

Expected:

- validation report contains `Real Data Validation`
- forecasting report contains `Forecasting Experiment`
- external models are marked `skipped_optional_dependency` when packages are absent

- [x] **Step 3: Git hygiene**

```bash
git diff --check
git diff --cached --check
git status --short --ignored
```

Expected:

- no whitespace errors
- no generated parquet, `.venv`, pycache, egg-info, or pytest cache staged

## Acceptance Criteria

- Long and wide real-data exports normalize into the canonical observation schema.
- Invalid real-data exports produce a written report and non-zero CLI exit code.
- Validation reports flag timestamp parse errors, non-numeric values, duplicate points, unknown sensors, unmapped stages, missing mapped source columns, and missing wide-format sensor columns.
- Forecasting experiment scaffold runs without external model weights and compares against `RobustStageForecaster`.
- Forecasting CLI rejects non-positive `--max-windows` before running the experiment.
- Forecast-first candidates include FlowState, TTM, TimesFM, Chronos, and Moirai.
- Optional external model dependencies remain optional.
- Docs expose the real-data validation and forecasting scaffold commands.
- Full pytest suite passes.
