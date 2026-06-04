# C 阶段最小证据实验 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 C 阶段最小证据实验的可执行契约、配置、静态验证和报告入口，使 `E1-E5` 能服务论文/专利主线，并为后续真实实验和 C -> B 决策提供稳定边界。

**Architecture:** 本计划先实现 C0 证据契约层，不直接启动大规模训练、不下载外部数据、不改变默认运行路径。核心资产由一个 YAML 实验契约、一个 Python 静态校验模块、一份研究阅读文档及其 HTML 页面、一个报告模板组成，后续真实实验必须通过这些契约进入。

**Tech Stack:** Python、pytest、PyYAML、Markdown、HTML/CSS、现有 `src/b08_model_core` 包结构。

---

## 计划边界

本计划承接规格文件：

`docs/superpowers/specs/2026-06-04-c-stage-minimum-evidence-design.md`

本计划只完成 C0 最小证据实验的执行准备层：

| 范围 | 本计划处理 | 本计划不处理 |
| --- | --- | --- |
| 证据契约 | 定义 `E1-E5`、`CT1-CT4`、`P1-P5` 的实验配置结构 | 不写论文正文，不做专利法律判断 |
| 数据 | 记录 FU13 与公开数据的字段、许可、split 和标签核对任务 | 不下载公开数据，不发布 FU13 原始数据 |
| 模型 | 记录 baseline 和开源模型候选、失败原因字段 | 不运行 TTM/MOMENT/UniTS 等真实模型实验 |
| 工程 | 增加轻量静态校验和报告模板 | 不做泛化源码重构，不改变默认 CLI 工作流 |
| 决策 | 显式加入 `CT4_decision_gate` 和 C -> B Go / No-Go 任务 | 不进入 B 阶段自研基础模型训练 |

## 文件结构

执行本计划时只触碰以下文件。若执行过程中发现必须修改其他文件，应暂停并先更新计划。

| 文件 | 操作 | 职责 |
| --- | --- | --- |
| `configs/c_stage_minimum_evidence.yaml` | Create | C0 最小证据实验契约，包含 `E1-E5`、`CT1-CT4`、`P1-P5`、数据、模型、指标、invalid claims 和 Go / No-Go |
| `src/b08_model_core/experiments/c_stage_contract.py` | Create | 读取并静态校验 C0 契约，不运行模型、不读取真实数据 |
| `tests/test_c_stage_contract.py` | Create | 验证契约完整性、主线映射、禁止过度解释和 `CT4_decision_gate` 显式存在 |
| `docs/research/c-stage-minimum-evidence-register.md` | Create | 简短索引页，只说明来源、核心 HTML 入口和契约位置，不复制 HTML 表格 |
| `docs/research/c-stage-minimum-evidence-register.html` | Create | 上述登记页的 HTML 阅读层，延续当前 research HTML 入口风格 |
| `docs/research/index.html` | Modify | 增加 C 阶段最小证据登记页入口 |
| `reports/c_stage_minimum_evidence_template.md` | Create | 后续真实实验的报告模板，要求输出指标、失败原因、样例、invalid claims 和 C -> B 决策 |

## 实施原则

1. 先写测试，再写契约和最小实现。
2. 所有测试只做静态校验，不依赖 FU13 原始数据、公开数据下载、模型权重或网络。
3. `CT4_decision_gate` 必须显式出现在配置、测试、研究登记页和报告模板中。
4. 每个 `evidence_id` 必须至少挂接一个论文贡献或专利候选。
5. 每个实验条目必须包含 `invalid_claims`，且至少禁止生产告警、FU13 RUL、自动维修或专利授权中的相关过度解释。
6. 若某模型、数据集或任务暂不可运行，应用 `status: planned`、`status: blocked` 或 `status: needs_review` 表示，不用空结果伪装完成。
7. HTML 是核心阅读入口；Markdown 只作为短索引或来源说明，避免维护两份重复证据表。

## Task 1: 建立 C0 契约静态测试

**Files:**

- Create: `tests/test_c_stage_contract.py`
- Create later in task: `configs/c_stage_minimum_evidence.yaml`
- Create later in task: `src/b08_model_core/experiments/c_stage_contract.py`

- [ ] **Step 1: 写入失败测试**

创建 `tests/test_c_stage_contract.py`，先写静态约束测试。测试应在契约文件和校验模块不存在时失败。

