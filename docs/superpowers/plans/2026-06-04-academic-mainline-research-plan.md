# Academic Mainline Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 A 阶段落实为可执行的学术调研、知识成果凝练、训练路线设计和项目主线重构工作，使 B08 短期第一目标聚焦论文/专利/学术知识成果，第二目标承接工程化模型产品成果，并在必要时纳入服务主线确立的代码与项目结构重构。

**Architecture:** 本计划以 `docs/research/` 作为 A 阶段研究资产目录，形成学术主线、开源模型论文矩阵、预测性维护数据集矩阵、任务指标矩阵、模型训练路线、论文专利方向和工程化产品承接路线。项目入口文档同步重构为“知识成果优先、工程产品承接”的主线叙事；如果执行中发现现有代码结构、CLI、配置或测试组织阻碍主线确立，则通过“主线必要重构审计”进入独立、可验证的代码重构任务，而不是把债务默认推迟。

**Tech Stack:** Markdown, static HTML, existing B08 docs structure, web research, ripgrep, uv/pytest for optional final regression safety.

---

## 权威输入

- 设计文档：`docs/superpowers/specs/2026-06-04-academic-mainline-research-design.md`
- 当前研发入口：`README.md`
- 当前阶段台账：`details.md`
- 当前文档导航：`docs/index.html`
- 当前研究路线入口：`docs/foundation-timeseries-research-roadmap.md`
- 已有开源模型调研：`docs/调研资料/开源时序基础模型调研.md`
- 已验证资产：
  - `docs/ttm-real-data-evaluation.md`
  - `docs/leak-current-scenario-evaluation.md`
  - `docs/reviews/real-data-schema-map.md`

## 范围守卫

- 短期第一目标是知识成果：论文主线、专利方向、学术综述、模型路线论证、数据集和任务矩阵。
- 第二目标是工程化产品成果：统一数据语料、模型训练路线、开源模型对比、未来 adapter / training prototype 的工程入口。
- 允许做项目入口、研究资产结构、代码结构、CLI、配置和测试组织的必要重构，但每一项重构都必须服务上述两条主线。
- 默认不做无证据的源码变更；一旦判断源码、CLI 或测试结构已经阻碍主线确立，必须先记录阻碍证据、目标边界、影响文件、验证命令和回滚风险，再执行重构。
- 代码重构不能泛化为清理历史债务；只有直接影响知识成果主线、模型训练路线、开源模型适配、统一数据语料或工程化产品承接的债务才纳入。
- 不移动真实数据、parquet、ignored reports 或 `hf_cache/`。
- 不启动大规模模型训练。
- 不把 `leak_current_monitoring` 写成项目终点。
- 不把 RUL、生产告警或维修建议写成第一版已经具备的能力。
- 不把自研训练写成已经决定；自研仍是 A/C 之后的条件性路线。

## 文件结构

Create:

- `docs/research/project-mainline-refactor-blueprint.md`
  - 项目整体重构蓝图，基于知识成果优先线和工程化产品承接线定义目标结构、迁移规则、前置重构范围和后续代码重构入口。

- `docs/research/index.md`
  - A 阶段研究资产入口，解释知识成果优先线和工程化产品承接线。

- `docs/research/academic-mainline-review.md`
  - 学术主线综述，凝练 B08 的论文问题意识、相关工作分类和学术缺口。

- `docs/research/open-source-model-paper-matrix.md`
  - 主流开源时序基础模型论文矩阵，覆盖 TTM、MOMENT、Chronos、TimesFM、Moirai、UniTS、TSPulse。

- `docs/research/predictive-maintenance-dataset-matrix.md`
  - 预测性维护和设备健康数据集矩阵，覆盖 FU13、C-MAPSS、IMS Bearing、PRONOSTIA/FEMTO、TEP 等。

- `docs/research/task-metric-matrix.md`
  - 任务与指标矩阵，按无标签任务、弱标签任务、预测性维护目标任务分层。

- `docs/research/foundation-model-training-route.md`
  - 模型训练路线，定义统一数据语料、预训练任务、小样本适配任务、开源模型对照和 Go / No-Go 条件。

- `docs/research/paper-patent-directions.md`
  - 论文与专利方向清单，区分框架型成果、方法型成果和工程化延展成果。

- `docs/research/productization-roadmap.md`
  - 工程化产品承接路线，说明知识成果如何沉淀为模型产品、adapter、评测工具和研发 workflow。

Modify:

- `README.md`
  - 增加或调整下一阶段说明，使短期第一目标是知识成果、第二目标是工程化产品成果。
  - 保留现有可复现命令。

- `details.md`
  - 增加 2026-06-04 A 阶段计划记录。
  - 明确知识成果与工程化产品成果的优先级。

- `docs/index.html`
  - 增加 `docs/research/` 研究资产入口。
  - 调整导航，让 A 阶段研究成果成为主线入口之一。

- `docs/foundation-timeseries-research-roadmap.md`
  - 将泛化路线与本次 `docs/research/` 执行资产对齐。

Potentially modify after mainline refactor audit:

- `src/b08_model_core/**`
  - 仅当 Task 2 的整体重构蓝图或 Task 12 的主线必要重构审计证明现有模块边界阻碍统一数据语料、模型 adapter、训练/评测 workflow 或研究成果沉淀时修改。

