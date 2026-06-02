# B08 Real Data Validation Loop Design

Date: 2026-06-02

## Purpose

This stage moves B08 from a simulated model-core sandbox into the first real FU13 data validation loop.

The goal is not only to run exploratory analysis, and not only to run a model. The goal is to prove that the uploaded real FU13 exports can move through the full model-core path:

```text
real multi-CSV exports
-> canonical observation schema
-> continuous-furnace cycle reconstruction
-> data quality and scenario diagnostics
-> stage-local and cross-stage model windows
-> baseline forecasting
-> TTM forecasting comparison
-> stage conclusion and next modeling route
```

## Current Inputs

The real data currently lives under `data/real/`.

Available files:

- Eight sensor CSV files, each with `time,value`.
- `stage_data.csv`, a stage transition table with `time,stage_name`.
- `readme.md` and `参数信息.md`, describing sensor tags, units, limits, scenarios, time policy, and label constraints.

Known constraints:

- The uploaded range is approximately one month.
- Timestamps are true UTC and should remain UTC in this stage.
- FU13 is a continuous furnace.
- Not every cycle has every stage, but `上盖关闭 -> 溶解 -> 浇筑` is the minimum guaranteed production structure.
- There are no abnormal, maintenance, downtime, or alarm records in this slice.
- Oxygen content is encoded relative to air oxygen content: air is roughly `0`, vacuum is roughly `-21`.

## Scope

In scope:

- Add a FU13-specific multi-CSV assembly path.
- Add a real FU13 schema/config file for this data slice.
- Generate a canonical long observation table for real data.
- Reconstruct `cycle_id` / `batch_id` from stage transitions.
- Produce data quality, EDA, and business-scenario diagnostics.
- Build both stage-local and cross-stage cycle windows.
- Run baseline forecasting on real windows.
- Run TTM forecasting on real windows and compare it to baseline under the same metric/reporting lens.
- Update project progress documentation after the validation loop is implemented.

Out of scope:

- Mutating original files in `data/real/`.
- Treating reconstructed `cycle_id` as an authoritative on-site batch number.
- Claiming real failure prediction, maintenance recommendation, RUL, or calibrated failure probability.
- Training a custom equipment foundation model in this stage.
- Implementing every fallback foundation model adapter.

## Key Decisions

1. The current stage is named **真实数据验证闭环**.
2. The stage includes standardization, data quality/EDA, scenario diagnostics, baseline forecasting, and TTM comparison.
3. The real FU13 input should use a dedicated multi-CSV assembly path instead of forcing it through the existing single-file long/wide schema map.
4. `batch_id` should be filled with reconstructed `cycle_id`.
5. A valid production cycle must at minimum contain `上盖关闭 -> 溶解 -> 浇筑`.
6. `抽真空`, `氩气导入`, `测温`, and `冷却` are optional cycle stages.
7. Both `stage-local` and `cross-stage cycle` windows should be considered.
8. Baseline forecasting is required.
9. TTM forecasting comparison is required for this stage. Completion does not require TTM to outperform baseline, but it does require a real attempt and a reportable outcome: ran and compared, or clearly blocked by dependency, cache, window shape, input scale, or runtime reason.
10. Reports must break results down by sensor and business scenario, not only global aggregate metrics.
11. Out-of-limit values are data quality issues or candidate abnormal signals, not real failure labels.
12. Without alarms, maintenance records, downtime records, or abnormal labels, this stage only validates normal-operation forecasting, residual behavior, and candidate abnormal signals.

## Configuration Design

Create a real data config such as:

```text
configs/fu13_real_data_schema.yaml
```

The config should be the engineering source of truth for this slice. Markdown files under `data/real/` remain business context, not runtime configuration.

The config should include:

- `device_id`: `FU13`
- timestamp policy: UTC
- stage file path
- cycle reconstruction rules
- sensor definitions:
  - source CSV file
  - Chinese parameter name
  - collector name
  - source tag
  - normalized `sensor_id`
  - unit
  - lower and upper limit
  - physical domain
  - business scenario
  - primary related stages

