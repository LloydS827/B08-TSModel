# C3.1 Local Raw Mapping Review Design

## 目标

本阶段目标是把 C3.1 从“C-MAPSS 授权证据已补齐，但默认仍未读取 raw”推进到“真实 C-MAPSS raw files 已在 ignored 本机目录完成 schema mapping / RUL metadata / split-leakage review，并产出可决策结论”。

本轮不再停留在纯文档设计。用户已允许下载，因此本轮必须完成一个真实执行闭环：

1. 从授权证据更清晰的 Zenodo C-MAPSS record 下载 `CMAPSSData.zip` 到 ignored 本机目录。
2. 解压并规范化经典 C-MAPSS 12 个文件到 `data/public/cmapss/raw/`。
3. 使用 explicit local opt-in 配置运行 `experiment c-stage-c31`。
4. 如果真实 raw 暴露 parser、schema、RUL metadata 或 leakage guard 问题，本分支内修正 C3.1。
5. 提交 tracked 的安全摘要、README/details 更新、必要测试和配置模板；不提交 raw、zip、parquet、cache 或 generated local report。

## 当前判断

项目已经具备本轮执行的前置条件：

- C-MAPSS source/download target 已校准。
- Zenodo / CC BY 4.0 license evidence 已记录，`license_review` 已推进到 `approved_for_research_training`、`verified`、`allowed`、`research_only`。
- C3.1 runner 已有 raw parser、canonical observation compatibility dry-run、RUL target metadata、split/leakage guard 和 report renderer。
- `.gitignore` 已覆盖 `data/public/`、`data/processed/cmapss/`、`reports/*.md`，可以安全保存本机下载和生成报告。
- Synthetic tests 已覆盖局部 C-MAPSS 结构，但真实 raw 还没有跑过。

因此，继续只写“local raw mapping review 设计”会偏慢。更贴近项目目标的下一步是：**用真实 C-MAPSS 文件验证 C3.1 实现是否真的能支撑 C3.2 Go / No-Go**。

## 方案比较

### 方案 A：只新增 opt-in config / runbook，不下载、不运行

优点是风险低、改动少。缺点是仍然没有验证真实 C-MAPSS 文件，项目会继续停在“应该能跑”的状态。这个方案已经不够推进主线。

### 方案 B：下载真实 C-MAPSS，运行 local raw mapping review，并提交安全摘要

下载 Zenodo `CMAPSSData.zip` 到 ignored 目录，解压 12 个经典 C-MAPSS 文件，使用 explicit opt-in 配置运行 C3.1。若报告通过，提交一个 tracked review summary 到 `docs/reviews/`，说明本机报告路径、文件清单、row / trajectory / RUL target / leakage guard / C3.2 gate 结论；不提交原始数据或 generated report。

这是推荐方案。它把授权证据转换成真实数据工程证据，同时仍保持仓库安全边界。

### 方案 C：下载后直接设计 C3.2 open model cross-dataset evaluation

优点是看起来最快。缺点是越过了当前最关键的实证门：真实 C-MAPSS schema、RUL metadata 和 split/leakage guard 是否全部通过。若 parser 或 RUL 语义存在问题，C3.2 会建立在不可靠数据上。

不采用。

## 设计决策

采用方案 B。

本轮成功后，项目状态应从：

```text
C3.1 license evidence ready, local raw mapping not executed
```

推进为：

```text
C3.1 real C-MAPSS local raw mapping review executed
```

如果完整经典 C-MAPSS 12 个文件通过 schema validation、RUL metadata 和 split/leakage guard，则下一阶段可以设计 C3.2。

如果不通过，本轮应优先修 C3.1 parser / mapping / RUL / leakage guard，而不是绕开失败进入 C3.2。

## 数据边界

下载和解压只允许发生在 ignored 本机目录：

```text
data/public/cmapss/raw/
```

生成报告只允许写到 ignored 本机报告路径，例如：

```text
reports/c_stage_c31_cmapss_local_raw_mapping_review.md
```

不得提交：

- `data/public/cmapss/raw/CMAPSSData.zip`
- `data/public/cmapss/raw/*.txt`
- `data/processed/cmapss/`
- `reports/c_stage_c31_cmapss_local_raw_mapping_review.md`
- cache、临时下载日志或 parquet

允许提交：

- explicit local opt-in 配置模板，前提是它不含本机绝对路径和真实数据内容；
- tracked review summary，前提是不包含原始数据样本、传感器读数行、zip 内容拷贝或派生 parquet；
- README/details 入口说明；
- 测试和 C3.1 实现修复。