- `tests/**`
  - 仅当源码或 CLI 发生主线必要重构时同步修改或补充测试。

- `configs/**`
  - 仅当 Task 2 或 Task 12 证明需要把数据语料、开源数据 schema map 或模型实验配置纳入主线入口时修改。

Do not modify without explicit mainline evidence:

- `data/**`
- `reports/real_*`
- `hf_cache/**`

## Task 1: 预检与边界确认

**Files:**
- Read: `docs/superpowers/specs/2026-06-04-academic-mainline-research-design.md`
- Read: `README.md`
- Read: `details.md`
- Read: `docs/index.html`
- Read: `docs/foundation-timeseries-research-roadmap.md`
- Read: `.gitignore`

- [ ] **Step 1: 确认工作区状态**

Run:

```bash
git status --short --ignored
```

Expected:

- Identify unrelated tracked changes before editing.
- Ignored local artifacts may include `data/real/`, `data/processed/`, `reports/real_*`, `hf_cache/`, `.pytest_cache/`, `__pycache__/`.
- Do not stage or edit unrelated changes.

- [ ] **Step 2: 确认 A 阶段设计输入存在**

Run:

```bash
rg -n "面向小样本工业物联设备健康管理|知识成果|工程化|TTM|MOMENT|C-MAPSS|Go / No-Go" docs/superpowers/specs/2026-06-04-academic-mainline-research-design.md
```

Expected:

- Spec contains academic mainline, model candidates, dataset candidates, and Go / No-Go framing.

- [ ] **Step 3: 确认代码重构不是默认排除项**

Run:

```bash
find src tests configs -maxdepth 2 -type f | sort
```

Expected:

- This is inspection only.
- The executor understands that code changes are allowed only after Task 11 mainline refactor audit identifies concrete evidence and exact files.
- Do not edit code in Task 1.

## Task 2: 创建 A 阶段研究资产入口

## Task 2: 项目整体重构蓝图与执行门

**Files:**
- Create: `docs/research/project-mainline-refactor-blueprint.md`
- Potentially modify after blueprint approval inside this task:
  - `README.md`
  - `details.md`
  - `docs/index.html`
  - `docs/foundation-timeseries-research-roadmap.md`

- [ ] **Step 1: 创建项目整体重构蓝图骨架**

Create `docs/research/project-mainline-refactor-blueprint.md`:

```markdown
# 项目整体重构蓝图

## 目的
## 总体目标
## 两条主线
## 当前项目结构观察
## 目标项目结构
## 前置重构范围
## 后续代码重构入口
## 保留与归档规则
## 文件迁移规则
## 文档入口规则
## 代码模块边界规则
## 配置与数据资产规则
## 测试与验证规则
## 风险与回滚
## 执行顺序决策
```

- [ ] **Step 2: 检查当前项目结构**

Run:

```bash
find . -maxdepth 2 \( -name .git -o -name node_modules -o -name __pycache__ -o -name .venv -o -name venv -o -name hf_cache -o -name data \) -prune -o -type d -print | sort
find README.md details.md docs src tests configs -maxdepth 2 -type f | sort
```

Expected:

- Capture top-level structure, docs structure, source package, tests, and configs.
- Do not edit during this step.

- [ ] **Step 3: 定义总体目标**

Write:

```markdown
本次整体重构的目标不是清理所有历史债务，而是正式确立 B08 的项目主线：短期第一目标服务知识成果，包括论文、专利、学术综述、模型路线和数据/任务矩阵；第二目标服务工程化产品成果，包括统一数据语料、开源模型适配、训练评测 workflow 和可复现模型研发工作台。
```

- [ ] **Step 4: 定义目标项目结构**

Use this target structure as the first draft:

```text
README.md                         # 研发执行入口，说明知识成果优先与工程化产品承接
details.md                        # 阶段判断台账
docs/index.html                   # 文档导航入口
docs/research/                    # A 阶段知识成果与训练路线资产
docs/superpowers/specs/           # 已确认设计
docs/superpowers/plans/           # 可执行计划
docs/reviews/                     # 评审、schema map、阶段 review
docs/调研资料/                    # 既有中文调研资料，逐步被 docs/research 承接或引用
docs/归档/                        # 历史规划和旧方案
src/b08_model_core/               # 模型研发工作台代码
configs/                          # 真实数据、schema map、实验配置
tests/                            # 可复现验证
reports/                          # 可提交白名单报告与 ignored 本机报告分离
data/                             # ignored 本机数据
hf_cache/                         # ignored 模型缓存
```

- [ ] **Step 5: 决定前置还是后置**

Record this decision:

```markdown
整体项目重构必须前置启动，因为后续研究资产、文档入口和工程化承接路线都依赖目标结构；但代码级重构不应在没有阻碍证据时贸然执行。前置阶段先完成目录、入口、导航和重构蓝图；源码、CLI、配置和测试结构的重构进入后续“主线必要重构审计与执行门”，以证据和子计划驱动。
```

- [ ] **Step 6: 定义前置重构范围**

Classify:

```markdown
| 类型 | 前置处理 | 原因 |
| --- | --- | --- |
| docs/research | 立即创建 | A 阶段研究资产需要稳定入口 |
| README/details/docs index | 立即更新 | 项目默认叙事必须先对齐主线 |
| 旧调研资料 | 保留并引用 | 不删除历史资料，避免破坏上下文 |
| docs/归档 | 保留 | 历史方案降级为归档，不抢主线入口 |
| src/tests/configs | 先审计后重构 | 代码重构需要行为验证和独立子计划 |
| data/reports/hf_cache | 不移动 | 本机资产和 ignored 规则不可破坏 |
```