```python
from pathlib import Path

import pytest
import yaml

from b08_model_core.experiments.c_stage_contract import (
    CStageContractError,
    load_c_stage_contract,
    validate_c_stage_contract,
)


CONFIG_PATH = Path("configs/c_stage_minimum_evidence.yaml")

REQUIRED_EXPERIMENT_FIELDS = {
    "experiment_id",
    "evidence_id",
    "paper_contribution_ids",
    "patent_ids",
    "dataset",
    "task_id",
    "model_or_baseline",
    "input_contract",
    "primary_metric",
    "comparison",
    "valid_when",
    "no_go_when",
    "artifact_output",
    "data_label_audit",
    "status",
    "invalid_claims",
}

REQUIRED_DATA_LABEL_AUDIT_FIELDS = {
    "source_status",
    "license_status",
    "schema_status",
    "label_status",
    "split_policy_status",
}


def test_c_stage_contract_file_exists():
    assert CONFIG_PATH.exists()


def test_contract_declares_all_required_evidence_ids():
    contract = load_c_stage_contract(CONFIG_PATH)
    evidence_ids = {item["evidence_id"] for item in contract["experiments"]}
    assert evidence_ids == {
        "E1_forecasting_residual",
        "E2_representation",
        "E3_imputation",
        "E4_open_data_pm",
        "E5_patent_effect",
    }


def test_contract_declares_ct4_decision_gate_explicitly():
    contract = load_c_stage_contract(CONFIG_PATH)
    contribution_ids = {
        contribution
        for item in contract["experiments"]
        for contribution in item.get("paper_contribution_ids", [])
    }
    assert "CT4_decision_gate" in contribution_ids


def test_each_experiment_has_invalid_claims():
    contract = load_c_stage_contract(CONFIG_PATH)
    for item in contract["experiments"]:
        assert item["invalid_claims"]
        invalid_claims_text = " ".join(item["invalid_claims"])
        assert any(
            forbidden in invalid_claims_text
            for forbidden in ["生产告警", "FU13 RUL", "自动维修", "专利授权"]
        )


def test_each_experiment_has_full_execution_contract():
    contract = load_c_stage_contract(CONFIG_PATH)
    for item in contract["experiments"]:
        assert REQUIRED_EXPERIMENT_FIELDS.issubset(item)
        assert item["input_contract"]
        assert item["comparison"]
        assert item["valid_when"]
        assert item["no_go_when"]


def test_each_experiment_has_data_label_audit_checklist():
    contract = load_c_stage_contract(CONFIG_PATH)
    for item in contract["experiments"]:
        assert REQUIRED_DATA_LABEL_AUDIT_FIELDS.issubset(item["data_label_audit"])


def test_patent_effect_examples_cover_p1_to_p5():
    contract = load_c_stage_contract(CONFIG_PATH)
    patent_effect = next(
        item
        for item in contract["experiments"]
        if item["evidence_id"] == "E5_patent_effect"
    )
    assert set(patent_effect["patent_effect_examples"]) == {
        "P1_stage_sensor_encoding",
        "P2_small_sample_pretraining",
        "P3_weak_label_anomaly_signal",
        "P4_real_open_data_fusion",
        "P5_multitask_health_evaluation",
    }


def test_decision_gate_declares_go_no_go_criteria():
    contract = load_c_stage_contract(CONFIG_PATH)
    criteria = contract["decision_gate"]["criteria"]
    assert criteria["primary_task"]
    assert criteria["strong_baseline"]
    assert criteria["minimum_gain"]
    assert criteria["seed_policy"]
    assert criteria["confidence_interval_policy"]
    assert criteria["failure_conditions"]


def test_contract_validation_rejects_missing_invalid_claims():
    contract = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    contract["experiments"][0]["invalid_claims"] = []
    with pytest.raises(CStageContractError):
        validate_c_stage_contract(contract)
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python -m pytest tests/test_c_stage_contract.py -v
```

Expected: FAIL，原因是 `b08_model_core.experiments.c_stage_contract` 或 `configs/c_stage_minimum_evidence.yaml` 尚不存在。

- [ ] **Step 3: 提交测试骨架**

```bash
git add tests/test_c_stage_contract.py
git commit -m "test: add c stage evidence contract checks"
```

## Task 2: 实现 C0 契约文件和校验模块

**Files:**

- Create: `configs/c_stage_minimum_evidence.yaml`
- Create: `src/b08_model_core/experiments/c_stage_contract.py`
- Modify: `tests/test_c_stage_contract.py`

- [ ] **Step 1: 创建 YAML 契约文件**

创建 `configs/c_stage_minimum_evidence.yaml`，保持静态、轻量、无本机路径。

每条 `experiments` 记录都必须包含 `input_contract`、`comparison`、`valid_when`、`no_go_when` 和 `data_label_audit`。E5 必须包含覆盖 `P1-P5` 的 `patent_effect_examples`。`decision_gate.criteria` 必须显式列出主任务、强基线、最低增益、多 seed 或置信区间口径，以及失败条件。