Recommended domains:

| Sensor | Domain |
| --- | --- |
| `O2Content`, `O2Content2` | `atmosphere` |
| `PumpShake1`, `PumpShake2` | `mechanical` |
| `CrucibleForwardPressure`, `CrucibleReturnPressure`, `SysSelfPressure` | `hydraulic` |
| `LeakElec` | `electrical` |

## Architecture

Keep the current generic schema map path for ordinary single-file exports. Add a dedicated FU13 multi-file path for this real dataset.

Suggested modules:

```text
src/b08_model_core/real_data/fu13_loader.py
src/b08_model_core/real_data/cycle_builder.py
src/b08_model_core/real_data/diagnostics.py
```

Responsibilities:

- `fu13_loader.py`: read the YAML config, load sensor CSV files, align stage transitions, attach metadata, and produce canonical observations.
- `cycle_builder.py`: reconstruct `cycle_id` / `batch_id` from `stage_data.csv`.
- `diagnostics.py`: compute quality, stage, cycle, sensor, and scenario diagnostics.

The original `schema_map.py` remains for generic long/wide real exports.

## Data Assembly

The real canonical table should contain the existing observation schema:

- `timestamp`
- `device_id`
- `batch_id`
- `stage`
- `sensor_id`
- `value`
- `unit`
- `domain`
- `quality_flag`
- `degradation_label`
- `failure_proxy`

Assembly rules:

- Read each sensor CSV as a time series with source `time,value`.
- Parse timestamps as UTC with mixed precision support.
- Preserve original sensor values; do not smooth or clean before diagnostics.
- Align stages using nearest previous stage transition.
- Use reconstructed `cycle_id` as `batch_id`.
- Set `degradation_label` to `normal`.
- Set `failure_proxy` to `false`.
- Do not alter files under `data/real/`.

Expected local derived output:

```text
data/processed/fu13_real_observations.parquet
```

Large generated data should remain local-only unless the user explicitly requests otherwise.

## Cycle Reconstruction

The cycle builder should treat FU13 as a continuous furnace.

Rules:

- `上盖关闭` is a candidate cycle start.
- A valid production cycle must contain `上盖关闭 -> 溶解 -> 浇筑` in order.
- `抽真空`, `氩气导入`, `测温`, and `冷却` are optional.
- Long `上盖开启` periods are waiting or interval states, not production-core stages.
- Repeated `溶解`, short jumps, and missing optional stages are not automatically errors.
- Segments that cannot satisfy the minimum structure should be marked `partial_cycle` or `unassigned_cycle`.

The report must state that `cycle_id` is reconstructed for model use and is not an on-site native furnace/batch identifier.

## Quality Flags

Use simple flags first:

- `good`: parseable time, parseable value, aligned stage, assigned cycle, and value within configured limits.
- `invalid`: nonnumeric value or value outside configured limits.
- `missing`: introduced by later resampling or alignment.
- `unassigned_stage`: no stage could be aligned.
- `unassigned_cycle`: no valid cycle could be assigned.

These flags support model input quality and candidate abnormal analysis. They do not establish failure labels.

## Diagnostics

Produce a real data validation report such as:

```text
reports/real_data_validation.md
```

It should include:

- sensor files loaded and matched
- timestamp parse status
- time range and sampling interval summary
- missing/gap/duplicate statistics
- stage coverage and stage duration distribution
- cycle counts and complete/partial/unassigned proportions
- per-sensor value distribution
- per-sensor out-of-limit counts
- readiness judgement for model-window construction

Produce a scenario diagnostics report such as:

```text
reports/real_scenario_diagnostics.md
```

Scenario coverage:

| Scenario | Sensors | Primary stages | Diagnostic focus |
| --- | --- | --- | --- |
| 炉内气氛检测 | `O2Content`, `O2Content2` | `溶解`, `浇筑` | oxygen behavior by stage, drift, out-of-limit points |
| 机械泵震动 | `PumpShake1`, `PumpShake2` | `抽真空` | vibration behavior in vacuum-related operation |
| 液压系统检测 | `CrucibleForwardPressure`, `CrucibleReturnPressure`, `SysSelfPressure` | `浇筑` | pressure response and limit behavior |
| 漏液电流监测 | `LeakElec` | production stages | trend, spikes, out-of-limit candidates |

Each scenario should conclude which task type is most suitable:

- forecasting
- residual detection
- threshold/rule diagnostics
- stage classification
- descriptive statistics only

## Model Validation

Baseline forecasting is required.

TTM forecasting comparison is also required for this stage. The required outcome is evidence, not a guaranteed win:

- If TTM runs, compare it with baseline using the same windows and metrics.
- If TTM does not run, record the precise reason and keep the failure as evidence for model-route planning.
- Do not mark TTM as successful unless real inference ran.

Window modes:

- `stage-local`: group by `device_id + cycle_id + stage`.
- `cross-stage cycle`: group by `device_id + cycle_id`, preserve `stage_token`.

Reporting must avoid misleading global-only metrics. At minimum, metrics should be broken down by:

- sensor
- business scenario
- window mode

The first model report may still include global metrics, but global metrics are secondary.

Candidate report paths:

```text
reports/real_baseline_forecasting.md
reports/real_ttm_forecasting.md
```

## CLI Direction

Suggested commands:

```bash
uv run b08-model-core real-data assemble-fu13 \
  --input-dir data/real \
  --config configs/fu13_real_data_schema.yaml \
  --output data/processed/fu13_real_observations.parquet \
  --report reports/real_data_validation.md
```

```bash
uv run b08-model-core real-data diagnose-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_scenario_diagnostics.md
```

The existing `experiment forecasting` command can be reused or extended for real-data window modes and scenario filtering. The implementation plan should decide whether to extend CLI flags directly or generate filtered parquet datasets as the smaller first path.

## Documentation Updates

After implementation and verification, update `details.md` to state that the project has entered the real data validation loop.

The update should distinguish:

- real data is now being validated and modeled
- reconstructed cycles are model-side identifiers
- the stage still does not have true failure labels
- baseline and TTM results are evidence for normal-operation forecasting and residual analysis, not final predictive-maintenance delivery

## Acceptance Criteria

The stage is complete when:

- All 8 configured sensors are loaded into the canonical long table.
- Stage transitions are aligned to sensor timestamps.
- `cycle_id` / `batch_id` is generated and cycle completeness is reported.
- Canonical observations pass schema validation or report clear, bounded validation issues.
- Per-sensor limits are checked and reported.
- Four business scenarios have diagnostics and task recommendations.
- Stage-local and cross-stage cycle window readiness is evaluated.
- Baseline forecasting runs on real windows.
- TTM forecasting is attempted on real windows and compared with baseline if it runs; otherwise the report records a specific blocker.
- Metrics are reported by sensor and scenario, not only globally.
- `details.md` is updated after verified implementation.

## Risks

### Cycle Reconstruction Bias

The reconstructed `cycle_id` may not match an operator-recognized furnace/batch ID. The implementation must label it as model-side reconstruction.

### No Failure Labels

Without alarms, maintenance records, downtime records, or abnormal labels, this stage cannot validate true failure prediction. It can validate normal forecasting, residual behavior, and candidate abnormal signals.

### Metric Misinterpretation

Different sensors have different scales and operating stages. Global MAE can hide failures. Sensor-level and scenario-level metrics are required.

### TTM Runtime Constraints

TTM may be blocked by dependency, cache, window shape, prediction length, or input scaling issues. A failed TTM run should be reported as route evidence, not hidden.

## Non-Goals

- No production alarms.
- No work-order recommendations.
- No RUL claims.
- No calibrated failure probability.
- No custom foundation model training.
- No broad refactor of unrelated model-core modules.