- [ ] **Step 7: 定义代码重构入口**

Write:

```markdown
如果后续发现 `src/b08_model_core`、CLI、configs 或 tests 的现有组织已经阻碍统一数据语料、开源模型 adapter、训练/评测 workflow 或知识成果沉淀，则必须创建独立 code-refactor spec 与 plan，并在测试保护下执行。代码重构不后置为模糊债务，但也不在没有证据时作为泛化清理执行。
```

- [ ] **Step 8: 验证蓝图关键词**

Run:

```bash
rg -n "知识成果|工程化产品|目标项目结构|前置重构|代码重构入口|src/b08_model_core|docs/research" docs/research/project-mainline-refactor-blueprint.md
```

Expected:

- Blueprint makes project-wide restructuring explicit.

- [ ] **Step 9: Commit**

Run:

```bash
git add docs/research/project-mainline-refactor-blueprint.md
git commit -m "docs: add project mainline refactor blueprint"
```

Expected:

- Commit contains only `docs/research/project-mainline-refactor-blueprint.md`.

## Task 3: 创建 A 阶段研究资产入口

**Files:**
- Create: `docs/research/index.md`

- [ ] **Step 1: 创建目录和入口文件**

Create `docs/research/index.md` with this structure:

```markdown
# B08 A 阶段研究资产入口

## 定位
## 两条主线
## 研究资产列表
## 知识成果优先线
## 工程化产品承接线
## 执行边界
## 阅读顺序
```

- [ ] **Step 2: 写入定位**

Use this wording:

```markdown
A 阶段用于把 B08 从“真实数据与模型评测沙盒”推进到“面向小样本工业物联设备健康管理的时序基础模型”学术主线。短期第一目标是知识成果，包括论文主线、专利方向、学术综述和模型路线论证；第二目标是工程化产品成果，包括统一数据语料、模型训练路线、开源模型适配和可复现评测 workflow。
```

- [ ] **Step 3: 写入研究资产列表**

List these files and responsibilities:

```markdown
- `project-mainline-refactor-blueprint.md`
- `academic-mainline-review.md`
- `open-source-model-paper-matrix.md`
- `predictive-maintenance-dataset-matrix.md`
- `task-metric-matrix.md`
- `foundation-model-training-route.md`
- `paper-patent-directions.md`
- `productization-roadmap.md`
```

- [ ] **Step 4: 验证入口关键字**

Run:

```bash
rg -n "知识成果|工程化产品|academic-mainline-review|productization-roadmap|预测性维护" docs/research/index.md
```

Expected:

- Entry document makes the two-track structure explicit.

- [ ] **Step 5: Commit**

Run:

```bash
git add docs/research/index.md
git commit -m "docs: add academic research asset index"
```

Expected:

- Commit contains only `docs/research/index.md`.

## Task 4: 编写学术主线综述

**Files:**
- Create: `docs/research/academic-mainline-review.md`

- [ ] **Step 1: 创建综述骨架**

Create:

```markdown
# 学术主线综述

## 核心命题
## 为什么不是普通 forecasting
## 工业物联设备健康管理的特殊性
## 现有路线分类
## B08 的学术缺口
## B08 的方法空间
## 与 FU13 当前资产的关系
## 与知识成果的关系
## 与工程化产品的关系
## 暂不主张的能力
```

- [ ] **Step 2: 写入核心命题**

Use:

```markdown
B08 的学术主线是：面向小样本工业物联设备健康管理的时序基础模型。它关注在真实故障样本稀缺、设备类型多样、工况阶段强结构化、传感器多物理域耦合的条件下，如何通过无标签或弱标签预训练学习通用设备运行表征，并以少量样本适配预测性维护相关任务。
```

- [ ] **Step 3: 写入现有路线分类**

Include:

```markdown
- forecasting-first time-series foundation models
- multi-task / representation time-series foundation models
- traditional predictive maintenance / RUL methods
- industrial anomaly detection and process monitoring
```

- [ ] **Step 4: 写入 B08 学术缺口**

Include:

```markdown
通用时序基础模型主要证明跨数据集 forecasting 能力，但工业设备健康管理需要同时处理工艺阶段、多传感器物理域、质量标记、弱标签、退化趋势和小样本适配。
```

- [ ] **Step 5: 写入边界**

State:

```markdown
本阶段不主张 B08 已具备生产告警、RUL 精确估计或自动维修建议能力。RUL 是第三层目标，依赖开源 run-to-failure 数据或后续真实维修记录支撑。
```

- [ ] **Step 6: 验证综述关键词**

Run:

```bash
rg -n "小样本工业物联|forecasting-first|multi-task|RUL|生产告警|知识成果|工程化产品" docs/research/academic-mainline-review.md
```

Expected:

- The document states academic problem, route classification, and boundaries.

- [ ] **Step 7: Commit**

Run:

```bash
git add docs/research/academic-mainline-review.md
git commit -m "docs: draft academic mainline review"
```

Expected:

- Commit contains only `docs/research/academic-mainline-review.md`.

## Task 5: 编写开源模型论文矩阵

