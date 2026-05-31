# B08 Code Review and Next-Stage Execution Plan

Date: 2026-05-31

## Current Stage

The project is now at the model-core MVP sandbox stage.

This means the workbench can generate FU13-like data, construct model windows, run baseline evaluation, produce route reports, and support the first round of open-source model experiments. It is not yet a production predictive-maintenance system and it is not yet a trained foundation model.

## Code Review Result

Reviewed areas:

- configuration and simulation consistency
- schema and model-window contract
- degradation labels and failure proxy
- baseline and benchmark reproducibility
- optional open-source model adapters
- report and knowledge-output artifacts

Findings addressed in this review pass:

1. Simulator configuration pass-through
   - Issue: stage durations and sensor definitions were partly hard-coded.
   - Fix: `generate_batch_timeline`, `generate_signals`, `simulate_dataset`, and CLI simulation now accept and use `config_path`.
   - Evidence: tests cover config-driven target batches, stage durations, and sensor lists.

2. Cross-stage model windows
   - Issue: `allow_cross_stage=True` still grouped windows by stage.
   - Fix: cross-stage windows now group by device and batch, preserving per-timestamp `stage_token`.
   - Evidence: tests verify at least one cross-stage window contains multiple stage tokens.

3. Benchmark credibility
   - Already addressed in the previous pass: benchmark now builds model windows and computes stage-aware baseline metrics.

Current verification command:

```bash
.venv/bin/python -m pytest -v
```

Current status:

- 21 tests pass.
- 45-day generated dataset remains a local ignored artifact.
- benchmark and route decision reports remain tracked artifacts.

## Real-Data Alignment Review

Before running serious model experiments, align one real FU13 data slice against the simulated schema.

Minimum review checklist:

| Area | Required evidence | Pass condition |
| --- | --- | --- |
| Batch identity | production batch ID or reconstructable batch boundary | every row can map to a batch or known idle period |
| Stage timeline | PLC event log, operation status, or inferred stage labels | stage labels can map to the 8 simulated stages or a documented extension |
| Sensor inventory | tag name, unit, domain, sampling period, normal range | each real tag maps to `sensor_id`, `unit`, and `domain` |
| Time axis | timezone, gaps, duplicated timestamps, sampling jitter | resampling policy is explicit and reproducible |
| Missingness | missing segments, invalid values, maintenance downtime | `quality_flag` can distinguish normal, missing, invalid, and maintenance states |
| Weak labels | maintenance logs, alarms, inspection notes, operator records | at least one failure proxy or degradation proxy can be linked to time windows |

Suggested next artifact:

```text
docs/reviews/real-data-schema-map.md
```

## First Model Experiment Plan

### Experiment 0: Freeze the current baseline

Goal: preserve a stable baseline before importing external model dependencies.

Use:

```bash
.venv/bin/b08-model-core simulate --days 45 --seed 42 --output data/simulated/furnace_fu13_45d.parquet
.venv/bin/b08-model-core benchmark --dataset data/simulated/furnace_fu13_45d.parquet --output reports/model_core_evaluation.md
```

Locked metrics:

- `RobustStageForecaster MAE`
- `interval_coverage`
- `StageSeasonalNaiveForecaster MAE`

### Experiment 1: Forecasting candidates

Primary candidates:

- IBM Granite TTM / FlowState: first local-deployment forecasting candidates.
- TimesFM: strong forecast-only comparison.
- Moirai / Uni2TS: probabilistic multivariate forecasting comparison.
- Chronos-2: probabilistic forecast reference with multivariate and covariate-informed forecasting support.

Minimum tasks:

- zero-shot or frozen inference on simulated windows
- same context/prediction lengths as baseline where possible
- compare MAE and interval/quantile coverage against `RobustStageForecaster`

### Experiment 2: Representation and imputation candidates

Primary candidates:

- MOMENT: representation, imputation, classification/anomaly probe.
- UniTS: unified multi-task comparison if installation and inference are stable.
- TSPulse: representation/anomaly candidate inside the Granite Time Series family.

Minimum tasks:

- masked imputation error
- frozen embedding stage classification
- frozen embedding degradation proxy classification
- weak-label lead-time analysis

### Experiment 3: Light adaptation

Enter only if a frozen or zero-shot backbone is useful but stage/domain gap remains.

Methods:

- linear probe
- shallow adapter
- LoRA or partial fine-tuning only after deployment cost is understood

Go/No-Go:

| Route | Go | No-Go |
| --- | --- | --- |
| direct reuse | model beats baseline and covers required IO without training | cannot represent stage/domain context |
| fine-tune | frozen backbone helps but task gap remains | gain is below baseline variance or dependency cost is too high |
| domain pretraining | open models fail stage-conditioned degradation tasks | real data volume or compute is insufficient |

## Current Source Notes

- IBM Granite Time Series now describes a family including FlowState, TTM, and TSPulse, with FlowState and TTM focused on forecasting and TSPulse on representation-oriented tasks.
- MOMENT remains relevant for forecasting, imputation, classification, anomaly detection, and representation experiments.
- TimesFM and Chronos remain forecast-oriented references; Chronos-2 should be tested rather than older Chronos-only assumptions.
- Moirai / Uni2TS remains a useful probabilistic multivariate forecasting comparison.
- UniTS remains relevant for multi-task time-series experiments.

Primary references:

- IBM Granite Time Series: https://www.ibm.com/granite/docs/models/time-series/
- IBM Granite TTM model card: https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2
- MOMENT: https://github.com/moment-timeseries-foundation-model/moment
- TimesFM: https://github.com/google-research/timesfm
- Chronos: https://github.com/amazon-science/chronos-forecasting
- Moirai / Uni2TS: https://github.com/SalesforceAIResearch/uni2ts
- UniTS: https://github.com/mims-harvard/UniTS

## Recommended Next Work Order

1. Create `docs/reviews/real-data-schema-map.md` from one real data export.
2. Add a `real-data validate` CLI command that checks schema compatibility without training.
3. Add adapter experiment scaffolding behind optional dependencies.
4. Run forecasting candidates first because they are easiest to compare against the current baseline.
5. Run representation/imputation candidates second because they are closer to the foundation-model knowledge-output value.
