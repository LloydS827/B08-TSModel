# Business Scenario Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 FU13 的 `leak_current_monitoring` 建立第一个业务场景评测闭环，把基础模型 forecasting 输出转化为可解释的候选异常信号报告。

**Architecture:** 新增一个小型场景评测层，复用现有 canonical observation、窗口构建、baseline、TTM adapter 和 Markdown 报告风格。第一阶段只做 `LeakElec` 的 forecasting residual，不做补全、表征、轻量机器学习模型或生产告警；等待态只做纳入/剔除口径比较和报告，不实现新的等待态模型。

**Tech Stack:** Python 3.11+, pandas, numpy, pydantic config objects, existing `b08-model-core` CLI, existing `build_model_windows`, existing baseline/TTM adapters, pytest, uv, Markdown docs.

---

## 权威输入

- 设计文档：`docs/superpowers/specs/2026-06-03-business-scenario-evaluation-design.md`
- FU13 真实数据配置：`configs/fu13_real_data_schema.yaml`
- 现有真实数据 forecasting：`src/b08_model_core/real_data/forecasting.py`
- 现有窗口构建：`src/b08_model_core/tasks/window_builder.py`
- 现有 baseline：`src/b08_model_core/baselines/robust_forecaster.py`、`src/b08_model_core/baselines/seasonal_naive.py`
- 现有 TTM adapter：`src/b08_model_core/adapters/ttm_adapter.py`
- 现有 CLI：`src/b08_model_core/cli.py`
- 当前本地 canonical parquet：`data/processed/fu13_real_observations.parquet`

## 范围守卫

- 第一场景固定为 `leak_current_monitoring`。
- 场景阶段来源必须使用 `configs/fu13_real_data_schema.yaml` 中 `LeakElec.related_stages`，不要在代码里硬编码“production stages”。
- 只做 forecasting residual 候选信号，不做 imputation、embedding、classification、RUL 或故障概率。
- 更强 baseline 的最小版本选择 rolling baseline，不同时实现 rolling 和 lag。
- 等待态处理只做 `related_stages` 与 `related_stages + waiting_stages` 的指标/报告对比，不实现等待态模型。
- 不接入 TimesFM、Chronos、Moirai、FlowState。
- 不训练或微调 TTM。
- 不改动 `data/real/`。
- 不提交 `data/processed/*.parquet`、`reports/real_*`、`hf_cache/` 或模型权重。

## 文件结构

Create:

- `src/b08_model_core/baselines/rolling.py`
  - 最小 rolling baseline。对每个 test window，用上下文窗口最后 N 个时间点的传感器均值预测整个 prediction horizon。
- `src/b08_model_core/real_data/scenario_evaluation.py`
  - 场景筛选、质量口径、等待态口径、baseline/TTM 运行、residual 候选信号和 Markdown 渲染。
- `tests/test_rolling_baseline.py`
  - rolling baseline 单元测试。
- `tests/test_scenario_evaluation.py`
  - 场景筛选、质量过滤、等待态口径、报告渲染测试。
- `docs/leak-current-scenario-evaluation.md`
  - 实施完成后的提交版总结报告。只汇总本地 ignored report 的关键结论，不提交本地真实数据报告原文。

Modify:

- `src/b08_model_core/baselines/__init__.py`
  - 导出 `RollingSensorForecaster`。
- `src/b08_model_core/cli.py`
  - 新增 `real-data evaluate-scenario` 子命令。
- `tests/test_cli_fu13_real_data.py`
  - 增加新 CLI 的轻量测试，使用临时 parquet，不依赖真实数据。
- `README.md`
  - 增加业务场景评测命令入口和报告说明。
- `details.md`
  - 实施完成后同步阶段进展。
- `docs/index.html`
  - 增加 `docs/leak-current-scenario-evaluation.md` 入口。

Generated local-only, do not stage:

- `reports/real_leak_current_scenario_evaluation_baseline.md`
- `reports/real_leak_current_scenario_evaluation_ttm.md`

## 关键接口设计

### Quality modes

Use exactly these mode names in code and reports:

```python
QUALITY_MODES = {"all", "good_only", "drop_invalid", "drop_unassigned_cycle"}
```

Meanings:

- `all`: keep all rows after scenario/stage filtering.
- `good_only`: keep only rows where `quality_flag == "good"`.
- `drop_invalid`: remove rows where `quality_flag == "invalid"`.
- `drop_unassigned_cycle`: remove rows where `quality_flag == "unassigned_cycle"`.

### Stage scopes

Use exactly these stage scopes:

```python
STAGE_SCOPES = {"related", "with_waiting"}
```

Meanings:

- `related`: stages from `LeakElec.related_stages` only.
- `with_waiting`: `LeakElec.related_stages + cfg.cycle_rules.waiting_stages`.

Do not add `waiting_only` model runs in this phase. Report waiting row counts as diagnostics only. In code and reports, `waiting_rows` means waiting-stage rows after scenario/stage filtering and after the selected quality filter is applied.

### Rolling baseline

Minimum behavior:

```python
RollingSensorForecaster(window_size=8).fit(train).predict(test)
```

- `fit()` returns self and does not need to learn global parameters.
- `predict()` returns `{"y_hat": np.ndarray}` with shape `(len(test), prediction_length, sensor_count)`.
- For each test window, compute the mean of the last `window_size` rows of `window.X` per sensor and repeat it for every prediction step.
- Use `window.mask` to ignore missing context values. If a sensor has no observed values in the rolling slice, fall back to `0.0` for that sensor.

