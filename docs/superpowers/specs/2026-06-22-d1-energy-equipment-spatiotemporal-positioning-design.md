# D1 能源设备时空智能样板定位修订设计

日期：2026-06-22

## 背景

团队母战略已将公司 MAS 中的 A 明确为“时空智能”。在船舶制造方向，A 更偏空间可达、大型构件空间约束、工位布局和仿真验证；在能源行业方向，A 更偏设备状态、运行过程、时间序列、调度约束和状态演化。B08 因此不应只被定义为“设备时序基础模型工作台”，而应作为 A 能力在能源设备时序方向的核心样板项目。

当前仓库已经形成 FU13 真实多 CSV 数据装配、canonical observations、cycle 重构、baseline / TTM 评测、`leak_current_monitoring` 场景样例、C 阶段开源模型适配验证等能力。下一步需要先修正项目入口叙事、输出层级和对外接口口径，再继续推进 C3.3 或更深的模型执行。

## 目标

1. 将 README 和 details 的项目定位更新为“能源设备时空智能样板”。
2. README 首页必须补充“船舶制造偏空间，能源偏时序，B08 是 A 能力在能源侧的证据项目”。
3. 将 C2/C3 开源模型评测统一表述为“模型适配性证据”，避免 leaderboard 或模型竞赛叙事。
4. 明确 B08 的四个输出层级：数据层、评测层、信号层、应用输入层。
5. 增加 `candidate_signal_report` 口径，用于聚合 residual、trend、spike、representation、imputation 等候选信号及工程解释。
6. 为 `leak_current_monitoring` 增加专家复核字段口径：候选信号含义、是否需要维护人员确认、是否进入运行建议。
7. 定义 B08 -> B06、B08 -> S01、B08 -> IP 的接口草案，尤其是候选信号到 S01 系统事件候选的字段。
8. 建立 Go / No-Go 判断表，说明复用开源模型、轻量适配、自研模型设计分别需要什么证据。

## 非目标

1. 本轮不新增模型 adapter，不运行 C3.3 single-candidate open model local evaluation。
2. 本轮不下载公开数据、不读取本机真实数据、不写 processed 数据、不生成新报告。
3. 本轮不宣称生产告警、故障概率、RUL 精确估计、维修建议、自动工单或自研基础模型优于开源模型。
4. 本轮不把 RUL 指标和 forecasting 指标合并为单一排行榜。
5. 本轮不修改默认 CLI 行为和已有实验计算逻辑。

## 设计判断

### 1. 项目定位

README 第一段应升级为：

> B08 是公司时空智能在能源设备时序方向的核心样板项目，目标是把真实设备数据、统一观测表、模型窗口、baseline、开源基础时序模型、候选信号和评测报告连接成可复现链路，为设备状态理解、运行优化建议输入、异常候选识别和后续系统级协同提供证据。基础模型评测是项目的重要技术路线，但项目目标不是追求模型排行榜，而是判断开源模型复用、轻量适配和条件性自研的工程可行性。

此表述保留现有工程主线，同时把“模型评测”从项目目的降级为技术路线。

### 2. 主链路

README 首页应呈现主链路：

```text
设备时序数据
  -> canonical observations
  -> cycle / stage / window
  -> baseline / open model evaluation
  -> candidate signals
  -> 工程解释与专家复核
  -> 运行优化建议输入或系统协同事件候选
```

该链路比旧版多出 `candidate signals`、专家复核和系统协同事件候选，符合母战略对状态理解和系统协同的要求。

### 3. 输出层级

B08 对外输出分为四层：

| 层级 | 输出 | 当前支撑 |
| --- | --- | --- |
| 数据层 | canonical observations、cycle 重构、窗口生成、质量标记 | FU13 observations、cycle builder、window builder、diagnostics |
| 评测层 | baseline、TTM、MOMENT、Chronos、TimesFM、Moirai 等模型适配性评测 | C1、C2、C2.1、C2.2、C3、C3.1、C3.2 |
| 信号层 | residual、trend、spike、representation、imputation 候选信号 | `leak_current_monitoring`、C1 task evidence |
| 应用输入层 | 设备状态解释输入、异常候选、运行优化建议输入、系统级协同事件候选 | `candidate_signal_report` 口径、B08 -> S01 事件草案 |

