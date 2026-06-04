# Project Mainline Roadmap Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将项目入口文档和研发路线收束到“设备时序基础模型研发与评测”主线，明确 A -> C -> B 下一阶段路线，同时不做代码结构迁移。

**Architecture:** 本计划只改文档和导航，不改 Python 源码、CLI、测试结构或真实数据产物。README 面向研发执行者，`details.md` 面向阶段判断，`docs/index.html` 面向资料导航，并新增一份研究路线入口文档承接 A 阶段调研。

**Tech Stack:** Markdown, static HTML, existing docs structure, git, ripgrep, uv/pytest for final regression safety.

---

## 权威输入

- 设计文档：`docs/superpowers/specs/2026-06-04-project-mainline-roadmap-refactor-design.md`
- 当前研发入口：`README.md`
- 当前进展台账：`details.md`
- 当前文档导航：`docs/index.html`
- 已验证资产：
  - `docs/ttm-real-data-evaluation.md`
  - `docs/leak-current-scenario-evaluation.md`
  - `docs/reviews/real-data-schema-map.md`
- 研究资料入口：
  - `docs/调研资料/开源时序基础模型调研.md`

## 范围守卫

- 不改 `src/b08_model_core/`。
- 不改 CLI 命令。
- 不改 tests。
- 不移动真实数据、parquet、reports 或 `hf_cache/`。
- 不删除历史文档，只调整入口层级和叙事权重。
- 不把 `leak_current_monitoring` 写成项目终点；它是验证样例。
- 不把自研训练写成已经决定的路线；它是 A/C 之后的条件性路线。
- 如果工作区存在与本计划无关的脏改，例如 `AGENTS.md`，不要暂存、提交或格式化它。

## 文件结构

Modify:

- `README.md`
  - 重新定位为研发执行者入口。
  - 保留可复现命令，但将当前状态和下一阶段路线改为基础时序模型研发主线。
  - 减少历史叙事，把管理解释和旧阶段材料下沉到 `details.md` 或 docs 导航。

- `details.md`
  - 从“流水进展”调整为“阶段判断台账”。
  - 更新当前阶段判断、未完成能力、下一阶段计划、风险和近期记录。

- `docs/index.html`
  - 从单一文档列表重组为四组导航：主线入口、已验证资产、研究与路线资料、归档资料。
  - 增加设计文档和研究路线文档入口。

Create:

- `docs/foundation-timeseries-research-roadmap.md`
  - 作为 A 阶段的研究路线入口。
  - 不做完整学术综述，只建立下一阶段资料框架、问题清单和阅读/评测路线。

Do not modify:

- `src/b08_model_core/**`
- `tests/**`
- `configs/**`
- `data/**`
- `reports/real_*`
- `hf_cache/**`

Generated local-only, do not stage:

- `.pytest_cache/`
- `__pycache__/`
- any generated report under `reports/real_*`

## Task 1: 预检与安全边界

**Files:**
- Read: `docs/superpowers/specs/2026-06-04-project-mainline-roadmap-refactor-design.md`
- Read: `README.md`
- Read: `details.md`
- Read: `docs/index.html`
- Read: `.gitignore`

- [ ] **Step 1: 确认分支和工作区状态**

Run:

```bash
git branch --show-current
git status --short --ignored
```

Expected:

- Current branch is intended for documentation refactor work.
- Any pre-existing unrelated tracked change is identified.
- If `AGENTS.md` is modified before this plan starts, treat it as unrelated unless the user explicitly includes it.
- Ignored artifacts may include `data/real/`, `data/processed/`, `reports/real_*`, `hf_cache/`, `.pytest_cache/`, `__pycache__/`.

- [ ] **Step 2: Confirm no code refactor is needed**

Run:

```bash
git diff -- README.md details.md docs/index.html docs/superpowers/specs/2026-06-04-project-mainline-roadmap-refactor-design.md
```

Expected:

- Only context inspection output.
- Do not edit code files in this task.

- [ ] **Step 3: Commit boundary**

No commit in this task unless a branch setup file is intentionally created. This task is a safety checkpoint.

## Task 2: README 研发执行者入口收束

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Draft target README outline before editing**

Use this target heading structure:

```markdown
# B08 设备时序基础模型

## 项目定位
## 当前可复现资产
## 标准研发流程
## 1. 准备环境
## 2. 装配 FU13 canonical observations
## 3. 运行数据诊断
## 4. 运行 baseline / TTM forecasting
## 5. 运行业务场景评测样例
## 6. 阅读报告与边界
## 下一阶段研发路线
## 关键目录
## 文档入口
## Agent 维护规则
## Git 安全边界
```

Expected:

- README remains command-oriented for研发执行者.
- Management-style explanation is minimized or linked out.

- [ ] **Step 2: Rewrite project positioning**