### Candidate signal summary

For the selected model predictions, report at least:

- residual MAE and RMSE.
- residual p50, p90, p95, p99 by absolute residual.
- count of residual points above p95 and p99.
- top residual windows with window index, stage summary, max absolute residual, mean absolute residual.

Do not call these failures. Use “candidate residual signal” or “候选异常信号”.

---

## Task 1: 预检与安全边界

**Files:**
- Read: `.gitignore`
- Read: `docs/superpowers/specs/2026-06-03-business-scenario-evaluation-design.md`
- Read: `configs/fu13_real_data_schema.yaml`

- [ ] **Step 1: 确认分支和工作区状态**

Run:

```bash
git branch --show-current
git status --short --ignored
```

Expected:

- Branch is the intended development branch.
- No unrelated tracked modifications are present.
- Ignored artifacts may include `data/real/`, `data/processed/`, `reports/real_*`, `hf_cache/`.

- [ ] **Step 2: 确认真实数据和本地报告仍被忽略**

Run:

```bash
for artifact in \
  data/real/stage_data.csv \
  data/processed/fu13_real_observations.parquet \
  reports/real_leak_current_scenario_evaluation_baseline.md \
  reports/real_leak_current_scenario_evaluation_ttm.md \
  hf_cache/
do
  git check-ignore -q "$artifact" || { echo "not ignored: $artifact"; exit 1; }
  git check-ignore -v "$artifact"
done
```

Expected:

- All listed paths are ignored.

- [ ] **Step 3: 确认 `LeakElec` 配置是阶段来源**

Run:

```bash
uv run python - <<'PY'
from b08_model_core.real_data.fu13_config import load_fu13_real_data_config

cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")
sensor = cfg.sensor_by_id["LeakElec"]
print(sensor.scenario)
print(sensor.related_stages)
print(cfg.cycle_rules.waiting_stages)
PY
```

Expected:

- First line: `leak_current_monitoring`
- Related stages include `抽真空`, `氩气导入`, `溶解`, `测温`, `浇筑`, `冷却`.
- Waiting stages include `上盖开启`.

---

## Task 2: Rolling baseline

**Files:**
- Create: `tests/test_rolling_baseline.py`
- Create: `src/b08_model_core/baselines/rolling.py`
- Modify: `src/b08_model_core/baselines/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_rolling_baseline.py`:

```python
import numpy as np

from b08_model_core.baselines.rolling import RollingSensorForecaster
from b08_model_core.tasks.window_builder import ModelWindow


def _window(values, mask=None):
    x = np.asarray(values, dtype=float)
    if mask is None:
        mask = np.ones_like(x, dtype=bool)
    return ModelWindow(
        X=x,
        mask=np.asarray(mask, dtype=bool),
        delta_t=np.zeros(x.shape[0]),
        stage_token=np.array(["溶解"] * x.shape[0], dtype=object),
        sensor_token=["LeakElec", "Other"],
        domain_token=["electrical", "other"],
        device_token="FU13",
        y=np.zeros((3, x.shape[1])),
        degradation_label="normal",
    )


def test_rolling_sensor_forecaster_repeats_context_tail_mean():
    window = _window([[1, 10], [2, 20], [3, 30], [4, 40]])

    predictions = RollingSensorForecaster(window_size=2).fit([]).predict([window])

    assert predictions["y_hat"].shape == (1, 3, 2)
    np.testing.assert_allclose(predictions["y_hat"][0], [[3.5, 35.0], [3.5, 35.0], [3.5, 35.0]])


def test_rolling_sensor_forecaster_ignores_masked_context_values():
    window = _window(
        [[1, 10], [2, 20], [3, 30], [4, 40]],
        mask=[[True, True], [True, True], [False, True], [True, False]],
    )

    predictions = RollingSensorForecaster(window_size=2).fit([]).predict([window])

    np.testing.assert_allclose(predictions["y_hat"][0], [[4.0, 30.0], [4.0, 30.0], [4.0, 30.0]])
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run python -m pytest tests/test_rolling_baseline.py -v
```

Expected:

- FAIL because `b08_model_core.baselines.rolling` does not exist.

- [ ] **Step 3: Implement minimal rolling baseline**

Create `src/b08_model_core/baselines/rolling.py`:

```python
from __future__ import annotations

import numpy as np


class RollingSensorForecaster:
    def __init__(self, window_size: int = 8) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be greater than 0")
        self.window_size = window_size

    def fit(self, windows: list[object]) -> "RollingSensorForecaster":
        return self

    def predict(self, windows: list[object]) -> dict[str, np.ndarray]:
        predictions = []
        for window in windows:
            context = np.asarray(window.X, dtype=float)
            mask = np.asarray(window.mask, dtype=bool)
            tail = context[-self.window_size :]
            tail_mask = mask[-self.window_size :]
            baseline = self._masked_mean(tail, tail_mask)
            horizon = int(window.y.shape[0])
            predictions.append(np.repeat(baseline[None, :], horizon, axis=0))
        return {"y_hat": np.stack(predictions, axis=0)}

    @staticmethod
    def _masked_mean(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
        masked = np.where(mask, values, np.nan)
        means = np.nanmean(masked, axis=0)
        return np.nan_to_num(means, nan=0.0)
```

Modify `src/b08_model_core/baselines/__init__.py`:

```python
from b08_model_core.baselines.rolling import RollingSensorForecaster

__all__ = ["RollingSensorForecaster"]
```

If `__init__.py` already exports other names, preserve them and add `RollingSensorForecaster`.

- [ ] **Step 4: Run rolling baseline tests**

Run:

```bash
uv run python -m pytest tests/test_rolling_baseline.py -v
```

Expected:

- PASS.

- [ ] **Step 5: Commit rolling baseline**

Run:

```bash
git add src/b08_model_core/baselines/rolling.py src/b08_model_core/baselines/__init__.py tests/test_rolling_baseline.py
git commit -m "feat: add rolling sensor baseline"
```

---

## Task 3: Scenario selection and quality filtering

**Files:**
- Create: `tests/test_scenario_evaluation.py`
- Create: `src/b08_model_core/real_data/scenario_evaluation.py`

- [ ] **Step 1: Write failing selection tests**

Create `tests/test_scenario_evaluation.py` with these first tests:

```python
import pandas as pd

from b08_model_core.real_data.fu13_config import load_fu13_real_data_config
from b08_model_core.real_data.scenario_evaluation import select_scenario_observations


def _frame():
    rows = []
    ts = pd.date_range("2026-05-01", periods=6, freq="5s", tz="UTC")
    stages = ["抽真空", "溶解", "浇筑", "上盖开启", "冷却", "停机"]
    flags = ["good", "invalid", "unassigned_cycle", "good", "good", "good"]
    for i, stage in enumerate(stages):
        for sensor, scenario, domain in [
            ("LeakElec", "leak_current_monitoring", "electrical"),
            ("O2Content", "atmosphere_detection", "atmosphere"),
        ]:
            rows.append(
                {
                    "timestamp": ts[i],
                    "device_id": "FU13",
                    "batch_id": "cycle_0001" if flags[i] != "unassigned_cycle" else "unassigned_cycle",
                    "stage": stage,
                    "sensor_id": sensor,
                    "value": float(i),
                    "unit": "ma",
                    "domain": domain,
                    "quality_flag": flags[i],
                    "degradation_label": "normal",
                    "failure_proxy": False,
                }
            )
    return pd.DataFrame(rows)


def test_select_scenario_observations_uses_leakelec_related_stages():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    selected, summary = select_scenario_observations(
        _frame(),
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="all",
        stage_scope="related",
    )

    assert set(selected["sensor_id"]) == {"LeakElec"}
    assert "上盖开启" not in set(selected["stage"])
    assert "停机" not in set(selected["stage"])
    assert summary.scenario == "leak_current_monitoring"
    assert summary.sensor_ids == ["LeakElec"]
    assert summary.related_stages == ["抽真空", "氩气导入", "溶解", "测温", "浇筑", "冷却"]


def test_select_scenario_observations_can_include_waiting_stage_for_comparison():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    selected, summary = select_scenario_observations(
        _frame(),
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="all",
        stage_scope="with_waiting",
    )

    assert "上盖开启" in set(selected["stage"])
    assert summary.waiting_rows == 1


def test_select_scenario_observations_applies_quality_modes():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    good_only, _ = select_scenario_observations(
        _frame(),
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="good_only",
        stage_scope="with_waiting",
    )
    drop_invalid, _ = select_scenario_observations(
        _frame(),
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="drop_invalid",
        stage_scope="with_waiting",
    )
    drop_unassigned, _ = select_scenario_observations(
        _frame(),
        cfg,
        scenario="leak_current_monitoring",
        quality_mode="drop_unassigned_cycle",
        stage_scope="with_waiting",
    )

    assert set(good_only["quality_flag"]) == {"good"}
    assert "invalid" not in set(drop_invalid["quality_flag"])
    assert "unassigned_cycle" not in set(drop_unassigned["quality_flag"])
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run python -m pytest tests/test_scenario_evaluation.py -v
```

Expected:

- FAIL because `scenario_evaluation.py` does not exist.

- [ ] **Step 3: Implement selection primitives**

