import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from b08_model_core.experiments import forecasting as forecasting_module
from b08_model_core.simulation.export_dataset import simulate_dataset
from b08_model_core.evaluation.open_source_matrix import candidate_matrix


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_default_forecasting_cli_runs_baseline_only_without_external_weights(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "forecasting_experiment.md"
    simulate_dataset(days=3, seed=23, output_path=dataset)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "experiment",
            "forecasting",
            "--dataset",
            str(dataset),
            "--output",
            str(report),
            "--max-windows",
            "40",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    text = report.read_text(encoding="utf-8")
    assert "Forecasting Foundation Model Experiment" in text
    assert "RobustStageForecaster" in text
    assert "StageSeasonalNaiveForecaster" in text
    assert "Route Recommendation" in text
    assert "BaselineOnly" in text
    assert "baseline" in text
    assert "skipped_by_user" in text


def test_baseline_forecasting_experiment_does_not_instantiate_ttm(tmp_path, monkeypatch):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "forecasting_experiment.md"
    simulate_dataset(days=3, seed=23, output_path=dataset)

    def fail_if_used(*args, **kwargs):
        raise AssertionError("baseline mode must not instantiate TTMForecastAdapter")

    monkeypatch.setattr(forecasting_module, "TTMForecastAdapter", fail_if_used, raising=False)

    output = forecasting_module.run_forecasting_experiment(
        dataset_path=dataset,
        output_path=report,
        max_windows=40,
        model="baseline",
    )

    assert output == report
    assert "skipped_by_user" in report.read_text(encoding="utf-8")


def test_ttm_forecasting_cli_returns_nonzero_for_non_success_but_writes_report(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "ttm_forecasting_experiment.md"
    empty_cache = tmp_path / "empty_hf_cache"
    empty_cache.mkdir()
    simulate_dataset(days=3, seed=23, output_path=dataset)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "experiment",
            "forecasting",
            "--dataset",
            str(dataset),
            "--output",
            str(report),
            "--max-windows",
            "40",
            "--model",
            "ttm",
            "--model-cache-dir",
            str(empty_cache),
            "--no-download",
        ],
        text=True,
        capture_output=True,
    )

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "TTM" in text
    assert "Foundation Model Status" in text
    assert result.returncode == 1, text
    assert any(
        status in text
        for status in [
            "missing_dependency",
            "missing_or_blocked_weights",
            "unsupported_window_shape",
            "runtime_failed",
        ]
    )


def test_forecasting_experiment_rejects_non_positive_max_windows(tmp_path):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "forecasting_experiment.md"
    simulate_dataset(days=3, seed=23, output_path=dataset)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "experiment",
            "forecasting",
            "--dataset",
            str(dataset),
            "--output",
            str(report),
            "--max-windows",
            "0",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "must be greater than 0" in result.stderr
    assert not report.exists()


@pytest.mark.parametrize("option", ["--context-length", "--prediction-length"])
def test_forecasting_experiment_rejects_non_positive_lengths(tmp_path, option):
    dataset = tmp_path / "fu13.parquet"
    report = tmp_path / "forecasting_experiment.md"
    simulate_dataset(days=3, seed=23, output_path=dataset)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "experiment",
            "forecasting",
            "--dataset",
            str(dataset),
            "--output",
            str(report),
            option,
            "0",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "must be greater than 0" in result.stderr
    assert not report.exists()


def test_forecasting_candidate_matrix_includes_current_forecast_first_models():
    names = {candidate.name for candidate in candidate_matrix()}
    assert {"FlowState", "TTM", "TimesFM", "Chronos", "Moirai"} <= names


def test_foundation_ttm_extra_and_local_model_artifacts_are_documented():
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    foundation_ttm = pyproject["project"]["optional-dependencies"]["foundation-ttm"]
    assert any(item.startswith("granite-tsfm>=") for item in foundation_ttm)
    assert any(item.startswith("torch>=") for item in foundation_ttm)
    assert any(item.startswith("transformers>=") for item in foundation_ttm)
    assert any(item.startswith("huggingface_hub>=") for item in foundation_ttm)

    ignore_rules = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "hf_cache/" in ignore_rules
    assert "model_cache/" in ignore_rules
    assert ".cache/" in ignore_rules
    assert "ttm_finetuned_models/" in ignore_rules
    assert "reports/*.md" in ignore_rules

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "uv sync --extra dev --extra foundation-ttm" in readme
    assert "--allow-download" in readme
    assert "HF_HOME=hf_cache" in readme
    assert "--context-length 90" in readme
    assert "--prediction-length 16" in readme
    assert "不要把这些文件上传到 GitHub" in readme


def test_c21_executable_evaluation_workflow_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "c-stage-c21" in readme
    assert "configs/c_stage_c21_executable_open_model_evaluation.yaml" in readme
    assert "reports/c_stage_c21_executable_open_model_evaluation.md" in readme
    assert "allow_network: false" in readme
    assert "allow_download: false" in readme
    assert "本机 opt-in" in readme


