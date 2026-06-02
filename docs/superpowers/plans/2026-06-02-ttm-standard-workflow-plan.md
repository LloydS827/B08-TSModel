# TTM Standard Workflow Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已跑通的 FU13 data pipeline 和 TTM 真实数据 forecasting 验证整理成可复现、可解释、可交接的标准开发流程。

**Architecture:** 不新增模型 adapter，不训练或微调 TTM。先用现有 CLI 复跑 baseline/TTM 的 first-N 窗口规模敏感性评测，再把结果沉淀为 `docs/ttm-real-data-evaluation.md`，最后将 `README.md` 调整为开发者入口，并同步 `details.md` 与文档索引。

**Tech Stack:** Python 3.11+, pandas, uv, pytest, existing `b08-model-core` CLI, optional `foundation-ttm` dependencies, Markdown docs.

---

## 权威输入

- 设计文档：`docs/superpowers/specs/2026-06-02-ttm-standard-workflow-design.md`
- 当前真实数据闭环计划：`docs/superpowers/plans/2026-06-02-real-data-validation-loop-plan.md`
- FU13 配置：`configs/fu13_real_data_schema.yaml`
- README 当前入口：`README.md`
- 项目进展台账：`details.md`
- 文档入口：`docs/index.html`
- 真实数据本地路径：
  - 优先：`data/real/`
  - 如果 worktree 中不存在，使用原工作区上传目录：`/Users/lloyd/Nutstore Files/Nutstore/CavLAB/P00-Projects/分类0-核心研发/B08-设备时序基础模型/data/real`
- 当前生成数据路径：`data/processed/fu13_real_observations.parquet`
- 当前本地报告路径：
  - `reports/real_data_validation.md`
  - `reports/real_scenario_diagnostics.md`
  - `reports/real_baseline_forecasting.md`
  - `reports/real_ttm_forecasting.md`

## 范围守卫

- 不接入 TimesFM、Chronos、Moirai、FlowState 等新模型。
- 不训练或微调 TTM。
- 不实现 scenario 过滤建窗、等待态过滤或质量标记过滤框架。
- 不把 TTM forecasting 结果写成故障预测、RUL、风险概率或维护建议。
- 不提交 `data/real/`、`data/processed/*.parquet`、本阶段临时 `reports/real_*` 报告、`hf_cache/`。
- 不重构 CLI 或模型代码，除非执行时发现现有命令无法按 spec 复跑；如果发现 bug，先使用 `superpowers:systematic-debugging`。

## 文件结构

Create:

- `docs/ttm-real-data-evaluation.md`
  - TTM 真实数据 forecasting 能力复核报告。提交 Git。

Modify:

- `README.md`
  - 改为开发者使用入口，主读者是内部研发人员，兼顾项目管理者和现场数据方。
- `details.md`
  - 同步阶段台账：data pipeline 已跑通，当前工作是 TTM 标准流程和能力复核。
- `docs/index.html`
  - 增加 `docs/ttm-real-data-evaluation.md` 入口；保持现有 HTML 风格。

Generated local-only, do not stage:

- `reports/real_baseline_forecasting_w20.md`
- `reports/real_ttm_forecasting_w20.md`
- `reports/real_baseline_forecasting_w40.md`
- `reports/real_ttm_forecasting_w40.md`
- `reports/real_baseline_forecasting_w80.md`
- `reports/real_ttm_forecasting_w80.md`

## 命令约定

开发环境：

```bash
uv sync --extra dev
```

TTM 依赖：

```bash
uv sync --extra dev --extra foundation-ttm
```

常规测试：

```bash
uv run python -m pytest -q
```

TTM cache：

```bash
HF_HOME=hf_cache
```

如果本 worktree 没有 `hf_cache/`，可使用原工作区绝对路径：

```bash
HF_HOME="/Users/lloyd/Nutstore Files/Nutstore/CavLAB/P00-Projects/分类0-核心研发/B08-设备时序基础模型/hf_cache"
```

---

## Task 1: 预检与数据安全确认

**Files:**
- Read: `.gitignore`
- Read: `README.md`
- Read: `docs/superpowers/specs/2026-06-02-ttm-standard-workflow-design.md`
- Generated local-only: `data/processed/fu13_real_observations.parquet`, `reports/real_*.md`

- [ ] **Step 1: 确认工作分支和状态**

