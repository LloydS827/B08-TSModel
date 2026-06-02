# TTM 标准流程与真实数据能力复核设计

## 背景

FU13 真实数据闭环已经跑通：现场导出的多 CSV 数据可以装配为 canonical observation 数据，生成数据诊断报告，并在真实窗口上完成 baseline 与 TTM 的同口径 forecasting 验证。

当前核心任务不是马上横向比较更多模型，而是先把现有 data pipeline 和 TTM 验证链路整理成标准流程。完成这一步之后，再进入模型选择、评测扩展、微调或训练会更稳。

## 目标

本阶段要回答两个问题：

1. TTM 在当前 FU13 真实数据上已经证明了什么、还没有证明什么。
2. 一个内部研发人员如何使用本项目完成从真实数据到 baseline/TTM 报告的标准开发流程。

交付物包括：

- 更新 `README.md`，让它成为以内部研发人员为主、兼顾项目管理者和现场数据方的项目使用入口。
- 新增独立报告 `docs/ttm-real-data-evaluation.md`，沉淀 TTM 真实数据能力复核、边界和下一阶段任务。
- 轻量复跑 TTM 相关评测，补充当前 `max-windows=40` 以外的窗口规模敏感性证据。

## 非目标

本阶段不做以下事情：

- 不接入 TimesFM、Chronos、Moirai、FlowState 等新模型。
- 不训练或微调 TTM。
- 不把 TTM forecasting 结果解释为真实故障预测、RUL、风险概率或维护建议。
- 不实现完整的 scenario 过滤建窗、等待态过滤或质量标记过滤框架。
- 不提交 `data/real/`、生成 parquet、实验报告或模型 cache。

## 读者

README 的主读者是内部研发人员。他们需要知道如何复现实验、修改配置、阅读报告，并据此开展下一阶段模型开发。

README 也需要兼顾：

- 项目/课题管理者：能够看懂项目当前跑通了什么、还没有证明什么、下一阶段为什么先做评测口径固化。
- 现场/数据提供方：能够知道真实数据应放在哪里、原始数据不会进入 Git，以及数据质量报告能反馈哪些问题。

## 当前事实基础

设计基于 `codex/real-data-validation-loop` 分支上的当前状态：

- FU13 真实数据装配：4,126,789 行 canonical observations。
- 传感器覆盖：8 个传感器。
- 工艺阶段覆盖：8 个阶段。
- cycle 重构：428 个 cycle，其中 247 个完整 cycle。
- 数据质量：`good`、`unassigned_cycle`、`invalid` 三类主要质量标记。
- baseline/TTM 真实窗口验证：`cross-stage`、`context_length=90`、`prediction_length=16`、`max-windows=40`。
- TTM 状态：`available_and_ran`。
- 真实数据、生成 parquet、本阶段生成的临时评测 reports 和模型 cache 均保持本机忽略。

当前 `max-windows=40` 结果显示：

- TTM 整体 MAE/RMSE 优于两个 baseline。
- TTM 在 `atmosphere_detection` 和 `leak_current_monitoring` 上表现明显优于 robust fallback。
- `pump_vibration` 和 `hydraulic_system_detection` 的结果需要谨慎解释，因为量纲、数值范围、等待态和质量标记都会影响窗口误差。

## TTM 复核设计

### 复核问题

TTM 复核不是为了宣布模型可用于生产，而是为了形成模型开发前的证据边界。

需要复核：

- TTM 是否能用本机 cache 离线复跑。
- TTM 相比 baseline 的优势是否在当前窗口构建顺序下的 first-N 窗口规模变化中仍然可见。
- 按传感器和 scenario 拆分后，哪些指标稳定、哪些指标受数据质量或窗口选择影响较大。
- 当前评测还能不能支持下一阶段进入模型开发。

### 评测配置

标准配置：

```bash
--window-mode cross-stage
--context-length 90
--prediction-length 16
--max-windows 40
```

轻量补充配置：

```bash
--max-windows 20
--max-windows 80
```

这里的 `max-windows=20/40/80` 不是随机抽样，也不是生产稳健性检验。当前实现会按窗口构建顺序取前 N 个窗口，因此这是 first-N 嵌套窗口规模敏感性证据，用于发现明显口径问题，不用于声称统计稳定性。

如果 `max-windows=80` 因窗口数量、运行时间或 TTM 资源问题失败，报告应记录失败原因，不把失败视为成功。

### 复现实验命令模板

每个窗口规模都应同时跑 baseline 和 TTM。下面以 `N=20` 为例，`40` 和 `80` 只替换 `--max-windows` 与输出文件名。

baseline：

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

TTM 离线 cache：

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

### 输出报告

每次复跑仍输出本机 ignored report，例如：

