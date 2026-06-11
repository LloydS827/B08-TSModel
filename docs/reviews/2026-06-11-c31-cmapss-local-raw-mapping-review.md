# C3.1 C-MAPSS Local Raw Mapping Review

Date: 2026-06-11

## Scope

本次 review 在 C3.1 授权证据已明确后，使用本机 ignored raw 目录执行 NASA C-MAPSS classic 12 文件 schema mapping dry-run、RUL metadata 检查和 split/leakage guard。它不提交 raw、zip、processed parquet、cache 或生成报告产物，也不运行模型训练。

## Local Inputs

- Source evidence: Zenodo record `https://zenodo.org/records/15346912`
- Downloaded local file: `data/public/cmapss/raw/CMAPSSData.zip`
- Verified size: `12425978`
- Verified MD5: `79a22f36e80606c69d0e9e4da5bb2b7a`
- Extracted reviewed files: 12 classic C-MAPSS text files, covering `train_FD001` through `train_FD004`, `test_FD001` through `test_FD004`, and `RUL_FD001` through `RUL_FD004`

## Command

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml \
  --output reports/c_stage_c31_cmapss_local_raw_mapping_review.md
```

The generated report path is ignored by Git.

## Validation Result

- Status: `schema_validated_ready_for_c32`
- Blocked reasons: none
- Readiness detail: `full_classic_cmapss_validated`
- Raw files present: 12
- Raw files missing: 0
- Observation rows: 6,366,144
- Trajectory count: 1,416
- Required observation schema valid: True

## RUL Metadata

- RUL target rows: 265,256
- Uses capped RUL: False
- Train RUL semantics: max cycle per train unit minus current cycle.
- Test RUL semantics: final RUL file value plus observed test max cycle minus current cycle.

## Split And Leakage Guard

| Guard | Count / Values |
| --- | --- |
| trajectory_overlap_count | 0 |
| duplicate_split_trajectory_count | 0 |
| missing_split_trajectory_count | 0 |
| unknown_split_trajectory_count | 0 |
| target_columns_in_input | none |
| window_adjacency_leakage_count | 0 |
| malformed_window_count | 0 |

## C3.2 Decision

Decision: Go. C-MAPSS has passed source/license preflight, full classic schema validation, RUL metadata review and split/leakage guard under explicit local opt-in. C3.2 may now enter open model cross-dataset evaluation design.

## Repository Boundary

Committed artifacts are limited to config templates, tests and documentation. The following remain local/ignored:

- `data/public/cmapss/raw/`
- `data/processed/cmapss/`
- `reports/c_stage_c31_cmapss_local_raw_mapping_review.md`

## Next Step

Start C3.2 as a design-first branch: define the open model cross-dataset evaluation contract, minimum runnable baseline, dataset split policy, metrics, reporting format and safety boundary before adding executable evaluation code.