Run:

```bash
git branch --show-current
git status --short --ignored
```

Expected:

- Branch is `codex/real-data-validation-loop`.
- No tracked modifications before work starts, except ignored generated artifacts.
- `data/real/`, `data/processed/`, `reports/real_*.md`, and `hf_cache/` are ignored if present.

- [ ] **Step 2: 确认忽略规则覆盖真实数据与临时报告**

Run:

```bash
for artifact in \
  data/real/stage_data.csv \
  data/processed/fu13_real_observations.parquet \
  reports/real_data_validation.md \
  reports/real_scenario_diagnostics.md \
  reports/real_baseline_forecasting.md \
  reports/real_ttm_forecasting.md \
  reports/real_ttm_forecasting_w20.md \
  reports/real_baseline_forecasting_w80.md \
  hf_cache/
do
  git check-ignore -q "$artifact" || { echo "not ignored: $artifact"; exit 1; }
  git check-ignore -v "$artifact"
done
```

Expected:

- All listed paths are ignored.
- If `data/real/stage_data.csv` does not exist in this worktree, `git check-ignore` can still show the ignore rule. If it does not, fix `.gitignore` before proceeding.

- [ ] **Step 3: 确认白名单 reports 仍可被 Git 跟踪**

Run:

```bash
git ls-files --error-unmatch reports/model_core_evaluation.md reports/model_route_decision.md
```

Expected:

- Both files are tracked. These reports are explicit repository artifacts and are not part of this stage's local-only `reports/real_*` outputs.

- [ ] **Step 4: 确认 canonical parquet 是否存在**

Run:

```bash
test -f data/processed/fu13_real_observations.parquet && ls -lh data/processed/fu13_real_observations.parquet
```

Expected:

- File exists.

If missing, run assemble using whichever input directory exists:

```bash
uv run b08-model-core real-data assemble-fu13 \
  --input-dir data/real \
  --config configs/fu13_real_data_schema.yaml \
  --output data/processed/fu13_real_observations.parquet \
  --report reports/real_data_validation.md
```

If `data/real` does not exist in the worktree, use:

```bash
uv run b08-model-core real-data assemble-fu13 \
  --input-dir "/Users/lloyd/Nutstore Files/Nutstore/CavLAB/P00-Projects/分类0-核心研发/B08-设备时序基础模型/data/real" \
  --config configs/fu13_real_data_schema.yaml \
  --output data/processed/fu13_real_observations.parquet \
  --report reports/real_data_validation.md
```

Expected if assemble is needed:

- Command exits `0`.
- `reports/real_data_validation.md` contains `schema_valid: True`, nonzero rows, 8 sensors, cycle summary, and quality counts.

- [ ] **Step 5: 确认 TTM 依赖和 cache**

Run:

```bash
uv run python - <<'PY'
for mod in ["torch", "tsfm_public", "transformers", "huggingface_hub"]:
    try:
        __import__(mod)
        print(mod, "ok")
    except Exception as exc:
        print(mod, "missing", type(exc).__name__, exc)
PY
```

Expected:

- All modules print `ok`.

If missing, run:

```bash
uv sync --extra dev --extra foundation-ttm
```

Then re-run the import check.

- [ ] **Step 6: Commit if `.gitignore` had to change**

Only if Step 2 required an ignore-rule fix:

```bash
git add .gitignore
git commit -m "chore: keep ttm workflow artifacts local"
```

---

## Task 2: 复跑 baseline/TTM first-N 窗口规模敏感性

**Files:**
- Read: `data/processed/fu13_real_observations.parquet`
- Read: `configs/fu13_real_data_schema.yaml`
- Generated local-only:
  - `reports/real_baseline_forecasting_w20.md`
  - `reports/real_ttm_forecasting_w20.md`
  - `reports/real_baseline_forecasting_w40.md`
  - `reports/real_ttm_forecasting_w40.md`
  - `reports/real_baseline_forecasting_w80.md`
  - `reports/real_ttm_forecasting_w80.md`

Important interpretation:

- `max-windows=20/40/80` uses first-N nested windows from current window construction order.
- This is not random sampling and not a statistical robustness claim.
- Any failure must be recorded precisely in `docs/ttm-real-data-evaluation.md`.

- [ ] **Step 1: Run baseline w20**

```bash
uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_baseline_forecasting_w20.md \
  --model baseline \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 20
```

