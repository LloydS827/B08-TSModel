# C3.2 Open Model Cross-Dataset Evaluation Design

Date: 2026-06-11

## Context

C3.1 has passed the NASA C-MAPSS explicit local raw mapping review. The tracked review summary records:

- `schema_validated_ready_for_c32`
- `full_classic_cmapss_validated`
- 12 classic C-MAPSS raw text files reviewed under explicit local opt-in
- RUL target metadata and split/leakage guard passed
- no raw, zip, parquet, cache, or generated report artifacts committed

The project should now stop treating C3.1 as the main blocker. The next useful step is C3.2: define and execute a small, default-safe cross-dataset evaluation scaffold that connects the C-MAPSS public degradation benchmark with the existing FU13 / FU13-like evidence assets and the C2.x open model evaluation work.

## Problem

The project currently has three related but separate pieces:

1. C2.x open model evaluation/audit entries.
2. C3/C3.1 public dataset registry and C-MAPSS schema/RUL validation.
3. FU13 real/simulated evidence assets and baseline forecasting workflows.

What is missing is a decision-grade bridge that says which dataset views, tasks, models, metrics, and safety constraints are allowed into a cross-dataset evaluation. Without that bridge, the project risks either moving too slowly by continuing C3.1 paperwork, or moving too fast by running ad hoc model comparisons that overclaim benchmark meaning.

## Goals

- Add a C3.2 stage with a CLI/report entry similar to existing C-stage experiments.
- Define a narrow cross-dataset evaluation contract covering dataset views, task families, model candidates, metrics, and Go / No-Go criteria.
- Keep the default path runnable offline without raw C-MAPSS data, public downloads, external weights, training, or processed data writes.
- Allow explicit local opt-in paths to record whether local C-MAPSS and FU13 artifacts are available, without committing those artifacts.
- Produce a Markdown report that is useful for deciding the next implementation step, not for claiming production performance.
- Update README and `details.md` so the current stage becomes C3.2 instead of C3.1.

## Non-Goals

- Do not train or fine-tune any model.
- Do not download public data in the default path.
- Do not submit C-MAPSS raw files, generated reports, parquet files, caches, or model weights.
- Do not add new public datasets beyond C-MAPSS in this branch.
- Do not claim production RUL, failure probability, maintenance recommendations, production alarms, or self-developed model superiority.
- Do not require optional open model dependencies for the default C3.2 report.

## Approaches Considered

### Approach A: Design-only C3.2 specification

This would create only a spec/plan for C3.2 and defer code. It is safe but too slow now that C3.1 has passed the real raw mapping gate. The project already has stable C-stage experiment patterns, so a minimal executable scaffold is a better next step.

### Approach B: Contract-first executable scaffold

This branch adds a default-safe `experiment c-stage-c32` command, config, loader/validator, and report. The report records dataset view readiness, model candidate status, metric contract, safety policy, and Go / No-Go. Default execution does not read raw data or run models; it proves that the evaluation contract is coherent and ready for an explicit local execution branch.

This is the recommended approach. It moves the project forward from C3.1 to C3.2 while preserving the repository's safety invariant.

### Approach C: Full open model benchmark run

This would try to run open models across C-MAPSS and FU13 immediately. It looks faster, but it would mix several unresolved concerns: optional model dependencies, local weights, raw data availability, task alignment, and metric validity. It also risks overclaiming results before the cross-dataset contract is reviewed.

## Proposed Design

### Stage

Add stage `C3_2_open_model_cross_dataset_evaluation` with CLI:

```bash
uv run b08-model-core experiment c-stage-c32 \
  --config configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml \
  --output reports/c_stage_c32_open_model_cross_dataset_evaluation.md
```

The default command must exit 0 and write a report, but it must not read C-MAPSS raw data, FU13 real data, model weights, caches, or processed data.

### Config

Create `configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml` with these top-level sections:

- `stage`: expected stage id.
- `safety_policy`: `allow_network`, `allow_download`, `allow_local_raw_data`, `allow_model_cache`, `allow_training`, `allow_write_processed`.
- `prerequisites`: structured references to C3.1 review docs and required statuses.
- `dataset_views`: C-MAPSS classic RUL benchmark, FU13 real evidence, and FU13-like simulated/sandbox evidence.
- `task_contracts`: first-round task definitions.
- `model_candidates`: baseline and open model candidates inherited from C2.x.
- `model_cache_policy`: configured cache path recorded for future local execution, not inspected by default.
- `metric_contract`: metric names and when each is allowed.
- `outputs`: report path.

Default safety policy values are all false for network/download/local raw/model cache/training/processed writes.

### Dataset View Contract

First-round C3.2 should include three dataset views:

| Dataset view | Default status | Role |
| --- | --- | --- |
| `cmapss_classic_rul` | eligible_but_local_raw_required | Public RUL/degradation benchmark validated by C3.1, but not read by default. |
| `fu13_real_forecasting_evidence` | documented_evidence_only | Existing real evidence asset; not read by default and not treated as RUL ground truth. |
| `fu13_like_simulated_forecasting` | contract_ready_no_scoring | Safe sandbox reference for contract readiness only; the default C3.2 branch does not compute forecasting metrics. |

The report must explicitly state that C-MAPSS RUL results and FU13 forecasting results are not directly interchangeable. The first C3.2 branch evaluates the contract, not model superiority.

### Task Contract

The first task set should be intentionally small:

- `rul_regression`: eligible only for C-MAPSS, blocked in default path because local raw data is disabled.
- `forecasting_residual`: eligible for FU13-like / FU13 forecasting evidence, with FU13 real data remaining documented evidence unless explicitly configured.
- `representation_diagnostics`: planned, not executed in this branch.

The report should include task compatibility rows and blocked/skipped reasons.

### Model Candidate Contract

Include these candidates:

- `baseline`: required contract baseline, default-runnable as a status/report entry.
- `ttm`: optional open model candidate, skipped by default without local cache/dependencies.
- `chronos`, `timesfm`, `moirai`: watchlist / optional forecasting candidates inherited from C2.2, skipped by default.
- `moment`, `units`: representation/imputation candidates inherited from C2.x, recorded as planned/skipped until representation diagnostics becomes executable.

Default C3.2 does not instantiate open model adapters. It records whether each candidate is allowed, skipped, or pending explicit local opt-in.

### Metric Contract

The report should define metrics without overclaiming:

- RUL: MAE, RMSE, NASA score; allowed only when C-MAPSS local raw data and target mapping are explicitly enabled.
- Forecasting: MAE, RMSE, residual ranking; allowed only on forecasting windows.
- Cross-dataset summary: readiness matrix and comparable/non-comparable status, not a single leaderboard.

### Go / No-Go

Default report status should be `contract_ready_local_execution_blocked` when:

- C3.1 prerequisite status is recorded as ready with:
  - review doc path
  - `schema_validated_ready_for_c32`
  - `full_classic_cmapss_validated`
  - 12 reviewed raw files
  - leakage guard passed
- Config schema is valid.
- Dataset/task/model/metric contracts are coherent.
- No executable local raw/model run was requested.

The report should say:

- Go for C3.2 local execution design.
- No-Go for benchmark claims, production claims, or self-developed model superiority.

### Safety Boundary

C3.2 must preserve these invariants:

- Default CLI uses no network.
- Default CLI downloads nothing.
- Default CLI reads no C-MAPSS raw files and no FU13 real raw files.
- Default CLI writes no processed data.
- Default CLI does not load model weights or caches.
- Default CLI does not inspect model cache directories.
- Default CLI does not instantiate open model adapters.
- Default CLI does not train or fine-tune models.
- Generated reports under `reports/*.md` remain ignored.

### Tests

Add focused tests for:

- Config loader rejects wrong stage and unsafe default policy.
- Default config contains required C3.1 prerequisite references.
- Dataset/task/model/metric contract renders expected readiness and skip reasons.
- CLI `experiment c-stage-c32` writes a report and returns 0.
- Default CLI does not inspect configured C-MAPSS raw paths, FU13 real paths, model cache paths, or instantiate open model adapters.
- README/details document the C3.2 workflow and safety boundary.
- Existing C2/C3/C3.1 CLI entries remain available.

## File-Level Plan Preview

Expected implementation files:

- `configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml`
- `src/b08_model_core/experiments/c32_open_model_cross_dataset_evaluation.py`
- `src/b08_model_core/cli.py`
- `tests/test_c32_open_model_cross_dataset_evaluation.py`
- `tests/test_experiment_scaffold.py`
- `README.md`
- `details.md`

## Acceptance Criteria

- `uv run b08-model-core experiment c-stage-c32 --config configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml --output <tmp-report>` exits 0.
- Report includes C3.1 prerequisite status, dataset view matrix, task compatibility, model candidate status, metric contract, safety policy, and Go / No-Go.
- Default report does not claim model training, model scoring, benchmark metrics, production RUL, production alarms, or model superiority.
- Default safety policy disables network, download, local raw, model cache, training, and processed writes.
- Tests pass.
- README and `details.md` identify C3.2 as the current stage and point to the new command.

## Next Step After This Branch

If C3.2 contract scaffold passes, the next branch should implement explicit local execution for the smallest useful slice:

1. C-MAPSS RUL baseline evaluation using ignored local raw data.
2. FU13-like forecasting baseline reference using safe local/simulated data.
3. A report that keeps RUL and forecasting metrics separate instead of producing a misleading leaderboard.