Create `src/b08_model_core/real_data/scenario_evaluation.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from b08_model_core.real_data.fu13_config import FU13RealDataConfig, FU13SensorConfig


QUALITY_MODES = {"all", "good_only", "drop_invalid", "drop_unassigned_cycle"}
STAGE_SCOPES = {"related", "with_waiting"}


@dataclass
class ScenarioSelectionSummary:
    scenario: str
    sensor_ids: list[str]
    related_stages: list[str]
    waiting_stages: list[str]
    stage_scope: str
    quality_mode: str
    input_rows: int
    selected_rows: int
    waiting_rows: int
    quality_counts: dict[str, int]


def select_scenario_observations(
    df: pd.DataFrame,
    cfg: FU13RealDataConfig,
    *,
    scenario: str,
    quality_mode: str,
    stage_scope: str,
) -> tuple[pd.DataFrame, ScenarioSelectionSummary]:
    if quality_mode not in QUALITY_MODES:
        raise ValueError(f"unsupported quality_mode: {quality_mode}")
    if stage_scope not in STAGE_SCOPES:
        raise ValueError(f"unsupported stage_scope: {stage_scope}")

    sensors = [sensor for sensor in cfg.sensors if sensor.scenario == scenario]
    if not sensors:
        raise ValueError(f"unknown scenario: {scenario}")

    sensor_ids = [sensor.sensor_id for sensor in sensors]
    related_stages = _ordered_unique(stage for sensor in sensors for stage in sensor.related_stages)
    waiting_stages = list(cfg.cycle_rules.waiting_stages)
    allowed_stages = related_stages if stage_scope == "related" else _ordered_unique([*related_stages, *waiting_stages])

    selected = df[df["sensor_id"].isin(sensor_ids) & df["stage"].isin(allowed_stages)].copy()
    selected = _apply_quality_mode(selected, quality_mode)
    waiting_rows = int(selected["stage"].isin(waiting_stages).sum())
    summary = ScenarioSelectionSummary(
        scenario=scenario,
        sensor_ids=sensor_ids,
        related_stages=related_stages,
        waiting_stages=waiting_stages,
        stage_scope=stage_scope,
        quality_mode=quality_mode,
        input_rows=int(len(df)),
        selected_rows=int(len(selected)),
        waiting_rows=waiting_rows,
        quality_counts={str(k): int(v) for k, v in selected["quality_flag"].value_counts().items()},
    )
    return selected, summary


def _apply_quality_mode(df: pd.DataFrame, quality_mode: str) -> pd.DataFrame:
    if quality_mode == "all":
        return df
    if quality_mode == "good_only":
        return df[df["quality_flag"] == "good"].copy()
    if quality_mode == "drop_invalid":
        return df[df["quality_flag"] != "invalid"].copy()
    if quality_mode == "drop_unassigned_cycle":
        return df[df["quality_flag"] != "unassigned_cycle"].copy()
    raise ValueError(f"unsupported quality_mode: {quality_mode}")


def _ordered_unique(values) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
```

- [ ] **Step 4: Run scenario selection tests**

Run:

```bash
uv run python -m pytest tests/test_scenario_evaluation.py -v
```

Expected:

- PASS.

- [ ] **Step 5: Commit scenario selection**

Run:

```bash
git add src/b08_model_core/real_data/scenario_evaluation.py tests/test_scenario_evaluation.py
git commit -m "feat: select leak current scenario windows"
```

---

## Task 4: Scenario evaluation runner and residual signal summary

**Files:**
- Modify: `tests/test_scenario_evaluation.py`
- Modify: `src/b08_model_core/real_data/scenario_evaluation.py`

- [ ] **Step 1: Add failing runner/report tests**

Append to `tests/test_scenario_evaluation.py`:

```python
import numpy as np

from b08_model_core.real_data.scenario_evaluation import (
    render_scenario_evaluation_report,
    run_scenario_evaluation,
)


def _long_leak_frame(path):
    timestamps = pd.date_range("2026-05-01", periods=220, freq="5s", tz="UTC")
    rows = []
    for i, ts in enumerate(timestamps):
        stage = "溶解" if i < 110 else "浇筑"
        value = 10 + np.sin(i / 8)
        if i in {150, 151, 152}:
            value += 15
        rows.append(
            {
                "timestamp": ts,
                "device_id": "FU13",
                "batch_id": "cycle_0001",
                "stage": stage,
                "sensor_id": "LeakElec",
                "value": value,
                "unit": "ma",
                "domain": "electrical",
                "quality_flag": "good",
                "degradation_label": "normal",
                "failure_proxy": False,
            }
        )
    pd.DataFrame(rows).to_parquet(path, index=False)


def test_run_scenario_evaluation_reports_rolling_baseline_and_candidate_signals(tmp_path):
    dataset = tmp_path / "leak.parquet"
    _long_leak_frame(dataset)
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    result = run_scenario_evaluation(
        dataset,
        cfg,
        scenario="leak_current_monitoring",
        model="baseline",
        quality_modes=["good_only"],
        stage_scopes=["related"],
        context_length=32,
        prediction_length=8,
        max_windows=8,
        rolling_window_size=4,
        allow_download=False,
        model_cache_dir=None,
    )
    text = render_scenario_evaluation_report(result)

    assert result.scenario == "leak_current_monitoring"
    assert result.model == "BaselineOnly"
    assert "RollingSensorForecaster" in result.runs[0].metrics
    assert "candidate residual signals" in text
    assert "not a failure prediction" in text
    assert "候选异常信号" in text
    assert "residual_mae" in text
    assert "residual_rmse" in text
    assert "top_window_stage_summary" in text
    assert result.runs[0].candidate_signal["abs_residual_p95"] >= 0
    assert result.runs[0].candidate_signal["residual_mae"] >= 0
    assert result.runs[0].candidate_signal["residual_rmse"] >= 0
    assert result.runs[0].candidate_signal["top_windows"]


def test_run_scenario_evaluation_reports_not_enough_windows(tmp_path):
    dataset = tmp_path / "short.parquet"
    timestamps = pd.date_range("2026-05-01", periods=20, freq="5s", tz="UTC")
    pd.DataFrame(
        [
            {
                "timestamp": ts,
                "device_id": "FU13",
                "batch_id": "cycle_0001",
                "stage": "溶解",
                "sensor_id": "LeakElec",
                "value": float(i),
                "unit": "ma",
                "domain": "electrical",
                "quality_flag": "good",
                "degradation_label": "normal",
                "failure_proxy": False,
            }
            for i, ts in enumerate(timestamps)
        ]
    ).to_parquet(dataset, index=False)
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    result = run_scenario_evaluation(
        dataset,
        cfg,
        scenario="leak_current_monitoring",
        model="baseline",
        quality_modes=["good_only"],
        stage_scopes=["related"],
        context_length=32,
        prediction_length=8,
        max_windows=8,
        rolling_window_size=4,
        allow_download=False,
        model_cache_dir=None,
    )

    assert result.runs[0].candidate_signal["status"] == "not_enough_windows"
    assert result.runs[0].test_windows == 0
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run python -m pytest tests/test_scenario_evaluation.py::test_run_scenario_evaluation_reports_rolling_baseline_and_candidate_signals -v
```