def test_c3_public_dataset_registry_workflow_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "c-stage-c3" in readme
    assert "configs/c_stage_c3_public_dataset_registry.yaml" in readme
    assert "reports/c_stage_c3_public_dataset_registry.md" in readme
    assert "不下载公开数据" in readme
    assert "C3" in details


def test_c31_cmapss_minimal_ingestion_workflow_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")
    section_header = "### C3.1. NASA C-MAPSS 最小接入与 schema validation"
    next_header = "\n## 项目边界"

    assert section_header in readme
    assert next_header in readme
    c31_section = readme.split(section_header, 1)[1].split(next_header, 1)[0]

    assert "c-stage-c31" in c31_section
    assert "configs/c_stage_c31_cmapss_minimal_ingestion.yaml" in c31_section
    assert "reports/c_stage_c31_cmapss_minimal_ingestion.md" in c31_section
    assert "allow_network: false" in c31_section
    assert "allow_download: false" in c31_section
    assert "allow_local_raw_data: false" in c31_section
    assert "allow_write_processed: false" in c31_section
    assert "不下载公开数据" in c31_section
    assert "不运行模型训练" in c31_section
    assert "docs/reviews/2026-06-10-c31-cmapss-source-license-review.md" in c31_section
    assert "c31-cmapss-license-evidence-update" in c31_section
    assert "docs/reviews/2026-06-11-c31-cmapss-local-raw-mapping-review.md" in c31_section
    assert "configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml" in c31_section
    assert "Zenodo" in c31_section
    assert "CC BY 4.0" in c31_section
    assert "local raw mapping review" in c31_section
    assert "schema_validated_ready_for_c32" in c31_section
    assert "full_classic_cmapss_validated" in c31_section
    assert "C3.2" in c31_section
    assert "local raw opt-in" in c31_section
    assert "可进入 C3.2" in c31_section
    assert "C3.1" in details
    assert "NASA C-MAPSS" in details
    assert "source/license review" in details
    assert "local raw mapping review" in details
    assert "schema_validated_ready_for_c32" in details


def test_energy_equipment_spatiotemporal_positioning_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "能源设备时空智能样板" in readme
    assert "公司时空智能在能源设备时序方向的核心样板项目" in readme
    assert "船舶制造偏空间" in readme
    assert "能源偏时序" in readme
    assert "A 能力在能源侧的证据项目" in readme
    assert "candidate signals" in readme
    assert "工程解释与专家复核" in readme
    assert "运行优化建议输入或系统协同事件候选" in readme
    assert "数据层" in readme
    assert "评测层" in readme
    assert "信号层" in readme
    assert "应用输入层" in readme
    assert "B08 -> B06" in readme
    assert "B08 -> S01" in readme
    assert "B08 -> IP" in readme
    assert "模型适配性证据" in readme
    assert "不生成 leaderboard" in readme
    assert "FU13 observations" in readme
    assert "cycle / window" in readme
    assert "baseline / TTM" in readme
    assert "leak_current_monitoring" in readme
    assert "能源设备时空智能样板" in details


def test_candidate_signal_and_system_event_interface_is_documented():
    interface_doc = (
        REPO_ROOT / "docs/candidate-signal-and-system-event-interface.md"
    ).read_text(encoding="utf-8")

    assert "candidate_signal_report" in interface_doc
    for signal_type in ["residual", "trend", "spike", "representation", "imputation"]:
        assert signal_type in interface_doc

    for event_field in [
        "device_id",
        "time_range",
        "stage",
        "signal_type",
        "confidence",
        "affected_scope",
        "suggested_action",
        "review_status",
    ]:
        assert event_field in interface_doc

    assert "equipment_timeseries_observation_package" in interface_doc
    assert "P0-06" in interface_doc
    assert "canonical observations" in interface_doc
    assert "quality flags" in interface_doc
    assert "P0-07" in interface_doc
    assert "cycle reconstruction" in interface_doc
    assert "window artifacts" in interface_doc
    assert "P0-08" in interface_doc
    assert "baseline / TTM / open model evaluation reports" in interface_doc
    assert "复用开源模型" in interface_doc
    assert "轻量适配" in interface_doc
    assert "条件性自研模型设计" in interface_doc
    assert "不生成 leaderboard" in interface_doc
    assert "不是生产告警" in interface_doc
    assert "不是维修建议" in interface_doc


def test_leak_current_monitoring_expert_review_fields_are_documented():
    leak_current_doc = (REPO_ROOT / "docs/leak-current-scenario-evaluation.md").read_text(
        encoding="utf-8"
    )

    assert "专家复核" in leak_current_doc
    assert "candidate_signal_report" in leak_current_doc
    assert "S01" in leak_current_doc
    for review_field in [
        "signal_meaning",
        "maintenance_confirmation_required",
        "operation_advice_candidate",
        "review_status",
    ]:
        assert review_field in leak_current_doc
    assert "不代表生产告警" in leak_current_doc
    assert "不代表维修建议" in leak_current_doc