README 首页还必须列出当前可复现资产：FU13 observations、cycle / window、baseline / TTM、`leak_current_monitoring` 和 C 阶段评测入口。

### 4. C2/C3 叙事

C2/C3 应避免“开源模型排行”叙事，改为：

- C2/C2.1/C2.2：验证开源基础时序模型在本项目任务矩阵、依赖、cache、adapter、失败分类和离线边界下的可执行性与适配性。
- C3/C3.1/C3.2：验证公开数据集与 FU13-like 参考链路是否能提供跨数据任务证据；C-MAPSS RUL 和 FU13-like forecasting 指标分开解释。
- Go / No-Go 的对象不是“哪一个模型排第一”，而是“何时复用开源模型、何时轻量适配、何时进入条件性自研设计”。

### 5. candidate_signal_report 口径

`candidate_signal_report` 是信号层与应用输入层之间的轻量报告口径，第一轮只定义字段和解释，不新增 CLI。

建议字段：

| 字段 | 含义 |
| --- | --- |
| `device_id` | 设备 ID，例如 `FU13` |
| `time_range` | 候选信号覆盖时间范围 |
| `stage` | 工艺阶段或 `cross-stage` |
| `signal_type` | residual、trend、spike、representation、imputation |
| `sensor_id` | 关联传感器 |
| `evidence_source` | baseline、TTM、C1 task、scenario evaluation 等 |
| `engineering_interpretation` | 工程含义解释 |
| `expert_review_required` | 是否需要专家或维护人员复核 |
| `operation_advice_candidate` | 是否可进入运行建议输入 |
| `s01_event_candidate` | 是否可转为 S01 系统事件候选 |
| `review_status` | pending、confirmed、rejected、needs_more_data |

### 6. leak_current_monitoring 专家复核

`leak_current_monitoring` 当前只应作为候选异常信号样例。本轮新增文档字段口径：

- `signal_meaning`：候选信号含义，例如 LeakElec residual 是否提示漏液电流行为偏离同阶段预测。
- `maintenance_confirmation_required`：是否需要维护人员确认，默认 yes。
- `operation_advice_candidate`：是否进入运行建议输入，默认 candidate only，需专家复核后才能进入建议输入。
- `review_status`：pending、confirmed、rejected、needs_more_data。

### 7. B08 -> S01 事件输出草案

B08 可以把候选信号转为 S01 事件候选，但不能直接变成生产告警或自动工单。

建议字段：

| 字段 | 含义 |
| --- | --- |
| `event_id` | 事件候选 ID |
| `device_id` | 设备 ID |
| `time_range` | 事件候选覆盖时间 |
| `stage` | 工艺阶段 |
| `signal_type` | residual、trend、spike、representation、imputation |
| `signal_summary` | 信号摘要 |
| `confidence` | low、medium、high 或数值置信度 |
| `affected_scope` | 影响范围，例如 sensor、stage、cycle、device |
| `suggested_action` | 建议动作输入，例如 expert_review、watch、adjust_operation_candidate |
| `review_status` | pending、confirmed、rejected、needs_more_data |
| `source_report` | 来源报告路径或报告 ID |

### 8. 外部接口

| 接口 | 输出口径 | 当前用途 |
| --- | --- | --- |
| B08 -> B06 | `equipment_timeseries_observation_package` profile | 把 canonical observations、cycle、window、quality flag 作为设备时序观测包 |
| B08 -> S01 | system event candidate | 把候选信号转为设备状态变化候选、风险候选、运行优化建议输入 |
| B08 -> IP | P0-06、P0-07、P0-08 证据 | P0-06 对应 canonical observations / quality flags；P0-07 对应 cycle reconstruction / window artifacts；P0-08 对应 baseline / TTM / open model evaluation reports |