**Files:**
- Create: `docs/research/open-source-model-paper-matrix.md`

- [ ] **Step 1: 创建矩阵骨架**

Create:

```markdown
# 开源时序基础模型论文矩阵

## 目的
## 调研字段
## Forecasting-first 模型
## Multi-task / representation 模型
## 对 B08 的适配缺口
## C 阶段优先级
## 参考链接
```

- [ ] **Step 2: 写入调研字段**

Use:

```markdown
| 字段 | 含义 |
| --- | --- |
| paper | 论文或模型卡 |
| open source | 代码或权重是否可用 |
| task coverage | 支持 forecasting、imputation、representation、anomaly、classification、RUL 中哪些任务 |
| input constraints | 单变量/多变量、上下文长度、预测长度、采样频率、metadata 支持 |
| training data | 预训练数据来源 |
| adaptation | zero-shot、few-shot、fine-tuning、adapter 支持 |
| B08 fit | 对小样本工业物联预测性维护的适配价值 |
| gap | 不能直接覆盖的缺口 |
```

- [ ] **Step 3: 填写 forecasting-first 初版表**

Include at minimum:

```markdown
| 模型 | 论文/资料 | 核心能力 | B08 价值 | 主要缺口 |
| --- | --- | --- | --- | --- |
| TTM / TinyTimeMixer | arXiv:2401.03955 | 轻量 zero/few-shot 多变量 forecasting | 预测残差基线、资源受限部署候选 | 主要偏 forecasting，设备结构 metadata 需要外部处理 |
| Chronos / Chronos-Bolt | arXiv:2403.07815 | token 化时序 forecasting | zero-shot forecasting 对照 | 对工业物理域、阶段和多任务表征支持有限 |
| TimesFM | arXiv:2310.10688 | decoder-only forecasting foundation model | 正常轨迹预测对照 | 主要偏 forecasting |
| Moirai / Uni2TS | arXiv:2402.02592 | universal probabilistic forecasting | 概率预测和跨数据集 forecasting 对照 | 预测性维护任务需额外适配 |
```

- [ ] **Step 4: 填写 multi-task / representation 初版表**

Include at minimum:

```markdown
| 模型 | 论文/资料 | 核心能力 | B08 价值 | 主要缺口 |
| --- | --- | --- | --- | --- |
| MOMENT | arXiv:2402.03885 | forecasting、imputation、classification、anomaly、representation | 多任务基础模型重要对照 | 工业设备结构和预测性维护语义需适配 |
| UniTS | arXiv:2403.00131 | unified time-series tasks | 多任务统一机制参考 | 工业 metadata 与设备健康任务需重构 |
| TSPulse / Granite Time Series | IBM Granite Time Series docs | 表征、预测、补全、分类、异常等 | 设备状态表征和异常候选信号对照 | 具体开源可运行性和任务接口需核对 |
```

- [ ] **Step 5: 写入 C 阶段优先级**

Use:

```markdown
C 阶段优先级不是按模型名气排序，而是按 B08 任务覆盖排序：先保留 TTM 作为已跑通 forecasting 参考，再补 MOMENT / UniTS / TSPulse 的 representation 与 multi-task 能力对照，同时用 Chronos / TimesFM / Moirai 作为 forecasting-first 横向比较。
```

- [ ] **Step 6: 验证模型覆盖**

Run:

```bash
rg -n "TTM|MOMENT|Chronos|TimesFM|Moirai|UniTS|TSPulse|B08 fit|C 阶段" docs/research/open-source-model-paper-matrix.md
```

Expected:

- All required models and C-stage priority appear.

- [ ] **Step 7: Commit**

Run:

```bash
git add docs/research/open-source-model-paper-matrix.md
git commit -m "docs: add open source model paper matrix"
```

Expected:

- Commit contains only `docs/research/open-source-model-paper-matrix.md`.

## Task 6: 编写预测性维护数据集矩阵

**Files:**
- Create: `docs/research/predictive-maintenance-dataset-matrix.md`

- [ ] **Step 1: 创建数据集矩阵骨架**

Create:

```markdown
# 预测性维护与设备健康数据集矩阵

## 目的
## 数据筛选原则
## 第一批候选数据集
## 与 FU13 的关系
## 统一 schema 映射问题
## 训练与评测用途
## 许可证和下载风险
```

- [ ] **Step 2: 写入数据筛选原则**

Use:

```markdown
优先选择预测性维护、设备健康、RUL、故障诊断和退化过程数据。暂不优先纳入金融、交通、天气、电力负荷等通用时间序列数据。
```

- [ ] **Step 3: 填写候选数据集表**

Include:

```markdown
| 数据集 | 类型 | 标签 | B08 用途 | 初始优先级 |
| --- | --- | --- | --- | --- |
| FU13 | 真机设备数据 | quality_flag、stage、failure_proxy 弱标签 | 真实设备 pipeline、第一真机样例 | 最高 |
| NASA C-MAPSS | 涡扇发动机退化 | RUL / run-to-failure | RUL 和退化趋势评测 | 高 |
| NASA IMS Bearing | 轴承退化 | 故障过程 | 设备健康和退化异常候选 | 高 |
| PRONOSTIA / FEMTO-ST | 轴承加速退化 | RUL / run-to-failure | 小样本 RUL 和退化预测 | 高 |
| Tennessee Eastman Process | 工业过程故障诊断 | 故障类型 | 多变量过程异常和分类 | 中高 |
```