def test_c32_cross_dataset_evaluation_workflow_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")
    section_header = "### C3.2. Open model cross-dataset evaluation"
    next_header = "\n## 项目边界"

    assert section_header in readme
    assert next_header in readme
    c32_section = readme.split(section_header, 1)[1].split(next_header, 1)[0]

    assert "c-stage-c32" in c32_section
    assert "configs/c_stage_c32_open_model_cross_dataset_evaluation.yaml" in c32_section
    assert "reports/c_stage_c32_open_model_cross_dataset_evaluation.md" in c32_section
    assert "contract_ready_local_execution_blocked" in c32_section
    assert "allow_network: false" in c32_section
    assert "allow_download: false" in c32_section
    assert "allow_local_raw_data: false" in c32_section
    assert "allow_model_cache: false" in c32_section
    assert "allow_training: false" in c32_section
    assert "allow_write_processed: false" in c32_section
    assert "不下载公开数据" in c32_section
    assert "不读取 C-MAPSS raw" in c32_section
    assert "不读取 FU13 real" in c32_section
    assert "不检查 model cache" in c32_section
    assert "不实例化 open model adapter" in c32_section
    assert "不运行模型训练" in c32_section
    assert "不计算模型分数" in c32_section
    assert "不生成 leaderboard" in c32_section
    assert "local execution design" in c32_section
    assert "C3.2" in details
    assert "contract_ready_local_execution_blocked" in details
    assert "local execution design" in details
    assert "不生成 leaderboard" in details
    assert "open model cross-dataset evaluation" in details
    assert details.count("\n## ") == 3
    assert "## 1. 当前阶段" in details
    assert "## 2. 每日更新" in details
    assert "## 3. 下一步计划" in details


def test_c32_explicit_local_execution_workflow_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "configs/local/c_stage_c32_explicit_local_execution.example.yaml" in readme
    assert "local_execution_baseline_reference_ready" in readme
    assert "C-MAPSS RUL baseline evaluation" in readme
    assert "FU13-like forecasting reference" in readme
    assert "不生成 leaderboard" in readme
    assert "不运行 open model adapter" in readme
    assert "explicit local execution" in details
    assert "C-MAPSS RUL baseline" in details
    assert "FU13-like forecasting reference" in details


def test_c33_single_candidate_local_evaluation_workflow_is_documented():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")
    section_header = "### C3.3. Single-candidate open model local evaluation"
    next_header = "\n## 项目边界"

    assert section_header in readme
    assert next_header in readme
    c33_section = readme.split(section_header, 1)[1].split(next_header, 1)[0]

    assert "c-stage-c33" in c33_section
    assert (
        "configs/c_stage_c33_single_candidate_open_model_local_evaluation.yaml"
        in c33_section
    )
    assert (
        "reports/c_stage_c33_single_candidate_open_model_local_evaluation.md"
        in c33_section
    )
    assert (
        "configs/local/c_stage_c33_ttm_fu13_like_local_evaluation.example.yaml"
        in c33_section
    )
    assert "reports/c_stage_c33_ttm_fu13_like_local_evaluation.md" in c33_section
    assert "contract_ready_single_candidate_local_execution_blocked" in c33_section
    assert "不检查 model cache" in c33_section
    assert "不实例化 TTM" in c33_section
    assert "TTM on FU13-like forecasting" in c33_section
    assert "C-MAPSS RUL remains baseline-only" in c33_section
    assert "RUL metrics 和 forecasting metrics separated" in c33_section
    assert "不生成 leaderboard" in c33_section
    assert "不运行模型训练" in c33_section
    assert "不提交 raw / cache / report" in c33_section
    assert (
        "docs/superpowers/specs/2026-06-22-c33-single-candidate-open-model-local-evaluation-design.md"
        in readme
    )
    assert (
        "docs/superpowers/plans/2026-06-22-c33-single-candidate-open-model-local-evaluation-plan.md"
        in readme
    )
    assert "C3.3 single-candidate open model local evaluation" in details
    assert "C3.4 decision review" in details
    assert "Review C3.3 TTM local evidence" in details
    assert "C-MAPSS RUL baseline-only" in details


def test_readme_documents_c34_decision_review_workflow():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    section_header = "### C3.4. Open model expansion decision review"
    next_header = "\n## 项目边界"

    assert section_header in readme
    c34_section = readme.split(section_header, 1)[1].split(next_header, 1)[0]
    assert "c-stage-c34" in c34_section
    assert "configs/c_stage_c34_open_model_expansion_decision_review.yaml" in c34_section
    assert "configs/local/c_stage_c34_review_c33_local_ttm_evidence.example.yaml" in c34_section
    assert "不运行第二候选 open model" in c34_section
    assert "不生成 leaderboard" in c34_section


def test_details_records_c34_completion_and_next_step():
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "C3.4 open model expansion decision review implemented" in details
    assert "C3.5 second forecasting candidate design" in details
    assert "hold_candidate_expansion_pending_ttm_local_evidence" in details


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


def test_details_c21_executable_evaluation_ledger_is_documented():
    details = (REPO_ROOT / "details.md").read_text(encoding="utf-8")

    assert "| 2026-06-06 | C2.1 开源模型真实执行评测进入执行入口" in details
    assert "configs/c_stage_c21_executable_open_model_evaluation.yaml" in details
    assert "uv run b08-model-core experiment c-stage-c21" in details
    assert "默认离线安全边界" in details
