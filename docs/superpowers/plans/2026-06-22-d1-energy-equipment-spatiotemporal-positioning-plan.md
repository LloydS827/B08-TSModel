# D1 能源设备时空智能样板定位修订执行计划

日期：2026-06-22

对应设计：`docs/superpowers/specs/2026-06-22-d1-energy-equipment-spatiotemporal-positioning-design.md`

## 成功标准

本轮完成后，README、details 和接口文档应统一说明：B08 是公司时空智能在能源设备时序方向的核心样板项目；C2/C3 是模型适配性证据而不是 leaderboard；候选信号通过专家复核后才可作为 S01 系统事件候选或运行优化建议输入；默认边界仍不宣称生产告警、故障概率、RUL 精确估计、维修建议、自动工单或自研模型领先。

## 执行步骤

### 1. 增加文档回归测试

修改范围：`tests/test_experiment_scaffold.py`

行动：

- 新增测试，读取 `README.md`、`details.md`、`docs/leak-current-scenario-evaluation.md`、`docs/candidate-signal-and-system-event-interface.md`。
- 断言 README 包含：
  - `能源设备时空智能样板`
  - `船舶制造偏空间`
  - `能源偏时序`
  - 主链路中的 `candidate signals`、`工程解释与专家复核`、`系统协同事件候选`
  - 四个输出层级
  - B08 -> B06 / S01 / IP
  - `模型适配性证据`
  - 不生成 `leaderboard`
- 断言接口文档包含：
  - `candidate_signal_report`
  - residual、trend、spike、representation、imputation
  - S01 事件字段：device、time、stage、signal、confidence、affected scope、suggested action、review status
  - Go / No-Go 三类决策
- 断言 leak current 文档包含专家复核字段。

验证：

```bash
uv run pytest tests/test_experiment_scaffold.py -q
```

预期：新增测试先失败，因为文档尚未更新。

### 2. 更新 README 首页和 C 阶段叙事

修改范围：`README.md`

行动：

- 将标题和项目定位改为“B08 能源设备时空智能样板”。
- 替换第一段为战略口径建议文本。
- 补充“船舶制造偏空间，能源偏时序，B08 是 A 能力在能源侧证据项目”。
- 调整主链路为：

```text
设备时序数据
  -> canonical observations
  -> cycle / stage / window
  -> baseline / open model evaluation
  -> candidate signals
  -> 工程解释与专家复核
  -> 运行优化建议输入或系统协同事件候选
```

- 增加四个输出层级和当前可复现资产之间的对应。
- 增加 B08 -> B06、B08 -> S01、B08 -> IP 的入口说明。
- 将 C2/C3 文字调整为“模型适配性证据”，明确不生成 leaderboard。
- 保留现有快速开始、命令、数据安全边界。

验证：

```bash
uv run pytest tests/test_experiment_scaffold.py -q
```

预期：README 相关断言通过，接口文档相关断言仍可能失败。

### 3. 更新 details 当前阶段与下一步计划

修改范围：`details.md`

行动：

- 标题改为“B08 能源设备时空智能样板进展台账”。
- 更新日期为 2026-06-22。
- 当前阶段说明为：D1 战略定位与接口口径修订中/完成后，下一步才进入 C3.3 single-candidate open model local evaluation design。
- 在已完成主线中补充四个输出层级和候选信号到系统事件的接口口径。
- 每日更新新增 2026-06-22 条目。
- 下一步计划保留 C3.3，但要求以“模型适配性证据”为目的，不扩大成排行榜或自研训练。

验证：

```bash
uv run pytest tests/test_experiment_scaffold.py -q
```

### 4. 新增候选信号与系统事件接口文档

修改范围：`docs/candidate-signal-and-system-event-interface.md`

行动：

- 定义 `candidate_signal_report` 的用途和字段。
- 定义 B08 -> S01 system event candidate 字段。
- 定义 B08 -> B06 的 `equipment_timeseries_observation_package` profile。
- 定义 B08 -> IP 对 P0-06、P0-07、P0-08 的支撑关系。
- 增加 Go / No-Go 判断表。
- 强调该文档是接口草案，不是生产告警、维修建议或自动工单。

验证：

```bash
uv run pytest tests/test_experiment_scaffold.py -q
```

### 5. 更新 leak_current_monitoring 场景文档

修改范围：`docs/leak-current-scenario-evaluation.md`

行动：

- 增加专家复核字段小节：
  - 候选信号含义
  - 是否需要维护人员确认
  - 是否进入运行建议
  - 复核状态
- 明确当前输出只能作为 `candidate_signal_report` 和 S01 event candidate 输入，不代表告警或维修建议。

验证：

```bash
uv run pytest tests/test_experiment_scaffold.py -q
```

### 6. 全量验证与收尾

行动：

- 运行目标测试：

```bash
uv run pytest tests/test_experiment_scaffold.py -q
```

- 如耗时可接受，运行全量测试：

```bash
uv run pytest -q
```

- 运行格式/空白检查：

```bash
git diff --check HEAD
```

- 查看变更：

```bash
git status --short
git diff --stat
```

验收：

- 所有新增/相关测试通过。
- README/details/docs 能回答设计文档中的 7 个验收问题。
- 默认使用路径仍可安装、运行、验证，没有引入本机数据或模型 cache 依赖。
