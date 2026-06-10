# C3.1 C-MAPSS License Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 C3.1 NASA C-MAPSS 授权边界从 `needs_review` 推进到可复核的 CC BY 4.0 / research-only 证据状态，同时保持默认 no-download / no-raw / no-processed / no-training 边界，并继续阻断 C3.2。

**Architecture:** 复用现有 C3.1 config / runner / report 结构，增加一个窄的 `license_evidence` 配置快照和报告表格。默认 runner 不访问网络、不读取 raw；状态变化只影响 preflight 阻断理由和下一步门禁说明。

**Tech Stack:** Python 3.11+, dataclasses, YAML config, existing C3.1 experiment module, pytest, uv, Markdown docs.

---

## File Structure

- Modify: `configs/c_stage_c31_cmapss_minimal_ingestion.yaml`
  - 将 `license_review` 推进为 `approved_for_research_training` / `verified` / `allowed` / `research_only`。
  - 新增 `license_evidence`，记录 Zenodo record、DOI、license id/name/url、file key/size/checksum、review date 和 interpretation。
  - 保持所有 safety flags 为 false。

- Modify: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
  - 新增 `C31LicenseEvidence` dataclass 和 config loader。
  - 将 evidence 快照放入 `C31CmapssConfig` 与 `C31CmapssRunResult`。
  - 报告渲染 license evidence table、local raw opt-in next gate 和 C3.2 No-Go 原因。
  - 不新增网络访问，不改变 raw inspection 顺序。

- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`
  - TDD 覆盖默认 license evidence 状态、默认 runner 不再因 license blocked、report 内容和 C3.2 阻断。

- Modify: `tests/test_experiment_scaffold.py`
  - 覆盖 README/details 对 license evidence update、local raw mapping review next gate、C3.2 blocked 的说明。

- Create: `docs/reviews/2026-06-10-c31-cmapss-license-evidence-update.md`
  - 记录 Zenodo API 证据、CC BY 4.0 解释、仓库禁提交策略和下一步门禁。

- Modify: `README.md`
  - 更新 C3.1 小节，说明授权证据已补齐但默认仍不读取 raw，C3.2 仍 blocked。

- Modify: `details.md`
  - 更新当前阶段、2026-06-10 台账和下一步计划。

---

## Task 1: TDD For License Evidence State

**Files:**
- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`
- Modify: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Update failing config expectations**

In `tests/test_c31_cmapss_minimal_ingestion.py`, update `test_c31_default_config_is_offline_and_lists_classic_cmapss_files`:

```python
assert config.license_review.decision == C31LicenseDecision.APPROVED_FOR_RESEARCH_TRAINING
assert config.license_review.license_status == "verified"
assert config.license_review.redistribution_status == "allowed"
assert config.license_review.training_use_status == "research_only"
assert config.license_evidence.record_url == "https://zenodo.org/records/15346912"
assert config.license_evidence.doi == "10.5281/zenodo.15346912"
assert config.license_evidence.license_id == "cc-by-4.0"
assert config.license_evidence.file_key == "CMAPSSData.zip"
assert config.license_evidence.file_size_bytes == 12425978
```

- [ ] **Step 2: Update failing default runner expectation**

In `test_c31_default_runner_blocks_without_reading_raw_data`, assert:

```python
reasons = [reason.value for reason in result.blocked_reasons]
assert "blocked_by_license_review" not in reasons
assert reasons == ["blocked_by_download_policy"]
assert result.status == C31TopLevelStatus.BLOCKED
assert result.c32_go_no_go == "No-Go: local raw mapping review not executed"
```

Keep the existing raw missing expectations. The default should still not inspect raw because `allow_local_raw_data` is false.

- [ ] **Step 3: Add failing report evidence test**

Add:

