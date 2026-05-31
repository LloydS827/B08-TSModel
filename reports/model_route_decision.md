# B08 Model Route Decision

Current baseline evidence: RobustStageForecaster MAE=9.124260, interval_coverage=0.927734.

| Route | Go condition | No-Go condition | Evidence |
| --- | --- | --- | --- |
| direct_reuse | Frozen model beats baseline and covers required IO | Cannot encode stage/domain context | zero-shot metrics and adapter availability |
| fine_tune | Backbone helps but domain gap remains | Fine-tuning gain is unstable or too costly | adapter/linear-probe lift against baseline |
| domain_pretraining | Open models fail stage-conditioned degradation tasks | Data or compute is insufficient | custom pretraining objective beats baseline |
