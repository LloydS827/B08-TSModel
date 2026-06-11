# C3.1 Local Raw Mapping Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Download authorized C-MAPSS raw data into ignored local storage, run C3.1 local raw mapping review, fix any C3.1 blockers exposed by real data, and record a tracked decision summary without committing data artifacts.

**Architecture:** Keep default C3.1 config safe and unchanged. Add a tracked local opt-in config example that reuses the existing C3.1 schema, use shell commands to download/extract Zenodo `CMAPSSData.zip` into ignored `data/public/cmapss/raw/`, run the existing C3.1 CLI, and commit only code/tests/docs/config templates and a safe review summary.

**Tech Stack:** Python 3.11+, existing C3.1 experiment module, YAML config, pytest, uv, shell `curl`/`unzip`/`md5`, Markdown docs.

---

## File Structure

- Create: `configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml`
  - Copy the current default C3.1 config shape.
  - Change only local opt-in fields:
    - `download_policy.allow_network: false`
    - `download_policy.allow_download: false`
    - `download_policy.allow_local_raw_data: true`
    - `download_policy.allow_write_processed: false`
    - `outputs.report: reports/c_stage_c31_cmapss_local_raw_mapping_review.md`
  - Keep `raw_dir: data/public/cmapss/raw`.

- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`
  - Add tests that the example config loads, keeps network/download/write disabled, reads local raw enabled, and targets ignored paths.
  - Add regression tests only if real raw exposes parser/RUL/leakage failures.

- Create or Modify: `docs/reviews/2026-06-11-c31-cmapss-local-raw-mapping-review.md`
  - Safe tracked summary of the local run.
  - No raw rows, sensor samples, zip contents, parquet, or generated local report body.

- Modify: `README.md`
  - Add local raw mapping review entry, example config path, and data boundary.

- Modify: `details.md`
  - Update current stage and next plan based on the actual local run result.

- Modify if needed: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`
  - Only if real C-MAPSS raw exposes a parser/schema/RUL/split bug.

Ignored local artifacts expected during execution:

- `data/public/cmapss/raw/CMAPSSData.zip`
- `data/public/cmapss/raw/train_FD001.txt` ... `RUL_FD004.txt`
- `reports/c_stage_c31_cmapss_local_raw_mapping_review.md`
- any temporary extraction directory under `data/public/cmapss/raw/`

---

## Task 1: Local Opt-In Config Contract

**Files:**
- Create: `configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml`
- Modify: `tests/test_c31_cmapss_minimal_ingestion.py`

- [ ] **Step 1: Write failing test for local opt-in example config**

Add to `tests/test_c31_cmapss_minimal_ingestion.py`:

```python
_LOCAL_RAW_CONFIG = (
    _REPO_ROOT
    / "configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml"
)


def test_c31_local_raw_mapping_example_config_is_explicit_opt_in():
    config = load_c31_cmapss_config(_LOCAL_RAW_CONFIG)

    assert config.download_policy.allow_network is False
    assert config.download_policy.allow_download is False
    assert config.download_policy.allow_local_raw_data is True
    assert config.download_policy.allow_write_processed is False
    assert config.download_policy.raw_dir == Path("data/public/cmapss/raw")
    assert config.outputs.report == Path(
        "reports/c_stage_c31_cmapss_local_raw_mapping_review.md"
    )
    assert config.download_policy.expected_files == expected_cmapss_files()
```

- [ ] **Step 2: Run test and confirm RED**

Run:

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py::test_c31_local_raw_mapping_example_config_is_explicit_opt_in -q
```

Expected: FAIL because the example config does not exist.

- [ ] **Step 3: Create local config directory and example config**

Create `configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml` by copying `configs/c_stage_c31_cmapss_minimal_ingestion.yaml`, then change:

```yaml
download_policy:
  allow_network: false
  allow_download: false
  allow_local_raw_data: true
  allow_write_processed: false
outputs:
  report: reports/c_stage_c31_cmapss_local_raw_mapping_review.md