Expected:

- Exit `0`.
- Report contains `model: BaselineOnly`, `Baseline Comparison`, `Sensor Metrics`, and `Scenario Metrics`.

- [ ] **Step 2: Run TTM w20 offline**

Use local worktree cache if present:

```bash
HF_HOME=hf_cache uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_ttm_forecasting_w20.md \
  --model ttm \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 20 \
  --model-cache-dir hf_cache \
  --no-download
```

If the worktree has no cache but the original workspace cache exists, use the absolute cache path:

```bash
HF_HOME="/Users/lloyd/Nutstore Files/Nutstore/CavLAB/P00-Projects/分类0-核心研发/B08-设备时序基础模型/hf_cache" uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_ttm_forecasting_w20.md \
  --model ttm \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 20 \
  --model-cache-dir "/Users/lloyd/Nutstore Files/Nutstore/CavLAB/P00-Projects/分类0-核心研发/B08-设备时序基础模型/hf_cache" \
  --no-download
```

Expected:

- Exit `0`.
- Report contains `status: available_and_ran`.
- Report contains `Foundation Metrics`, `Sensor Metrics`, and `Scenario Metrics`.

If exit is nonzero:

- Inspect the report and stderr.
- Record the precise blocker in the evaluation report.
- Do not claim TTM w20 succeeded.

- [ ] **Step 3: Run baseline w40**

```bash
uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_baseline_forecasting_w40.md \
  --model baseline \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40
```

Expected: same as baseline w20, with `train_windows` and `test_windows` recorded.

- [ ] **Step 4: Run TTM w40 offline**

```bash
HF_HOME=hf_cache uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_ttm_forecasting_w40.md \
  --model ttm \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --model-cache-dir hf_cache \
  --no-download
```

If needed, use the original workspace absolute `hf_cache` path as in Step 2.

Expected:

- Exit `0`.
- Report contains `status: available_and_ran`.

- [ ] **Step 5: Run baseline w80**

```bash
uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_baseline_forecasting_w80.md \
  --model baseline \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 80
```

Expected:

- Exit `0`, or a precise, reportable blocker.

- [ ] **Step 6: Run TTM w80 offline**

```bash
HF_HOME=hf_cache uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_ttm_forecasting_w80.md \
  --model ttm \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 80 \
  --model-cache-dir hf_cache \
  --no-download
```

If needed, use the original workspace absolute `hf_cache` path as in Step 2.

Expected:

- Exit `0` and `status: available_and_ran`, or a precise, reportable blocker.

- [ ] **Step 7: Extract key metrics for documentation**

Run:

```bash
reports=(
  reports/real_baseline_forecasting_w20.md \
  reports/real_ttm_forecasting_w20.md \
  reports/real_baseline_forecasting_w40.md \
  reports/real_ttm_forecasting_w40.md \
  reports/real_baseline_forecasting_w80.md \
  reports/real_ttm_forecasting_w80.md
)
existing_reports=()
for report in "${reports[@]}"; do
  if test -f "$report"; then
    existing_reports+=("$report")
  else
    echo "missing report, record blocker if this run failed: $report"
  fi
done
test "${#existing_reports[@]}" -gt 0 || { echo "no reports available"; exit 1; }
rg -n "model:|train_windows|test_windows|status:|RobustStageForecaster|StageSeasonalNaiveForecaster|foundation \\||grouped_metrics_source|hydraulic_system_detection|leak_current_monitoring|atmosphere_detection|pump_vibration" "${existing_reports[@]}"
```

Expected:

- Output includes dataset summary, baseline metrics, foundation metrics, and scenario metrics for each existing report.
- Missing reports are printed explicitly and must be reflected as blockers in `docs/ttm-real-data-evaluation.md` if their runs failed.
- Keep this output as local evidence for writing `docs/ttm-real-data-evaluation.md`.

- [ ] **Step 8: Confirm generated reports remain ignored**

Run:

```bash
for artifact in \
  reports/real_baseline_forecasting_w20.md \
  reports/real_ttm_forecasting_w20.md \
  reports/real_baseline_forecasting_w40.md \
  reports/real_ttm_forecasting_w40.md \
  reports/real_baseline_forecasting_w80.md \
  reports/real_ttm_forecasting_w80.md
do
  git check-ignore -q "$artifact" || { echo "not ignored: $artifact"; exit 1; }
  git check-ignore -v "$artifact"
done
```

