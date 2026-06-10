# C3.1 C-MAPSS Source And License Review

Date: 2026-06-10

## Review Scope

本次 review 只校准 C3.1 NASA C-MAPSS 最小接入的 source identity、download-target identity、引用要求和使用边界。结论不启用网络、下载、本机 raw mapping、processed 写入、训练、评测或 C3.2。

`source_status: verified` 仅表示 source 和 download target 身份已经人工校准，不表示 license、redistribution、research training/evaluation use 或 benchmark 使用许可已经通过。

## Official Source Calibration

官方来源校准为 NASA PCoE #6 Turbofan Engine Degradation Simulation Data Set：

- Primary source: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
- Download target: https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip
- Citation: Saxena, A., Goebel, K., Simon, D., and Eklund, N. Damage propagation modeling for aircraft engine run-to-failure simulation. 2008.

人工 review 期间，S3 target HEAD 返回 `200 OK`、`Content-Type: application/zip`、content length `12429152`。这是人工记录的 review evidence；C3.1 CLI 默认路径不得执行 runtime network checks。

NASA Open Data Portal C-MAPSS page 只作为 calibration source。该页面显示 `License not specified`，并存在 unavailable / non-public signals，因此不能作为 license approval 或 download approval。

## License And Use Boundary

当前 license、redistribution 和 research training/evaluation use 仍未明确：

- `license_status: needs_review`
- `redistribution_status: needs_review`
- `training_use_status: needs_review`

在这些状态解决之前，不能声称 C-MAPSS raw files 可提交、可再分发、可生成可提交 parquet，或可用于 research training/evaluation。

## Local Raw Opt-In Decision

Local raw opt-in 继续 blocked。默认配置保持：

- `allow_network: false`
- `allow_download: false`
- `allow_local_raw_data: false`
- `allow_write_processed: false`

即使用户本机已有 raw zip 或解压后的 raw files，C3.1 默认路径也不读取 raw directory，不写 processed data，不运行模型训练。

## C3.2 Decision

C3.2 继续 No-Go。进入 C3.2 前至少需要：

- source 和 download target 身份维持已校准状态；
- license、redistribution、research training/evaluation use 有明确结论；
- local raw opt-in 被显式记录；
- C3.1 schema validation、RUL target metadata、split/leakage guard 均无阻断；
- raw、zip、parquet、cache 和 generated report artifacts 仍保持 ignored / untracked。

## Next Options

1. 获取 NASA C-MAPSS 使用授权或可复核 license / redistribution / research training-evaluation use 结论。
2. 若 C-MAPSS 使用边界无法澄清，选择 C3 registry 中下一个公开数据集做同等 source/license preflight。