- [ ] **Step 4: 写入 schema 映射问题**

List:

```markdown
- timestamp
- device_id
- batch_id / run_id
- stage 或 operating condition
- sensor_id
- value
- unit
- domain
- quality_flag
- degradation_label
- failure_proxy
- RUL / maintenance_event if available
```

- [ ] **Step 5: 写入训练用途**

Use:

```markdown
FU13 用于验证真实工业设备 pipeline 和弱标签任务；开源 run-to-failure 数据用于补足 RUL、故障分类和退化趋势；模拟或退化注入数据只作为弱标签和冷启动补充，不作为第一证据。
```

- [ ] **Step 6: 验证数据集覆盖**

Run:

```bash
rg -n "FU13|C-MAPSS|IMS|PRONOSTIA|FEMTO|Tennessee|RUL|schema|quality_flag" docs/research/predictive-maintenance-dataset-matrix.md
```

Expected:

- All candidate datasets and schema fields appear.

- [ ] **Step 7: Commit**

Run:

```bash
git add docs/research/predictive-maintenance-dataset-matrix.md
git commit -m "docs: add predictive maintenance dataset matrix"
```

Expected:

- Commit contains only `docs/research/predictive-maintenance-dataset-matrix.md`.

## Task 7: 编写任务与指标矩阵

**Files:**
- Create: `docs/research/task-metric-matrix.md`

- [ ] **Step 1: 创建任务矩阵骨架**

Create:

```markdown
# 任务与指标矩阵

## 目的
## 三层任务结构
## 无标签任务
## 弱标签 / 业务代理任务
## 预测性维护目标任务
## FU13 当前支持情况
## 开源数据补充情况
## 进入 C / B 阶段的指标要求
```

- [ ] **Step 2: 写入三层任务结构**

Use:

```markdown
第一层是无标签可验证任务，第二层是弱标签或业务代理任务，第三层是预测性维护目标任务。当前 FU13 优先支持第一层和第二层，第三层需要开源 run-to-failure 数据、维修记录、停机记录或专家复核补充。
```

- [ ] **Step 3: 填写任务表**

Include:

```markdown
| 层级 | 任务 | 指标 | 当前 FU13 支持 | 开源数据支持 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 无标签 | forecasting | MAE、RMSE、coverage | 已支持 | 广泛支持 | TTM 已在 FU13 跑通 |
| 无标签 | imputation / reconstruction | MAE、mask reconstruction error | 待实现 | 部分支持 | 适合 MOMENT / UniTS / 自研预训练 |
| 无标签 | representation consistency | clustering、linear probe | 待实现 | 部分支持 | 支持状态表征主线 |
| 弱标签 | stage classification | accuracy、F1 | 可支持 | 视数据而定 | 验证工艺阶段表征 |
| 弱标签 | quality_flag prediction | accuracy、F1 | 可支持 | 视数据而定 | 验证质量标记语义 |
| 弱标签 | residual high-percentile detection | precision@k、expert review hit rate | 可支持 | 部分支持 | 对接候选异常信号 |
| 预测性维护 | fault classification | accuracy、F1、AUROC | 需标签 | 支持 | 依赖公开故障数据 |
| 预测性维护 | degradation trend / RUL | MAE、RMSE、lead-time metric | 需标签 | 支持 | 第三层目标 |
```

- [ ] **Step 4: 写入 C / B 指标要求**

Use:

```markdown
C 阶段要求每个开源模型在可支持任务上给出同口径指标或明确失败原因。B 阶段要求自研原型至少在一个 representation / imputation / weak-label 任务上显示相对 forecasting-only 模型的明确增益，否则不进入更大规模训练。
```

- [ ] **Step 5: 验证任务覆盖**

Run:

```bash
rg -n "forecasting|imputation|representation|stage classification|quality_flag|RUL|C 阶段|B 阶段" docs/research/task-metric-matrix.md
```

Expected:

- Three-layer task structure and C/B gates appear.

- [ ] **Step 6: Commit**

Run:

```bash
git add docs/research/task-metric-matrix.md
git commit -m "docs: add task metric matrix"
```

Expected:

- Commit contains only `docs/research/task-metric-matrix.md`.

## Task 8: 编写模型训练路线

**Files:**
- Create: `docs/research/foundation-model-training-route.md`

- [ ] **Step 1: 创建训练路线骨架**

Create:

```markdown
# 基础模型训练路线

## 定位
## 数据语料
## 输入结构
## 预训练任务
## 小样本适配任务
## 开源模型对照
## 最小自研原型
## Go / No-Go 条件
## 工程化产品承接
```

- [ ] **Step 2: 写入定位**

Use:

```markdown
训练路线用于把知识成果主线落到可验证实验。A 阶段不直接启动大规模训练，而是定义统一数据语料、预训练目标、小样本适配任务、对照模型和最小自研原型条件。
```

- [ ] **Step 3: 写入输入结构**

Include:

```markdown
device_id、sensor_id、physical_domain、process_stage、quality_flag、batch/cycle、sampling pattern、weak degradation/failure proxy
```

- [ ] **Step 4: 写入预训练任务**

Include:

```markdown
masked sensor reconstruction
next-window forecasting
cross-sensor imputation
stage-aware representation learning
contrastive normal/abnormal representation
residual / trend / spike candidate signal generation
```

