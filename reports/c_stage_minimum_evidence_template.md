# C 阶段最小证据报告模板

本模板用于记录契约校验后的真实实验或审计结果。填写前必须先通过 `configs/c_stage_minimum_evidence.yaml` 的契约校验；未执行、未复核或未通过的内容只能标记为待填写、needs-review 或 failed。

## 报告元信息

- report_id:
- author:
- date:
- contract_version: `configs/c_stage_minimum_evidence.yaml`
- run_id:
- status: planned / running / needs-review / failed / accepted
- linked_artifacts:

## 数据与标签核对

| evidence_id | source_status | license_status | schema_status | label_status | split_policy_status | reviewer | status |
|---|---|---|---|---|---|---|---|
| E1_forecasting_residual | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |
| E2_representation | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |
| E3_imputation | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |
| E4_open_data_pm | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |
| E5_patent_effect | inherited_from_E1_to_E4 | mixed_boundary_review_required | evidence_output_traceability_required | expert_or_proxy_review_status_required_where_used | inherited_from_E1_to_E4 | 待填写 | 待填写 |

## E1_forecasting_residual

- experiment_id: `c0_fu13_forecast_residual_v1`
- primary evidence question:
- dataset and split:
- baseline and candidate:
- metrics:
- artifacts:
- result_summary:
- failure_cases:
- boundary_notes:
- invalid_claims: 不得解释为生产告警、FU13 RUL、自动维修建议或专利授权结论。

## E2_representation

- experiment_id: `c0_fu13_representation_probe_v1`
- primary evidence question:
- dataset and split:
- baseline and candidate:
- metrics:
- artifacts:
- result_summary:
- failure_cases:
- boundary_notes:
- invalid_claims: 不得解释为真实健康等级、生产告警、自动维修建议或专利授权结论。

## E3_imputation

- experiment_id: `c0_fu13_imputation_reconstruction_v1`
- primary evidence question:
- dataset and split:
- baseline and candidate:
- metrics:
- artifacts:
- result_summary:
- failure_cases:
- boundary_notes:
- invalid_claims: 不得解释为异常识别结论、生产告警、FU13 RUL 或自动维修建议。

## E4_open_data_pm

- experiment_id: `c0_open_data_pm_audit_v1`
- primary evidence question:
- open dataset candidates:
- license and use boundary:
- task metric mapping:
- FU13 gap note:
- result_summary:
- failure_cases:
- boundary_notes:
- invalid_claims: 不得解释为 FU13 已具备同等标签、生产级 RUL、生产告警或自动维修建议。

## E5_patent_effect

- experiment_id: `c0_patent_effect_and_decision_gate_v1`
- required input evidence: E1_forecasting_residual, E2_representation, E3_imputation, E4_open_data_pm
- CT mapping: `CT4_decision_gate`
- patent ids: P1_stage_sensor_encoding, P2_small_sample_pretraining, P3_weak_label_anomaly_signal, P4_real_open_data_fusion, P5_multitask_health_evaluation
- prior-art risk table link:
- result_summary:
- failure_cases:
- boundary_notes:
- invalid_claims: 不得解释为专利授权结论，不得解释为新颖性或创造性法律判断，不得解释为生产告警或自动维修建议。

## P1-P5 技术效果样例表

| patent_id | minimum comparison | evidence artifact | prior-art risk entry | status |
|---|---|---|---|---|
| P1_stage_sensor_encoding | with vs without stage and sensor domain encoding | representation_or_residual_group_difference | required | 待填写 |
| P2_small_sample_pretraining | zero_shot_vs_frozen_probe_vs_few_shot_adapter | small_sample_adaptation_table | required | 待填写 |
| P3_weak_label_anomaly_signal | forecasting_residual_vs_imputation_error_vs_weak_proxy_queue | candidate_signal_review_table | required | 待填写 |
| P4_real_open_data_fusion | fu13_schema_vs_open_data_schema_task_metric_mapping | fusion_mapping_and_gap_table | required | 待填写 |
| P5_multitask_health_evaluation | forecasting_only_vs_residual_reconstruction_probe_open_data_summary | multitask_health_evidence_table | required | 待填写 |

## CT4_decision_gate / C -> B 决策

- decision: Go_to_B_minimal_prototype / Stay_in_C_adaptation / Knowledge_only_consolidation / No_Go_hold
- evidence basis:
- missing evidence:
- reviewer notes:
- final rationale:

## Go / No-Go criteria

- primary_task:
- strong_baseline:
- minimum_gain:
- seed_policy:
- confidence_interval_policy:
- failure_conditions:

## 禁止过度解释

- 不得把 planned、needs-review 或 failed 状态写成 completed。
- 不得把 proxy、残差、重建误差、probe 分数或开放数据映射写成线上业务结论、FU13 剩余寿命结论、自动维修建议、专利授权结论、新颖性判断或创造性判断。
- 缺少核对项时不得 Go；不得在缺少 source_status、license_status、schema_status、label_status、split_policy_status 任一核对项时给出 Go_to_B_minimal_prototype。
- 不得绕过 prior-art 风险入口给出 P1-P5 技术效果总结。