```yaml
stage: C0_minimum_evidence
status: planned
updated_at: "2026-06-04"
source_spec: docs/superpowers/specs/2026-06-04-c-stage-minimum-evidence-design.md
principles:
  - 论文/专利知识成果优先
  - FU13 真实场景优先
  - 最小闭环优先
  - 强基线优先
  - 失败可记录
  - 禁止过度解释
experiments:
  - experiment_id: c0_fu13_forecast_residual_v1
    evidence_id: E1_forecasting_residual
    paper_contribution_ids:
      - CT2_layered_validation
    patent_ids:
      - P3_weak_label_anomaly_signal
      - P5_multitask_health_evaluation
    dataset:
      name: FU13
      role: real_pipeline_validation
      license_status: internal_boundary_to_confirm
      mapping_status: planned
      split_policy: time_or_run_split_to_define
    task_id: fu13_forecasting_residual_v1
    model_or_baseline:
      - rolling_or_seasonal_naive
      - TTM
    primary_metric:
      - MAE
      - RMSE
    input_contract:
      window: FU13 aligned multivariate window
      metadata_policy: stage and quality fields recorded; direct input usage must be declared
      leakage_guard: future observations and review labels excluded from model inputs
    comparison:
      required_baseline: rolling_or_seasonal_naive
      candidate_model: TTM
      same_split_required: true
    valid_when:
      - window_horizon_target_and_missing_rules_are_fixed_before_run
      - residuals_can_be_traced_to_variable_time_and_stage
    no_go_when:
      - split_policy_cannot_prevent_future_leakage
      - residual_candidates_cannot_be_reproduced_or_traced
    artifact_output:
      - forecasting_metrics_table
      - residual_distribution
      - top_k_candidate_examples
      - failure_cases
    data_label_audit:
      source_status: internal_source_record_required
      license_status: internal_use_boundary_required
      schema_status: timestamp_device_sensor_stage_quality_required_or_unknown
      label_status: weak_label_source_and_confidence_required
      split_policy_status: time_or_run_split_required_before_execution
    status: planned
    invalid_claims:
      - 不得解释为生产告警
      - 不得解释为 FU13 RUL
      - 不得解释为自动维修建议
      - 不得解释为专利授权结论
  - experiment_id: c0_fu13_representation_probe_v1
    evidence_id: E2_representation
    paper_contribution_ids:
      - CT1_problem_definition
    patent_ids:
      - P1_stage_sensor_encoding
      - P2_small_sample_pretraining
    dataset:
      name: FU13
      role: real_pipeline_validation
      license_status: internal_boundary_to_confirm
      mapping_status: planned
      split_policy: time_batch_or_run_split_to_define
    task_id: fu13_representation_probe_v1
    model_or_baseline:
      - simple_statistical_embedding
      - MOMENT
      - UniTS
    primary_metric:
      - macro_F1
      - clustering_score
    input_contract:
      window: FU13 representation window
      metadata_policy: stage_quality_and_failure_proxy_must_be_marked_as_input_or_probe_label
      leakage_guard: probe labels must not be used to train frozen embeddings
    comparison:
      required_baseline: simple_statistical_embedding
      candidate_model:
        - MOMENT
        - UniTS
      same_split_required: true
    valid_when:
      - label_source_and_input_exclusion_are_declared
      - probe_train_and_test_windows_are_isolated
    no_go_when:
      - stage_or_quality_label_leaks_into_probe_input
      - class_distribution_or_split_policy_makes_probe_uninterpretable
    artifact_output:
      - representation_probe_report
      - metadata_input_exclusion_note
      - visualization_examples
    data_label_audit:
      source_status: internal_source_record_required
      license_status: internal_use_boundary_required
      schema_status: stage_quality_sensor_domain_required_or_unknown
      label_status: probe_label_source_and_confidence_required
      split_policy_status: time_batch_or_run_split_required_before_execution
    status: planned
    invalid_claims:
      - 不得解释为真实健康等级
      - 不得解释为生产告警
      - 不得解释为自动维修建议
      - 不得解释为专利授权结论
  - experiment_id: c0_fu13_imputation_reconstruction_v1
    evidence_id: E3_imputation
    paper_contribution_ids:
      - CT2_layered_validation
      - CT3_unified_schema_metric
    patent_ids:
      - P5_multitask_health_evaluation
    dataset:
      name: FU13
      role: real_pipeline_validation
      license_status: internal_boundary_to_confirm
      mapping_status: planned
      split_policy: time_or_run_split_to_define
    task_id: fu13_imputation_reconstruction_v1
    model_or_baseline:
      - simple_imputation_baseline
      - MOMENT
      - UniTS
    primary_metric:
      - reconstruction_MAE
      - reconstruction_RMSE
    input_contract:
      window: FU13 multivariate reconstruction window
      metadata_policy: mask_strategy_and_visible_context_declared_before_execution
      leakage_guard: mask positions generated only inside evaluation windows
    comparison:
      required_baseline: simple_imputation_baseline
      candidate_model:
        - MOMENT
        - UniTS
      same_split_required: true
    valid_when:
      - mask_ratio_visible_context_and_target_variables_are_fixed_before_run
      - reconstruction_errors_can_be_reported_by_variable_and_mask_type
    no_go_when:
      - mask_task_is_trivial_or_uninterpretable
      - train_and_evaluation_windows_leak
    artifact_output:
      - imputation_metrics_table
      - variable_level_reconstruction_errors
      - mask_strategy_note
      - reconstruction_failure_examples
    data_label_audit:
      source_status: internal_source_record_required
      license_status: internal_use_boundary_required
      schema_status: sensor_domain_unit_and_missing_rules_required_or_unknown
      label_status: no_supervised_label_required_but_mask_policy_required
      split_policy_status: time_or_run_split_required_before_execution
    status: planned
    invalid_claims:
      - 不得解释为异常识别结论
      - 不得解释为生产告警
      - 不得解释为 FU13 RUL
      - 不得解释为自动维修建议
  - experiment_id: c0_open_data_pm_audit_v1
    evidence_id: E4_open_data_pm
    paper_contribution_ids:
      - CT2_layered_validation
      - CT3_unified_schema_metric
    patent_ids:
      - P4_real_open_data_fusion
    dataset:
      name:
        - C-MAPSS
        - IMS Bearing
        - PRONOSTIA / FEMTO-ST
        - Tennessee Eastman Process
      role: open_data_supplement
      license_status: needs_review
      mapping_status: planned
      split_policy: dataset_specific_to_define
    task_id: open_data_pm_mapping_v1
    model_or_baseline:
      - dataset_specific_engineering_baseline
      - shared_adapter_candidate
    primary_metric:
      - dataset_specific_metric
    input_contract:
      window: dataset_specific_run_or_process_window
      metadata_policy: source_dataset_label_semantics_and_mapping_status_declared
      leakage_guard: same_unit_run_or_fault_trajectory_must_not_cross_splits
    comparison:
      required_baseline: dataset_specific_engineering_baseline
      candidate_model: shared_adapter_candidate
      same_split_required: true
    valid_when:
      - official_source_license_label_and_split_policy_are_recorded
      - dataset_task_maps_to_task_metric_matrix
    no_go_when:
      - license_or_training_use_boundary_is_unclear
      - label_semantics_cannot_support_the_selected_metric
    artifact_output:
      - source_license_audit_table
      - task_metric_mapping
      - fu13_gap_note
    data_label_audit:
      source_status: official_or_primary_source_required
      license_status: license_and_training_use_review_required
      schema_status: dataset_to_b08_schema_mapping_required
      label_status: label_semantics_and_confidence_required
      split_policy_status: unit_run_fault_or_process_split_required
    status: needs_review
    invalid_claims:
      - 不得解释为 FU13 已具备同等标签
      - 不得解释为生产级 RUL
      - 不得解释为生产告警
      - 不得解释为自动维修建议
  - experiment_id: c0_patent_effect_and_decision_gate_v1
    evidence_id: E5_patent_effect
    paper_contribution_ids:
      - CT4_decision_gate
    patent_ids:
      - P1_stage_sensor_encoding
      - P2_small_sample_pretraining
      - P3_weak_label_anomaly_signal
      - P4_real_open_data_fusion
      - P5_multitask_health_evaluation
    dataset:
      name:
        - FU13
        - open_data_candidates
      role: patent_effect_and_stage_decision
      license_status: mixed_to_confirm
      mapping_status: planned
      split_policy: inherited_from_e1_to_e4
    task_id: c_to_b_decision_gate_v1
    model_or_baseline:
      - e1_to_e4_outputs
    primary_metric:
      - go_no_go_decision
    input_contract:
      window: inherited_from_e1_to_e4
      metadata_policy: patent_effect_examples_must_reference_evidence_outputs_not_raw_claims
      leakage_guard: no_post_hoc_task_selection_for_go_decision
    comparison:
      required_baseline: e1_to_e4_baseline_outputs
      candidate_model: e1_to_e4_candidate_outputs
      same_split_required: inherited_where_applicable
    valid_when:
      - e1_to_e4_outputs_or_failure_reasons_are_available
      - prior_art_risk_entries_are_recorded_for_p1_to_p5
    no_go_when:
      - patent_effect_examples_lack_corresponding_evidence
      - c_to_b_decision_criteria_are_missing_or_post_hoc
    artifact_output:
      - patent_effect_examples
      - prior_art_risk_table
      - c_to_b_decision_table
    data_label_audit:
      source_status: inherited_from_e1_to_e4
      license_status: mixed_boundary_review_required
      schema_status: evidence_output_traceability_required
      label_status: expert_or_proxy_review_status_required_where_used
      split_policy_status: inherited_from_e1_to_e4
    patent_effect_examples:
      P1_stage_sensor_encoding:
        comparison: with_vs_without_stage_and_sensor_domain_encoding
        evidence_artifact: representation_or_residual_group_difference
        prior_art_risk_entry: required
      P2_small_sample_pretraining:
        comparison: zero_shot_vs_frozen_probe_vs_few_shot_adapter
        evidence_artifact: small_sample_adaptation_table
        prior_art_risk_entry: required
      P3_weak_label_anomaly_signal:
        comparison: forecasting_residual_vs_imputation_error_vs_weak_proxy_queue
        evidence_artifact: candidate_signal_review_table
        prior_art_risk_entry: required
      P4_real_open_data_fusion:
        comparison: fu13_schema_vs_open_data_schema_task_metric_mapping
        evidence_artifact: fusion_mapping_and_gap_table
        prior_art_risk_entry: required
      P5_multitask_health_evaluation:
        comparison: forecasting_only_vs_residual_reconstruction_probe_open_data_summary
        evidence_artifact: multitask_health_evidence_table
        prior_art_risk_entry: required
    status: planned
    invalid_claims:
      - 不得解释为专利授权结论
      - 不得解释为新颖性或创造性法律判断
      - 不得解释为生产告警
      - 不得解释为自动维修建议
decision_gate:
  contribution_id: CT4_decision_gate
  allowed_decisions:
    - Go_to_B_minimal_prototype
    - Stay_in_C_adaptation
    - Knowledge_only_consolidation
    - No_Go_hold
  requires:
    - E1_forecasting_residual
    - E2_representation
    - E3_imputation
    - E4_open_data_pm
    - E5_patent_effect
  criteria:
    primary_task: must_be_selected_before_results_are_known
    strong_baseline: engineering_baseline_and_relevant_open_source_model_required
    minimum_gain: must_be_declared_before_execution_for_any_go_decision
    seed_policy: multi_seed_or_documented_exception_required_for_go
    confidence_interval_policy: confidence_interval_or_bootstrap_required_for_go
    failure_conditions:
      - strong_baseline_already_covers_current_task
      - representation_imputation_or_weak_label_gain_is_not_stable
      - data_license_label_or_split_policy_is_insufficient
      - result_requires_post_hoc_metric_or_task_selection
```