Replace the old “当前阶段为 FU13 real data pipeline + TTM real-data forecasting validation” framing with:

```markdown
本项目是面向设备时序数据的基础模型研发与评测项目。当前 FU13 真实数据 pipeline、TTM 真实推理和漏液电流场景评测，是为了验证基础模型研发所需的数据标准化、窗口构建、模型输入输出、评测指标和候选信号映射能力。
```

Expected:

- README clearly says the project is not merely a business alarm workflow.
- `leak_current_monitoring` is described as a validation sample, not endpoint.

- [ ] **Step 3: Preserve reproducible commands**

Keep commands for:

- `uv sync --extra dev`
- `uv run python -m pytest -q`
- `real-data assemble-fu13`
- `real-data diagnose-fu13`
- `real-data forecast-fu13 --model baseline`
- `real-data forecast-fu13 --model ttm`
- `real-data evaluate-scenario`

Expected:

- A developer can still reproduce the current pipeline from README.
- Commands still reference ignored local outputs under `data/processed/` and `reports/real_*`.

- [ ] **Step 4: Replace next-stage section with A -> C -> B route**

Use this route:

```text
A. 学术 / 行业 / 模型路线调研
  -> C. 开源基础时序模型系统适配与对比
    -> B. 自研设备时序基础模型训练方案设计
```

Required wording:

- A comes first because the project must decide what设备时序基础模型 should learn and evaluate.
- C comes second because open-source foundation models must be tested before自研.
- B is conditional and should not be described as already decided.

- [ ] **Step 5: Verify README headings and boundary language**

Run:

```bash
rg -n "^## |A -> C -> B|设备时序数据的基础模型研发与评测|验证样例|不是项目终点|自研.*条件" README.md
```

Expected:

- README contains the new project positioning.
- README contains A -> C -> B or equivalent route.
- README does not frame `leak_current_monitoring` as the project endpoint.

- [ ] **Step 6: Commit README update**

Run:

```bash
git add README.md
git commit -m "docs: refocus readme on model research mainline"
```

Expected:

- Commit contains only `README.md`.

## Task 3: details.md 阶段判断台账收束

**Files:**
- Modify: `details.md`

- [ ] **Step 1: Update current stage judgment**

Replace the previous “业务场景评测口径固化” dominant framing with:

```markdown
当前阶段已经完成真实数据 pipeline、TTM 真实评测和第一个业务场景评测样例。下一步主线从业务场景闭环回到设备时序基础模型研发：先补学术与行业路线判断，再系统适配开源模型，最后决定是否进入自研训练方案设计。
```

Expected:

- `details.md` explains why business scenario work is a validation sample.
- It separates engineering application work from model research work.

- [ ] **Step 2: Update “已经具备的能力”**

Ensure this section includes:

- FU13 canonical data pipeline.
- Baseline / TTM real-data forecasting.
- `leak_current_monitoring` scenario evaluation as candidate signal sample.
- Reproducible Python/uv workflow.

Expected:

- Existing capabilities are not lost.
- The scenario evaluation is not over-claimed as fault prediction.

- [ ] **Step 3: Update “目前还没有具备的能力”**

Ensure this section distinguishes:

- Not yet completed academic/industry route review.
- Not yet completed systematic open-source model comparison.
- Not yet designed self-trained equipment time-series foundation model.
- Not yet production predictive maintenance system.

Expected:

- Lack of maintenance records is described as engineering application limitation, not the only next blocker.

- [ ] **Step 4: Replace next-stage plan with A -> C -> B**

Use three subsections:

```markdown
### A. 学术 / 行业 / 模型路线调研
### C. 开源基础时序模型系统适配与对比
### B. 自研设备时序基础模型训练方案设计
```

Expected:

- A/C/B order is explicit.
- B remains conditional on A/C findings.

- [ ] **Step 5: Add recent update row**

Add a `2026-06-04` row:

```markdown
| 2026-06-04 | 完成项目主线与研发路线收束设计：README 面向研发执行者，下一阶段按 A-C-B 推进，即先补学术/行业路线调研，再系统适配开源模型，最后判断是否进入自研训练方案设计。 |
```

Expected:

- The update records this document-level route shift.

- [ ] **Step 6: Verify details boundary language**

Run:

```bash
rg -n "A\\. 学术|C\\. 开源|B\\. 自研|工程团队|验证样例|不是.*生产|不能.*故障概率|路线调研" details.md
```

Expected:

- New route appears.
- Business/engineering boundary appears.
- No over-claiming production maintenance capability.

- [ ] **Step 7: Commit details update**

Run:

```bash
git add details.md
git commit -m "docs: update project stage roadmap"
```

Expected:

- Commit contains only `details.md`.

## Task 4: 新增研究路线入口文档

