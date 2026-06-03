# 漏液电流监测场景评测报告

## 评测目标

本报告验证 `leak_current_monitoring` 的业务场景评测口径：在 FU13 真实数据上，先按漏液电流监测相关传感器、工艺阶段、质量标记和等待态口径构建窗口，再比较 baseline 与 TTM 的 forecasting residual。

本报告不是故障预测验收，不是 RUL 估计，不是维护建议，也不是生产告警。当前输出只能作为候选异常信号的本地评测摘要，完整本地报告仍保留在 ignored 的 `reports/real_leak_current_scenario_evaluation_*.md` 中。

## 数据与场景口径

- scenario: `leak_current_monitoring`
- sensor: `LeakElec`
- related stages: 来自 `configs/fu13_real_data_schema.yaml` 的 `LeakElec.related_stages`，包括 `抽真空`、`氩气导入`、`溶解`、`测温`、`浇筑`、`冷却`
- waiting stage comparison: `related` vs `with_waiting`
- quality modes: `all`、`good_only`、`drop_invalid`、`drop_unassigned_cycle`
- context length: `90`
- prediction length: `16`
- max windows: `40`
- rolling window size: `8`
- window split: 每个评测组合实际得到 `train_windows=28`、`test_windows=12`

`related` 口径只使用漏液电流监测相关阶段；`with_waiting` 在相关阶段基础上纳入等待态，用于观察等待态对误差和候选信号的影响。本轮输入为 FU13 canonical observation parquet，装配后共有 `4,126,789` 行观测。

## Baseline 与 TTM 结果

baseline 报告模型为 `BaselineOnly`，基础模型状态为 `skipped_by_user`。候选残差信号来源使用 `RollingSensorForecaster`，因为 baseline-only 模式未选择 foundation model。

在 `related` stage scope 下，`all`、`good_only`、`drop_invalid`、`drop_unassigned_cycle` 四种 quality mode 的 baseline 结果一致：`RollingSensorForecaster` 的 `residual_mae=0.490885`、`residual_rmse=0.669266`、`abs_residual_p95=1.306250`、`abs_residual_p99=2.000000`。同口径下 `RobustStageForecaster` 为 `mae=0.583333`、`rmse=0.803638`，`StageSeasonalNaiveForecaster` 为 `mae=0.750000`、`rmse=1.015505`。

在 `with_waiting` stage scope 下，`all` 和 `drop_invalid` 的 baseline 候选信号为 `residual_mae=0.898438`、`residual_rmse=1.029512`、`abs_residual_p95=2.000000`、`abs_residual_p99=2.000000`；等待态上下文的 top residual windows 主要来自 `上盖开启:90`。`good_only` 和 `drop_unassigned_cycle` 在本轮数据中回到 related 口径的指标，说明质量过滤会改变等待态窗口是否进入评测。

TTM 使用 `HF_HOME=hf_cache`、`--model-cache-dir hf_cache`、`--no-download` 本地离线运行成功，报告状态为 `foundation_status=available_and_ran`、`dependency_status=installed`、`weight_status=available`，候选残差信号来源为 `TTM`。运行日志提示 TTM R2 会以支持的 `prediction_length=30` 加载模型，再过滤到本次请求的 `prediction_length=16`；本轮命令退出码为 0。

在 `related` stage scope 下，TTM 四种 quality mode 的结果一致：`residual_mae=0.513041`、`residual_rmse=0.684900`、`abs_residual_p95=1.381422`、`abs_residual_p99=1.870826`。在 `with_waiting` stage scope 下，`all` 和 `drop_invalid` 为 `residual_mae=0.677300`、`residual_rmse=0.891807`、`abs_residual_p95=2.035048`、`abs_residual_p99=2.191932`；`good_only` 和 `drop_unassigned_cycle` 与 related 口径一致。

本轮结果说明：在这个漏液电流最小场景里，TTM 可以本地离线跑通并生成同口径候选残差信号；baseline 中 `RollingSensorForecaster` 是很强的工程对照，related 口径下 MAE/RMSE 略低于 TTM，with_waiting 口径下 TTM 低于 rolling baseline。这个差异更像窗口口径和等待态处理问题，不足以单独推出模型优劣或现场告警能力。

## 候选异常信号

当前候选异常信号来自预测值与真实 `LeakElec` 值之间的 residual。`residual_mae` 和 `residual_rmse` 描述整体误差水平；`abs_residual_p95` 和 `abs_residual_p99` 描述本次运行内部绝对残差分布的高分位；top residual windows 用来定位残差较高的上下文窗口。

`p95/p99` 是 within-run empirical residual distribution summaries，不是独立告警阈值，也不是跨设备、跨批次或跨日期可直接复用的报警线。`points_above_p95/p99` 只是相对本次运行的经验分布统计。

top residual windows 的解释要非常克制。baseline related 口径下 top residual contexts 主要是 `溶解:90`，with_waiting 口径下主要是 `上盖开启:90`；TTM related 口径下 top residual contexts 也主要是 `溶解:90`，with_waiting 口径下主要是 `上盖开启:90`。这可以提示后续检查趋势、尖峰或等待态造成的残差放大，但不能直接归因到未来目标阶段，也不能直接解释为漏液故障。

趋势和尖峰的后续解释建议：

- residual p95/p99：用于筛选本次运行中相对偏大的残差片段。
- residual_mae/rmse：用于比较同一窗口口径下模型或 baseline 的整体 forecasting 误差。
- top residual windows：用于交给工艺专家复核上下文阶段、采样质量和现场事件。
- trend/spike：需要结合连续窗口、原始曲线和维修记录判断，不能只看单次残差峰值。

## 边界

- 当前只是 forecasting residual candidate signal。
- 缺少真实故障标签、维修记录和维护闭环时不能推出故障概率、RUL 或维修建议。
- top_window_stage_summary is context window only, not future target-stage attribution。

## 下一步

建议先不要直接把方法横向复制到 `atmosphere_detection` 作为结论扩张。更稳妥的下一步是先把漏液电流场景的窗口样本、top residual windows、等待态影响和质量过滤差异交给现场专家复核，并尽量补充维修记录、停机原因或人工标注。

如果专家复核确认 residual 高分位、趋势或尖峰确实对应可解释的现场现象，再把同一套方法复制到 `atmosphere_detection`。如果暂时拿不到维护记录，也可以先做 `atmosphere_detection` 的同口径评测，但文档中仍应把它限定为候选信号探索，而不是业务告警验证。