- [ ] **Step 2: 创建静态校验模块**

创建 `src/b08_model_core/experiments/c_stage_contract.py`。

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_EVIDENCE_IDS = {
    "E1_forecasting_residual",
    "E2_representation",
    "E3_imputation",
    "E4_open_data_pm",
    "E5_patent_effect",
}


class CStageContractError(ValueError):
    """Raised when the C-stage evidence contract is incomplete."""


def load_c_stage_contract(path: str | Path) -> dict[str, Any]:
    contract_path = Path(path)
    return yaml.safe_load(contract_path.read_text(encoding="utf-8"))


def validate_c_stage_contract(contract: dict[str, Any]) -> None:
    experiments = contract.get("experiments")
    if not isinstance(experiments, list) or not experiments:
        raise CStageContractError("experiments must be a non-empty list")

    evidence_ids = {item.get("evidence_id") for item in experiments}
    if evidence_ids != REQUIRED_EVIDENCE_IDS:
        raise CStageContractError("contract must declare exactly E1-E5 evidence ids")

    contribution_ids = {
        contribution
        for item in experiments
        for contribution in item.get("paper_contribution_ids", [])
    }
    if "CT4_decision_gate" not in contribution_ids:
        raise CStageContractError("CT4_decision_gate must be explicit")

    for item in experiments:
        required_fields = [
            "experiment_id",
            "evidence_id",
            "paper_contribution_ids",
            "patent_ids",
            "dataset",
            "task_id",
            "model_or_baseline",
            "input_contract",
            "primary_metric",
            "comparison",
            "valid_when",
            "no_go_when",
            "artifact_output",
            "data_label_audit",
            "status",
            "invalid_claims",
        ]
        missing = [field for field in required_fields if field not in item]
        if missing:
            raise CStageContractError(f"{item.get('experiment_id')} missing {missing}")
        if not item["invalid_claims"]:
            raise CStageContractError(f"{item['experiment_id']} missing invalid claims")

        for field in ["input_contract", "comparison", "valid_when", "no_go_when", "data_label_audit"]:
            if not item[field]:
                raise CStageContractError(f"{item['experiment_id']} has empty {field}")

    decision_gate = contract.get("decision_gate", {})
    criteria = decision_gate.get("criteria", {})
    for field in [
        "primary_task",
        "strong_baseline",
        "minimum_gain",
        "seed_policy",
        "confidence_interval_policy",
        "failure_conditions",
    ]:
        if not criteria.get(field):
            raise CStageContractError(f"decision_gate.criteria missing {field}")

    patent_effect = next(
        item for item in experiments if item.get("evidence_id") == "E5_patent_effect"
    )
    required_patents = {
        "P1_stage_sensor_encoding",
        "P2_small_sample_pretraining",
        "P3_weak_label_anomaly_signal",
        "P4_real_open_data_fusion",
        "P5_multitask_health_evaluation",
    }
    if set(patent_effect.get("patent_effect_examples", {})) != required_patents:
        raise CStageContractError("E5 must declare patent_effect_examples for P1-P5")


