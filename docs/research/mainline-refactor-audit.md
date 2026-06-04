# 主线必要重构审计

## 目的

本审计用于给 B08 项目主线建立“是否需要立即代码重构”的执行门。用户已经明确要求：为了确立项目主线，必要重构不能作为模糊债务后置；但代码重构必须满足证据、验证、回滚路径，不做泛化清理。

本任务只做审计，不执行源码、CLI、配置或测试重构。当前文件是 A 阶段研究资产的一部分，用于记录哪些问题必须现在处理，哪些问题进入后续 C/B 阶段或具体工程模块实现前的子 spec/plan。

本次只读检查已执行：

```bash
find src/b08_model_core tests configs -maxdepth 3 -type f | sort
```

```bash
rg -n "adapter|foundation|real-data|scenario|forecast|knowledge|paper|patent|dataset|schema|window|TTM|MOMENT|Chronos|TimesFM|Moirai|UniTS" src tests configs README.md details.md docs
```

## 判定原则

本审计采用以下三类决策：

| Decision | 判定口径 |
| --- | --- |
| `fix now` | 该债务阻碍 A 阶段知识成果、模型训练路线、开源模型比较、统一数据语料、adapter workflow、可复现研究交接或工程化产品承接，并且有可引用证据、验证路径和回滚边界。 |
| `document for later` | 债务真实存在，但不阻碍当前知识成果第一目标或工程化产品第二目标。 |
| `ignore` | 美观、历史、缓存、生成物或与当前主线无关的问题。 |

代码重构的进入条件必须同时满足：

1. 有明确阻碍证据，且该阻碍影响当前主线交付，而不是一般清理偏好。
2. 能指出精确文件、预期行为、需要新增或修改的测试。
3. 有可执行验证路径和可接受的回滚边界。
4. 不与当前任务边界冲突；本任务不得实际修改源码、CLI、配置或测试。

## 当前项目主线

当前主线是 A -> C -> B：

| 阶段 | 当前含义 | 仓库证据 |
| --- | --- | --- |
| A | 短期第一目标是知识成果：论文主线、专利方向、学术综述、开源模型论文矩阵、预测性维护数据矩阵和模型训练路线。 | `README.md:218` 说明 A 阶段第一目标是知识成果，第二目标是工程化产品承接。 |
| C | 系统验证开源 foundation models，在同一批设备窗口、指标和报告口径下比较 TTM、MOMENT、Chronos、TimesFM、Moirai、UniTS 等候选模型。 | `README.md:222` 和 `details.md:193` 均指出还需系统适配并比较更多开源模型。 |
| B | 基于 A/C 证据，再决定是否进入自研设备时序基础模型训练方案设计。 | `details.md:322` 说明下一步应先补学术/行业/模型路线调研，再系统适配开源模型，最后判断是否进入自研训练方案设计。 |

现有工程主线基础设施已经包括：

| 能力 | 只读检查证据 | 当前判断 |
| --- | --- | --- |
| 真实数据 pipeline | `src/b08_model_core/real_data/*.py`、`configs/fu13_real_data_schema.yaml`、`configs/real_data_schema_map.template.yaml`、`tests/test_fu13_loader.py`、`tests/test_real_data_forecasting.py`、`tests/test_scenario_evaluation.py`。 | 已能承接 A 阶段关于统一数据语料、数据矩阵和训练路线的研究表达；后续 C/B 扩展再按具体 spec 进入代码修改。 |
| 窗口与 schema | `src/b08_model_core/tasks/schema.py`、`src/b08_model_core/tasks/window_builder.py`、`tests/test_simulation_schema.py`、`tests/test_window_builder.py`。 | 已有 canonical schema 与 window builder 基础，不构成 A 阶段阻碍。 |
| foundation / adapter workflow | `src/b08_model_core/foundation/*.py`、`src/b08_model_core/adapters/base.py`、`chronos_adapter.py`、`moment_adapter.py`、`timesfm_adapter.py`、`ttm_adapter.py`、`tests/test_foundation_runner.py`、`tests/test_foundation_results.py`、`tests/test_ttm_adapter.py`。 | 已有 adapter/foundation 骨架与 TTM 真实链路；多模型 adapter 完整验证属于 C 阶段工程扩展，不应在 A 阶段泛化重构。 |
| knowledge outputs | `src/b08_model_core/knowledge/paper_candidates.py`、`src/b08_model_core/knowledge/patent_candidates.py`、`tests/test_knowledge_outputs.py`。 | 已有知识候选输出入口，可承接 A 阶段研究资产；不需要立即源码重构。 |
| CLI 入口 | `src/b08_model_core/cli.py`、`tests/test_cli_real_data_validate.py`、`tests/test_cli_fu13_real_data.py`、`tests/test_cli_simulate.py`；README 记录 `real-data assemble-fu13`、`diagnose-fu13`、`forecast-fu13`、`evaluate-scenario`。 | 未发现必须立即修改 CLI 的主线阻碍。 |