## 下载来源

优先使用 Zenodo record：

```text
https://zenodo.org/records/15346912
https://zenodo.org/api/records/15346912/files/CMAPSSData.zip/content
```

原因：

- Zenodo record 明确记录 `cc-by-4.0`。
- 文件名、title、creator、description 和 C-MAPSS 内容与 NASA PCoE #6 经典数据集对应。
- 上一阶段已记录 S3 与 Zenodo 文件大小不同，因此本轮以 Zenodo zip 作为授权更清晰的实际下载来源，不声称它与 S3 zip byte-identical。

## Config 设计

新增 tracked 模板：

```text
configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml
```

模板应与默认 C3.1 配置保持同一 schema，但显式设置：

```yaml
download_policy:
  allow_network: false
  allow_download: false
  allow_local_raw_data: true
  allow_write_processed: false
```

说明：

- 下载由本机 shell / runbook 完成，不由 C3.1 CLI 自动下载。
- C3.1 CLI 只读取已存在的 ignored raw files。
- `raw_dir` 保持相对路径 `data/public/cmapss/raw`。
- `outputs.report` 指向 ignored local report。

是否新增自动 downloader：本轮不新增。理由是 C3.1 runner 当前职责是 preflight / mapping / reporting；把下载器做进 CLI 会扩大安全面，也会让默认路径更复杂。先用 runbook 命令完成下载，下一阶段若需要再设计下载 helper。

## Review Summary

新增 tracked review summary：

```text
docs/reviews/2026-06-11-c31-cmapss-local-raw-mapping-review.md
```

内容包括：

- 下载来源和本机 ignored 路径。
- Zenodo file size / checksum 核对结果。
- 12 个 expected files 是否齐全。
- C3.1 local opt-in config 路径。
- 本机 generated report 路径。
- `status`、`readiness_detail`、`c32_go_no_go`。
- observation rows、trajectory count、RUL target rows、leakage guard counts。
- 是否允许 C3.2 进入设计。
- 不包含任何 raw rows、传感器样本或派生 parquet。

## README / Details

README C3.1 小节应补充：

- local raw mapping review 已有 explicit opt-in 模板和 tracked summary。
- 默认命令仍不下载、不读 raw、不写 processed、不训练。
- 真实 raw review 的 generated report 和数据文件仍 ignored。

`details.md` 应更新：

- 当前阶段反映 C3.1 local raw mapping review 的执行结果。
- 如果通过，下一步主线变为 C3.2 open model cross-dataset evaluation design。
- 如果不通过，下一步主线变为修复 C3.1 parser / schema / RUL / leakage guard。

## 测试策略

采用 TDD：

1. 先写测试要求 local opt-in example config 被文档化且可加载。
2. 先写测试要求 full synthetic mapping 的 review report 文案不会在 blocked 情况下误报完成。
3. 若真实 raw 暴露解析问题，先写 focused regression test，再修 parser。
4. 对真实下载不写入仓库测试；用 shell 验证 ignored 路径和 `git status`。
5. 最终运行 C3.1 targeted tests、docs regression、默认 CLI、local opt-in CLI 和全量 pytest。

## 成功标准

- baseline tests 通过。
- Zenodo zip 下载到 ignored 目录，并校验 size/checksum。
- 12 个经典 C-MAPSS 文件存在于 ignored raw dir。
- explicit local opt-in C3.1 CLI 返回 0。
- local report 显示完整 schema / RUL metadata / split-leakage gate 结论。
- tracked review summary 写明 C3.2 是否可以进入设计。
- README/details 更新。
- `uv run python -m pytest -q` 通过。
- `git status` 不显示 raw、zip、parquet、cache、generated reports。

## 下一阶段

如果本轮真实 C-MAPSS local raw mapping review 通过，下一阶段应直接进入 C3.2 open model cross-dataset evaluation 设计，重点回答：

- 使用 C-MAPSS 作为公开 RUL / run-to-failure benchmark；
- 选择哪些 C2.2 open model / baseline 进入跨数据评测；
- 如何避免 FU13、C-MAPSS、后续公开数据之间的任务口径混淆；
- 如何把 C3.2 结果用于 B 阶段自研 Go / No-Go，而不是直接承诺生产告警或 RUL。

如果本轮不通过，则下一阶段不进入 C3.2，优先修 C3.1。