def load_and_validate_c_stage_contract(path: str | Path) -> dict[str, Any]:
    contract = load_c_stage_contract(path)
    validate_c_stage_contract(contract)
    return contract
```

- [ ] **Step 3: 补充测试覆盖校验函数通过路径**

在 `tests/test_c_stage_contract.py` 中增加：

```python
def test_contract_validation_accepts_current_contract():
    contract = load_c_stage_contract(CONFIG_PATH)
    validate_c_stage_contract(contract)
```

- [ ] **Step 4: 运行 C0 契约测试**

Run:

```bash
python -m pytest tests/test_c_stage_contract.py -v
```

Expected: PASS。

- [ ] **Step 5: 提交契约和校验模块**

```bash
git add configs/c_stage_minimum_evidence.yaml src/b08_model_core/experiments/c_stage_contract.py tests/test_c_stage_contract.py
git commit -m "feat: add c stage evidence contract"
```

## Task 3: 建立研究侧 C0 证据登记页

**Files:**

- Create: `docs/research/c-stage-minimum-evidence-register.md`
- Create: `docs/research/c-stage-minimum-evidence-register.html`
- Modify: `docs/research/index.html`

- [ ] **Step 1: 创建 Markdown 短索引页**

创建 `docs/research/c-stage-minimum-evidence-register.md`。该文件只作为短索引和来源说明，不维护完整证据表，避免和 HTML 阅读页长期漂移。

```markdown
# C 阶段最小证据登记页