## 需要立即解决的阻碍

当前没有发现必须在 A 阶段立即修改源码、CLI、配置或测试结构的主线阻碍。本阶段只执行研究资产和入口文档重构；源码级重构进入后续 C/B 阶段或具体工程模块实现前的子 spec/plan。

本次唯一需要立即补齐的是“主线必要重构审计与执行门”本身，即当前文档。它不是代码重构，而是防止后续把必要重构模糊后置，或反过来把泛化清理伪装成主线阻碍。

| Finding | Evidence | Impact on mainline | Decision | Required action |
| --- | --- | --- | --- | --- |
| 缺少本次 Task 12 要求的主线必要重构执行门。 | 用户任务明确要求创建 `docs/research/mainline-refactor-audit.md`，并要求判断是否需要立即代码重构。 | 若不记录，后续可能把“必要重构”变成模糊债务，影响 A -> C -> B 主线排序。 | `fix now` | 创建本审计文档；不执行代码重构。 |
| A -> C -> B 主线已经在入口文档中明确，当前审计应服务该主线而不是替代该主线。 | `README.md:218`、`README.md:222`、`details.md:322`。 | 主线清晰，审计重点应是是否有阻碍该主线的工程结构问题。 | `ignore` | 不修改 README/details；以本 research 文档记录门控结论。 |
| adapter/foundation/real_data/knowledge 模块已经存在，可承接 A 阶段文档路线。 | `find` 输出包含 `src/b08_model_core/adapters/`、`foundation/`、`real_data/`、`knowledge/`；测试包含 `test_foundation_*`、`test_real_data_*`、`test_knowledge_outputs.py`。 | 不阻碍 A 阶段知识成果、模型训练路线和研究交接。 | `ignore` | 不做立即源码重构；后续按 C/B 具体 spec 验证扩展。 |
| 多模型 adapter 比较尚未完全工程化验证。 | `README.md:222` 和 `details.md:193` 指出仍需比较 MOMENT、Chronos、TimesFM、Moirai、UniTS 等；`find` 显示 adapter 文件已存在，但测试结构中明确可见的 adapter 专项测试主要是 `tests/test_ttm_adapter.py`。 | 会影响 C 阶段系统开源模型比较，但不阻碍 A 阶段先完成知识成果和路线判断。 | `document for later` | C 阶段前创建独立 `docs/research/open-source-adapter-comparison-plan.md` 或 code-refactor spec，明确模型、窗口形状、依赖、失败状态和测试矩阵。 |
| 当前未发现必须立即修改 CLI 的主线阻碍。 | README 已记录 `real-data assemble-fu13`、`diagnose-fu13`、`forecast-fu13`、`evaluate-scenario`；`find` 显示 `src/b08_model_core/cli.py` 及 `tests/test_cli_real_data_validate.py`、`tests/test_cli_fu13_real_data.py`、`tests/test_cli_simulate.py`。 | CLI 已能表达当前真实数据、forecasting 和 scenario 验证链路，不阻碍 A 阶段。 | `ignore` | 不修改 CLI；若 C 阶段新增模型 adapter，再由具体 CLI spec 决定是否扩展命令参数。 |
| 当前未发现必须立即修改 tests/configs 的主线阻碍。 | `find` 显示 `configs/fu13_real_data_schema.yaml`、`configs/real_data_schema_map.template.yaml` 及真实数据、foundation、window、schema、knowledge 等测试文件。 | 配置与测试结构覆盖当前工作台主链路；A 阶段不需要结构性测试/配置重构。 | `ignore` | 不修改测试或配置；未来代码重构必须先写明新增/修改测试。 |
| `.DS_Store` 和 `__pycache__` 生成/缓存痕迹存在。 | `find` 输出包含 `src/b08_model_core/.DS_Store`、多处 `__pycache__/*.pyc`、`tests/__pycache__/*.pyc`；本次指定 `find` 范围未显示 egg-info。 | 属于生成/缓存痕迹，不阻碍 A 阶段知识成果或 C/B 工程承接。 | `ignore` | 本任务不删除；如后续仓库卫生任务处理，应单独提出清理范围和回滚边界。 |
| `docs/research/` 是当前执行资产，不应被误判为债务。 | 用户任务明确要求在 `docs/research/` 创建本审计文档；`rg` 范围包含 docs，用于主线研究资产检索。 | research 文档是 A 阶段知识成果和交接资产的一部分。 | `ignore` | 保留并继续按任务创建 research 文档；不清理其他 research 文档。 |