**Files:**
- Create: `docs/foundation-timeseries-research-roadmap.md`

- [ ] **Step 1: Create document skeleton**

Create:

```markdown
# 设备时序基础模型研究路线

## 目的
## 当前基础
## A. 学术 / 行业 / 模型路线调研
## C. 开源基础时序模型系统适配与对比
## B. 自研设备时序基础模型训练方案设计
## 资料清单
## Go / No-Go 问题
## 与业务场景评测的关系
```

Expected:

- This document is a route scaffold, not a completed literature review.

- [ ] **Step 2: Fill purpose and current foundation**

Required points:

- The project has a working FU13 pipeline and evaluation bridge.
- The next step is to determine foundation-model research direction.
- Real maintenance records and production alarms are engineering application concerns, not the sole next research blocker.

- [ ] **Step 3: Fill A/C/B sections**

For A:

- list task taxonomy: forecasting, imputation, representation, anomaly, classification, RUL.
- list industrial time-series characteristics.
- list models/papers to investigate.

For C:

- list open-source model candidates: TTM, MOMENT, Chronos, TimesFM, Moirai, UniTS.
- list comparison dimensions: task coverage, input constraints, dependency cost, inference speed, fine-tuning support.

For B:

- list conditional self-training design questions: data format, pretraining objective, validation split, minimal prototype, compute budget.

Expected:

- The document gives enough structure for a later research task.
- It does not pretend that research has already been completed.

- [ ] **Step 4: Fill business-scenario relationship**

Required wording:

```markdown
`leak_current_monitoring` 是基础模型输出到候选业务信号的验证样例，不是基础模型研发路线的终点。
```

Expected:

- Business scenario evaluation is retained as evidence and interface.
- It does not dominate the next research route.

- [ ] **Step 5: Verify route scaffold**

Run:

```bash
rg -n "TTM|MOMENT|Chronos|TimesFM|Moirai|UniTS|Go / No-Go|验证样例|预训练目标|representation" docs/foundation-timeseries-research-roadmap.md
```

Expected:

- All planned route anchors appear.

- [ ] **Step 6: Commit research roadmap scaffold**

Run:

```bash
git add docs/foundation-timeseries-research-roadmap.md
git commit -m "docs: add foundation timeseries research roadmap"
```

Expected:

- Commit contains only the new roadmap document.

## Task 5: docs/index.html 导航重组

**Files:**
- Modify: `docs/index.html`

- [ ] **Step 1: Update header lead**

Replace old “TTM 真实数据能力复核、标准评测口径和开发者 workflow 固化阶段” framing with:

```html
<p class="lead">面向设备时序基础模型研发与评测。FU13 真实数据 pipeline、TTM 真实推理和漏液电流场景评测已经形成最小数据与评测闭环；下一阶段按学术/行业路线调研、开源模型系统适配、自研训练方案设计推进。</p>
```

Expected:

- Header matches the new mainline.

- [ ] **Step 2: Replace document cards with grouped sections**

Use four sections:

```html
<section class="grid" aria-label="主线入口">
...
</section>
<section class="grid" aria-label="已验证资产">
...
</section>
<section class="grid" aria-label="研究与路线资料">
...
</section>
<section class="grid" aria-label="归档资料">
...
</section>
```

Expected:

- The first visible group is mainline entry.
- Historical documents are moved into archive/research groups, not deleted.

- [ ] **Step 3: Add mainline cards**

Required cards:

- `../README.md` or `README` reference if appropriate in static site context.
- `../details.md` or `details` reference if appropriate.
- `superpowers/specs/2026-06-04-project-mainline-roadmap-refactor-design.md`

If relative links outside `docs/` are unsuitable for GitHub Pages, keep README/details in text but link to files from repository context only where current docs pattern allows.

Expected:

- The design spec is discoverable from docs index.

- [ ] **Step 4: Add validated asset cards**

Required cards:

- `ttm-real-data-evaluation.md`
- `leak-current-scenario-evaluation.md`
- `reviews/real-data-schema-map.md`

Expected:

- Existing verified assets remain easy to find.

- [ ] **Step 5: Add research route cards**

Required cards:

- `foundation-timeseries-research-roadmap.md`
- `调研资料/开源时序基础模型调研.md`
- `model-route-decision.html`
- `model-capability-matrix.html`
- `open-source-model-fit.html`

Expected:

- A stage research entry is visible.

- [ ] **Step 6: Archive historical/process docs**

Move these cards into archive group:

- `brainstorming-result.html`
- `data-simulation-scenario.html`
- `implementation-plan.html`
- `foundation-model-inference-design.html`
- `foundation-model-inference-plan.html`
- `foundation-model-verification-report.html`
- `knowledge-output-plan.html`
- `reviews/2026-05-31-code-review-and-next-stage.md`
- existing `原始材料/` and `归档/` links