## 定位

本页是 C 阶段最小证据登记的 Markdown 短索引。

核心阅读入口：`docs/research/c-stage-minimum-evidence-register.html`

执行契约入口：`configs/c_stage_minimum_evidence.yaml`

报告模板入口：`reports/c_stage_minimum_evidence_template.md`

## 边界

本页不代表实验已经完成。任何真实实验必须先通过 `configs/c_stage_minimum_evidence.yaml` 和 `tests/test_c_stage_contract.py` 的静态契约校验。
```

- [ ] **Step 2: 创建 HTML 阅读页**

创建 `docs/research/c-stage-minimum-evidence-register.html`，沿用 `docs/research/research-style.css`。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>C 阶段最小证据登记页</title>
  <link rel="stylesheet" href="./research-style.css">
</head>
<body>
  <main class="page">
    <p class="eyebrow">B08 Research Mainline</p>
    <h1>C 阶段最小证据登记页</h1>
    <p class="lead">本页把 C0 实验契约转化为可阅读的证据登记入口，服务论文/专利知识成果和后续 C -> B 决策。</p>

    <section class="card">
      <h2>E1-E5 证据包</h2>
      <table>
        <thead>
          <tr>
            <th>证据</th>
            <th>实验</th>
            <th>主线映射</th>
            <th>产物</th>
            <th>禁止解释</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>E1 forecasting residual</td>
            <td>c0_fu13_forecast_residual_v1</td>
            <td>CT2 / P3 / P5</td>
            <td>残差表、top-k 样例、失败案例</td>
            <td>生产告警、FU13 RUL、自动维修</td>
          </tr>
          <tr>
            <td>E2 representation</td>
            <td>c0_fu13_representation_probe_v1</td>
            <td>CT1 / P1 / P2</td>
            <td>probe 报告、metadata 缺口</td>
            <td>真实健康等级、生产告警</td>
          </tr>
          <tr>
            <td>E3 imputation</td>
            <td>c0_fu13_imputation_reconstruction_v1</td>
            <td>CT2 / CT3 / P5</td>
            <td>重建误差表、mask 说明</td>
            <td>异常识别、RUL、维修建议</td>
          </tr>
          <tr>
            <td>E4 open-data PM</td>
            <td>c0_open_data_pm_audit_v1</td>
            <td>CT2 / CT3 / P4</td>
            <td>来源许可表、任务映射</td>
            <td>FU13 同等标签、生产级 RUL</td>
          </tr>
          <tr>
            <td>E5 patent effect</td>
            <td>c0_patent_effect_and_decision_gate_v1</td>
            <td>CT4 / P1-P5</td>
            <td>技术效果样例、C -> B 决策表</td>
            <td>专利授权、新颖性法律判断</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2>C -> B 决策门</h2>
      <p><code>CT4_decision_gate</code> 必须显式承接 E5，并汇总 E1-E4 的结果。允许结论只有 Go to B minimal prototype、Stay in C adaptation、Knowledge-only consolidation 和 No-Go / hold。</p>
    </section>

    <section class="card">
      <h2>数据与标签核对</h2>
      <p>每个实验必须在执行前记录 source、license、schema、label 和 split policy 五类状态。缺失项应写为 unknown、needs review 或 blocked，不能用空结果伪装完成。</p>
    </section>

    <section class="card">
      <h2>P1-P5 最小技术效果样例</h2>
      <p>P1 覆盖阶段与传感器编码对照，P2 覆盖小样本适配对照，P3 覆盖弱标签异常候选信号，P4 覆盖真机与公开数据融合映射，P5 覆盖多任务健康评估表。所有样例都必须带 prior-art 风险入口。</p>
    </section>
  </main>
</body>
</html>
```

- [ ] **Step 3: 更新 research HTML 入口**

在 `docs/research/index.html` 的研究资产列表中增加 `c-stage-minimum-evidence-register.html` 链接。不要把入口改回 Markdown 优先。

- [ ] **Step 4: 做静态链接检查**

Run:

```bash
python - <<'PY'
from pathlib import Path

html = Path("docs/research/index.html").read_text(encoding="utf-8")
assert "c-stage-minimum-evidence-register.html" in html
assert Path("docs/research/c-stage-minimum-evidence-register.html").exists()
PY
```

Expected: PASS，无输出。

- [ ] **Step 5: 提交研究登记页**

```bash
git add docs/research/c-stage-minimum-evidence-register.md docs/research/c-stage-minimum-evidence-register.html docs/research/index.html
git commit -m "docs: add c stage evidence register"
```

## Task 4: 建立 C0 报告模板

**Files:**

- Create: `reports/c_stage_minimum_evidence_template.md`
- Modify: `tests/test_c_stage_contract.py`

- [ ] **Step 1: 为报告模板写静态测试**

在 `tests/test_c_stage_contract.py` 中增加：

