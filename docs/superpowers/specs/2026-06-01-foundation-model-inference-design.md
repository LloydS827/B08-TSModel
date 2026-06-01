# B08 Foundation Model Inference Design

Date: 2026-06-01

## Purpose

The previous stage finished the model-core sandbox: simulated FU13-like data, canonical observation schema, model windows, forecasting baselines, benchmark reports, real-data validation, and an experiment scaffold.

This design defines the next stage. The goal is to use simulated data to run a real open-source time-series foundation model end to end, compare it against the existing baselines, and form an evidence-based judgement about the next modeling route.

The first implementation should prioritize a lightweight forecasting model such as TTM, but the design must not bind the project to one model vendor, ecosystem, or checkpoint. TTM is the first viable adapter, not the project architecture.

## Decisions Already Made

- The first version should run a real foundation model, not only dependency checks.
- Open-source model dependencies and weights may be installed or downloaded on the local machine.
- Model weights must not be committed to GitHub.
- README must explain how to install dependencies, download or cache weights, and run the experiment.
- The first dataset for this stage is simulated FU13 data, because it is already controlled, reproducible, and has a baseline report.
- The design must support fallback models instead of binding the project to a fixed model family.

## Scope

In scope:

- Run zero-shot forecasting on simulated FU13 model windows with at least one real open-source foundation model.
- Compare the foundation model against `RobustStageForecaster` and `StageSeasonalNaiveForecaster`.
- Produce a Markdown experiment report with model status, metrics, local dependency and weight status, failure reasons, and route recommendation.
- Keep optional model dependencies optional, so core tests and baseline workflows do not require external model weights.
- Update README with local setup and usage instructions.
- Preserve model weights and caches as local-only artifacts.

Out of scope:

- Production alarm rules, work orders, dashboards, or report-generation systems.
- Training a custom equipment foundation model in this first pass.
- Running every candidate model at once.
- Making real FU13 data alignment the first implementation dependency.
- Committing large generated datasets, model caches, or transient experiment reports.

## Recommended First Path

Use a model-agnostic runner with TTM as the first adapter.

TTM is a suitable first model because it is forecast-first, lightweight compared with larger general-purpose models, has official Granite Time Series documentation, and maps naturally to the existing forecasting experiment scaffold.

Primary official references:

- IBM Granite Time Series documentation: https://www.ibm.com/granite/docs/models/time-series/
- Granite TTM R2 model card: https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2
- Granite TSFM getting-started notebook: https://github.com/ibm-granite/granite-tsfm/blob/main/notebooks/hfdemo/ttm_getting_started.ipynb

The first adapter may use TTM implementation details, but the surrounding experiment should speak in generic terms: model name, dependency status, weight source, context length, prediction length, metrics, and recommendation.

## Fallback Model Strategy

The project should treat model selection as a route table, not a hard-coded dependency.

| Priority | Candidate | First use | Why it is useful | Expected limitation |
| --- | --- | --- | --- | --- |
| 1 | TTM / TinyTimeMixer | zero-shot forecasting | lightweight first local inference path | forecast-only, limited stage/domain semantics |
| 2 | FlowState / Granite Time Series | forecast-first fallback | same broad Granite family, useful if TTM constraints block the first run | ecosystem may still overlap with TTM |
| 3 | TimesFM | forecasting comparator | strong forecast-only reference | different dependency and model API |
| 4 | Chronos | probabilistic forecasting comparator | useful for probabilistic forecast comparison | may require univariate or model-specific reshaping |
| 5 | Moirai / Uni2TS | multivariate probabilistic forecasting | good later comparator for uncertainty and multivariate support | heavier integration path |
| 6 | MOMENT / TSPulse / UniTS | representation, imputation, anomaly follow-up | better aligned with later multi-head foundation-model evaluation | not the shortest first forecasting path |

Fallback rule:

- If the first candidate cannot be installed, cannot download weights, or cannot adapt to `ModelWindow`, the report should record the reason and select the next candidate rather than blocking the whole stage.
- If the first candidate runs but performs poorly, it still remains useful evidence. Poor performance should trigger route judgement, not silent replacement.
- In the first implementation plan, fallback selection means a report recommendation for the next adapter to try. It does not require the first pass to implement and run every fallback model automatically.

## Architecture

### Existing Inputs

The existing canonical chain remains authoritative:

1. Simulated or normalized observation rows.
2. `build_model_windows()`.
3. `ModelWindow` objects with `X`, `mask`, `delta_t`, `stage_token`, `sensor_token`, `domain_token`, `device_token`, and `y`.
4. Baseline forecasting metrics.

