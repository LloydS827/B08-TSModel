# C3.1 C-MAPSS License Evidence And Next Gate Design

## 目标

本阶段目标是把 C3.1 从“source/download target 已校准但授权边界不清晰”推进到“C-MAPSS 授权依据可复核，下一步可以设计 ignored local raw mapping review”。

范围必须保持克制：本阶段只更新 license / redistribution / research training-evaluation use 的证据、配置状态、默认 preflight 报告和项目入口文档。不下载 C-MAPSS，不读取本机 raw files，不写 processed parquet，不运行开源模型，不设计 C3.2 cross-dataset evaluation。

成功后，默认命令仍应是安全的：

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output reports/c_stage_c31_cmapss_minimal_ingestion.md
```

默认配置仍保持：

```yaml
allow_network: false
allow_download: false
allow_local_raw_data: false
allow_write_processed: false
```

## 项目现状判断

当前项目已经完成：

- FU13 真实设备数据到 canonical observations、cycle 重构、baseline / TTM forecasting 和 `leak_current_monitoring` 场景样例。
- C1、C2、C2.1、C2.2 的开源模型证据和默认离线执行入口。
- C3 public dataset registry。
- C3.1 NASA PCoE #6 经典 C-MAPSS 默认离线配置、loader、parser、schema mapping dry-run、RUL target metadata、split/leakage guard、CLI report 和 source/license review 文档。

当前阻断点不是 parser 或测试覆盖，而是授权证据。`docs/reviews/2026-06-10-c31-cmapss-source-license-review.md` 已记录：NASA PCoE #6 source 和 S3 download target 身份已校准，但 license、redistribution、research training/evaluation use 未明确，因此 local raw opt-in 和 C3.2 继续 blocked。

本轮联网复核得到的新证据是：

- NASA PCoE repository 仍是经典 C-MAPSS 的 primary source 校准入口。
- NASA Open Data 的 C-MAPSS / CMAPSS Jet Engine Simulated Data 页面仍不能作为明确授权依据，因为页面展示 license 未指定或数据可用性信号不稳定。
- Zenodo record `15346912` 标题为 `Turbofan Engine Degradation Simulation Data Set`，作者和发布方指向 NASA Diagnostics and Prognostics Group / NASA Prognostics Center of Excellence，文件名、大小和经典 PCoE zip target 对应，并明确标注 `Creative Commons Attribution 4.0 International`。
- CC BY 4.0 明确允许 share 和 adapt，要求 attribution。由此可以合理推断：在保留 attribution、不提交 raw/zip/parquet 到仓库的前提下，研究训练和评测使用可以进入下一步本机 opt-in review。但这个推断必须写成可复核授权判断，不应被表述为 NASA PCoE 原始页面本身新增了 license。

## 方案比较

### 方案 A：维持 C3.1 blocked，回到 C3 registry 选择下一数据集

优点是最保守，不需要解释 Zenodo 与 NASA PCoE 原始入口之间的关系。缺点是会忽略已经出现的明确 CC BY 4.0 记录，使项目在 C-MAPSS 上过早放弃，而 C-MAPSS 仍是最适合验证 RUL / run-to-failure / split leakage 的单数据集。

不推荐作为本轮主线。只有当 Zenodo 记录无法与 NASA PCoE #6 经典文件对应，或 CC BY 4.0 记录被撤回时，才回退到此方案。

### 方案 B：更新 C-MAPSS license 证据，但默认只开放到“可设计 local raw mapping review”

把 Zenodo CC BY 4.0 记录作为 C3.1 授权证据，更新 tracked review doc、默认 config 和默认 report。`source_status` 继续表示 NASA PCoE / download target 身份已校准；`license_review` 从 `needs_review` 推进到 `approved_for_research_training`，`license_status: verified`，`redistribution_status: allowed`，`training_use_status: research_only`。

同时保持所有 download/raw/processed flags 为 false。默认 C3.1 report 不再因 license blocked，而是因默认 download/local-raw policy blocked。这样既承认授权边界已经足以设计本机 raw mapping review，又不在本阶段读取数据或推进 C3.2。

这是推荐方案。它符合项目目标：用证据逐步解锁下一关，而不是直接跨越数据、schema、leakage 和模型评测。

### 方案 C：直接启用 local raw mapping review 或进入 C3.2 设计

优点是进度快。缺点是越过了用户明确要求的顺序：授权明确后，仍要先做 ignored local raw mapping review，并且只有 schema validation、RUL metadata、split/leakage guard 全部通过后才能设计 C3.2。

不采用。

## 设计决策

采用方案 B。

本阶段只完成 C3.1 license evidence upgrade。阶段结束时：

- C-MAPSS 不再因为 license / redistribution / training-use 未明确而 blocked。
- 默认命令仍不下载、不读 raw、不写 processed、不训练。
- 默认 report 应显示 license evidence 来自 Zenodo CC BY 4.0，并注明这是基于 Zenodo 记录与 NASA PCoE #6 经典包对应关系的授权判断。
- C3.2 仍然 No-Go，因为完整 local raw mapping review 尚未执行。
- 下一阶段应是 C3.1 local raw mapping review 的 opt-in 方案，而不是 C3.2。

## 配置状态

修改 `configs/c_stage_c31_cmapss_minimal_ingestion.yaml`：

```yaml
license_review:
  decision: approved_for_research_training
  license_status: verified
  redistribution_status: allowed
  training_use_status: research_only
  citation_required: true