Expected:

- FAIL because runner/report functions do not exist.

- [ ] **Step 3: Implement runner dataclasses**

Extend `src/b08_model_core/real_data/scenario_evaluation.py`:

```python
from pathlib import Path
from collections.abc import Sequence

import numpy as np

from b08_model_core.adapters.ttm_adapter import TTMForecastAdapter
from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.baselines.rolling import RollingSensorForecaster
from b08_model_core.baselines.seasonal_naive import StageSeasonalNaiveForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.experiments.forecasting import BaselineOnlyAdapter
from b08_model_core.foundation.results import FoundationForecastResult, FoundationModelStatus
from b08_model_core.tasks.window_builder import build_model_windows
```

Add dataclasses:

```python
@dataclass
class ScenarioRunResult:
    quality_mode: str
    stage_scope: str
    selection: ScenarioSelectionSummary
    train_windows: int
    test_windows: int
    metrics: dict[str, dict[str, float | int | None]]
    foundation_result: FoundationForecastResult
    candidate_signal: dict[str, object]


@dataclass
class ScenarioEvaluationResult:
    scenario: str
    model: str
    context_length: int
    prediction_length: int
    max_windows: int
    rolling_window_size: int
    runs: list[ScenarioRunResult]
```

- [ ] **Step 4: Implement `run_scenario_evaluation`**

Add:

```python
def run_scenario_evaluation(
    dataset_path: str | Path,
    cfg: FU13RealDataConfig,
    *,
    scenario: str,
    model: str,
    quality_modes: Sequence[str],
    stage_scopes: Sequence[str],
    context_length: int,
    prediction_length: int,
    max_windows: int,
    rolling_window_size: int,
    allow_download: bool,
    model_cache_dir: str | None,
) -> ScenarioEvaluationResult:
    if model not in {"baseline", "ttm"}:
        raise ValueError(f"unsupported scenario evaluation model: {model}")
    df = pd.read_parquet(dataset_path)
    runs: list[ScenarioRunResult] = []
    model_name = "BaselineOnly" if model == "baseline" else "TTM"

    for quality_mode in quality_modes:
        for stage_scope in stage_scopes:
            selected, selection = select_scenario_observations(
                df,
                cfg,
                scenario=scenario,
                quality_mode=quality_mode,
                stage_scope=stage_scope,
            )
            windows = build_model_windows(
                selected,
                context_length=context_length,
                prediction_length=prediction_length,
                stride=prediction_length,
                allow_cross_stage=True,
            )[:max_windows]
            if len(windows) < 2:
                runs.append(_not_enough_windows_run(quality_mode, stage_scope, selection, len(windows)))
                continue

            split = max(1, int(len(windows) * 0.7))
            train = windows[:split]
            test = windows[split:]
            if not test:
                runs.append(_not_enough_windows_run(quality_mode, stage_scope, selection, len(windows)))
                continue

            predictions = {
                "RobustStageForecaster": RobustStageForecaster().fit(train).predict(test),
                "StageSeasonalNaiveForecaster": StageSeasonalNaiveForecaster().fit(train).predict(test),
                "RollingSensorForecaster": RollingSensorForecaster(window_size=rolling_window_size).fit(train).predict(test),
            }
            metrics = {name: forecasting_metrics(pred, test) for name, pred in predictions.items()}
            foundation_result = _scenario_adapter(model).predict(
                test,
                context_length=context_length,
                prediction_length=prediction_length,
                allow_download=allow_download,
                model_cache_dir=model_cache_dir,
            )
            candidate_predictions = predictions["RollingSensorForecaster"]
            if foundation_result.succeeded and foundation_result.predictions():
                foundation_result.metrics = forecasting_metrics(foundation_result.predictions(), test)
                metrics["foundation"] = foundation_result.metrics
                candidate_predictions = foundation_result.predictions()

            runs.append(
                ScenarioRunResult(
                    quality_mode=quality_mode,
                    stage_scope=stage_scope,
                    selection=selection,
                    train_windows=len(train),
                    test_windows=len(test),
                    metrics=metrics,
                    foundation_result=foundation_result,
                    candidate_signal=_candidate_signal_summary(candidate_predictions, test),
                )
            )

    return ScenarioEvaluationResult(
        scenario=scenario,
        model=model_name,
        context_length=context_length,
        prediction_length=prediction_length,
        max_windows=max_windows,
        rolling_window_size=rolling_window_size,
        runs=runs,
    )
```

Implement helpers:

```python
def _scenario_adapter(model: str):
    if model == "baseline":
        return BaselineOnlyAdapter()
    if model == "ttm":
        return TTMForecastAdapter()
    raise ValueError(f"unsupported scenario evaluation model: {model}")


def _not_enough_windows_run(quality_mode, stage_scope, selection, window_count):
    return ScenarioRunResult(
        quality_mode=quality_mode,
        stage_scope=stage_scope,
        selection=selection,
        train_windows=window_count,
        test_windows=0,
        metrics={},
        foundation_result=FoundationForecastResult(
            model_name="not_available",
            adapter_name="scenario_evaluation",
            status=FoundationModelStatus.SKIPPED_BY_USER,
            reason="not enough windows for scenario evaluation",
            dependency_status="not_required",
            weight_status="not_attempted",
        ),
        candidate_signal={"status": "not_enough_windows", "window_count": int(window_count)},
    )


def _candidate_signal_summary(predictions: dict[str, np.ndarray], windows: list[object]) -> dict[str, object]:
    truth = np.stack([window.y for window in windows], axis=0)
    y_hat = np.asarray(predictions["y_hat"], dtype=float)
    residual = y_hat - truth
    abs_residual = np.abs(residual).reshape(-1)
    if abs_residual.size == 0:
        return {"status": "not_available"}
    per_window_abs = np.abs(residual).reshape(residual.shape[0], -1)
    top_order = np.argsort(per_window_abs.max(axis=1))[::-1][:3]
    p95 = float(np.percentile(abs_residual, 95))
    p99 = float(np.percentile(abs_residual, 99))
    return {
        "status": "available",
        "residual_mae": float(np.mean(abs_residual)),
        "residual_rmse": float(np.sqrt(np.mean(residual**2))),
        "abs_residual_p50": float(np.percentile(abs_residual, 50)),
        "abs_residual_p90": float(np.percentile(abs_residual, 90)),
        "abs_residual_p95": p95,
        "abs_residual_p99": p99,
        "points_above_p95": int((abs_residual > p95).sum()),
        "points_above_p99": int((abs_residual > p99).sum()),
        "top_windows": [
            {
                "window_index": int(index),
                "max_abs_residual": float(per_window_abs[index].max()),
                "mean_abs_residual": float(per_window_abs[index].mean()),
                "top_window_stage_summary": _stage_summary(windows[int(index)]),
            }
            for index in top_order
        ],
    }


def _stage_summary(window: object) -> str:
    values, counts = np.unique(np.asarray(window.stage_token, dtype=object), return_counts=True)
    return ", ".join(f"{value}:{int(count)}" for value, count in zip(values, counts, strict=False))
```

- [ ] **Step 5: Implement Markdown rendering**

Add:

```python
def render_scenario_evaluation_report(result: ScenarioEvaluationResult) -> str:
    lines = [
        "# Leak Current Scenario Evaluation",
        "",
        "This report evaluates forecasting residuals as candidate residual signals, not a failure prediction, RUL, maintenance recommendation, or production alarm.",
        "本报告只讨论候选异常信号，不是故障预测、RUL、维修建议或生产告警。",
        "",
        "## Summary",
        f"- scenario: {result.scenario}",
        f"- model: {result.model}",
        f"- context_length: {result.context_length}",
        f"- prediction_length: {result.prediction_length}",
        f"- max_windows: {result.max_windows}",
        f"- rolling_window_size: {result.rolling_window_size}",
        "",
    ]
    for run in result.runs:
        lines.extend(_render_run(run))
    return "\n".join(lines) + "\n"
```

Implement `_render_run(run)` with sections:

- `## Run: quality=<mode>, stage_scope=<scope>`
- selection rows, waiting rows, related stages.
- train/test windows.
- metric table with Robust, Seasonal, Rolling, and foundation if present.
- candidate residual signal table.
- top residual windows table with `window_index`, `max_abs_residual`, `mean_abs_residual`, and `top_window_stage_summary`.
- boundary note: “candidate residual signal only”.

Use the existing `_format_metric` and markdown escaping pattern from `real_data/forecasting.py`, or copy the small formatting helpers into `scenario_evaluation.py` to keep this module self-contained.

- [ ] **Step 6: Run scenario evaluation tests**

Run:

```bash
uv run python -m pytest tests/test_scenario_evaluation.py -v
```

Expected:

- PASS.

- [ ] **Step 7: Commit scenario runner**

Run:

```bash
git add src/b08_model_core/real_data/scenario_evaluation.py tests/test_scenario_evaluation.py
git commit -m "feat: evaluate leak current scenario residuals"
```

---

## Task 5: CLI entrypoint

**Files:**
- Modify: `src/b08_model_core/cli.py`
- Modify: `tests/test_cli_fu13_real_data.py`

- [ ] **Step 1: Add failing CLI test**

Append to `tests/test_cli_fu13_real_data.py`. Follow this file's existing `subprocess.run([sys.executable, "-m", "b08_model_core.cli", ...])` style rather than importing `main()` directly:

```python
def test_cli_evaluate_leak_current_scenario_writes_report(tmp_path):
    dataset = tmp_path / "leak.parquet"
    timestamps = pd.date_range("2026-05-01", periods=220, freq="5s", tz="UTC")
    rows = []
    for i, ts in enumerate(timestamps):
        rows.append(
            {
                "timestamp": ts,
                "device_id": "FU13",
                "batch_id": "cycle_0001",
                "stage": "溶解",
                "sensor_id": "LeakElec",
                "value": float(i % 20),
                "unit": "ma",
                "domain": "electrical",
                "quality_flag": "good",
                "degradation_label": "normal",
                "failure_proxy": False,
            }
        )
    pd.DataFrame(rows).to_parquet(dataset, index=False)
    output = tmp_path / "report.md"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "b08_model_core.cli",
            "real-data",
            "evaluate-scenario",
            "--dataset",
            str(dataset),
            "--config",
            "configs/fu13_real_data_schema.yaml",
            "--output",
            str(output),
            "--scenario",
            "leak_current_monitoring",
            "--model",
            "baseline",
            "--quality-mode",
            "good_only",
            "--stage-scope",
            "related",
            "--context-length",
            "32",
            "--prediction-length",
            "8",
            "--max-windows",
            "8",
        ],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    text = output.read_text(encoding="utf-8")
    assert "Leak Current Scenario Evaluation" in text
    assert "RollingSensorForecaster" in text
    assert "not a failure prediction" in text
```