```python
REPORT_TEMPLATE_PATH = Path("reports/c_stage_minimum_evidence_template.md")


def test_report_template_includes_all_evidence_ids_and_decision_gate():
    text = REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    for evidence_id in [
        "E1_forecasting_residual",
        "E2_representation",
        "E3_imputation",
        "E4_open_data_pm",
        "E5_patent_effect",
    ]:
        assert evidence_id in text
    assert "CT4_decision_gate" in text
    assert "C -> B" in text
    for required in [
        "数据与标签核对",
        "primary_task",
        "strong_baseline",
        "minimum_gain",
        "seed_policy",
        "confidence_interval_policy",
        "failure_conditions",
    ]:
        assert required in text
    for patent_id in [
        "P1_stage_sensor_encoding",
        "P2_small_sample_pretraining",
        "P3_weak_label_anomaly_signal",
        "P4_real_open_data_fusion",
        "P5_multitask_health_evaluation",
    ]:
        assert patent_id in text
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python -m pytest tests/test_c_stage_contract.py::test_report_template_includes_all_evidence_ids_and_decision_gate -v
```

Expected: FAIL，原因是报告模板尚不存在。

- [ ] **Step 3: 创建报告模板**

创建 `reports/c_stage_minimum_evidence_template.md`。

```markdown
# C 阶段最小证据实验报告模板

## 报告元信息

- experiment_batch_id:
- generated_at:
- data_versions:
- contract_file: `configs/c_stage_minimum_evidence.yaml`
- spec_file: `docs/superpowers/specs/2026-06-04-c-stage-minimum-evidence-design.md`

## 数据与标签核对

| item | status | evidence |
| --- | --- | --- |
| source_status |  |  |
| license_status |  |  |
| schema_status |  |  |
| label_status |  |  |
| split_policy_status |  |  |

## E1_forecasting_residual

- experiment_id:
- dataset:
- model_or_baseline:
- input_contract:
- comparison:
- primary_metric:
- valid_when:
- no_go_when:
- result_summary:
- residual_candidate_examples:
- failure_cases:
- invalid_claims:

## E2_representation

- experiment_id:
- dataset:
- model_or_baseline:
- input_contract:
- comparison:
- primary_metric:
- valid_when:
- no_go_when:
- probe_or_clustering_summary:
- metadata_input_exclusion:
- invalid_claims:

## E3_imputation

- experiment_id:
- dataset:
- model_or_baseline:
- input_contract:
- comparison:
- primary_metric:
- valid_when:
- no_go_when:
- mask_strategy:
- reconstruction_summary:
- invalid_claims:

## E4_open_data_pm

- experiment_id:
- dataset:
- input_contract:
- comparison:
- source_license_status:
- task_metric_mapping:
- valid_when:
- no_go_when:
- fu13_gap_note:
- invalid_claims:

## E5_patent_effect

- experiment_id:
- patent_effect_examples:
- prior_art_risk_table:
- invalid_claims:

| patent_id | comparison | evidence_artifact | prior_art_risk_entry |
| --- | --- | --- | --- |
| P1_stage_sensor_encoding |  |  |  |
| P2_small_sample_pretraining |  |  |  |
| P3_weak_label_anomaly_signal |  |  |  |
| P4_real_open_data_fusion |  |  |  |
| P5_multitask_health_evaluation |  |  |  |

## CT4_decision_gate / C -> B 决策

### Go / No-Go criteria

- primary_task:
- strong_baseline:
- minimum_gain:
- seed_policy:
- confidence_interval_policy:
- failure_conditions:

允许结论只能选择一个：

| decision | selected | evidence |
| --- | --- | --- |
| Go_to_B_minimal_prototype |  |  |
| Stay_in_C_adaptation |  |  |
| Knowledge_only_consolidation |  |  |
| No_Go_hold |  |  |

## 禁止过度解释

本报告不得被解释为生产告警、FU13 RUL、自动维修建议、专利授权结论、新颖性或创造性法律判断。
```

- [ ] **Step 4: 运行完整 C0 契约测试**

Run:

```bash
python -m pytest tests/test_c_stage_contract.py -v
```

Expected: PASS。

- [ ] **Step 5: 提交报告模板**

```bash
git add reports/c_stage_minimum_evidence_template.md tests/test_c_stage_contract.py
git commit -m "docs: add c stage evidence report template"
```

## Task 5: 更新计划和默认入口的轻量引用

**Files:**

- Modify: `README.md`
- Modify: `details.md`
- Modify: `docs/index.html`
- Modify: `tests/test_c_stage_contract.py`

- [ ] **Step 1: 添加入口引用测试**

在 `tests/test_c_stage_contract.py` 中增加静态检查，确保默认入口能找到 C0 证据契约。

```python
def test_default_docs_reference_c_stage_evidence_assets():
    readme = Path("README.md").read_text(encoding="utf-8")
    docs_index = Path("docs/index.html").read_text(encoding="utf-8")
    details = Path("details.md").read_text(encoding="utf-8")

    assert "configs/c_stage_minimum_evidence.yaml" in readme
    assert "c-stage-minimum-evidence-register.html" in docs_index
    assert "C 阶段最小证据" in details
```

- [ ] **Step 2: 运行入口引用测试确认失败**

Run:

```bash
python -m pytest tests/test_c_stage_contract.py::test_default_docs_reference_c_stage_evidence_assets -v
```

Expected: FAIL，原因是入口尚未补充。

- [ ] **Step 3: 更新 README**

