# B08 Model Core Evaluation

Dataset summary: rows=5213392, batches=160, sensors=16, stages=8, failure_proxy_rows=160455

The stage-aware robust median/MAD forecaster is the baseline comparison for forecasting and interval coverage.

## Baseline Metrics

Window count used: train=140, test=60, context_length=128, prediction_length=32.
RobustStageForecaster MAE: 9.124260; interval_coverage: 0.927734.
StageSeasonalNaiveForecaster MAE: 18.430603; interval_coverage: 0.000000.

## Adapter availability

- TTM: unavailable: optional TTM dependency is not installed; heads=forecasting
- MOMENT: unavailable: optional MOMENT dependency is not installed; heads=forecasting, imputation, representation
- Chronos: unavailable: optional Chronos dependency is not installed; heads=forecasting
- TimesFM: unavailable: optional TimesFM dependency is not installed; heads=forecasting

Related route report: reports/model_route_decision.md

| model name | task | metric | baseline comparison | route recommendation | reason |
| --- | --- | --- | --- | --- | --- |
| RobustStageForecaster | forecasting | MAE, interval_coverage | baseline | baseline | Minimum delivery bar for the model-core sandbox. |
| FlowState | forecasting | direct_use_score, fine_tune_score | 0.76 direct / 0.80 fine-tune vs baseline | direct_reuse | Useful as an additional forecast-first comparator before custom pretraining. |
| TSPulse | forecasting, representation, anomaly | direct_use_score, fine_tune_score | 0.62 direct / 0.82 fine-tune vs baseline | fine_tune | Promising backbone, but B08 stage/domain conditioning needs adaptation. |
| MOMENT | forecasting, imputation, classification, representation | direct_use_score, fine_tune_score | 0.70 direct / 0.86 fine-tune vs baseline | fine_tune | Covers many heads, but degradation labels require project-specific heads. |
| TTM | forecasting | direct_use_score, fine_tune_score | 0.75 direct / 0.78 fine-tune vs baseline | direct_reuse | Useful as a frozen forecasting gate before custom work. |
| Chronos | forecasting | direct_use_score, fine_tune_score | 0.72 direct / 0.75 fine-tune vs baseline | direct_reuse | Worth evaluating for forecasting, but not sufficient for full B08 IO contract. |
| TimesFM | forecasting | direct_use_score, fine_tune_score | 0.74 direct / 0.76 fine-tune vs baseline | direct_reuse | Good for forecast head, insufficient for full B08 IO contract. |
| UniTS | forecasting, classification, imputation | direct_use_score, fine_tune_score | 0.64 direct / 0.83 fine-tune vs baseline | fine_tune | Needs adapter work but maps well to the B08 task mix. |
| Moirai | forecasting | direct_use_score, fine_tune_score | 0.72 direct / 0.79 fine-tune vs baseline | direct_reuse | Good for forecasting benchmark before custom heads are justified. |

Domain pretraining gate: choose domain_pretraining when direct_reuse and fine_tune fail to cover stage-conditioned, multi-domain degradation representation.
Route recommendation: first benchmark direct_reuse candidates, then fine_tune MOMENT/TSPulse/UniTS, then consider domain_pretraining only if required IO coverage remains below baseline.
