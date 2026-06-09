# C2.2 结果复核与 C3/B 交接设计

更新日期：2026-06-09

## 1. 阶段定位

C2.2 已经完成的是 **升级版开源模型真实执行与审计入口**，不是最终模型能力结论。

当前已经具备：

- 默认离线安全配置：`configs/c_stage_c22_open_model_executable_upgrade.yaml`
- CLI 入口：`uv run b08-model-core experiment c-stage-c22`
- C2.1 runner wrapper 和 adapter contract 复用
- 六个核心模型的版本化目标矩阵
- frontier watchlist audit
- strict required-attempt 检查
- C2.2 Markdown 报告与 cache manifest 输出

因此，下一步不是继续扩大 C2.2 实现范围，而是用已有入口产出和复核一份可决策证据。这个阶段是 C2.2 到 C3/B 的过渡总结层：确认 C2.2 报告是否足以支撑“继续开源模型跨数据验证”“补依赖/权重/接口后重跑”或“进入条件性自研判断”。

## 2. 本阶段目标

本阶段目标是执行并复核 C2.2 结果，而不是开发新 runner 或新增模型体系。

核心问题：

1. C2.2 报告是否完整覆盖六个核心模型和 frontier watchlist？
2. TTM 是否仍能作为本机 anchor / control 被复核？
3. Chronos-2 / Chronos-Bolt、TimesFM 2.5、Moirai 2.0 / Uni2TS、MOMENT、UniTS 的状态是否足够具体？
4. 失败原因是否从笼统的 `needs_review` 推进到依赖、权重、接口、窗口形状、任务头、许可证或资源限制？
5. 哪些模型和任务值得进入 C3 跨数据验证？
6. 哪些缺口可能构成 B 阶段轻量适配或自研模型设计的证据？

本阶段非目标：

- 不新增公开数据集 registry。
- 不做大规模模型训练。
- 不设计自研 backbone。
- 不扩大成十几个模型全部真实执行。
- 不把 C2.2 报告解释为生产告警、维修建议、故障概率或 RUL 结论。

## 3. 执行与复核流程

第一步是做默认离线 preflight。确认 FU13 processed parquet、C2.2 配置、cache 路径、报告输出路径和默认安全边界均清楚可控。默认配置必须保持 `allow_network: false` 和 `allow_download: false`，避免把本机下载、权重状态或外部网络混入默认路径。

第二步是运行默认离线 C2.2 报告：

```bash
uv run b08-model-core experiment c-stage-c22 \
  --config configs/c_stage_c22_open_model_executable_upgrade.yaml \
  --output reports/c_stage_c22_open_model_executable_upgrade.md
```

报告生成后，需要复核以下内容：

- 报告是否写出六个核心模型的 target model ref、executed model ref、task attempt 和 status。
- TTM 是否作为 anchor / control 保持可复核。
- Chronos-2 / Chronos-Bolt、TimesFM 2.5、Moirai 2.0 / Uni2TS 是否进入 forecasting attempt 或给出明确阻塞原因。
- MOMENT、UniTS 是否围绕 representation / imputation / multi-task interface 给出明确状态。
- frontier watchlist 是否保持 audit-only，并覆盖 Time-MoE、Sundial、Timer-S1 / Timer-XL、Kairos、Toto、IBM FlowState / TSPulse、TabPFN-TS。
- cache manifest 是否记录本轮是否联网、是否下载、使用了哪些本机 cache 或权重路径。

第三步是判断是否需要显式本机 opt-in 重跑。只有当默认离线报告证明某个 priority 模型的主要阻塞是缺失依赖或缺失权重，并且 license、资源和接口风险可接受时，才允许单独设计本机 opt-in 配置。opt-in 重跑必须记录：

- 启用的 dependency group 或本机安装方式
- 权重来源和 model ref
- cache 路径
- 是否联网
- 是否下载
- 失败阶段或成功任务

第四步是形成 C2.2 结论表。每个核心模型和 watchlist route 至少归入以下一种或多种状态：

| 状态 | 含义 |
| --- | --- |
| `run_ready` | 当前本机环境和任务口径下可以运行或已运行 |
| `blocked_by_dependency` | 缺少 Python 包、系统依赖或版本不兼容 |
| `blocked_by_weights` | 权重缺失、下载受限、cache 不存在或 model ref 不可取 |
| `interface_review` | 官方接口、adapter 接口或输入输出 contract 仍需核验 |
| `task_mismatch` | 模型能力与当前 forecasting / representation / imputation 任务不匹配 |
| `resource_limited` | 本机 CPU/GPU/内存/磁盘条件不足 |
| `license_review` | 许可证、用途或分发条件需要复核 |
| `candidate_for_c3` | 值得进入跨数据验证 |
| `possible_b_gap` | 可能构成轻量适配或自研模型设计证据 |

## 4. C3/B 交接规则

C3 只承接 C2.2 中已经形成清楚证据的模型和任务。进入 C3 的条件是：模型至少有明确 task attempt 或明确可补齐阻塞，任务口径与 FU13 结果有延续性，并且跨数据验证能回答一个具体问题，例如泛化能力、任务稳定性、工业数据适配性或数据泄漏风险。

B 阶段仍是条件性路线。只有当 C2.2 或后续 C3 证明开源模型在关键需求上存在稳定缺口，并且缺口不能通过简单依赖补齐、权重下载、接口适配或轻量配置解决时，才进入 B 阶段自研模型设计。进入 B 阶段前需要先形成可审查问题定义，而不是直接训练模型。

推荐交接输出：

| 输出 | 用途 |
| --- | --- |
| C2.2 result review summary | 汇总本轮报告结论和阻塞原因 |
| C3 candidate list | 记录值得跨数据验证的模型、任务和指标 |
| dependency/weights action list | 记录需要补齐的本机依赖、权重和 cache |
| B-stage gap notes | 记录可能支持轻量适配或自研判断的证据缺口 |

## 5. 完成标准

本阶段完成时，应具备以下结果：

- C2.2 报告已经执行或明确记录无法执行的本机原因。
- 六个核心模型均有可复核状态，不再停留在笼统描述。
- frontier watchlist 有 audit-only 结论，不被误解释为必跑模型。
- 是否需要 opt-in 联网/下载有明确判断。
- C3 候选和 B 阶段缺口被分开记录。
- README 继续作为项目入口，`details.md` 继续作为当前阶段、每日更新和下一步计划台账；本文件作为 C2.2 到 C3/B 的阶段总结与交接说明。