Expected:

- No linked historical document is deleted.
- The first screen no longer reads like a chronological pile.

- [ ] **Step 7: Update note and footer**

Set note to:

```html
当前主线收束为设备时序基础模型研发与评测：真实数据 pipeline 和场景评测样例已经验证最小闭环；下一阶段先补学术/行业路线调研，再系统适配开源模型，最后判断是否进入自研训练方案设计。
```

Set footer date to `2026-06-04`.

- [ ] **Step 8: Verify links and labels**

Run:

```bash
rg -n "主线入口|已验证资产|研究与路线资料|归档资料|foundation-timeseries-research-roadmap|project-mainline-roadmap-refactor|2026-06-04" docs/index.html
```

Expected:

- All four groups appear.
- New design and roadmap links appear.
- Footer date updated.

- [ ] **Step 9: Commit docs index update**

Run:

```bash
git add docs/index.html
git commit -m "docs: reorganize documentation index"
```

Expected:

- Commit contains only `docs/index.html`.

## Task 6: Cross-document consistency pass

**Files:**
- Modify as needed: `README.md`
- Modify as needed: `details.md`
- Modify as needed: `docs/index.html`
- Modify as needed: `docs/foundation-timeseries-research-roadmap.md`

- [ ] **Step 1: Search for outdated dominant framing**

Run:

```bash
rg -n "当前阶段为|唯一主线|业务场景评测口径固化|马上横向|还没有完成 scenario-filtered|TTM 真实数据能力复核、标准评测口径" README.md details.md docs/index.html docs/foundation-timeseries-research-roadmap.md
```

Expected:

- Any remaining outdated text is either intentionally historical or needs editing.

- [ ] **Step 2: Search for required new framing**

Run:

```bash
rg -n "设备时序.*基础模型研发|A -> C -> B|学术 / 行业|开源基础时序模型|自研设备时序基础模型|验证样例|不是项目终点" README.md details.md docs/index.html docs/foundation-timeseries-research-roadmap.md
```

Expected:

- Required new framing appears across the document set.

- [ ] **Step 3: Fix inconsistencies**

If Step 1 finds outdated wording that conflicts with the new spec, edit the smallest relevant paragraph.

Expected:

- Do not rewrite unrelated sections.
- Do not add new code tasks.

- [ ] **Step 4: Verify no generated assets staged**

Run:

```bash
git status --short --ignored
git diff --name-only --cached
```

Expected:

- Only intended Markdown/HTML docs are tracked or staged.
- `AGENTS.md` remains untouched unless explicitly included by user.
- `data/real/`, `data/processed/`, `reports/real_*`, and `hf_cache/` remain ignored.

- [ ] **Step 5: Commit consistency pass if changes were made**

If files changed:

```bash
git add README.md details.md docs/index.html docs/foundation-timeseries-research-roadmap.md
git commit -m "docs: align roadmap refactor language"
```

If no files changed, do not commit.

## Task 7: Final verification and handoff

**Files:**
- Read: all modified docs
- Read: git status

- [ ] **Step 1: Run Markdown/HTML text checks**

Run:

```bash
rg -n "设备时序.*基础模型研发|A -> C -> B|验证样例|不是项目终点|不做代码" README.md details.md docs/index.html docs/foundation-timeseries-research-roadmap.md docs/superpowers/specs/2026-06-04-project-mainline-roadmap-refactor-design.md
```

Expected:

- New mainline appears in README/details/docs index/roadmap/spec.

- [ ] **Step 2: Run repository regression tests**

Run:

```bash
uv run python -m pytest -q
```

Expected:

- Tests pass.
- If tests fail due to environment only, record exact failure and do not claim full verification.

- [ ] **Step 3: Run git whitespace check**

Run:

```bash
git diff --check
```

Expected:

- No output.

- [ ] **Step 4: Verify git status**

Run:

```bash
git status --short --ignored
```

Expected:

- No unintended tracked modifications.
- `AGENTS.md` pre-existing changes are called out if still present and unrelated.
- Ignored local data/cache/report artifacts remain ignored.

- [ ] **Step 5: Final review checklist**

Confirm:

- README first reader is研发执行者.
- `details.md` explains the route shift.
- `docs/index.html` is grouped by use.
- Research roadmap scaffold exists.
- `leak_current_monitoring` is described as验证样例.
- A -> C -> B route is explicit.
- No source code or tests were changed.

- [ ] **Step 6: Commit final verification note if needed**

No commit is required if verification only ran commands.

- [ ] **Step 7: Handoff**

Report:

- Files changed.
- Commits made.
- Verification commands and results.
- Any unrelated dirty files, especially `AGENTS.md`.
- Recommended next step: push branch / PR / or proceed to execution if not already executed.