Ensure the test file already imports `subprocess`, `sys`, and `pandas as pd`; add imports only if missing.

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run python -m pytest tests/test_cli_fu13_real_data.py::test_cli_evaluate_leak_current_scenario_writes_report -v
```

Expected:

- FAIL because `evaluate-scenario` CLI does not exist.

- [ ] **Step 3: Add CLI parser and command handler**

In `src/b08_model_core/cli.py`, import:

```python
from b08_model_core.real_data.scenario_evaluation import (
    render_scenario_evaluation_report,
    run_scenario_evaluation,
)
```

Add parser under `real_data_sub`:

```python
evaluate_scenario = real_data_sub.add_parser("evaluate-scenario")
evaluate_scenario.add_argument("--dataset", required=True)
evaluate_scenario.add_argument("--config", required=True)
evaluate_scenario.add_argument("--output", required=True)
evaluate_scenario.add_argument("--scenario", choices=["leak_current_monitoring"], required=True)
evaluate_scenario.add_argument("--model", choices=["baseline", "ttm"], required=True)
evaluate_scenario.add_argument("--quality-mode", action="append", dest="quality_modes")
evaluate_scenario.add_argument("--stage-scope", action="append", dest="stage_scopes")
evaluate_scenario.add_argument("--context-length", type=_positive_int, default=90)
evaluate_scenario.add_argument("--prediction-length", type=_positive_int, default=16)
evaluate_scenario.add_argument("--max-windows", type=_positive_int, default=40)
evaluate_scenario.add_argument("--rolling-window-size", type=_positive_int, default=8)
evaluate_scenario.add_argument("--model-cache-dir")
scenario_download = evaluate_scenario.add_mutually_exclusive_group()
scenario_download.add_argument("--allow-download", action="store_true", dest="allow_download")
scenario_download.add_argument("--no-download", action="store_false", dest="allow_download")
evaluate_scenario.set_defaults(allow_download=False)
```

Add handler:

```python
if args.command == "real-data" and args.real_data_command == "evaluate-scenario":
    cfg = load_fu13_real_data_config(args.config)
    result = run_scenario_evaluation(
        args.dataset,
        cfg,
        scenario=args.scenario,
        model=args.model,
        quality_modes=args.quality_modes or ["all", "good_only", "drop_invalid", "drop_unassigned_cycle"],
        stage_scopes=args.stage_scopes or ["related", "with_waiting"],
        context_length=args.context_length,
        prediction_length=args.prediction_length,
        max_windows=args.max_windows,
        rolling_window_size=args.rolling_window_size,
        allow_download=args.allow_download,
        model_cache_dir=args.model_cache_dir,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_scenario_evaluation_report(result), encoding="utf-8")
    if args.model == "ttm" and any(run.foundation_result.status != FoundationModelStatus.AVAILABLE_AND_RAN for run in result.runs if run.test_windows):
        return 1
    return 0
```

- [ ] **Step 4: Run CLI test**

Run:

```bash
uv run python -m pytest tests/test_cli_fu13_real_data.py::test_cli_evaluate_leak_current_scenario_writes_report -v
```

Expected:

- PASS.

- [ ] **Step 5: Run related tests**

Run:

```bash
uv run python -m pytest tests/test_cli_fu13_real_data.py tests/test_scenario_evaluation.py tests/test_rolling_baseline.py -q
```

Expected:

- PASS.

- [ ] **Step 6: Commit CLI entrypoint**

Run:

```bash
git add src/b08_model_core/cli.py tests/test_cli_fu13_real_data.py
git commit -m "feat: add leak current scenario evaluation cli"
```

---

## Task 6: Local real-data evaluation and tracked summary

**Files:**
- Generated local-only: `reports/real_leak_current_scenario_evaluation_baseline.md`
- Generated local-only: `reports/real_leak_current_scenario_evaluation_ttm.md`
- Create: `docs/leak-current-scenario-evaluation.md`
- Modify: `docs/index.html`
- Modify: `README.md`
- Modify: `details.md`

- [ ] **Step 1: Confirm canonical parquet exists**

Run:

```bash
test -f data/processed/fu13_real_observations.parquet && ls -lh data/processed/fu13_real_observations.parquet
```

Expected:

- File exists.

If missing, assemble using the README command and keep generated parquet ignored.

- [ ] **Step 2: Run baseline scenario evaluation**

Run:

```bash
uv run b08-model-core real-data evaluate-scenario \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_leak_current_scenario_evaluation_baseline.md \
  --scenario leak_current_monitoring \
  --model baseline \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --rolling-window-size 8