```

Do not add absolute local paths.

- [ ] **Step 4: Run targeted test and confirm GREEN**

Run:

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py::test_c31_local_raw_mapping_example_config_is_explicit_opt_in -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml tests/test_c31_cmapss_minimal_ingestion.py
git commit -m "test: add c31 local raw opt-in config"
```

---

## Task 2: Download, Extract, And Run Real C-MAPSS Review

**Files:**
- Ignored local artifacts only, unless Task 2 reveals code bugs requiring tests/fixes.
- Possible Modify: `tests/test_c31_cmapss_minimal_ingestion.py`
- Possible Modify: `src/b08_model_core/experiments/c31_cmapss_minimal_ingestion.py`

- [ ] **Step 1: Download Zenodo zip into ignored raw dir**

Run:

```bash
mkdir -p data/public/cmapss/raw
curl -L --fail \
  https://zenodo.org/api/records/15346912/files/CMAPSSData.zip/content \
  -o data/public/cmapss/raw/CMAPSSData.zip
```

Expected: file exists under ignored `data/public/`.

- [ ] **Step 2: Verify file size and md5**

Run:

```bash
stat -f '%z' data/public/cmapss/raw/CMAPSSData.zip
md5 -q data/public/cmapss/raw/CMAPSSData.zip
```

Expected:

```text
12425978
79a22f36e80606c69d0e9e4da5bb2b7a
```

If the checksum differs, stop and inspect source before proceeding.

- [ ] **Step 3: Inspect archive file list without extracting**

Run:

```bash
unzip -l data/public/cmapss/raw/CMAPSSData.zip | sed -n '1,80p'
```

Expected: archive contains the classic C-MAPSS data files. Identify whether files are nested under a folder such as `CMAPSSData/`.

- [ ] **Step 4: Extract only expected files**

Run one of these depending on archive layout.

If archive has files at root:

```bash
unzip -o data/public/cmapss/raw/CMAPSSData.zip \
  'train_FD*.txt' 'test_FD*.txt' 'RUL_FD*.txt' \
  -d data/public/cmapss/raw
```

If archive nests files under `CMAPSSData/`, extract then copy only expected files:

```bash
mkdir -p data/public/cmapss/raw/_extract
unzip -o data/public/cmapss/raw/CMAPSSData.zip -d data/public/cmapss/raw/_extract
find data/public/cmapss/raw/_extract -type f \
  \( -name 'train_FD*.txt' -o -name 'test_FD*.txt' -o -name 'RUL_FD*.txt' \) \
  -exec cp {} data/public/cmapss/raw/ \;
rm -rf data/public/cmapss/raw/_extract
```

Do not commit extracted files.

- [ ] **Step 5: Verify exactly 12 expected txt files**

Run:

```bash
find data/public/cmapss/raw -maxdepth 1 -type f \
  \( -name 'train_FD*.txt' -o -name 'test_FD*.txt' -o -name 'RUL_FD*.txt' \) \
  | sort
```

Expected exactly:

```text
data/public/cmapss/raw/RUL_FD001.txt
data/public/cmapss/raw/RUL_FD002.txt
data/public/cmapss/raw/RUL_FD003.txt
data/public/cmapss/raw/RUL_FD004.txt
data/public/cmapss/raw/test_FD001.txt
data/public/cmapss/raw/test_FD002.txt
data/public/cmapss/raw/test_FD003.txt
data/public/cmapss/raw/test_FD004.txt
data/public/cmapss/raw/train_FD001.txt
data/public/cmapss/raw/train_FD002.txt
data/public/cmapss/raw/train_FD003.txt
data/public/cmapss/raw/train_FD004.txt
```

- [ ] **Step 6: Run local raw mapping review**

Run:

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml \
  --output reports/c_stage_c31_cmapss_local_raw_mapping_review.md