```python
def test_c31_report_renders_license_evidence_and_next_gate():
    config = load_c31_cmapss_config(_DEFAULT_CONFIG)
    result = run_c31_cmapss_minimal_ingestion(config, config_path=_DEFAULT_CONFIG)

    text = render_c31_cmapss_report(result)

    assert "https://zenodo.org/records/15346912" in text
    assert "10.5281/zenodo.15346912" in text
    assert "Creative Commons Attribution 4.0 International" in text
    assert "cc-by-4.0" in text
    assert "CMAPSSData.zip" in text
    assert "12425978" in text
    assert "| license_decision | approved_for_research_training |" in text
    assert "| redistribution_status | allowed |" in text
    assert "| training_use_status | research_only |" in text
    assert "Local raw opt-in: eligible for a separate explicit opt-in review, but disabled in the default configuration." in text
    assert "Current default C3.2 gate: No-Go until local raw mapping review validates full schema, RUL metadata, and leakage guard." in text
    assert "blocked_by_license_review" not in text
```

- [ ] **Step 4: Update license-block tests to force unresolved license**

Any test that expects `blocked_by_license_review` must modify the temp config explicitly:

```python
data["license_review"].update(
    {
        "decision": "needs_review",
        "license_status": "needs_review",
        "redistribution_status": "needs_review",
        "training_use_status": "needs_review",
    }
)
```

Do not rely on default config for license-block scenarios.

- [ ] **Step 5: Add failing docs regression expectations**

In `tests/test_experiment_scaffold.py`, extend `test_c31_cmapss_minimal_ingestion_workflow_is_documented`:

```python
assert "c31-cmapss-license-evidence-update" in c31_section
assert "Zenodo" in c31_section
assert "CC BY 4.0" in c31_section
assert "local raw mapping review" in c31_section
assert "C3.2" in c31_section
assert "local raw mapping review" in details
assert "C3.2" in details
```

- [ ] **Step 6: Run targeted tests and confirm RED**

Run:

```bash
uv run python -m pytest \
  tests/test_c31_cmapss_minimal_ingestion.py::test_c31_default_config_is_offline_and_lists_classic_cmapss_files \
  tests/test_c31_cmapss_minimal_ingestion.py::test_c31_default_runner_blocks_without_reading_raw_data \
  tests/test_c31_cmapss_minimal_ingestion.py::test_c31_report_renders_license_evidence_and_next_gate \
  tests/test_experiment_scaffold.py::test_c31_cmapss_minimal_ingestion_workflow_is_documented \
  -q
```

Expected: FAIL because `license_evidence` and updated report/docs do not exist yet.

- [ ] **Step 7: Commit RED tests**

```bash
git add tests/test_c31_cmapss_minimal_ingestion.py tests/test_experiment_scaffold.py
git commit -m "test: cover cmapss license evidence gate"
```

---

## Task 2: Implement Config And Report Evidence

**Files:**
- Modify: `configs/c_stage_c31_cmapss_minimal_ingestion.yaml`
- Modify: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`

- [ ] **Step 1: Update config**

In `configs/c_stage_c31_cmapss_minimal_ingestion.yaml`, change:

```yaml
license_review:
  decision: approved_for_research_training
  license_status: verified
  redistribution_status: allowed
  training_use_status: research_only
  citation_required: true
license_evidence:
  review_date: "2026-06-10"
  record_title: "PCoE Turbofan Engine Degradation Simulation"
  record_url: https://zenodo.org/records/15346912
  api_url: https://zenodo.org/api/records/15346912
  doi: "10.5281/zenodo.15346912"
  creator: "National Aeronautics and Space Administration"
  license_id: cc-by-4.0
  license_name: "Creative Commons Attribution 4.0 International"
  license_url: https://creativecommons.org/licenses/by/4.0/
  file_key: CMAPSSData.zip
  file_size_bytes: 12425978
  file_checksum: "md5:79a22f36e80606c69d0e9e4da5bb2b7a"
  evidence_note: "Zenodo record identifies a NASA-created C-MAPSS dataset under CC BY 4.0; this resolves C3.1 research training/evaluation planning, but does not allow committing raw/zip/parquet/cache artifacts."
```

Do not alter any `download_policy` flag.

- [ ] **Step 2: Add dataclass and config loader**

In `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`, add:

```python
@dataclass(frozen=True)
class C31LicenseEvidence:
    review_date: str
    record_title: str
    record_url: str
    api_url: str
    doi: str
    creator: str
    license_id: str
    license_name: str
    license_url: str
    file_key: str
    file_size_bytes: int
    file_checksum: str
    evidence_note: str