The foundation-model layer must adapt to this contract. It must not replace the canonical schema.

### New Boundaries

Add a small generic foundation forecasting boundary:

```text
ModelWindow list
  -> FoundationForecastRunner
  -> FoundationForecastAdapter
  -> model-specific input conversion
  -> local model inference
  -> FoundationForecastResult
  -> metrics and report
```

Recommended units:

- `FoundationForecastRunner`: orchestrates baseline comparison, selected model execution, status handling, and metric aggregation.
- `FoundationForecastAdapter`: abstract protocol or base class for dependency checks, model loading, input conversion, prediction, and metadata.
- `TTMForecastAdapter`: first concrete adapter. It owns all TTM-specific imports and conversion logic.
- `ForecastingExperimentReport`: turns results into a Markdown report that is useful for both engineers and non-technical reviewers.

The existing `run_forecasting_experiment()` can call this runner. It should remain a simple public entry point.

## CLI Design

Extend the existing command without breaking current usage:

```bash
uv run b08-model-core experiment forecasting \
  --dataset data/simulated/furnace_fu13_45d.parquet \
  --output reports/forecasting_ttm_experiment.md \
  --model ttm \
  --context-length 512 \
  --prediction-length 96 \
  --max-windows 40
```

Recommended CLI options:

| Option | Meaning | Default |
| --- | --- | --- |
| `--model` | `baseline`, `ttm`, or later `timesfm`, `chronos`, `moirai`, `auto` | `baseline` or existing scaffold behavior |
| `--context-length` | model history length | current default unless model requires a supported value |
| `--prediction-length` | forecast horizon | current default unless model requires a supported value |
| `--max-windows` | window cap for local experiments | existing default |
| `--model-cache-dir` | optional local model cache directory | Hugging Face default cache |
| `--allow-download` | whether model weights may be downloaded | enabled for user-run model experiments, disabled in tests |

If dependency or weight setup is missing, the command should still write a report and exit with a status that makes the problem clear. Core baseline-only mode should keep returning success.

Recommended exit-code behavior:

- Baseline-only mode returns `0` when the baseline report is written successfully.
- Foundation-model mode returns `0` when the selected model runs successfully and the report is written.
- Foundation-model mode returns `1` when validation, dependency, weight, unsupported-shape, or runtime failure is captured in the report.
- Invalid CLI arguments, such as non-positive lengths, continue to be rejected by `argparse` with exit code `2`.

This keeps automation honest: a failed model run is visible to scripts, while still leaving a useful diagnostic report on disk.

## Dependency and Weight Management

Core dependencies must stay lightweight. Foundation-model dependencies should live behind optional extras, for example:

```toml
[project.optional-dependencies]
dev = ["pytest>=7"]
foundation-ttm = [
  "granite-tsfm",
  "torch",
  "transformers",
  "huggingface_hub",
]
```

Exact package names and versions should be verified during implementation against current official installation instructions. If `granite-tsfm` or its dependency names differ from the current model card, the implementation plan should use the official names available at that time.

Model weights should be local-only:

- Prefer the standard Hugging Face cache for normal use.
- Allow a local cache override such as `HF_HOME` or `--model-cache-dir`.
- Ignore `models/`, `hf_cache/`, `.cache/`, and generated model output directories.
- Do not commit downloaded checkpoints, generated parquet files, or transient experiment reports.

README should explicitly state that weights are local artifacts and must not be uploaded to GitHub.

## Data Conversion

The adapter must convert `ModelWindow` into the selected model's expected format.

General rules:

- Keep sensor channel order stable using `window.sensor_token`.
- Use only numeric `X` as the first-pass foundation-model signal.
- Preserve `stage_token`, `domain_token`, and `sensor_token` as metadata in the report even if the first model cannot consume them directly.
- Keep scaling or preprocessing inside the adapter or a shared preprocessing helper.
- Do not add TTM-specific fields to `ModelWindow`.

For forecast-only models that cannot consume stage/domain tokens, report this explicitly as an IO-coverage limitation. This limitation matters for the later direct reuse versus fine-tuning decision.

## Report Design

The experiment report should include:

- Dataset path, row count if available, window count, context length, prediction length, and sensor count.
- Baseline metrics for `RobustStageForecaster` and `StageSeasonalNaiveForecaster`.
- Foundation model selected, adapter name, package status, weight source, cache location if known, and model checkpoint identifier.
- Foundation model metrics: at minimum MAE and RMSE; interval or quantile coverage only when the model produces usable intervals or quantiles.
- Comparison against baseline, including absolute difference and percentage difference.
- IO coverage notes: whether the model used only numeric values or also supported covariates, stage, domain, and sensor context.
- Failure status and reason when inference does not complete.
- Route recommendation: direct reuse candidate, few-shot candidate, fallback comparator, or no-go for this model.