```

Expected:

- Exit `0`.
- Report contains `Leak Current Scenario Evaluation`, `RollingSensorForecaster`, quality modes, stage scopes, and candidate residual signal sections.

- [ ] **Step 3: Run TTM scenario evaluation if cache/dependency is available**

Use local cache if present:

```bash
HF_HOME=hf_cache uv run b08-model-core real-data evaluate-scenario \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_leak_current_scenario_evaluation_ttm.md \
  --scenario leak_current_monitoring \
  --model ttm \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --rolling-window-size 8 \
  --model-cache-dir hf_cache \
  --no-download
```

Expected if dependency/cache is available:

- Exit `0`.
- Report contains `status: available_and_ran` for runs with test windows.

If TTM is unavailable:

- Keep the generated report if written.
- Record the precise blocker in `docs/leak-current-scenario-evaluation.md`.
- Do not claim TTM scenario evaluation succeeded.

- [ ] **Step 4: Extract key values from local reports**

Run:

```bash
rg -n "scenario:|model:|quality=|stage_scope=|RobustStageForecaster|StageSeasonalNaiveForecaster|RollingSensorForecaster|foundation|abs_residual_p95|not a failure prediction|status:" \
  reports/real_leak_current_scenario_evaluation_baseline.md \
  reports/real_leak_current_scenario_evaluation_ttm.md
```

Expected:

- Output includes enough lines to summarize metrics and candidate residual signals.

- [ ] **Step 5: Write tracked summary report**

Create `docs/leak-current-scenario-evaluation.md` with sections:

```markdown
# 漏液电流监测场景评测报告

## 评测目标

说明本报告验证 `leak_current_monitoring` 的业务场景评测口径，不是故障预测、RUL、维护建议或生产告警。

## 数据与场景口径

- scenario: `leak_current_monitoring`
- sensor: `LeakElec`
- related stages: 来自 `configs/fu13_real_data_schema.yaml` 的 `LeakElec.related_stages`
- waiting stage comparison: `related` vs `with_waiting`
- quality modes: `all`, `good_only`, `drop_invalid`, `drop_unassigned_cycle`

## Baseline 与 TTM 结果

汇总本地 ignored reports 的关键指标。不要粘贴整份本地报告。

## 候选异常信号

说明 residual p95/p99、top residual windows 和尖峰/趋势能说明什么。

## 边界

- 当前只是 forecasting residual candidate signal。
- 缺少真实故障标签、维修记录和维护闭环时不能推出故障概率或维修建议。

## 下一步

说明是否建议复制到 `atmosphere_detection`，或先补维修记录/专家复核。
```

- [ ] **Step 6: Update docs index, README, and details**

Update:

- `docs/index.html`: add a card for `leak-current-scenario-evaluation.md`.
- `README.md`: add the `evaluate-scenario` command near the real-data workflow and link the new report.
- `details.md`: add a recent update line and adjust current conclusion only if the real evaluation actually ran.

- [ ] **Step 7: Verify generated reports remain ignored**

Run:

```bash
git status --short --ignored
git check-ignore -v reports/real_leak_current_scenario_evaluation_baseline.md reports/real_leak_current_scenario_evaluation_ttm.md
```

Expected:

- Local reports are ignored.
- Tracked changes only include docs and source/test files.

- [ ] **Step 8: Commit documentation summary**

Run:

```bash
git add docs/leak-current-scenario-evaluation.md docs/index.html README.md details.md
git commit -m "docs: summarize leak current scenario evaluation"
```

---

## Task 7: Final verification

**Files:**
- Read: all touched files.

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run python -m pytest \
  tests/test_rolling_baseline.py \
  tests/test_scenario_evaluation.py \
  tests/test_cli_fu13_real_data.py \
  -q
```

Expected:

- PASS.

- [ ] **Step 2: Run full tests**

Run:

```bash
uv run python -m pytest -q
```

Expected:

- PASS.

- [ ] **Step 3: Check formatting and git status**

Run:

```bash
git diff --check
git status --short --ignored
```

Expected:

- `git diff --check` has no output.
- No real data, parquet, local reports, or cache are staged.

- [ ] **Step 4: Confirm report language is bounded**

Run:

```bash
rg -n "故障概率|RUL|维修建议|生产告警|not a failure prediction|候选异常|candidate" \
  docs/leak-current-scenario-evaluation.md \
  reports/real_leak_current_scenario_evaluation_baseline.md \
  reports/real_leak_current_scenario_evaluation_ttm.md
```

Expected:

- The docs explicitly say candidate signals are not failure prediction, RUL, maintenance recommendation, or production alarm.
- No text claims production readiness.

- [ ] **Step 5: Final commit if verification required doc touch-ups**

Only if Step 1-4 required edits:

```bash
git add <changed tracked files>
git commit -m "fix: clarify leak current evaluation boundaries"
```

---

## Execution notes

- If a CLI TTM run fails because optional dependencies or cache are missing, do not debug model installation unless the user explicitly asks. Record the blocker and keep baseline scenario evaluation complete.
- If quality mode filtering leaves too few windows for some mode/scope, report `not_enough_windows` for that run rather than failing the whole command.
- If `RollingSensorForecaster` triggers `RuntimeWarning: Mean of empty slice`, replace the `np.nanmean` block with explicit masked sums/counts:

```python
counts = mask.sum(axis=0)
totals = np.where(mask, values, 0.0).sum(axis=0)
return np.divide(totals, counts, out=np.zeros_like(totals, dtype=float), where=counts > 0)
```

- Keep changes surgical. Do not refactor `window_builder.py` unless tests prove it cannot support scenario evaluation.