Expected:

- All six reports are ignored.

---

## Task 3: 编写 TTM 真实数据能力评测报告

**Files:**
- Create: `docs/ttm-real-data-evaluation.md`
- Read local-only:
  - `reports/real_data_validation.md`
  - `reports/real_scenario_diagnostics.md`
  - `reports/real_baseline_forecasting_w20.md`
  - `reports/real_ttm_forecasting_w20.md`
  - `reports/real_baseline_forecasting_w40.md`
  - `reports/real_ttm_forecasting_w40.md`
  - `reports/real_baseline_forecasting_w80.md`
  - `reports/real_ttm_forecasting_w80.md`

- [ ] **Step 1: Draft report skeleton**

Create `docs/ttm-real-data-evaluation.md` with these sections:

```markdown
# TTM 真实数据能力复核报告

## 评测目标
## 数据与窗口
## 复现实验命令
## 整体指标
## 传感器指标
## 场景指标
## 能力判断
## 边界与风险
## 下一阶段模型开发任务
```

- [ ] **Step 2: Fill evaluation target and boundaries**

Write concise text stating:

- This is a real-data forecasting evaluation.
- It is not fault prediction, RUL, risk probability, or maintenance recommendation.
- TTM is being evaluated as the first foundation-model candidate after the data pipeline has run through.

Expected phrases to include:

```text
forecasting 能力复核
不是故障预测验收
不能推出 RUL 或维护建议
```

- [ ] **Step 3: Fill data and window section**

Include:

- 4,126,789 rows.
- 8 sensors.
- 8 stages.
- 428 reconstructed cycles, 247 complete cycles.
- `good`, `unassigned_cycle`, `invalid` counts from validation report.
- Standard window config: `cross-stage`, `90/16`.
- `max-windows=20/40/80` is first-N nested windows, not random sampling.

- [ ] **Step 4: Fill command section**

Include complete commands for:

- baseline w20, with note to change `20` to `40` and `80`.
- TTM w20 offline cache, with note to change `20` to `40` and `80`.
- TTM dependency setup:

```bash
uv sync --extra dev --extra foundation-ttm
```

Ensure commands match the CLI exactly:

- `--dataset`
- `--config`
- `--output`
- `--model baseline|ttm`
- `--window-mode cross-stage`
- `--context-length 90`
- `--prediction-length 16`
- `--max-windows N`
- `--model-cache-dir hf_cache`
- `--no-download`

- [ ] **Step 5: Fill overall metrics table**

Use local reports to create a table like:

```markdown
| max_windows | train_windows | test_windows | robust_mae | seasonal_mae | ttm_status | ttm_mae | ttm_rmse |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | actual_value | actual_value | actual_value | actual_value | actual_status | actual_value | actual_value |
```

Rules:

- Use actual report values.
- If w80 failed, record status and blocker instead of metrics.
- Do not invent missing values.

- [ ] **Step 6: Fill sensor and scenario summaries**

Include compact tables:

- Sensor-level TTM MAE/RMSE for w40 or latest successful standard run.
- Scenario-level TTM MAE/RMSE for w40 or latest successful standard run.
- Optional: include baseline fallback MAE only where useful for contrast.

Keep the tables readable. Do not paste entire local reports.

- [ ] **Step 7: Fill ability judgment**

Write conclusions:

- TTM can run offline from cache in the current workflow if dependencies and weights exist.
- TTM is a meaningful forecasting candidate.
- The strongest current evidence is numeric forecasting on the constructed windows, especially where TTM improves large baseline errors.
- It is not yet a complete anomaly or maintenance model.

- [ ] **Step 8: Fill boundaries and next development tasks**

Include:

- `unassigned_cycle` and `invalid` require data governance.
- Waiting stages may enter cross-stage windows.
- Current scenario is metrics grouping, not scenario-filtered model evaluation.
- Missing maintenance/failure labels blocks failure prediction.
- Next tasks:
  - scenario filtering.
  - quality flag filtering.
  - waiting-stage handling.
  - stronger baseline.
  - then model selection/fine-tuning.

- [ ] **Step 9: Self-check report wording**

Run:

```bash
rg -n "故障概率|RUL|维护建议|告警|生产" docs/ttm-real-data-evaluation.md
```