### 9. Go / No-Go 判断表

| 决策 | Go 证据 | No-Go / 暂缓证据 |
| --- | --- | --- |
| 复用开源模型 | 默认离线边界可运行；依赖与 cache 可控；在目标任务上稳定产生可解释候选信号；工程成本低于维护自研 | 依赖不可控、权重不可审计、常见任务失败、输出难解释或无法进入候选信号口径 |
| 轻量适配 | 开源模型基础输出有效，但在 FU13 / C-MAPSS 关键任务上存在稳定偏差；少量适配可明显改善目标指标或信号质量 | 适配需要大量标签、训练成本接近自研、收益只体现在单次排行榜指标 |
| 条件性自研模型设计 | 真实数据、公开数据、候选信号和专家复核都显示开源模型无法覆盖关键设备状态理解；已有足够数据治理和评测资产支撑设计 | 缺少故障标签、维护闭环、寿命定义或专家复核证据；开源模型尚未完成公平适配验证 |

## 文件范围

本轮计划修改：

1. `README.md`：首页定位、主链路、当前资产、输出层级、接口、C 阶段叙事、边界。
2. `details.md`：当前阶段和下一步计划从 C3.3 前移为 D1 战略口径修订完成后的 C3.3。
3. `docs/leak-current-scenario-evaluation.md`：补充专家复核字段和边界。
4. 新增 `docs/candidate-signal-and-system-event-interface.md`：集中记录 `candidate_signal_report`、B08 -> S01 事件草案、B08 -> B06/IP 口径和 Go / No-Go 表。
5. `tests/test_experiment_scaffold.py` 或新增轻量文档测试：锁定战略定位、接口字段、非 leaderboard 叙事和边界。

## 验收标准

完成后，仓库默认文档应能回答：

1. B08 为什么属于时空智能，而不仅是时序模型项目。
2. FU13 链路当前已经提供哪些真实证据。
3. open model evaluation 的结论如何进入工程判断。
4. 候选信号如何被专家复核。
5. 哪些信号可以转成 S01 的系统事件候选。
6. P0-06、P0-07、P0-08 分别由哪些报告和数据结构支撑。
7. 默认边界仍清楚说明：不宣称生产告警、故障概率、RUL 精确估计、维修建议、自动工单或自研基础模型领先。

验收锚点：

| 验收项 | 文档位置 | 测试断言 |
| --- | --- | --- |
| 战略定位与 A 能力解释 | `README.md`、`details.md` | 包含“能源设备时空智能样板”“船舶制造偏空间”“能源偏时序” |
| 当前 FU13 证据 | `README.md`、`details.md` | 包含 observations、cycle / window、baseline / TTM、`leak_current_monitoring`、C 阶段评测 |
| 模型适配性证据 | `README.md`、`docs/candidate-signal-and-system-event-interface.md` | 包含“模型适配性证据”和“不生成 leaderboard” |
| 候选信号专家复核 | `docs/leak-current-scenario-evaluation.md`、接口文档 | 包含 `signal_meaning`、`maintenance_confirmation_required`、`operation_advice_candidate`、`review_status` |
| S01 系统事件候选 | 接口文档 | 包含 device、time、stage、signal、confidence、affected scope、suggested action、review status |
| P0-06 / P0-07 / P0-08 | 接口文档、`README.md` | 分别映射 canonical observations、cycle / window、model evaluation reports |
| 当前边界 | `README.md`、接口文档、leak current 文档 | 排除生产告警、故障概率、RUL 精确估计、维修建议、自动工单 |

## 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 文档升级后显得像已经进入应用系统交付 | 反复使用“候选”“输入”“专家复核”“草案”，并在边界中排除生产告警和自动工单 |
| C2/C3 被误解为模型排行榜 | 明确指标分开解释，Go / No-Go 面向工程路线选择 |
| 接口字段过度设计 | 第一轮只做文档契约，不新增 schema runtime，不改变 CLI |
| README 过长 | README 只放入口级解释，字段细节放入独立接口文档 |
