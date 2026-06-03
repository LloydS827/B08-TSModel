# TTM 真实数据能力复核报告

## 评测目标

本报告是 FU13 真实数据 pipeline 跑通后的 TTM forecasting 能力复核，用于回答 TTM 作为第一批时序基础模型候选，在当前真实窗口构造口径下能否离线运行、能否输出可比较的数值预测结果，以及这些结果能支持下一阶段哪些模型开发工作。

本报告不是故障预测验收，也不是异常检测或预测性维护验收。当前证据只能说明 constructed windows 上的数值 forecasting 表现，不能推出 RUL 或维护建议，也不能推出故障概率。

本报告汇总以下本地 ignored reports 的关键值，不提交这些本地报告原文：

- `reports/real_data_validation.md`
- `reports/real_scenario_diagnostics.md`
- `reports/real_baseline_forecasting_w20.md`
- `reports/real_ttm_forecasting_w20.md`
- `reports/real_baseline_forecasting_w40.md`
- `reports/real_ttm_forecasting_w40.md`
- `reports/real_baseline_forecasting_w80.md`
- `reports/real_ttm_forecasting_w80.md`

## 数据与窗口

FU13 真实数据已经装配为 canonical observation 数据，并通过 schema 验证。`schema_valid=True` 只代表 canonical schema 验证通过，不代表数据质量完美。

| 项目 | 实际值 |
| --- | --- |
| observations | 4,126,789 |
| sensors | 8 |
| stages | 8 |
| reconstructed cycles | 428 |
| complete cycles | 247 |
| partial cycles | 181 |
| `good` rows | 3,391,823 |
| `unassigned_cycle` rows | 529,790 |
| `invalid` rows | 205,176 |

当前窗口配置为 `window_mode=cross-stage`、`context_length=90`、`prediction_length=16`。`max-windows=20/40/80` 使用当前窗口构造顺序下的 first-N 嵌套窗口：w20 是前 20 个窗口，w40 是前 40 个窗口，w80 是前 80 个窗口。它不是随机抽样，也不是统计稳健性检验，只能作为轻量窗口规模敏感性证据。

本次 first-N 切分采用当前 CLI 的顺序切分口径，训练/测试窗口数分别为：

| max_windows | train_windows | test_windows |
| --- | ---: | ---: |
| 20 | 14 | 6 |
| 40 | 28 | 12 |
| 80 | 56 | 24 |

场景诊断中的行数与 invalid 行数如下。这里的 scenario 是指标分组，不是 scenario 过滤建窗。

| scenario | rows | invalid_rows |
| --- | ---: | ---: |
| atmosphere_detection | 1,034,358 | 4,180 |
| hydraulic_system_detection | 1,552,151 | 195,833 |
| leak_current_monitoring | 517,177 | 4,886 |
| pump_vibration | 1,023,103 | 277 |

## 复现实验命令

先安装 TTM optional 依赖：

```bash
uv sync --extra dev --extra foundation-ttm
```

baseline w20 命令如下。复跑 w40/w80 时，将 `--max-windows 20` 与输出文件名中的 `w20` 分别替换为 `40`/`w40` 或 `80`/`w80`。

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

TTM 离线 cache w20 命令如下。复跑 w40/w80 时，将 `--max-windows 20` 与输出文件名中的 `w20` 分别替换为 `40`/`w40` 或 `80`/`w80`。

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

本次 TTM 运行有一个非阻塞行为需要记录：请求的 `prediction_length=16` 使用底层 TTM 30-step 输出中的 `prediction_filter_length` 取所需预测长度。该行为不改变本次本地报告状态，w20/w40/w80 均记录为 `available_and_ran`。

## 整体指标

整体指标来自同口径窗口上的 baseline 与 TTM reports。TTM 指标在本地报告中以 `foundation` 行输出。

| max_windows | train_windows | test_windows | robust_mae | robust_rmse | seasonal_mae | seasonal_rmse | ttm_status | ttm_mae | ttm_rmse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 20 | 14 | 6 | 0.916775 | 2.939051 | 1.469075 | 4.825605 | available_and_ran | 0.793907 | 2.882161 |
| 40 | 28 | 12 | 6.265136 | 11.216530 | 1.748390 | 4.266436 | available_and_ran | 0.479867 | 1.325608 |
| 80 | 56 | 24 | 2.469608 | 6.249011 | 0.444218 | 1.317205 | available_and_ran | 0.356300 | 1.111430 |

从 first-N 结果看，TTM 在 w20/w40/w80 的整体 MAE/RMSE 均低于 `RobustStageForecaster`；相对 `StageSeasonalNaiveForecaster`，TTM 在三组 first-N 窗口上也更低。但因为这些窗口不是随机抽样，不能把这三行结果解释为统计稳健性证明。

## 传感器指标

下表为标准 w40 运行的 TTM 传感器级 MAE/RMSE。w40 是当前标准配置，且本次状态为 `available_and_ran`。