Expected:

- Any matches must be boundary statements, not claims of achieved capability.

- [ ] **Step 10: Commit report**

```bash
git add docs/ttm-real-data-evaluation.md
git commit -m "docs: summarize ttm real data evaluation"
```

---

## Task 4: 更新 README 为标准开发流程入口

**Files:**
- Modify: `README.md`
- Read: `docs/ttm-real-data-evaluation.md`
- Read: `docs/superpowers/specs/2026-06-02-ttm-standard-workflow-design.md`

- [ ] **Step 1: Re-outline README**

Rewrite README around this structure:

```markdown
# B08 设备时序基础模型

## 当前状态
## 适用读者
## 标准开发流程
## 1. 准备环境
## 2. 放置真实数据
## 3. 装配 canonical observations
## 4. 运行数据诊断
## 5. 运行 baseline
## 6. 运行 TTM
## 7. 如何阅读报告
## TTM 当前结论
## 不能得出的结论
## 下一阶段开发任务
## 关键目录
## 文档入口
## Agent 维护规则
```

Preserve important existing context:

- What FU13 is.
- Canonical observation schema summary.
- TTM optional dependency/cache explanation.
- Git safety boundary.
- Documentation links.

- [ ] **Step 2: Add standard workflow commands**

Ensure README includes copyable commands for:

```bash
uv sync --extra dev
uv sync --extra dev --extra foundation-ttm
```

README command examples must be complete and copyable. Do not leave `...` in command blocks.

Assemble:

```bash
uv run b08-model-core real-data assemble-fu13 \
  --input-dir data/real \
  --config configs/fu13_real_data_schema.yaml \
  --output data/processed/fu13_real_observations.parquet \
  --report reports/real_data_validation.md
```

Diagnose:

```bash
uv run b08-model-core real-data diagnose-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_scenario_diagnostics.md
```

Baseline:

```bash
uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_baseline_forecasting.md \
  --model baseline \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40
```

TTM offline cache:

```bash
HF_HOME=hf_cache uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_ttm_forecasting.md \
  --model ttm \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --model-cache-dir hf_cache \
  --no-download
```

All README commands must include required CLI arguments, including `--report` for `assemble-fu13`.

- [ ] **Step 3: Add report-reading guide**

Explain:

- `schema_valid=True`.
- `quality_counts`.
- `available_and_ran`.
- `Baseline Comparison`.
- `Foundation Metrics`.
- `Sensor Metrics`.
- `Scenario Metrics`.

Include caveats:

- Scenario metrics are grouping metrics, not scenario-filtered training/evaluation.
- Cross-stage windows may include waiting stages.
- No fault/RUL claim.

- [ ] **Step 4: Add TTM summary and link to independent report**

Include:

- TTM can run offline from cache.
- TTM is currently a forecasting candidate.
- Summary of w20/w40/w80 first-N evidence from `docs/ttm-real-data-evaluation.md`.
- Link:

```markdown
[TTM 真实数据能力复核报告](docs/ttm-real-data-evaluation.md)
```

- [ ] **Step 5: Add next development tasks**

List:

- window quality governance.
- scenario-filtered evaluation.
- quality-flag filtering.
- waiting-stage handling.
- stronger baselines.
- then model selection/fine-tuning.

Avoid saying “next step is immediately compare more models.”

- [ ] **Step 6: Self-check README claims**

Run:

```bash
rg -n "故障预测|故障概率|RUL|维护建议|直接用于|生产" README.md
```

Expected:

- Matches are explanatory boundaries only.
- No claim that TTM is production-ready.

- [ ] **Step 7: Commit README update**

```bash
git add README.md
git commit -m "docs: clarify standard ttm workflow"
```

---

## Task 5: 更新进展台账和文档入口

**Files:**
- Modify: `details.md`
- Modify: `docs/index.html`
- Read: `docs/ttm-real-data-evaluation.md`

- [ ] **Step 1: Update details current stage**

In `details.md`, update current stage to state:

- data pipeline has run through.
- current work has standardized TTM evaluation and developer workflow.
- next phase is model development after evaluation criteria are clear.

Do not remove the previously recorded real-data validation facts.

- [ ] **Step 2: Add recent update entry**

Add a `2026-06-02` row:

```markdown
| 2026-06-02 | 梳理 TTM 真实数据能力复核和标准开发流程：README 改为研发使用入口，并新增 TTM 真实数据评测报告，为后续模型选择、微调或训练做准备。 |
```

- [ ] **Step 3: Update docs/index.html**

Add a link/card/entry for:

```text
TTM 真实数据能力复核报告
docs/ttm-real-data-evaluation.md
```

Follow existing HTML style. Do not redesign the page.

- [ ] **Step 4: Verify docs references**

Run:

```bash
rg -n "ttm-real-data-evaluation|TTM 真实数据能力复核|标准开发流程" README.md details.md docs/index.html docs/ttm-real-data-evaluation.md
```

Expected:

- All intended docs link to or mention the new report.

- [ ] **Step 5: Commit docs index/progress update**

```bash
git add details.md docs/index.html
git commit -m "docs: update project stage for ttm workflow"
```

---

## Task 6: 最终验证和自审

**Files:**
- Read: all modified docs.
- Generated local-only: real reports and processed data.

- [ ] **Step 1: Run focused tests**

```bash
uv run python -m pytest tests/test_real_data_forecasting.py tests/test_cli_fu13_real_data.py -q
```

Expected:

- All tests pass.

- [ ] **Step 2: Run full test suite**

```bash
uv run python -m pytest -q
```

Expected:

- All tests pass.

- [ ] **Step 3: Verify generated artifacts are ignored**

```bash
for artifact in \
  data/real/stage_data.csv \
  data/processed/fu13_real_observations.parquet \
  reports/real_data_validation.md \
  reports/real_scenario_diagnostics.md \
  reports/real_baseline_forecasting.md \
  reports/real_ttm_forecasting.md \
  reports/real_baseline_forecasting_w20.md \
  reports/real_ttm_forecasting_w20.md \
  reports/real_baseline_forecasting_w40.md \
  reports/real_ttm_forecasting_w40.md \
  reports/real_baseline_forecasting_w80.md \
  reports/real_ttm_forecasting_w80.md \
  hf_cache/
do
  git check-ignore -q "$artifact" || { echo "not ignored: $artifact"; exit 1; }
  git check-ignore -v "$artifact"
done

git ls-files --error-unmatch reports/model_core_evaluation.md reports/model_route_decision.md
```

Expected:

- All existing generated/local paths are ignored.
- `reports/model_core_evaluation.md` and `reports/model_route_decision.md` remain tracked whitelist reports.

- [ ] **Step 4: Verify Git status**

```bash
git status --short --ignored
```

Expected:

- No tracked modifications.
- Only ignored generated artifacts, caches, and Python cache directories may appear.

- [ ] **Step 5: Self-review docs for overclaiming**

Run:

```bash
rg -n "故障概率|RUL|维护建议|生产|告警|直接用于" README.md details.md docs/ttm-real-data-evaluation.md
```

Expected:

- Any matches are caveats or non-goals.
- No doc claims TTM delivers production maintenance decisions.

- [ ] **Step 6: Request code/doc review**

Use `superpowers:requesting-code-review` with a reviewer context:

- What changed: README standard workflow, TTM real data report, details, docs index, plan/spec.
- Requirements: align with spec, no overclaiming, generated artifacts ignored, tests pass.
- Base SHA: plan start commit.
- Head SHA: current HEAD.

Expected:

- Reviewer returns no Critical or Important issues.
- Fix any valid Critical/Important issues and rerun relevant checks.

## Final Verification Gate

Do not claim completion until all are true:

- `docs/ttm-real-data-evaluation.md` exists and summarizes w20/w40/w80 first-N evidence or precise blockers.
- `README.md` is usable as a standard developer workflow entrance.
- `details.md` reflects that the data pipeline is through and the next phase is model development after TTM/evaluation standardization.
- `docs/index.html` links to the new TTM report.
- TTM standard config was rerun or a precise blocker was recorded.
- Full tests pass.
- No real raw data, processed parquet, temporary reports, or model cache are staged.
- A review pass has no unresolved Critical/Important issues.

## Execution Handoff

After this plan is reviewed and approved:

**Option 1: Subagent-Driven (recommended)**
Use `superpowers:subagent-driven-development`. Dispatch task-sized workers, review after each task, and keep write scopes disjoint.

**Option 2: Inline Execution**
Use `superpowers:executing-plans`. Execute the plan in this session with checkpoints between tasks.