```

保持不变：

```yaml
source.source_status: verified
download_policy.allow_network: false
download_policy.allow_download: false
download_policy.allow_local_raw_data: false
download_policy.allow_write_processed: false
```

含义：

- `approved_for_research_training` 只表示 C3.1 可进入本机 ignored raw mapping review 和后续研究评测候选，不表示可以提交 raw、zip、parquet 或 cache。
- `redistribution_status: allowed` 只来自 CC BY 4.0 对 share/adapt 的授权，仓库策略仍禁止提交 raw/zip/parquet。
- `training_use_status: research_only` 表示 C 阶段研究训练/评测候选可继续，但不代表生产使用、商业部署、FU13 现场 RUL 或维护建议。

## 报告增强

修改 `render_c31_cmapss_report`，让默认 report 区分两类状态：

1. License evidence resolved
   - 展示 Zenodo record URL。
   - 展示 license name `Creative Commons Attribution 4.0 International`。
   - 展示 attribution required。
   - 展示 derived decision：research training/evaluation review resolved for C3.1 local mapping planning。

2. Local raw mapping still blocked by default policy
   - 当 `allow_local_raw_data: false` 时，报告文字不能再写成“blocked until license review resolved”。
   - 应写成“Local raw opt-in: eligible for a separate explicit opt-in review, but disabled in the default configuration.”
   - C3.2 decision 应写明：No-Go until local raw mapping review validates full schema, RUL metadata, and leakage guard。

报告不新增网络访问，不检查 Zenodo，不下载文件，不读取 raw dir。

## Review Doc

新增 `docs/reviews/2026-06-10-c31-cmapss-license-evidence-update.md`。

文档必须包含：

- Review scope：只更新授权证据，不执行 raw mapping 或 C3.2。
- Evidence sources：
  - NASA PCoE repository primary source URL。
  - NASA PCoE S3 classic zip target。
  - Zenodo record `https://zenodo.org/records/15346912`。
  - CC BY 4.0 license URL。
- Evidence interpretation：
  - Zenodo 记录与经典 PCoE #6 zip 的对应关系。
  - CC BY 4.0 支持 share/adapt 和 attribution requirement。
  - research training/evaluation use 是基于 CC BY 4.0 的项目内保守推断。
- Decision：
  - license status verified。
  - redistribution status allowed by license, but repository policy still forbids committing raw/zip/parquet/cache。
  - training use status research_only。
  - local raw mapping review may be designed next as explicit opt-in。
  - C3.2 remains No-Go until mapping/schema/RUL/split gates pass。

## README / Details

README 的 C3.1 小节需要从“license 未明确”更新为：

- C-MAPSS source/download target 已校准。
- Zenodo CC BY 4.0 evidence 已补充，授权边界足以设计下一步 local raw mapping review。
- 默认命令仍不下载、不读取 raw、不写 processed、不训练。
- C3.2 仍 blocked，直到 local raw mapping review 验证完整 schema validation、RUL metadata 和 split/leakage guard。

`details.md` 需要更新：

- 当前阶段：C3.1 license evidence upgrade 已完成，下一步是 C3.1 explicit local raw mapping review 设计。
- 每日台账：记录本阶段新增授权证据、报告状态和默认边界。
- 下一步计划：把“优先获取 C-MAPSS 授权”改为“设计本机 ignored raw mapping review opt-in”，并保留 fallback：若后续证据被推翻，再回到 C3 registry 选择许可证更清晰的数据集做 C3.1b。

## 测试策略

采用 TDD：

1. 先更新 C3.1 测试，要求默认 config 的 license 状态变为 verified / allowed / research_only / approved_for_research_training。
2. 先更新 report 测试，要求默认 report 展示 Zenodo URL、CC BY 4.0、research training/evaluation resolved、local raw mapping 仍由默认 policy disabled、C3.2 仍 No-Go。
3. 更新 docs regression 测试，要求 README 和 details 同时提到 license evidence update、local raw mapping review next、C3.2 still blocked。
4. 再实现 config、report 和 docs。
5. 运行 C3.1 相关测试、文档测试、默认 CLI 和全量 pytest。

## 成功标准

- `uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py tests/test_experiment_scaffold.py -q` 通过。
- `uv run b08-model-core experiment c-stage-c31 --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml --output <tmp-report>` 返回 0。
- 默认 report 不再出现 `blocked_by_license_review`，但仍出现默认 local raw/download policy 阻断。
- 默认 report 明确 C3.2 仍 No-Go。
- `uv run python -m pytest -q` 通过。
- README 和 `details.md` 与阶段边界一致。

## 下一阶段

下一阶段不是 C3.2，而是 C3.1 local raw mapping review opt-in：

1. 在 ignored 本机目录放置 C-MAPSS raw files 或 zip 解压结果。
2. 使用单独本机配置打开 `allow_local_raw_data: true`，仍默认不提交 raw、zip、parquet、cache 或 generated reports。
3. 复核 parser、schema validation、canonical mapping、RUL target metadata、split/leakage guard。
4. 只有完整经典 C-MAPSS schema validation、RUL metadata 和 split/leakage guard 都通过后，再设计 C3.2 open model cross-dataset evaluation。