- [ ] **Step 5: 写入最小自研原型条件**

Use:

```markdown
只有当 C 阶段证明 forecasting-first 模型无法覆盖设备状态表征、弱标签任务或预测性维护候选信号生成时，才进入最小自研原型。最小原型应优先验证结构感知 token、masked reconstruction、stage-aware representation 和 weak-label probing，而不是直接追求大模型规模。
```

- [ ] **Step 6: 写入工程化产品承接**

Include:

```markdown
工程化产品成果应沉淀为：统一数据语料构建命令、模型 adapter contract、训练/评测配置、报告模板、模型缓存策略和可复现 workflow。
```

- [ ] **Step 7: 验证训练路线关键词**

Run:

```bash
rg -n "预训练|小样本|Go / No-Go|结构感知|adapter contract|工程化产品|masked" docs/research/foundation-model-training-route.md
```

Expected:

- Training route supports both knowledge output and productization.

- [ ] **Step 8: Commit**

Run:

```bash
git add docs/research/foundation-model-training-route.md
git commit -m "docs: add foundation model training route"
```

Expected:

- Commit contains only `docs/research/foundation-model-training-route.md`.

## Task 9: 编写论文与专利方向

**Files:**
- Create: `docs/research/paper-patent-directions.md`

- [ ] **Step 1: 创建成果方向骨架**

Create:

```markdown
# 论文与专利方向

## 知识成果定位
## 论文方向
## 专利方向
## 数据集 / benchmark 成果
## 模型资产成果
## 优先级
## 风险与证据需求
```

- [ ] **Step 2: 写入论文方向**

Include:

```markdown
| 类型 | 题目占位 | 核心贡献 | 证据需求 |
| --- | --- | --- | --- |
| 框架与验证 | 面向小样本工业物联设备健康管理的时序基础模型框架与验证 | 问题定义、任务谱系、数据语料、开源模型缺口 | A 阶段综述、模型矩阵、数据矩阵 |
| 方法创新 | 阶段感知、多传感器、多任务工业设备时序基础模型 | 结构感知 token、多任务预训练、弱标签适配 | C/B 阶段实验结果 |
| benchmark | 真机与开源设备健康数据融合的工业时序基础模型评测基准 | FU13 + 开源数据统一 schema 和评测协议 | 数据映射和任务指标矩阵 |
```

- [ ] **Step 3: 写入专利方向**

Include:

```markdown
- 工艺阶段与传感器物理域联合编码方法。
- 工业设备小样本预测性维护的基础时序模型预训练方法。
- 无故障标签条件下的设备异常候选信号生成方法。
- 真机数据与开源设备健康数据融合的设备时序基础模型训练方法。
- 基于多任务输出的设备状态表征、预测残差和退化趋势联合评估方法。
```

- [ ] **Step 4: 写入优先级**

Use:

```markdown
第一优先级是框架与验证型论文和专利背景材料，因为它们能立即承接 A 阶段调研。第二优先级是方法创新型论文和核心算法专利，它们依赖 C/B 阶段实验结果。第三优先级是工程化模型资产和 benchmark 发布，它们依赖数据授权、复现稳定性和项目发布边界。
```

- [ ] **Step 5: 验证知识成果关键词**

Run:

```bash
rg -n "论文|专利|benchmark|工艺阶段|物理域|无故障标签|优先级" docs/research/paper-patent-directions.md
```

Expected:

- Knowledge output roadmap is explicit.

- [ ] **Step 6: Commit**

Run:

```bash
git add docs/research/paper-patent-directions.md
git commit -m "docs: add paper and patent directions"
```

Expected:

- Commit contains only `docs/research/paper-patent-directions.md`.

## Task 10: 编写工程化产品承接路线

**Files:**
- Create: `docs/research/productization-roadmap.md`

- [ ] **Step 1: 创建工程化路线骨架**

Create:

```markdown
# 工程化产品承接路线

## 定位
## 与知识成果的关系
## 产品化资产
## 当前已有工程基础
## 下一步工程化模块
## 不做事项
## Go / No-Go 条件
```

- [ ] **Step 2: 写入定位**

Use:

```markdown
工程化产品成果是 B08 的第二目标。它不抢占 A 阶段知识成果优先级，而是把论文、专利和模型路线沉淀为可复现、可扩展、可交付的模型研发工作台。
```

- [ ] **Step 3: 写入当前已有工程基础**

Include:

```markdown
- FU13 canonical observations pipeline。
- real-data assemble / diagnose / forecast / evaluate-scenario CLI。
- baseline 与 TTM 同口径 forecasting。
- `leak_current_monitoring` residual candidate signal 样例。
- uv + pytest 本地验证路径。
```

- [ ] **Step 4: 写入下一步工程化模块**

Include:

```markdown
- 开源数据集 schema mapper。
- 统一 dataset registry。
- 统一 adapter contract。
- 多任务 evaluation runner。
- research report renderer。
- model cache and dependency policy。
- experiment configuration templates。
```

- [ ] **Step 5: 写入不做事项**

State:

```markdown
A 阶段不开发生产告警系统、不做维修决策闭环、不承诺模型服务化部署。产品化承接只到研发工作台和模型评测/训练基础设施。
```

- [ ] **Step 6: 验证工程化关键词**

Run:

```bash
rg -n "工程化产品|工作台|adapter contract|dataset registry|production|告警|Go / No-Go" docs/research/productization-roadmap.md
```

Expected:

- Productization is second target and bounded.

- [ ] **Step 7: Commit**

Run:

```bash
git add docs/research/productization-roadmap.md
git commit -m "docs: add productization roadmap"
```

Expected:

- Commit contains only `docs/research/productization-roadmap.md`.

## Task 11: 重构项目入口叙事

**Files:**
- Modify: `README.md`
- Modify: `details.md`
- Modify: `docs/foundation-timeseries-research-roadmap.md`
- Modify: `docs/index.html`

- [ ] **Step 1: 更新 README 下一阶段路线**

Modify `README.md` so the next-stage section states:

```markdown
A 阶段短期第一目标是知识成果：凝练论文主线、专利方向、学术综述、开源模型论文矩阵、预测性维护数据矩阵和模型训练路线。第二目标是工程化产品成果：把研究主线沉淀为统一数据语料、模型 adapter、训练/评测 workflow 和可复现研发工作台。
```

Expected:

- Existing reproducible commands stay intact.
- README still describes FU13 pipeline and TTM/scenario evaluation as verified assets.

- [ ] **Step 2: 更新 details 阶段台账**

Add a recent update row:

```markdown
| 2026-06-04 | 认可 A 阶段学术主线 spec，并进入 writing-plans：下一阶段短期第一目标聚焦论文、专利、学术综述和模型路线等知识成果，第二目标承接统一数据语料、开源模型适配、训练评测 workflow 等工程化产品成果。 |
```

Expected:

- `details.md` captures the knowledge-first/product-second priority.

- [ ] **Step 3: 更新 research roadmap**

Modify `docs/foundation-timeseries-research-roadmap.md` to link the A-stage outputs:

```markdown
本阶段执行资产维护在 `docs/research/`。其中 `academic-mainline-review.md`、`paper-patent-directions.md` 服务知识成果优先线；`foundation-model-training-route.md` 和 `productization-roadmap.md` 服务工程化产品承接线。
```

- [ ] **Step 4: 更新 docs index**

Add cards or links for:

```text
docs/research/index.md
docs/research/project-mainline-refactor-blueprint.md
docs/research/academic-mainline-review.md
docs/research/open-source-model-paper-matrix.md
docs/research/predictive-maintenance-dataset-matrix.md
docs/research/foundation-model-training-route.md
docs/research/paper-patent-directions.md
docs/research/productization-roadmap.md
```

Expected:

- `docs/index.html` shows A 阶段研究资产 as a mainline route, not archive.

- [ ] **Step 5: 验证入口一致性**

Run:

```bash
rg -n "知识成果|工程化产品|docs/research|academic-mainline|paper-patent|productization" README.md details.md docs/foundation-timeseries-research-roadmap.md docs/index.html
```

Expected:

- All main entry docs point to the new A-stage research assets.

- [ ] **Step 6: Commit**

Run:

```bash
git add README.md details.md docs/foundation-timeseries-research-roadmap.md docs/index.html
git commit -m "docs: refocus project entry on academic mainline"
```

Expected:

- Commit contains only the four entry/navigation docs.

## Task 12: 主线必要重构审计与执行门

**Files:**
- Create: `docs/research/mainline-refactor-audit.md`
- Potentially modify after audit:
  - `src/b08_model_core/**`
  - `tests/**`
  - `configs/**`
  - `docs/superpowers/specs/*`
  - `docs/superpowers/plans/*`

- [ ] **Step 1: Create mainline refactor audit document**

Create `docs/research/mainline-refactor-audit.md`:

```markdown
# 主线必要重构审计

## 目的
## 判定原则
## 当前项目主线
## 需要立即解决的阻碍
## 可以后置但需记录的债务
## 不属于本阶段的债务
## 源码 / CLI / 配置 / 测试影响
## 是否需要代码重构
## 如果需要，重构子计划
## 验证要求
```

- [ ] **Step 2: Inspect source boundaries for mainline blockers**

Run:

```bash
find src/b08_model_core tests configs -maxdepth 3 -type f | sort
```

Expected:

- Identify where current pipeline, adapters, foundation runner, real-data flow, and tests live.
- This command is inspection only.

- [ ] **Step 3: Search for mainline-relevant modules**

Run:

```bash
rg -n "adapter|foundation|real-data|scenario|forecast|knowledge|paper|patent|dataset|schema|window|TTM|MOMENT|Chronos|TimesFM|Moirai|UniTS" src tests configs README.md details.md docs
```

Expected:

- Surface whether existing code already has natural seams for research assets, model adapters, dataset schema, and knowledge outputs.
- Do not edit during this step.

- [ ] **Step 4: Classify debt**

In `docs/research/mainline-refactor-audit.md`, classify each finding as:

```markdown
| Finding | Evidence | Impact on mainline | Decision | Required action |
| --- | --- | --- | --- | --- |
| ... | ... | blocks knowledge output / blocks productization / cosmetic only | fix now / document for later / ignore | ... |
```

Decision rules:

- `fix now`: The debt blocks A-stage knowledge outputs, model training route, open-source model comparison, unified data corpus, adapter workflow, or reproducible research handoff.
- `document for later`: The debt is real but does not block the current knowledge-first/product-second mainline.
- `ignore`: The issue is cosmetic, historical, or unrelated to the current mainline.

