# C3.1 Default Preflight Review And Source License Decision Design

## 目标

本阶段目标是完成 C3.1 NASA C-MAPSS 默认 preflight 的首次正式 review，把当前报告从“能生成”提升到“能支撑是否进入 local raw mapping / C3.2 的决策”。

范围保持克制：不下载 C-MAPSS，不读取本机 raw files，不生成 processed parquet，不训练模型，不进入 C3.2 设计。阶段产物应说明默认报告为何 blocked、NASA PCoE #6 来源与下载入口是否可验证、license / redistribution / research training/evaluation use 是否足够明确，以及下一步是否允许 local raw opt-in。

## 当前判断

已运行默认命令：

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output reports/c_stage_c31_cmapss_minimal_ingestion.md
```

默认配置保持：

```yaml
allow_network: false
allow_download: false
allow_local_raw_data: false
allow_write_processed: false
```

本机生成报告状态为 `blocked`，C3.2 为 `No-Go: not schema validated`。报告已经覆盖 blocked reasons、download boundary、expected files、schema mapping dry-run、RUL metadata、split/leakage guard 和 invalid claims；主要缺口是 source/license section 过薄，只显示 blocked flag，不展示 source URL、download target、citation、license / redistribution / training-use 状态和 review 结论。

官方来源 review 的初步判断：

- NASA PCoE repository 页面存在 #6 Turbofan Engine Degradation Simulation 条目，说明数据由 NASA Ames PCoE 提供，包含 C-MAPSS、四组 operating condition / fault mode 组合、sensor channels 和 fault evolution 描述。
- 配置中的 S3 download target 当前返回 `200 OK`，`Content-Type: application/zip`，说明下载入口可达。
- NASA PCoE 页面提供 citation 文本。
- NASA Open Data Portal 的 C-MAPSS Aircraft Engine Simulator Data 是校准材料，不是 C3.1 主入口；页面显示 `License not specified`、数据 unavailable / non-public 相关描述，不能用来放宽 C3.1。
- PCoE 页面未给出足够明确的 redistribution 或 research training/evaluation 授权文本。因此本阶段不能允许 local raw opt-in，也不能进入 C3.2。

## 方案比较

### 方案 A：只记录人工结论，不改代码

优点是最小改动，风险低。缺点是 C3.1 report 本身仍不够可决策，下一次运行默认命令时读者还要回到外部讨论找 source/license 结论。

### 方案 B：保守增强报告与文档，继续阻断后续动作

把已完成的 source/license review 写入 tracked review doc；增强 C3.1 report 的 source/license section，使默认报告直接展示 primary source、download target、citation 和 license / redistribution / training-use 状态；更新 README 和 details，让项目入口明确本阶段结论。默认仍不下载、不读取 raw、不写 processed、不训练。

这是推荐方案。它符合 C3.1 的真实阶段：来源入口可以校准，但授权边界不足以推进 local raw 或 C3.2。

### 方案 C：把 source 标为 verified 并允许 local raw schema validation

这能更快进入真实 raw mapping，但需要明确 license、redistribution 和 training/evaluation use。当前官方材料不足以支撑，且用户明确要求这些边界明确后才允许 local raw opt-in。因此本阶段不采用。

## 设计

### Source / License Review Doc

新增 `docs/reviews/2026-06-10-c31-cmapss-source-license-review.md`，作为可跟踪 review 记录。文档只记录事实、判断和边界，不复制长网页内容。

必须包含：

- Review 日期和本阶段命令。
- Primary source：NASA PCoE #6 Turbofan Engine Degradation Simulation Data Set。
- Download target：当前 S3 zip URL 和 HEAD 结果摘要。
- Citation：使用 NASA PCoE 页面给出的 dataset citation。
- Calibration source：NASA Open Data Portal C-MAPSS Aircraft Engine Simulator Data，仅作为校准；记录 license not specified / data unavailable / non-public 信号。
- Decision：official source and download target are usable as calibration evidence; license, redistribution, and research training/evaluation use remain unresolved.
- Boundary：do not enable local raw opt-in; do not download; do not commit raw/zip/parquet/cache/report artifacts; C3.2 remains No-Go.

### Config Status

`configs/c_stage_c31_cmapss_minimal_ingestion.yaml` 暂不放开任何安全开关。是否把 `source.source_status` 从 `needs_review` 改为 `verified` 取决于实现时的最小测试影响：

- 允许改为 `verified`，因为官方 PCoE source 和 download target 已可验证。
- 但 `license_review.decision` 必须继续是 `needs_review`，`license_status`、`redistribution_status`、`training_use_status` 必须继续是 `needs_review`。
- 即使 source verified，默认命令仍必须 `blocked`，且不得读取 raw dir。

推荐采用 `source_status: verified`，让 blocked reason 从笼统的 source/license review 收敛为 license/training-use review。这样更贴近事实，也让下一步门槛更清晰。

### Report Enhancement

增强 `render_c31_cmapss_report` 的 source/license section。为了避免扩大 runner 状态面，最小实现是让 `C31CmapssRunResult` 持有 `source` 和 `license_review` 快照，报告渲染时直接输出配置中的 review 字段。

报告必须新增或展示：

- Primary source name / URL。
- Download target URL。
- Source status。
- Citation required 和 citation。
- License decision、license status、redistribution status、training-use status。
- Local raw opt-in decision：blocked until license / redistribution / training-use are resolved.
- C3.2 decision explanation：No-Go until full classic schema validation, leakage guard, and research training/evaluation use are all clear.

报告不得新增网络访问，也不得因为写报告而检查 raw dir。

### README / Details

README 继续作为项目入口，C3.1 小节补充 source/license review doc 链接和当前结论：official source / download target 已校准，license / redistribution / training-use 未清晰，因此 local raw opt-in 和 C3.2 仍 blocked。

`details.md` 更新当前阶段和当日台账：默认 preflight 已运行并 review；报告质量已增强；source/license review 结论是保持 blocked。下一步计划从“运行 default preflight”推进为“如需继续 C-MAPSS，先取得明确使用授权或人工许可依据；否则回到 C3 registry 选择下一个公开数据集深入对象”。

### 测试

采用 TDD，小步修改：

1. 先写失败测试，要求默认 config source status 为 `verified`、license/training-use 仍 `needs_review`，默认 runner blocked 且不读 raw。
2. 先写失败测试，要求默认 report 包含 primary source、download target、citation、license decision、redistribution status、training-use status、local raw opt-in decision。
3. 先写失败测试，要求 README 和 details 提到 source/license review doc 与 local raw blocked 结论。
4. 实现最小代码和文档修改。
5. 运行 C3.1 相关测试、文档测试、全量 pytest，再运行默认 C3.1 CLI 生成本机 report 做人工审阅。

## 成功标准

- 默认 C3.1 CLI 仍返回 0 并生成本机 report。
- report 状态仍为 `blocked`，不得下载、不得读取 raw、不得写 processed、不得训练。
- source 可被记录为 verified，但 license / redistribution / training-use 未 resolved 时 local raw opt-in 仍 blocked。
- tracked review doc 明确说明不允许 local raw opt-in，也不允许进入 C3.2。
- README 和 details 与当前阶段一致。
- `uv run python -m pytest -q` 通过。

## 后续路径

本阶段完成后，下一阶段不要直接进入 C3.2。合理路线只有两条：

1. 取得足够明确的 C-MAPSS license / redistribution / research training/evaluation use 依据，再用 ignored 本机 raw 目录做 C3.1 local mapping review。
2. 如果 C-MAPSS 授权边界仍不清晰，回到 C3 registry，从 PRONOSTIA / IMS Bearing 等候选中选择一个许可证更明确的数据集做 C3.1b 单数据集深入。