```text
reports/real_baseline_forecasting_w20.md
reports/real_ttm_forecasting_w20.md
reports/real_baseline_forecasting_w40.md
reports/real_ttm_forecasting_w40.md
reports/real_baseline_forecasting_w80.md
reports/real_ttm_forecasting_w80.md
```

这些报告只作为本地证据，不提交 Git。

提交 Git 的是整理后的 `docs/ttm-real-data-evaluation.md`。该报告应直接汇总 w20/w40/w80 的 baseline 与 TTM 关键指标表，并引用本地 ignored reports 的文件名作为复核来源；不要求把本地 reports 原文提交。

## README 信息架构

`README.md` 应从项目背景长文调整为开发者入口。

建议结构：

1. 当前阶段一句话。
2. 使用本项目的标准流程。
3. 环境准备。
4. 真实数据放置和安全边界。
5. FU13 数据装配命令。
6. 数据诊断命令。
7. baseline forecasting 命令。
8. TTM forecasting 命令。
9. 如何阅读报告。
10. TTM 当前评测结论摘要。
11. 哪些结论不能下。
12. 下一阶段模型开发任务。
13. 文档入口和维护规则。

README 中只放必要指标和结论摘要，避免把 README 写成完整评测论文。完整评测放在独立报告。

## TTM 评测报告信息架构

新增 `docs/ttm-real-data-evaluation.md`。

建议结构：

1. 评测目标。
2. 数据和窗口。
3. 复现实验命令。
4. 整体指标结果。
5. 传感器指标结果。
6. scenario 指标结果。
7. 能力判断。
8. 边界与风险。
9. 下一阶段模型开发任务。

报告要明确：

- 这是真实数据 forecasting 能力复核，不是故障预测验收。
- TTM 当前可以作为后续模型开发的重要候选，但还不能直接代表生产级预测性维护能力。
- 下一阶段优先事项是窗口质量治理、scenario 过滤建窗、等待态处理、质量标记过滤和更强 baseline，而不是马上堆更多模型名字。

## 数据流

标准使用流程如下：

```text
data/real/
  -> real-data assemble-fu13
  -> data/processed/fu13_real_observations.parquet
  -> real-data diagnose-fu13
  -> reports/real_scenario_diagnostics.md
  -> real-data forecast-fu13 --model baseline
  -> reports/real_baseline_forecasting*.md
  -> real-data forecast-fu13 --model ttm
  -> reports/real_ttm_forecasting*.md
  -> docs/ttm-real-data-evaluation.md
```

`data/real/`、`data/processed/*.parquet`、`hf_cache/` 和本阶段生成的 `reports/real_*forecasting*.md`、`reports/real_*diagnostics*.md` 等本地实验报告都应保持 ignored。仓库已有白名单报告，例如 `reports/model_core_evaluation.md` 和 `reports/model_route_decision.md`，不属于本阶段临时报告。

## 错误处理与边界说明

README 和评测报告都要说明：

- `schema_valid=True` 只代表 canonical schema 验证通过，不代表数据质量完美。
- `available_and_ran` 只代表 TTM 依赖、权重和推理链路成功运行，不代表模型可用于告警。
- `unassigned_cycle` 和 `invalid` 是后续数据治理重点。
- 当前 scenario 是指标分组，不是单场景过滤建窗。
- 当前等待态仍可能进入 cross-stage 窗口，是否剔除是下一阶段任务。
- 缺少真实故障标签和维修记录时，不能给出故障概率、RUL 或维护建议。

## 测试与验证

实施阶段需要完成：

- 复跑 baseline/TTM 标准配置。
- 复跑 `max-windows=20` 和 `max-windows=80`，或记录明确失败原因。
- 在独立评测报告中说明 `max-windows` 敏感性是 first-N 嵌套窗口比较，不是随机抽样稳定性检验。
- 运行相关测试：

```bash
uv run python -m pytest tests/test_real_data_forecasting.py tests/test_cli_fu13_real_data.py -q
```

- 运行全量测试：

```bash
uv run python -m pytest -q
```

- 检查 Git 状态，确保真实数据和本地报告没有被 staged。

## 成功标准

本阶段完成时应满足：

- `README.md` 能让内部研发人员按步骤复现完整真实数据 pipeline 和 TTM 评测。
- `docs/ttm-real-data-evaluation.md` 清楚总结 TTM 当前能力、指标证据、边界和下一阶段任务。
- TTM 至少在标准配置上离线 cache 复跑成功。
- 窗口规模敏感性结果被记录；如果某个规模失败，失败原因被记录。
- 文档没有把 forecasting 结果夸大为故障预测、RUL 或维护建议。
- 全量测试通过。
- Git 不包含真实原始数据、生成 parquet、本阶段临时 reports 或模型 cache；仓库白名单报告例外仍可保留。