在 `README.md` 的研究主线或下一阶段入口附近增加一段简短说明：

```markdown
### C 阶段最小证据实验入口

C 阶段先执行最小证据契约，不直接启动大规模自研训练。执行入口是 `configs/c_stage_minimum_evidence.yaml`，阅读入口是 `docs/research/c-stage-minimum-evidence-register.html`，报告模板是 `reports/c_stage_minimum_evidence_template.md`。
```

- [ ] **Step 4: 更新 details**

在 `details.md` 的阶段台账中增加一条：

```markdown
## 2026-06-04 C 阶段最小证据实验规划

已确认 C 阶段先以最小证据实验承接论文/专利主线，核心契约为 `configs/c_stage_minimum_evidence.yaml`。该阶段只建立 `E1-E5` 证据包、`P1-P5` 技术效果样例和 `CT4_decision_gate`，不直接进入 B 阶段自研基础模型训练。
```

- [ ] **Step 5: 更新 docs/index.html**

在 `docs/index.html` 的研究或路线导航中增加 `docs/research/c-stage-minimum-evidence-register.html` 的链接。链接文字建议：

`C 阶段最小证据登记页`

- [ ] **Step 6: 运行入口引用测试**

Run:

```bash
python -m pytest tests/test_c_stage_contract.py::test_default_docs_reference_c_stage_evidence_assets -v
```

Expected: PASS。

- [ ] **Step 7: 提交入口更新**

```bash
git add README.md details.md docs/index.html tests/test_c_stage_contract.py
git commit -m "docs: reference c stage evidence entrypoints"
```

## Task 6: 完成 C0 静态验收

**Files:**

- Verify only: `configs/c_stage_minimum_evidence.yaml`
- Verify only: `tests/test_c_stage_contract.py`
- Verify only: `docs/research/c-stage-minimum-evidence-register.html`
- Verify only: `reports/c_stage_minimum_evidence_template.md`

- [ ] **Step 1: 运行 C0 契约测试**

Run:

```bash
python -m pytest tests/test_c_stage_contract.py -v
```

Expected: PASS。

- [ ] **Step 2: 运行关键入口静态检查**

Run:

```bash
python - <<'PY'
from pathlib import Path

required_paths = [
    "configs/c_stage_minimum_evidence.yaml",
    "docs/research/c-stage-minimum-evidence-register.html",
    "reports/c_stage_minimum_evidence_template.md",
]
for path in required_paths:
    assert Path(path).exists(), path

docs_index = Path("docs/research/index.html").read_text(encoding="utf-8")
assert "c-stage-minimum-evidence-register.html" in docs_index

report = Path("reports/c_stage_minimum_evidence_template.md").read_text(encoding="utf-8")
assert "CT4_decision_gate" in report
assert "C -> B" in report
assert "primary_task" in report
assert "P5_multitask_health_evaluation" in report
PY
```

Expected: PASS，无输出。

- [ ] **Step 3: 检查无默认路径破坏**

Run:

```bash
python -m pytest tests/test_config.py tests/test_experiment_scaffold.py tests/test_foundation_runner.py -v
```

Expected: PASS。

- [ ] **Step 4: 提交最终验收记录**

如果 Task 6 发现只需要修正文档或契约，则提交修正：

```bash
git add configs/c_stage_minimum_evidence.yaml docs/research/c-stage-minimum-evidence-register.html reports/c_stage_minimum_evidence_template.md tests/test_c_stage_contract.py
git commit -m "chore: finalize c stage evidence contract"
```

若没有文件变化，则不创建空提交。

## 执行后的完成标准

计划执行完成后，应满足：

1. `configs/c_stage_minimum_evidence.yaml` 存在，并声明 `E1-E5`、`CT4_decision_gate`、`P1-P5`、invalid claims 和 C -> B 决策。
2. `src/b08_model_core/experiments/c_stage_contract.py` 能静态校验 C0 契约，不依赖真实数据或模型权重。
3. `tests/test_c_stage_contract.py` 覆盖证据完整性、`input_contract`、`comparison`、`valid_when`、`no_go_when`、`data_label_audit`、`CT4_decision_gate`、报告模板和默认入口引用。
4. `docs/research/c-stage-minimum-evidence-register.html` 作为 HTML 核心阅读入口出现在 `docs/research/index.html` 中，Markdown 只保留短索引。
5. `reports/c_stage_minimum_evidence_template.md` 明确要求每个证据包输出指标、失败原因、数据标签核对、invalid claims、P1-P5 技术效果样例和 C -> B 决策 criteria。
6. 默认 README、details 和 docs index 能指向 C 阶段入口。
7. 没有下载数据、没有运行外部模型、没有进入 B 阶段训练、没有改变默认 CLI workflow。

## 后续执行选择

本计划完成后建议使用 `superpowers:subagent-driven-development` 执行。推荐顺序是：

1. 一个 worker 执行 Task 1-2，完成配置和静态校验。
2. 一个 worker 执行 Task 3-4，完成研究登记页和报告模板。
3. 主会话执行 Task 5-6，更新入口并做最终验收。

若用户希望更稳，可以改用 `superpowers:executing-plans` 在本会话内逐项执行，每个任务结束后停下来 review。