Recommended status values:

| Status | Meaning |
| --- | --- |
| `available_and_ran` | dependencies and weights were available, inference completed |
| `missing_dependency` | optional dependency is not installed |
| `missing_or_blocked_weights` | dependency exists but weights cannot be downloaded or loaded |
| `unsupported_window_shape` | model cannot consume the requested context, horizon, or channels |
| `runtime_failed` | model loaded but inference failed |
| `skipped_by_user` | user selected baseline-only mode |

## Route Judgement

The first pass should not require the foundation model to beat the baseline. The output should support judgement:

| Evidence | Judgement |
| --- | --- |
| Foundation model is clearly better than baseline and dependency cost is acceptable | direct reuse candidate |
| Foundation model is close to baseline and runs reliably | few-shot or frozen-backbone adaptation candidate |
| Foundation model is worse than baseline but cheap and stable | keep as comparator, test fallback model |
| Foundation model cannot consume the needed window shape or multi-sensor structure | no-go for direct reuse, test fallback |
| Foundation model cannot use stage/domain/sensor metadata | forecast-only candidate, not enough for full B08 foundation-model IO |
| Multiple forecast models fail or underperform | consider representation/imputation candidates before domain pretraining |

The stage should end with a grounded next-step decision, not with a model leaderboard alone.

## Testing Strategy

Required tests for implementation:

- Baseline-only experiment still runs without foundation-model dependencies.
- `--model ttm` without optional dependencies writes a clear missing-dependency report.
- Adapter input conversion preserves window count, context length, prediction length, and sensor order.
- Report contains status, checkpoint or intended checkpoint, baseline metrics, and route recommendation.
- CLI rejects invalid non-positive lengths and window counts.
- `.gitignore` protects local model caches and generated artifacts.

Optional manual verification when dependencies and weights are available:

```bash
uv sync --extra dev --extra foundation-ttm
uv run b08-model-core simulate \
  --days 45 \
  --seed 42 \
  --output data/simulated/furnace_fu13_45d.parquet
uv run b08-model-core experiment forecasting \
  --dataset data/simulated/furnace_fu13_45d.parquet \
  --output reports/forecasting_ttm_experiment.md \
  --model ttm \
  --context-length 512 \
  --prediction-length 96 \
  --max-windows 40
```

## README Requirements

README should document:

- The difference between baseline-only mode and foundation-model mode.
- The optional dependency install command.
- The expected local weight cache behavior.
- How to set or override model cache location.
- The command to run the TTM first-pass experiment.
- That model weights, caches, generated parquet data, and transient experiment reports must not be committed.
- How to interpret the report and choose direct reuse, few-shot, fallback, or no-go.

## Details.md Requirements

The progress ledger should change the next-stage plan from a generic open-source model evaluation to a more specific first step:

1. Use simulated FU13 data to run at least one real open-source foundation model locally.
2. Compare the result against existing baselines.
3. Use the evidence to decide whether to continue with direct reuse, few-shot adaptation, or fallback candidates.
4. Continue real-data alignment after the simulated-data foundation inference path is proven.

## Risks

### Dependency Drift

Open-source model packages and model cards change. Optional dependency names and exact APIs must be verified at implementation time.

Mitigation: keep all model-specific imports inside adapters and keep dependency failures reportable.

### Large Local Artifacts

Weights and model caches may be large.

Mitigation: use local caches, update ignore rules, and document that weights must not be committed.

### Misleading Forecast-Only Success

A forecast-only model may beat baseline while still failing to represent stage, sensor, and physical-domain context.

Mitigation: report IO coverage and avoid claiming full B08 model-core success from forecasting alone.

### Simulated Data Overfit

The first result uses simulated data and may not transfer to real FU13 exports.

Mitigation: use this stage to prove the model execution and evaluation chain, then validate on real data once schema alignment is ready.

## Acceptance Criteria

This design is ready for implementation planning when:

- The spec explains how to run a real foundation model locally.
- The spec keeps the first model replaceable through adapters.
- The spec includes fallback candidates and no-go conditions.
- The spec explains local-only weight handling and README updates.
- The spec defines report contents, error states, and route judgement.
- The spec stays inside the model-core sandbox boundary.

Implementation will begin only after the written spec is reviewed and approved.