## 可以后置但需记录的债务

以下债务真实存在或很可能会在 C/B 阶段显性化，但不应在 A 阶段立即改代码：

| 债务 | 后置原因 | 触发重构的条件 |
| --- | --- | --- |
| 多模型 adapter 合同与测试矩阵需要完整化。 | 当前 A 阶段第一目标是知识成果与路线判断；已有 adapter/foundation 骨架和 TTM 链路足够支撑研究表达。 | C 阶段开始系统比较 MOMENT、Chronos、TimesFM、Moirai、UniTS 等模型时，若出现窗口形状、依赖、输出 schema 或失败状态不一致，必须创建 code-refactor spec/plan。 |
| scenario 评测从验证样例扩展到多业务场景时，可能需要更明确的 scenario contract。 | 当前 `leak_current_monitoring` 是验证样例，不是产品化告警闭环；A 阶段不依赖更多场景代码。 | 当 C/B 阶段要求多个场景共享同一 residual、embedding、anomaly response 或 RUL 输出口径时，再定义 scenario contract 与测试。 |
| 统一数据语料可能需要跨设备、跨产线 schema 扩展。 | 当前 FU13 pipeline 已能支持 A 阶段数据矩阵和训练路线讨论；没有证据显示必须现在改 schema/config。 | 当引入非 FU13 数据、维修记录、停机事件、寿命标签或跨设备字段时，再提出 schema/config 迁移计划。 |
| 生成/缓存文件的仓库卫生治理。 | `.DS_Store`、`__pycache__` 不影响当前主线判断；删除行为不属于本任务。 | 后续若要清理仓库卫生，应单独开 housekeeping 任务，只处理生成物并确认不会误删研究资产。 |

## 不属于本阶段的债务

以下事项不进入 A 阶段重构：

| 项目 | 原因 |
| --- | --- |
| 为美观统一目录命名、注释风格或代码排版。 | 属于泛化清理，不能证明阻碍主线。 |
| 删除历史计划、执行记录或 research 文档。 | `docs/research/` 和既有计划文档是当前研究交接资产，不应被误判为债务。 |
| 把所有开源模型 adapter 一次性抽象为更复杂框架。 | 在 C 阶段模型和任务矩阵没有完全确定前，过早抽象会增加风险。 |
| 把当前 scenario 样例提升为生产告警系统。 | README 和 details 已明确当前不能推出故障概率、RUL、维护建议或生产告警能力。 |
| 清理 `.DS_Store`、`__pycache__` 等生成/缓存痕迹。 | 本任务边界禁止修改除本文件外的其他文件；这些痕迹也不阻碍主线。 |

## 源码 / CLI / 配置 / 测试影响