```

Expected:

- Exit 0.
- Report exists only in ignored `reports/*.md`.
- If C3.1 implementation is correct, report should show:
  - no blocked reasons,
  - `full_classic_cmapss_validated`,
  - `schema_validated_ready_for_c32`,
  - `Go: schema validated and research training/evaluation use approved`,
  - leakage counts all zero.

- [ ] **Step 7: Inspect local report decision lines**

Run:

```bash
rg -n "Status:|Blocked reasons:|Readiness detail:|Decision:|Observation rows:|Trajectory count:|RUL target rows:|trajectory_overlap_count|missing_split_trajectory_count|target_columns_in_input" reports/c_stage_c31_cmapss_local_raw_mapping_review.md
```

If the report is blocked:

1. Treat it as a C3.1 blocker.
2. Write a focused failing test that reproduces the parser/RUL/leakage issue using a minimal fixture.
3. Fix C3.1.
4. Re-run C3.1 tests and the real local review.

Do not proceed to C3.2 or write a passing summary until the report is decision-grade.

- [ ] **Step 8: Verify ignored artifacts remain untracked**

Run:

```bash
git status --short --ignored data/public/cmapss/raw reports/c_stage_c31_cmapss_local_raw_mapping_review.md
```

Expected: raw zip/txt and local report appear ignored, not tracked.

---

## Task 3: Tracked Summary And Project Docs

**Files:**
- Create: `docs/reviews/2026-06-11-c31-cmapss-local-raw-mapping-review.md`
- Modify: `README.md`
- Modify: `details.md`
- Modify: `tests/test_experiment_scaffold.py`

- [ ] **Step 1: Write docs regression test**

In `tests/test_experiment_scaffold.py`, extend `test_c31_cmapss_minimal_ingestion_workflow_is_documented`:

```python
assert "configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml" in c31_section
assert "2026-06-11-c31-cmapss-local-raw-mapping-review.md" in c31_section
assert "C3.2" in c31_section
assert "local raw mapping review" in details
```

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c31_cmapss_minimal_ingestion_workflow_is_documented -q
```

Expected: FAIL before docs update.

- [ ] **Step 2: Create tracked review summary**

Create `docs/reviews/2026-06-11-c31-cmapss-local-raw-mapping-review.md` from the actual generated report.

Required sections:

```markdown
# C3.1 C-MAPSS Local Raw Mapping Review

Date: 2026-06-11

## Scope
## Local Inputs
## Command
## Validation Result
## RUL Metadata
## Split And Leakage Guard
## C3.2 Decision
## Repository Boundary
## Next Step
```

Required values must come from the actual run:

- Zenodo URL and checksum verification.
- Expected files present count.
- Generated local report path.
- Status.
- Readiness detail.
- C3.2 decision.
- Observation rows.
- Trajectory count.
- RUL target rows.
- Leakage guard counts.
- Whether C3.2 can enter design.

Do not paste raw rows or sensor values.

- [ ] **Step 3: Update README**

In the C3.1 section, add:

- local raw mapping review summary link;
- local opt-in config path;
- generated report remains ignored;
- default command remains no-download/no-raw/no-training;
- if review passed, C3.2 may now enter design; if blocked, say C3.1 must be fixed first.

- [ ] **Step 4: Update details**

Update:

- current stage;
- 2026-06-11 daily row;
- next plan.

If local review passed, next plan should be C3.2 open model cross-dataset evaluation design.

If local review failed, next plan should be C3.1 fix.

- [ ] **Step 5: Run docs tests**

Run:

```bash
uv run python -m pytest tests/test_experiment_scaffold.py::test_c31_cmapss_minimal_ingestion_workflow_is_documented -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add docs/reviews/2026-06-11-c31-cmapss-local-raw-mapping-review.md README.md details.md tests/test_experiment_scaffold.py
git commit -m "docs: record c31 local raw mapping review"
```

---

## Task 4: Final Verification And Safety Audit

**Files:**
- No code/doc changes expected unless verification reveals issues.

- [ ] **Step 1: Run C3.1 targeted tests**

```bash
uv run python -m pytest tests/test_c31_cmapss_minimal_ingestion.py -q
```

Expected: PASS.

- [ ] **Step 2: Run docs scaffold tests**

```bash
uv run python -m pytest tests/test_experiment_scaffold.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full tests**

```bash
uv run python -m pytest -q
```

Expected: PASS.

- [ ] **Step 4: Re-run default safe C3.1 CLI**

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/c_stage_c31_cmapss_minimal_ingestion.yaml \
  --output /tmp/c31_default_safe_report.md
```

Expected: default remains blocked by `blocked_by_download_policy`.

- [ ] **Step 5: Re-run local raw mapping CLI**

```bash
uv run b08-model-core experiment c-stage-c31 \
  --config configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml \
  --output reports/c_stage_c31_cmapss_local_raw_mapping_review.md
```

Expected: same decision as tracked summary.

- [ ] **Step 6: Verify no forbidden artifacts are tracked**

Run:

```bash
git status --short --ignored data/public/cmapss/raw reports/c_stage_c31_cmapss_local_raw_mapping_review.md data/processed/cmapss
git ls-files data/public data/processed/cmapss reports/c_stage_c31_cmapss_local_raw_mapping_review.md
git diff --check
```

Expected:

- raw/report artifacts ignored, not tracked;
- `git ls-files` prints nothing for forbidden paths;
- `git diff --check` clean.

- [ ] **Step 7: Final code review**

Dispatch final code reviewer with:

- spec path;
- plan path;
- tracked summary path;
- verification commands and results;
- note that raw/zip/local report remain ignored.

Fix any blocking findings before PR.

---

## Task 5: PR, Merge, And Cleanup

**Files:**
- No file changes expected.

- [ ] **Step 1: Push branch**

Run:

```bash
git push -u origin codex/c31-local-raw-mapping-review
```

Expected: branch pushed.

- [ ] **Step 2: Create PR**

Write a concise PR body to `/tmp/c31_local_raw_mapping_pr_body.md`, then run:

```bash
gh pr create \
  --base main \
  --head codex/c31-local-raw-mapping-review \
  --title "Run C3.1 C-MAPSS local raw mapping review" \
  --body-file /tmp/c31_local_raw_mapping_pr_body.md
```

PR body must include:

- summary of the real local raw mapping review;
- C3.2 Go/No-Go result;
- verification commands;
- note that raw/zip/generated report artifacts remain ignored.

- [ ] **Step 3: Check PR state**

Run:

```bash
gh pr view <PR_NUMBER> --json number,state,mergeStateStatus,statusCheckRollup,url
```

Expected: mergeable or clear next action.

- [ ] **Step 4: Merge PR**

Run:

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch \
  --subject "Run C3.1 C-MAPSS local raw mapping review" \
  --body "Merge C3.1 local raw mapping review after verification."
```

If `gh pr merge` reports a local checkout error after remote merge, verify PR state with:

```bash
gh pr view <PR_NUMBER> --json number,state,mergedAt,mergeCommit,url
```

- [ ] **Step 5: Clean local branch and worktree**

From the main workspace root:

```bash
git worktree remove .worktrees/c31-local-raw-mapping-review
git branch -D codex/c31-local-raw-mapping-review
git fetch origin
git merge --ff-only origin/main
```

Expected: main workspace fast-forwards to merged commit.

- [ ] **Step 6: Final state check**

Run from main workspace:

```bash
git status --short --branch
git worktree list
gh pr view <PR_NUMBER> --json number,state,mergedAt,mergeCommit,url
```

Expected: clean `main`, PR merged, feature worktree removed.

---

## Completion Criteria

- `configs/local/c_stage_c31_cmapss_local_raw_mapping_review.example.yaml` exists and loads.
- Zenodo zip was downloaded and verified in ignored storage.
- 12 expected C-MAPSS files were extracted into ignored raw dir.
- C3.1 local raw mapping review was executed with real files.
- Tracked summary records the actual result and next gate.
- README/details reflect current state.
- No forbidden data/report/cache artifacts are tracked.
- Tests pass.
- PR is created, merged, and branch/worktree cleanup is complete.