```

Add `license_evidence: C31LicenseEvidence` to `C31CmapssConfig`.

Add `license_evidence: C31LicenseEvidence | None = None` to `C31CmapssRunResult`.

Implement `_load_license_evidence(raw)` using `_load_mapping` and required string helpers. For `file_size_bytes`, require a positive integer:

```python
value = evidence_raw.get("file_size_bytes")
if not isinstance(value, int) or value <= 0:
    raise C31CmapssConfigError("license_evidence.file_size_bytes must be a positive integer")
```

- [ ] **Step 3: Populate evidence snapshots**

In `load_c31_cmapss_config`, pass `license_evidence=_load_license_evidence(raw)`.

In every `C31CmapssRunResult(...)`, pass:

```python
license_evidence=config.license_evidence
```

- [ ] **Step 4: Add local raw mapping C3.2 no-go constant**

Add:

```python
_C32_NO_GO_LOCAL_RAW_MAPPING_NOT_EXECUTED = (
    "No-Go: local raw mapping review not executed"
)
```

When blocked only by default download/local-raw policy before mapping, use this c32 decision in the returned result.

Do not use this for source/license blocked or schema mismatch states.

- [ ] **Step 5: Render license evidence**

Inside `render_c31_cmapss_report`, under `## Source And License Preflight`, after the existing source/license table, add an evidence table if `result.license_evidence` is present:

```markdown
### License Evidence

| Field | Value |
| --- | --- |
| review_date | ... |
| record_title | ... |
...
```

Include all evidence fields.

Replace the unconditional local raw sentence with:

```python
if (
    license_review
    and license_review.decision == C31LicenseDecision.APPROVED_FOR_RESEARCH_TRAINING
    and C31BlockedReason.BLOCKED_BY_DOWNLOAD_POLICY.value in blocked_reasons
    and result.mapping_summary is None
):
    lines.append("Local raw opt-in: eligible for a separate explicit opt-in review, but disabled in the default configuration.")
else:
    lines.append("Local raw opt-in: blocked until license, redistribution, and training-use review are resolved.")
```

This wording must be keyed to the actual default/no-local-raw blocked state, not only to `license_review.decision`, so future opt-in mapping reports remain accurate.

In the existing `source_review` and `license_review` check rows, stop rendering blocked reason tokens when the check is clear. Use helper variables such as:

```python
source_evidence = (
    "blocked_by_source_review"
    if C31BlockedReason.BLOCKED_BY_SOURCE_REVIEW.value in blocked_reasons
    else "source review clear"
)
license_evidence = (
    "blocked_by_license_review"
    if C31BlockedReason.BLOCKED_BY_LICENSE_REVIEW.value in blocked_reasons
    else "license review clear"
)
```

The default resolved-license report must not contain the literal string `blocked_by_license_review`.

In `## C3.2 Go / No-Go`, add the default gate sentence only when the current result is blocked by default download/local-raw policy before mapping:

```markdown
- Current default C3.2 gate: No-Go until local raw mapping review validates full schema, RUL metadata, and leakage guard.
```

Do not render this sentence unconditionally for future opt-in reports that may have `result.c32_go_no_go` set to a Go decision after full schema/RUL/split validation.

- [ ] **Step 6: Run targeted tests and confirm GREEN**

Run:

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit implementation**

```bash
git add configs/c_stage_c31_cmapss_minimal_ingestion.yaml src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py tests/test_c31_cmapss_minimal_ingestion.py
git commit -m "feat: record cmapss license evidence"
```

---

## Task 3: Review Doc, README, Details, And Verification

**Files:**
- Create: `docs/reviews/2026-06-10-c31-cmapss-license-evidence-update.md`
- Modify: `README.md`
- Modify: `details.md`
- Modify: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Create review doc**

Create `docs/reviews/2026-06-10-c31-cmapss-license-evidence-update.md` with sections:

```markdown
# C3.1 C-MAPSS License Evidence Update

Date: 2026-06-10

## Review Scope

## Evidence Sources

## Evidence Interpretation

## License And Use Decision

## Local Raw Mapping Gate

## C3.2 Decision

## Repository Boundary

## Next Step
```

Required facts:

- NASA PCoE repository remains the primary source calibration entrance.
- S3 target HEAD on 2026-06-10 returned `200 OK`, `Content-Type: application/zip`, `Content-Length: 12429152`.
- Zenodo API record `15346912` on 2026-06-10 returned:
  - title `PCoE Turbofan Engine Degradation Simulation`
  - DOI `10.5281/zenodo.15346912`
  - creator `National Aeronautics and Space Administration`
  - license id `cc-by-4.0`
  - file `CMAPSSData.zip`
  - file size `12425978`
  - checksum `md5:79a22f36e80606c69d0e9e4da5bb2b7a`
- CC BY 4.0 permits sharing/adaptation with attribution; this project interprets that as sufficient for C3.1 research training/evaluation planning.
- S3 and Zenodo file sizes differ, so the review records correspondence by dataset identity, title, creator, description, and classic C-MAPSS content, not checksum equivalence.
- Repository policy still forbids committing raw, zip, parquet, cache, generated local reports, or downloaded artifacts.
- C3.2 remains No-Go until local raw mapping review passes full schema/RUL/split gates.

- [ ] **Step 2: Update README C3.1 section**

Replace the current unresolved-license paragraph with:

```markdown
2026-06-10 source/license review 见 ...；license evidence update 见 [C3.1 C-MAPSS License Evidence Update](docs/reviews/2026-06-10-c31-cmapss-license-evidence-update.md)。当前结论是 NASA PCoE #6 source 和 download target 已完成校准，Zenodo CC BY 4.0 记录已提供可复核授权依据，足以设计下一步 explicit local raw mapping review；默认路径仍不下载公开数据、不读取本机 raw files、不写 processed data、不运行模型训练。C3.2 仍 blocked，直到完整 schema validation、RUL metadata 和 split/leakage guard 均通过。
```

- [ ] **Step 3: Update details**

In `details.md`:

- Current stage: C3.1 license evidence upgrade completed; next is explicit local raw mapping review design.
- Daily row for 2026-06-10: append evidence update and default boundary.
- Next plan:
  1. Design C3.1 explicit local raw mapping review using ignored local raw directory.
  2. Execute raw mapping only after explicit config opt-in; do not commit raw/zip/parquet/cache/reports.
  3. Validate full schema, RUL metadata, split/leakage guard.
  4. Only then design C3.2.
  5. If license evidence is later contradicted, fall back to C3 registry and select a clearer dataset for C3.1b.

- [ ] **Step 4: Run docs regression tests**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c31_cmapss_minimal_ingestion_workflow_is_documented -q
```

Expected: PASS.

- [ ] **Step 5: Run default C3.1 CLI**

Run:

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output /tmp/c31_cmapss_license_evidence_report.md
```

Expected: exit 0. Inspect report:

```bash
rg -n "Zenodo|CC BY 4.0|blocked_by_download_policy|blocked_by_license_review|C3.2 remains No-Go|local raw mapping" /tmp/c31_cmapss_license_evidence_report.md
```

Expected:

- Zenodo / CC BY / local raw mapping / C3.2 No-Go present.
- `blocked_by_download_policy` present.
- `blocked_by_license_review` absent.

- [ ] **Step 6: Run full verification**

Run:

```bash
uv run python -m pytest -q
```

Expected: PASS.

- [ ] **Step 7: Commit docs and verification-backed final state**

```bash
git add docs/reviews/2026-06-10-c31-cmapss-license-evidence-update.md README.md details.md tests/test_experiment_scaffold.py
git commit -m "docs: update cmapss license evidence gate"
```

---

## Final Checklist

- [ ] Spec exists: `docs/superpowers/specs/2026-06-10-c31-cmapss-license-evidence-design.md`.
- [ ] Plan exists: `docs/superpowers/plans/2026-06-10-c31-cmapss-license-evidence-plan.md`.
- [ ] Default C3.1 config has license evidence and keeps all safety flags false.
- [ ] Default C3.1 report shows license evidence and remains blocked by local raw/download policy.
- [ ] README and details point to the review doc and next gate.
- [ ] No raw, zip, parquet, cache, or local reports are tracked.
- [ ] Full pytest passes.