| 范围 | 当前影响 | 是否需要立即修改 |
| --- | --- | --- |
| 源码 | 现有 `adapters`、`foundation`、`real_data`、`knowledge`、`tasks` 模块能支撑 A 阶段研究路线描述和已有真实数据/TTM 工作台证据。 | 否 |
| CLI | README 已有真实数据装配、诊断、forecasting、scenario 评测入口；测试结构中有 CLI 覆盖。 | 否 |
| 配置 | FU13 真实数据 schema 与 schema map template 已存在，可支撑当前真实数据语料描述。 | 否 |
| 测试 | 已有 foundation、TTM adapter、real_data、scenario、schema/window、knowledge 等测试文件；本任务不运行测试。 | 否 |
| 文档 | 本任务只新增当前审计文档；不修改 README、details、docs/index 或其他 research 文档。 | 仅新增本文件 |

## 是否需要代码重构

不需要立即代码重构。

当前没有发现必须在 A 阶段立即修改源码、CLI、配置或测试结构的主线阻碍。本阶段只执行研究资产和入口文档重构；源码级重构进入后续 C/B 阶段或具体工程模块实现前的子 spec/plan。

判断依据：

1. A 阶段第一目标是知识成果和路线判断，当前已有 `knowledge` 入口、研究文档资产、真实数据 pipeline、TTM/baseline 证据和 adapter/foundation 骨架可支撑表达。
2. C 阶段多模型 adapter 比较尚未完全工程化，但这是下一阶段需要验证和扩展的对象，不是 A 阶段立即修改代码的阻碍。
3. CLI、tests、configs 均已有当前主线所需入口或覆盖迹象；没有证据表明必须现在改结构才能完成 A 阶段交接。
4. 生成/缓存痕迹不影响主线，不应转化为本阶段代码清理任务。

## 如果需要，重构子计划

当前不需要创建代码重构子计划。

若后续 C/B 阶段触发代码重构，建议先创建独立子计划文件，例如：

| 建议文件名 | 触发条件 | 必须写清 |
| --- | --- | --- |
| `docs/research/open-source-adapter-code-refactor-plan.md` | 多模型 adapter 系统比较开始前，发现现有 adapter contract 无法统一表达模型输入、输出、失败状态或依赖约束。 | 精确文件、阻碍证据、预期行为、新增/修改测试、验证命令、回滚路径。 |
| `docs/research/real-data-schema-extension-plan.md` | 引入非 FU13 数据、维修记录、停机事件、寿命标签或跨设备训练语料时，现有 schema/config 无法承接。 | schema 迁移边界、兼容旧配置的策略、fixture 更新、CLI 验证路径。 |
| `docs/research/scenario-contract-refactor-plan.md` | 从单一 `leak_current_monitoring` 样例扩展到多个业务场景，且需要共享 residual、embedding、anomaly response 或 RUL 输出口径。 | 场景 contract、评测指标、报告字段、测试样例、回滚边界。 |

任一代码重构子计划不得以“清理”“统一风格”“未来灵活性”为理由启动，必须绑定当前主线阻碍。

## 验证要求

本审计任务的验证边界：

| 类型 | 要求 |
| --- | --- |
| 当前任务 | 只确认 `docs/research/mainline-refactor-audit.md` 存在并包含本任务要求结构、审计表和关键结论。 |
| 本任务禁止项 | 不运行测试；不使用 git；不修改源码、CLI、配置、README、details、docs/index、其他 research 文档或其他文件。 |
| 后续 research 文档 | 应由人工或后续文档任务检查与 README/details 主线一致性。 |
| 后续代码重构 | 必须先有 code-refactor spec/plan，写明精确文件、阻碍证据、预期行为、新增/修改测试、验证命令和回滚路径。 |
| 后续验证命令 | 根据改动范围选择最小验证，例如 adapter 改动运行对应 adapter/foundation 测试，schema 改动运行 schema/window/real_data 测试，CLI 改动运行对应 CLI 测试。 |

如果未来判断需要代码重构，最低验证门槛是：

1. 新增或修改能复现阻碍的测试。
2. 实现最小代码改动，不做泛化清理。
3. 运行与改动范围匹配的测试命令并记录结果。
4. 明确回滚边界，确保默认项目路径仍可安装、运行和交接。