- [ ] **Step 5: Decide whether code refactor is required**

If no mainline blocker exists, write:

```markdown
当前没有发现必须在 A 阶段立即修改源码、CLI、配置或测试结构的主线阻碍。本阶段只执行研究资产和入口文档重构。
```

If one or more blockers exist, write:

```markdown
当前发现以下主线阻碍必须在 A 阶段解决，不能作为历史债务推迟：
```

Then list exact files, affected commands, tests, and expected behavior.

- [ ] **Step 6: If code refactor is required, create a dedicated sub-spec and sub-plan before editing**

Create:

```text
docs/superpowers/specs/YYYY-MM-DD-academic-mainline-code-refactor-design.md
docs/superpowers/plans/YYYY-MM-DD-academic-mainline-code-refactor-plan.md
```

The sub-plan must include:

- Exact source files to modify.
- Exact tests to add or update.
- Expected failing tests before implementation.
- Minimal implementation steps.
- Verification commands.
- Commit boundaries.

Expected:

- Do not modify `src/**`, `tests/**`, or `configs/**` until the sub-plan exists.
- Execute the code refactor sub-plan before continuing to cross-document consistency.

- [ ] **Step 7: If code refactor is not required, commit audit only**

Run:

```bash
git add docs/research/mainline-refactor-audit.md
git commit -m "docs: audit mainline refactor scope"
```

Expected:

- Commit contains only `docs/research/mainline-refactor-audit.md`.

- [ ] **Step 8: If code refactor was executed, verify and commit according to the sub-plan**

Run the verification commands defined in the sub-plan.

Expected:

- Code changes are limited to mainline blockers.
- Tests covering changed behavior pass.
- Research docs and project entry docs reflect the new structure.

## Task 13: Cross-document consistency pass

**Files:**
- Modify as needed:
  - `docs/research/*.md`
  - `README.md`
  - `details.md`
  - `docs/foundation-timeseries-research-roadmap.md`
  - `docs/index.html`

- [ ] **Step 1: Search for outdated framing**

Run:

```bash
rg -n "业务场景.*唯一|直接.*大规模训练|已经.*RUL|生产告警|维修建议|项目终点" README.md details.md docs/foundation-timeseries-research-roadmap.md docs/index.html docs/research
```

Expected:

- Any occurrence is either a boundary statement or needs correction.

- [ ] **Step 2: Search for required new framing**

Run:

```bash
rg -n "知识成果|工程化产品|小样本工业物联|预测性维护|时序基础模型|A -> C -> B|Go / No-Go" README.md details.md docs/foundation-timeseries-research-roadmap.md docs/index.html docs/research
```

Expected:

- Required framing appears across entry docs and research docs.

- [ ] **Step 3: Fix inconsistencies surgically**

Edit the smallest conflicting paragraph only.

Expected:

- No unrelated formatting churn.
- No code changes.

- [ ] **Step 4: Commit if changed**

Run:

```bash
git add README.md details.md docs/foundation-timeseries-research-roadmap.md docs/index.html docs/research
git commit -m "docs: align academic mainline language"
```

Expected:

- Commit only if Step 3 made changes.

## Task 14: Final verification and handoff

**Files:**
- Read/inspect via command output only:
  - all modified docs
  - git status

- [ ] **Step 1: Verify research docs exist**

Run:

```bash
find docs/research -maxdepth 1 -type f | sort
```

Expected:

```text
docs/research/academic-mainline-review.md
docs/research/foundation-model-training-route.md
docs/research/index.md
docs/research/open-source-model-paper-matrix.md
docs/research/paper-patent-directions.md
docs/research/predictive-maintenance-dataset-matrix.md
docs/research/productization-roadmap.md
docs/research/project-mainline-refactor-blueprint.md
docs/research/task-metric-matrix.md
```

- [ ] **Step 2: Verify knowledge-first/product-second framing**

Run:

```bash
rg -n "第一目标.*知识成果|第二目标.*工程化产品|知识成果优先|工程化产品承接" README.md details.md docs/research docs/foundation-timeseries-research-roadmap.md
```

Expected:

- The priority appears in project entry and research docs.

- [ ] **Step 3: Verify source code changes match audit decision**

Run:

```bash
git diff --name-only HEAD -- src tests configs
```

Expected:

- If Task 12 decided no code refactor was required, no output.
- If Task 12 executed a code refactor sub-plan, output contains only files approved by `docs/research/mainline-refactor-audit.md` and the dedicated code-refactor plan.

- [ ] **Step 4: Optional repository regression**

Run only if the executor or user wants regression evidence after docs-only changes:

```bash
uv run python -m pytest -q
```

Expected:

- Tests pass.
- If skipped because this is docs-only, state explicitly that tests were not run.

- [ ] **Step 5: Whitespace check**

Run:

```bash
git diff --check
```

Expected:

- No output.

- [ ] **Step 6: Verify worktree status**

Run:

```bash
git status --short --ignored
```

Expected:

- No unintended tracked modifications.
- Ignored local data/cache/report artifacts remain ignored.

- [ ] **Step 7: Handoff**

Report:

- Files created.
- Files modified.
- Commits made.
- Verification commands and results.
- Any skipped tests and reason.
- Recommended next step: execute plan with `superpowers:subagent-driven-development` or `superpowers:executing-plans`.
