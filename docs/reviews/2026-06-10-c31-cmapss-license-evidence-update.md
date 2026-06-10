# C3.1 C-MAPSS License Evidence Update

Date: 2026-06-10

## Review Scope

本次 update 只补充 C3.1 NASA C-MAPSS 的 license / redistribution / research training-evaluation use 证据。结论不启用网络、下载、本机 raw mapping、processed 写入、训练、评测或 C3.2。

本文件延续 [C3.1 C-MAPSS Source And License Review](2026-06-10-c31-cmapss-source-license-review.md)：前一份 review 已校准 NASA PCoE #6 source 和 S3 download target，但将 license / redistribution / research training-evaluation use 保持为 `needs_review`。本次 update 只处理这个授权证据缺口。

## Evidence Sources

- Primary source calibration: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
- NASA PCoE S3 target: https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip
- Zenodo record: https://zenodo.org/records/15346912
- Zenodo API record: https://zenodo.org/api/records/15346912
- CC BY 4.0 license: https://creativecommons.org/licenses/by/4.0/

Manual review evidence on 2026-06-10:

- S3 target HEAD returned `200 OK`, `Content-Type: application/zip`, `Content-Length: 12429152`.
- Zenodo API record `15346912` returned title `PCoE Turbofan Engine Degradation Simulation`.
- Zenodo DOI is `10.5281/zenodo.15346912`.
- Zenodo creator is `National Aeronautics and Space Administration`.
- Zenodo license id is `cc-by-4.0`.
- Zenodo file is `CMAPSSData.zip`, size `12425978`, checksum `md5:79a22f36e80606c69d0e9e4da5bb2b7a`.

These are recorded review evidence only. The default C3.1 CLI must not perform runtime network checks.

## Evidence Interpretation

The Zenodo record identifies a NASA-created C-MAPSS dataset and describes the same four-set engine degradation simulation family used by the classic NASA PCoE #6 C-MAPSS benchmark. The file name `CMAPSSData.zip`, dataset title, creator, description, and C-MAPSS content establish a sufficient project-level correspondence for C3.1 license evidence.

The S3 target and Zenodo file sizes differ, so this review does not claim checksum equivalence between the S3 zip and Zenodo zip. The evidence is used to resolve license/use planning for C3.1, not to prove byte-identical mirrors.

CC BY 4.0 allows sharing and adaptation with attribution. For this project, that is sufficient to move C-MAPSS from unresolved license review to research training/evaluation planning eligibility. Attribution remains required.

## License And Use Decision

Default C3.1 config should record:

- `license_review.decision: approved_for_research_training`
- `license_review.license_status: verified`
- `license_review.redistribution_status: allowed`
- `license_review.training_use_status: research_only`
- `license_review.citation_required: true`

`redistribution_status: allowed` is a license interpretation from CC BY 4.0. It does not override this repository's stricter data boundary.

`training_use_status: research_only` means C3.1 may design a local raw mapping review and may later become a research evaluation candidate. It does not imply production use, commercial deployment, FU13 field RUL, maintenance advice, or production alarm readiness.

## Local Raw Mapping Gate

Local raw mapping is now eligible to be designed as a separate explicit opt-in review, but it is not enabled by this update.

Default flags remain:

- `allow_network: false`
- `allow_download: false`
- `allow_local_raw_data: false`
- `allow_write_processed: false`

An opt-in local raw mapping review must use ignored local paths, must not commit raw/zip/parquet/cache/generated reports, and must validate parser behavior, schema mapping, RUL target metadata, split policy, and leakage guard before any C3.2 design.

## C3.2 Decision

C3.2 remains No-Go after this update. The blocker has changed:

- Before: license / redistribution / research training-evaluation use unresolved.
- Now: full local raw mapping review has not been executed.

C3.2 may only be designed after full classic C-MAPSS schema validation, RUL metadata, and split/leakage guard all pass under explicit local raw opt-in.

## Repository Boundary

Even with CC BY 4.0 evidence, the repository policy remains stricter than the license:

- Do not commit C-MAPSS raw files.
- Do not commit downloaded zip files.
- Do not commit generated parquet or processed data.
- Do not commit model cache or dataset cache.
- Do not commit local generated C3.1 raw mapping reports unless a future tracked report exception is explicitly designed.

## Next Step

Design C3.1 explicit local raw mapping review. If the Zenodo / CC BY evidence is later contradicted or withdrawn, return to the C3 registry and choose a clearer fallback dataset for C3.1b rather than proceeding to raw mapping or C3.2.