| sensor | ttm_mae | ttm_rmse |
| --- | ---: | ---: |
| CrucibleForwardPressure | 0.000405 | 0.001510 |
| CrucibleReturnPressure | 0.000426 | 0.001508 |
| LeakElec | 1.329442 | 2.510613 |
| O2Content | 0.119336 | 0.300402 |
| O2Content2 | 0.083365 | 0.234334 |
| PumpShake1 | 1.521342 | 2.326539 |
| PumpShake2 | 0.783778 | 1.482148 |
| SysSelfPressure | 0.000844 | 0.003038 |

压力类传感器的绝对误差很小，但其量纲和数值范围也很小；LeakElec、PumpShake 等离散或振动相关信号的误差更高，需要结合质量标记、等待阶段和 scenario 过滤后再判断模型路线。

## 场景指标

下表汇总 w40 与 w80 的 TTM scenario 级 MAE/RMSE。scenario 级指标按传感器映射聚合，不代表每个 scenario 都独立过滤建窗或独立训练评测。

| max_windows | scenario | ttm_mae | ttm_rmse |
| --- | --- | ---: | ---: |
| 40 | hydraulic_system_detection | 0.000558 | 0.002144 |
| 40 | leak_current_monitoring | 1.329442 | 2.510613 |
| 40 | atmosphere_detection | 0.101351 | 0.269401 |
| 40 | pump_vibration | 1.152560 | 1.950583 |
| 80 | hydraulic_system_detection | 0.000749 | 0.002456 |
| 80 | leak_current_monitoring | 0.330011 | 0.443541 |
| 80 | atmosphere_detection | 0.078938 | 0.249974 |
| 80 | pump_vibration | 1.180132 | 2.186377 |

w40 中 TTM 在 `leak_current_monitoring`、`atmosphere_detection` 上显著压低了 robust fallback 的大误差；w80 中 `leak_current_monitoring` 进一步下降。不过 `hydraulic_system_detection` 的 invalid 行数最高，且等待态可能进入 cross-stage 窗口，因此这些场景指标更适合作为后续治理优先级，而不是最终业务结论。

## 能力判断

TTM 在当前工作流中可以从本机 cache 离线运行：w20/w40/w80 的依赖状态为 `installed`，权重状态为 `available`，TTM 状态为 `available_and_ran`。

TTM 是有意义的 forecasting 候选模型。当前最强证据是：在同一批 constructed windows、同一套 baseline、同一套 MAE/RMSE 指标下，TTM 输出了真实推理结果，并在整体指标上优于两个 baseline。

这还不是完整异常模型或维护模型。当前结果没有使用真实维修记录、真实故障标签、停机事件标签或 RUL 标签，也没有完成 scenario 过滤建窗、质量标记过滤、等待态剔除和更强 baseline 对照。

## 边界与风险

- `available_and_ran` 只说明 TTM 依赖、权重和推理链路成功运行，不代表模型可以用于告警。
- 本报告没有证明生产级预测性维护能力；当前证据只覆盖 forecasting 评测口径。
- 缺少真实故障标签和维修记录时，不能推出故障概率。
- 缺少寿命标签和退化过程定义时，不能推出 RUL 或维护建议。
- `unassigned_cycle=529,790` 与 `invalid=205,176` 是下一阶段数据治理重点。
- 当前 `cross-stage` 窗口可能包含等待阶段或跨阶段混合片段，需要单独评估是否剔除。
- 当前 scenario 只是指标分组，不是 scenario-filtered model evaluation。
- `max-windows=20/40/80` 是 first-N 嵌套窗口规模敏感性，不是随机抽样或统计稳健性结论。

## 下一阶段模型开发任务

下一阶段主线是业务场景评测口径固化。当前 TTM 报告证明 forecasting 链路可以运行，但它还没有证明模型输出能直接变成故障概率、RUL、维护建议或生产告警。

推荐先选一个业务场景做最小闭环。第一场景选定为 `leak_current_monitoring`，因为它只有 `LeakElec` 一个核心传感器，更适合先验证 forecasting 残差、趋势和尖峰能否形成候选异常信号。`atmosphere_detection` 作为第二候选场景保留。

1. 定义业务场景所需的传感器、工艺阶段和有效窗口。
2. 比较 `good only`、去除 `invalid`、去除 `unassigned_cycle` 等质量口径下的指标变化。
3. 评估等待态保留、剔除或单独建模对 forecasting 误差的影响。
4. 引入一个 rolling 或 lag baseline，并与现有 baseline、TTM 同口径比较。
5. 将 TTM 输出转化为残差、趋势、尖峰或分位数候选信号。
6. 说明这些候选信号还需要哪些维修记录、专家复核或真实故障标签才能进入维护决策。

在上述评测桥梁稳定后，再进入更多模型选择、轻量微调或领域模型训练。
