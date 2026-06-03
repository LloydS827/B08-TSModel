# Real Data Validation Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 FU13 真实多 CSV 导出装配为 canonical observation 数据，完成数据质量/场景诊断，并在真实窗口上完成 baseline 与 TTM 的同口径验证。

**Architecture:** 新增 FU13 专用真实数据路径，不改动现有通用 `schema_map.py`。多 CSV 装配、连续炉 cycle 重构、诊断报告和真实数据 forecasting 各自独立成小模块；最终通过 CLI 串起 `assemble -> diagnose -> forecast` 闭环。TTM 在本阶段是必须尝试并报告的验证项，但不要求一定优于 baseline。

**Tech Stack:** Python 3.11+, pandas, numpy, pydantic, PyYAML, pyarrow, pytest, uv, existing `b08_model_core` CLI, optional `foundation-ttm` dependencies for TTM.

---

## 权威输入

- 设计文档：`docs/superpowers/specs/2026-06-02-real-data-validation-loop-design.md`
- 真实数据说明：`data/real/readme.md`
- 参数信息：`data/real/参数信息.md`
- 阶段数据：`data/real/stage_data.csv`
- 现有 schema 校验：`src/b08_model_core/tasks/schema.py`
- 现有窗口构建：`src/b08_model_core/tasks/window_builder.py`
- 现有 baseline：`src/b08_model_core/baselines/`
- 现有 TTM adapter：`src/b08_model_core/adapters/ttm_adapter.py`
- 现有基础模型 runner/report：`src/b08_model_core/foundation/`

## 范围守卫

- 不修改 `data/real/` 原始文件。
- 不提交真实大数据 parquet、模型 cache、Hugging Face 权重。
- 不声称真实故障预测、RUL、维护建议或故障概率。
- 不实现 TimesFM、Chronos、Moirai 等其他 adapter。
- 不重构无关模块。

## 文件结构

Create:

- `configs/fu13_real_data_schema.yaml`
  - FU13 真实数据工程配置：文件名、tag、中文名、单位、上下限、domain、scenario、相关阶段、cycle 规则。
- `src/b08_model_core/real_data/fu13_config.py`
  - Pydantic 配置模型与 YAML loader。
- `src/b08_model_core/real_data/cycle_builder.py`
  - 连续炉 `cycle_id` 重构和 cycle 完整度判断。
- `src/b08_model_core/real_data/fu13_loader.py`
  - 读取多传感器 CSV，阶段对齐，metadata 填充，quality flag，生成 canonical observations。
- `src/b08_model_core/real_data/diagnostics.py`
  - 数据质量、阶段、cycle、传感器、场景诊断统计和 Markdown 渲染。
- `src/b08_model_core/real_data/forecasting.py`
  - 真实数据窗口模式、scenario 过滤、baseline/TTM 同口径运行、按传感器/场景拆分指标和报告渲染。
- `tests/test_fu13_real_config.py`
- `tests/test_fu13_cycle_builder.py`
- `tests/test_fu13_loader.py`
- `tests/test_fu13_diagnostics.py`
- `tests/test_cli_fu13_real_data.py`
- `tests/test_real_data_forecasting.py`

Modify:

- `src/b08_model_core/real_data/__init__.py`
  - 导出新增入口。
- `src/b08_model_core/cli.py`
  - 新增 `real-data assemble-fu13`、`diagnose-fu13`、`forecast-fu13`。
- `details.md`
  - 实现和验证完成后更新阶段台账。
- `.gitignore`
  - 确认忽略 `data/processed/*.parquet`、临时真实数据产物、模型 cache；如果已有则不改。

## 命令约定

使用当前环境里更可靠的 pytest 入口：

```bash
uv run python -m pytest -q
```

运行 TTM 前如需补依赖：

```bash
uv sync --extra dev --extra foundation-ttm
```

TTM 权重和 cache 仍只保存在本机，例如 `hf_cache/`。

---

## Task 1: FU13 真实数据配置

**Files:**
- Create: `configs/fu13_real_data_schema.yaml`
- Create: `src/b08_model_core/real_data/fu13_config.py`
- Modify: `src/b08_model_core/real_data/__init__.py`
- Test: `tests/test_fu13_real_config.py`

- [ ] **Step 1: 写失败测试：配置能加载 8 个传感器**

Create `tests/test_fu13_real_config.py`:

```python
from pathlib import Path

from b08_model_core.real_data.fu13_config import load_fu13_real_data_config


def test_load_fu13_real_data_config_maps_all_sensors():
    cfg = load_fu13_real_data_config("configs/fu13_real_data_schema.yaml")

    assert cfg.device_id == "FU13"
    assert cfg.timezone_policy == "UTC"
    assert cfg.stage_file == "stage_data.csv"
    assert len(cfg.sensors) == 8
    assert {sensor.sensor_id for sensor in cfg.sensors} == {
        "O2Content2",
        "CrucibleForwardPressure",
        "CrucibleReturnPressure",
        "PumpShake1",
        "PumpShake2",
        "LeakElec",
        "O2Content",
        "SysSelfPressure",
    }
    assert cfg.sensor_by_id["O2Content"].domain == "atmosphere"
    assert cfg.sensor_by_id["LeakElec"].scenario == "leak_current_monitoring"
    assert Path(cfg.sensor_by_id["PumpShake1"].source_file).name == "FU13_Pump_01_PumpShake1.csv"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
uv run python -m pytest tests/test_fu13_real_config.py -v
```

Expected: FAIL because `fu13_config.py` and config file do not exist.

- [ ] **Step 3: 创建配置文件**

Create `configs/fu13_real_data_schema.yaml`:

```yaml
device_id: FU13
timezone_policy: UTC
stage_file: stage_data.csv
cycle_rules:
  start_stage: 上盖关闭
  required_order:
    - 上盖关闭
    - 溶解
    - 浇筑
  optional_stages:
    - 抽真空
    - 氩气导入
    - 测温
    - 冷却
  waiting_stages:
    - 上盖开启
sensors:
  - parameter_name: 下料口氧含量
    collector: FU13_Record
    source_tag: O2Content2
    sensor_id: O2Content2
    source_file: FU13_Record_O2Content2.csv
    lower_limit: -21
    upper_limit: 0
    unit: "%"
    domain: atmosphere
    scenario: atmosphere_detection
    related_stages: [浇筑]
  - parameter_name: 坩埚前倾压力
    collector: FU13
    source_tag: CrucibleForwardPressure
    sensor_id: CrucibleForwardPressure
    source_file: FU13_CrucibleForwardPressure.csv
    lower_limit: 0
    upper_limit: 12
    unit: MPa
    domain: hydraulic
    scenario: hydraulic_system_detection
    related_stages: [浇筑]
  - parameter_name: 坩埚回程压力
    collector: FU13
    source_tag: CrucibleReturnPressure
    sensor_id: CrucibleReturnPressure
    source_file: FU13_CrucibleReturnPressure.csv
    lower_limit: 0
    upper_limit: 12
    unit: MPa
    domain: hydraulic
    scenario: hydraulic_system_detection
    related_stages: [浇筑]
  - parameter_name: 机械泵振动1
    collector: FU13_Pump_01
    source_tag: PumpShake1
    sensor_id: PumpShake1
    source_file: FU13_Pump_01_PumpShake1.csv
    lower_limit: 0
    upper_limit: 10
    unit: um
    domain: mechanical
    scenario: pump_vibration
    related_stages: [抽真空]
  - parameter_name: 机械泵振动2
    collector: FU13_Pump_02
    source_tag: PumpShake2
    sensor_id: PumpShake2
    source_file: FU13_Pump_02_PumpShake2.csv
    lower_limit: 0
    upper_limit: 7
    unit: um
    domain: mechanical
    scenario: pump_vibration
    related_stages: [抽真空]
  - parameter_name: 泄漏电流
    collector: FU13_Record
    source_tag: LeakElec
    sensor_id: LeakElec
    source_file: FU13_Record_LeakElec.csv
    lower_limit: 0
    upper_limit: 60
    unit: ma
    domain: electrical
    scenario: leak_current_monitoring
    related_stages: [抽真空, 氩气导入, 溶解, 测温, 浇筑, 冷却]
  - parameter_name: 真空管氧含量
    collector: FU13_Record
    source_tag: O2Content
    sensor_id: O2Content
    source_file: FU13_Record_O2Content.csv
    lower_limit: -21
    upper_limit: 0
    unit: "%"
    domain: atmosphere
    scenario: atmosphere_detection
    related_stages: [溶解]
  - parameter_name: 系统压力
    collector: FU13
    source_tag: SysSelfPressure
    sensor_id: SysSelfPressure
    source_file: FU13_SysSelfPressure.csv
    lower_limit: 0
    upper_limit: 15
    unit: MPa
    domain: hydraulic
    scenario: hydraulic_system_detection
    related_stages: [浇筑]
```

- [ ] **Step 4: 实现配置模型**

Create `src/b08_model_core/real_data/fu13_config.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class FU13CycleRules(BaseModel):
    start_stage: str
    required_order: list[str]
    optional_stages: list[str] = []
    waiting_stages: list[str] = []


class FU13SensorConfig(BaseModel):
    parameter_name: str
    collector: str
    source_tag: str
    sensor_id: str
    source_file: str
    lower_limit: float
    upper_limit: float
    unit: str
    domain: str
    scenario: str
    related_stages: list[str]


class FU13RealDataConfig(BaseModel):
    device_id: str
    timezone_policy: str
    stage_file: str
    cycle_rules: FU13CycleRules
    sensors: list[FU13SensorConfig]

    @property
    def sensor_by_id(self) -> dict[str, FU13SensorConfig]:
        return {sensor.sensor_id: sensor for sensor in self.sensors}

    @property
    def sensor_by_file(self) -> dict[str, FU13SensorConfig]:
        return {sensor.source_file: sensor for sensor in self.sensors}


def load_fu13_real_data_config(path: str | Path) -> FU13RealDataConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return FU13RealDataConfig.model_validate(payload)
```

- [ ] **Step 5: 导出模块入口**

Modify `src/b08_model_core/real_data/__init__.py`:

```python
from b08_model_core.real_data.fu13_config import FU13RealDataConfig, load_fu13_real_data_config

__all__ = ["FU13RealDataConfig", "load_fu13_real_data_config"]
```

- [ ] **Step 6: 测试通过并提交**

Run:

```bash
uv run python -m pytest tests/test_fu13_real_config.py -v
```

Expected: PASS.

Commit:

```bash
git add configs/fu13_real_data_schema.yaml src/b08_model_core/real_data/fu13_config.py src/b08_model_core/real_data/__init__.py tests/test_fu13_real_config.py
git commit -m "feat: add fu13 real data config"
```

---

## Task 2: 连续炉 cycle 重构

**Files:**
- Create: `src/b08_model_core/real_data/cycle_builder.py`
- Test: `tests/test_fu13_cycle_builder.py`

- [ ] **Step 1: 写失败测试：有效 cycle 和 partial cycle**

Create `tests/test_fu13_cycle_builder.py`:

```python
import pandas as pd

from b08_model_core.real_data.cycle_builder import assign_cycle_ids, summarize_cycles
from b08_model_core.real_data.fu13_config import FU13CycleRules


def _rules():
    return FU13CycleRules(
        start_stage="上盖关闭",
        required_order=["上盖关闭", "溶解", "浇筑"],
        optional_stages=["抽真空", "氩气导入", "测温", "冷却"],
        waiting_stages=["上盖开启"],
    )


def test_assign_cycle_ids_marks_valid_cycles():
    stages = pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2026-05-01T00:00:00Z",
                    "2026-05-01T00:01:00Z",
                    "2026-05-01T00:02:00Z",
                    "2026-05-01T00:03:00Z",
                    "2026-05-01T00:04:00Z",
                    "2026-05-01T00:05:00Z",
                ],
                utc=True,
            ),
            "stage_name": ["上盖开启", "上盖关闭", "抽真空", "溶解", "浇筑", "冷却"],
        }
    )

    assigned, cycles = assign_cycle_ids(stages, _rules())

    assert cycles.iloc[0]["cycle_id"] == "cycle_0001"
    assert cycles.iloc[0]["cycle_status"] == "complete"
    assert assigned.loc[assigned["stage_name"].eq("溶解"), "cycle_id"].iloc[0] == "cycle_0001"
    assert assigned.loc[assigned["stage_name"].eq("上盖开启"), "cycle_status"].iloc[0] == "unassigned_cycle"


def test_assign_cycle_ids_marks_missing_required_stage_as_partial():
    stages = pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2026-05-01T00:00:00Z", "2026-05-01T00:01:00Z", "2026-05-01T00:02:00Z"],
                utc=True,
            ),
            "stage_name": ["上盖关闭", "溶解", "冷却"],
        }
    )

    assigned, cycles = assign_cycle_ids(stages, _rules())

    assert cycles.iloc[0]["cycle_status"] == "partial_cycle"
    assert assigned["cycle_id"].dropna().unique().tolist() == ["cycle_0001"]


def test_summarize_cycles_counts_statuses():
    cycles = pd.DataFrame({"cycle_id": ["cycle_0001", "cycle_0002"], "cycle_status": ["complete", "partial_cycle"]})

    summary = summarize_cycles(cycles)

    assert summary["total_cycles"] == 2
    assert summary["complete_cycles"] == 1
    assert summary["partial_cycles"] == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
uv run python -m pytest tests/test_fu13_cycle_builder.py -v
```

Expected: FAIL because `cycle_builder.py` does not exist.

- [ ] **Step 3: 实现 cycle builder**

Create `src/b08_model_core/real_data/cycle_builder.py`:

```python
from __future__ import annotations

import pandas as pd

from b08_model_core.real_data.fu13_config import FU13CycleRules


def assign_cycle_ids(stage_events: pd.DataFrame, rules: FU13CycleRules) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = stage_events.copy()
    events["time"] = pd.to_datetime(events["time"], utc=True, format="mixed")
    events = events.sort_values("time").reset_index(drop=True)
    events["cycle_id"] = pd.NA
    events["cycle_status"] = "unassigned_cycle"

    starts = events.index[events["stage_name"].eq(rules.start_stage)].tolist()
    cycle_records: list[dict[str, object]] = []
    for number, start_idx in enumerate(starts, start=1):
        next_start = starts[number] if number < len(starts) else len(events)
        idx = list(range(start_idx, next_start))
        cycle_id = f"cycle_{number:04d}"
        stages = events.loc[idx, "stage_name"].tolist()
        status = "complete" if _contains_required_order(stages, rules.required_order) else "partial_cycle"
        events.loc[idx, "cycle_id"] = cycle_id
        events.loc[idx, "cycle_status"] = status
        cycle_records.append(
            {
                "cycle_id": cycle_id,
                "cycle_status": status,
                "start_time": events.loc[start_idx, "time"],
                "end_time": events.loc[idx[-1], "time"],
                "stages": stages,
            }
        )

    cycles = pd.DataFrame(cycle_records)
    return events, cycles


def summarize_cycles(cycles: pd.DataFrame) -> dict[str, int]:
    statuses = cycles["cycle_status"].value_counts()
    return {
        "total_cycles": int(len(cycles)),
        "complete_cycles": int(statuses.get("complete", 0)),
        "partial_cycles": int(statuses.get("partial_cycle", 0)),
    }


def _contains_required_order(stages: list[str], required_order: list[str]) -> bool:
    cursor = 0
    for stage in stages:
        if cursor < len(required_order) and stage == required_order[cursor]:
            cursor += 1
    return cursor == len(required_order)
```

- [ ] **Step 4: 测试通过并提交**

Run:

```bash
uv run python -m pytest tests/test_fu13_cycle_builder.py -v
```

Expected: PASS.

Commit:

```bash
git add src/b08_model_core/real_data/cycle_builder.py tests/test_fu13_cycle_builder.py
git commit -m "feat: reconstruct fu13 real data cycles"
```

---

## Task 3: 多 CSV 装配 canonical observations

**Files:**
- Create: `src/b08_model_core/real_data/fu13_loader.py`
- Test: `tests/test_fu13_loader.py`

- [ ] **Step 1: 写失败测试：临时多 CSV 能装配为 canonical schema**

Create `tests/test_fu13_loader.py`:

```python
from pathlib import Path

import pandas as pd

from b08_model_core.real_data.fu13_loader import assemble_fu13_observations
from b08_model_core.tasks.schema import REQUIRED_OBSERVATION_COLUMNS, validate_observation_frame


def _write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    pd.DataFrame(rows, columns=["time", "value"]).to_csv(path, index=False)


def test_assemble_fu13_observations_from_multiple_sensor_files(tmp_path):
    (tmp_path / "stage_data.csv").write_text(
        "time,stage_name\n"
        "2026-05-01T00:00:00Z,上盖关闭\n"
        "2026-05-01T00:00:05Z,溶解\n"
        "2026-05-01T00:00:10Z,浇筑\n",
        encoding="utf-8",
    )
    _write_csv(tmp_path / "FU13_Record_O2Content.csv", [("2026-05-01T00:00:06Z", -20.0)])
    _write_csv(tmp_path / "FU13_Record_LeakElec.csv", [("2026-05-01T00:00:11Z", 61.0)])

    config = tmp_path / "config.yaml"
    config.write_text(
        """
device_id: FU13
timezone_policy: UTC
stage_file: stage_data.csv
cycle_rules:
  start_stage: 上盖关闭
  required_order: [上盖关闭, 溶解, 浇筑]
  optional_stages: []
  waiting_stages: [上盖开启]
sensors:
  - parameter_name: 真空管氧含量
    collector: FU13_Record
    source_tag: O2Content
    sensor_id: O2Content
    source_file: FU13_Record_O2Content.csv
    lower_limit: -21
    upper_limit: 0
    unit: "%"
    domain: atmosphere
    scenario: atmosphere_detection
    related_stages: [溶解]
  - parameter_name: 泄漏电流
    collector: FU13_Record
    source_tag: LeakElec
    sensor_id: LeakElec
    source_file: FU13_Record_LeakElec.csv
    lower_limit: 0
    upper_limit: 60
    unit: ma
    domain: electrical
    scenario: leak_current_monitoring
    related_stages: [浇筑]
""".strip(),
        encoding="utf-8",
    )

    observations, cycle_summary = assemble_fu13_observations(tmp_path, config)

    assert REQUIRED_OBSERVATION_COLUMNS <= set(observations.columns)
    assert validate_observation_frame(observations).valid
    assert set(observations["sensor_id"]) == {"O2Content", "LeakElec"}
    assert observations.loc[observations["sensor_id"].eq("O2Content"), "stage"].iloc[0] == "溶解"
    assert observations.loc[observations["sensor_id"].eq("LeakElec"), "quality_flag"].iloc[0] == "invalid"
    assert observations["batch_id"].iloc[0] == "cycle_0001"
    assert cycle_summary["complete_cycles"] == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
uv run python -m pytest tests/test_fu13_loader.py -v
```

Expected: FAIL because `fu13_loader.py` does not exist.

- [ ] **Step 3: 实现 loader**

Create `src/b08_model_core/real_data/fu13_loader.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from b08_model_core.real_data.cycle_builder import assign_cycle_ids, summarize_cycles
from b08_model_core.real_data.fu13_config import FU13SensorConfig, load_fu13_real_data_config


CANONICAL_COLUMNS = [
    "timestamp",
    "device_id",
    "batch_id",
    "stage",
    "sensor_id",
    "value",
    "unit",
    "domain",
    "quality_flag",
    "degradation_label",
    "failure_proxy",
]


def assemble_fu13_observations(input_dir: str | Path, config_path: str | Path) -> tuple[pd.DataFrame, dict[str, int]]:
    root = Path(input_dir)
    cfg = load_fu13_real_data_config(config_path)
    stage_events = _read_stage_events(root / cfg.stage_file)
    assigned_stages, cycles = assign_cycle_ids(stage_events, cfg.cycle_rules)
    aligned_stages = assigned_stages.rename(columns={"time": "timestamp", "stage_name": "stage"}).sort_values("timestamp")

    frames = [_read_sensor(root, cfg.device_id, sensor, aligned_stages) for sensor in cfg.sensors]
    observations = pd.concat(frames, ignore_index=True).sort_values(["timestamp", "sensor_id"])
    observations["batch_id"] = observations["batch_id"].fillna("unassigned_cycle")
    observations["quality_flag"] = observations.apply(_quality_flag, axis=1)
    return observations[CANONICAL_COLUMNS], summarize_cycles(cycles)


def _read_stage_events(path: Path) -> pd.DataFrame:
    events = pd.read_csv(path, encoding="utf-8-sig")
    events["time"] = pd.to_datetime(events["time"], utc=True, format="mixed")
    return events.sort_values("time")


def _read_sensor(root: Path, device_id: str, sensor: FU13SensorConfig, stages: pd.DataFrame) -> pd.DataFrame:
    raw = pd.read_csv(root / sensor.source_file, encoding="utf-8-sig")
    raw["timestamp"] = pd.to_datetime(raw["time"], utc=True, format="mixed")
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    raw = raw.sort_values("timestamp")
    merged = pd.merge_asof(raw[["timestamp", "value"]], stages, on="timestamp", direction="backward")
    merged["device_id"] = device_id
    merged["batch_id"] = merged["cycle_id"]
    merged["sensor_id"] = sensor.sensor_id
    merged["unit"] = sensor.unit
    merged["domain"] = sensor.domain
    merged["lower_limit"] = sensor.lower_limit
    merged["upper_limit"] = sensor.upper_limit
    merged["degradation_label"] = "normal"
    merged["failure_proxy"] = False
    return merged


def _quality_flag(row: pd.Series) -> str:
    if pd.isna(row.get("stage")):
        return "unassigned_stage"
    if pd.isna(row.get("cycle_id")):
        return "unassigned_cycle"
    if pd.isna(row.get("value")):
        return "missing"
    if row["value"] < row["lower_limit"] or row["value"] > row["upper_limit"]:
        return "invalid"
    return "good"
```

- [ ] **Step 4: 测试通过并提交**

Run:

```bash
uv run python -m pytest tests/test_fu13_loader.py -v
```

Expected: PASS.

Commit:

```bash
git add src/b08_model_core/real_data/fu13_loader.py tests/test_fu13_loader.py
git commit -m "feat: assemble fu13 real observations"
```

---

## Task 4: 数据质量和场景诊断报告

**Files:**
- Create: `src/b08_model_core/real_data/diagnostics.py`
- Test: `tests/test_fu13_diagnostics.py`

- [ ] **Step 1: 写失败测试：诊断报告覆盖质量和 4 个场景**

Create `tests/test_fu13_diagnostics.py`:

```python
import pandas as pd

from b08_model_core.real_data.diagnostics import build_fu13_diagnostics, render_fu13_diagnostics
from b08_model_core.real_data.fu13_config import FU13RealDataConfig, FU13CycleRules, FU13SensorConfig


def _cfg():
    sensors = [
        FU13SensorConfig(parameter_name="氧1", collector="c", source_tag="O2Content", sensor_id="O2Content", source_file="o2.csv", lower_limit=-21, upper_limit=0, unit="%", domain="atmosphere", scenario="atmosphere_detection", related_stages=["溶解"]),
        FU13SensorConfig(parameter_name="氧2", collector="c", source_tag="O2Content2", sensor_id="O2Content2", source_file="o22.csv", lower_limit=-21, upper_limit=0, unit="%", domain="atmosphere", scenario="atmosphere_detection", related_stages=["浇筑"]),
        FU13SensorConfig(parameter_name="振动", collector="c", source_tag="PumpShake1", sensor_id="PumpShake1", source_file="p.csv", lower_limit=0, upper_limit=10, unit="um", domain="mechanical", scenario="pump_vibration", related_stages=["抽真空"]),
        FU13SensorConfig(parameter_name="压力", collector="c", source_tag="SysSelfPressure", sensor_id="SysSelfPressure", source_file="s.csv", lower_limit=0, upper_limit=15, unit="MPa", domain="hydraulic", scenario="hydraulic_system_detection", related_stages=["浇筑"]),
        FU13SensorConfig(parameter_name="电流", collector="c", source_tag="LeakElec", sensor_id="LeakElec", source_file="l.csv", lower_limit=0, upper_limit=60, unit="ma", domain="electrical", scenario="leak_current_monitoring", related_stages=["溶解"]),
    ]
    return FU13RealDataConfig(
        device_id="FU13",
        timezone_policy="UTC",
        stage_file="stage_data.csv",
        cycle_rules=FU13CycleRules(start_stage="上盖关闭", required_order=["上盖关闭", "溶解", "浇筑"]),
        sensors=sensors,
    )


def test_render_fu13_diagnostics_mentions_scenarios_and_quality():
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-05-01T00:00:00Z"] * 5, utc=True),
            "device_id": ["FU13"] * 5,
            "batch_id": ["cycle_0001"] * 5,
            "stage": ["溶解", "浇筑", "抽真空", "浇筑", "溶解"],
            "sensor_id": ["O2Content", "O2Content2", "PumpShake1", "SysSelfPressure", "LeakElec"],
            "value": [-20, -19, 4, 14, 61],
            "unit": ["%", "%", "um", "MPa", "ma"],
            "domain": ["atmosphere", "atmosphere", "mechanical", "hydraulic", "electrical"],
            "quality_flag": ["good", "good", "good", "good", "invalid"],
            "degradation_label": ["normal"] * 5,
            "failure_proxy": [False] * 5,
        }
    )

    report = build_fu13_diagnostics(df, _cfg())
    text = render_fu13_diagnostics(report)

    assert "Real FU13 Data Diagnostics" in text
    assert "invalid" in text
    assert "atmosphere_detection" in text
    assert "pump_vibration" in text
    assert "hydraulic_system_detection" in text
    assert "leak_current_monitoring" in text
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
uv run python -m pytest tests/test_fu13_diagnostics.py -v
```

Expected: FAIL because diagnostics module does not exist.

- [ ] **Step 3: 实现诊断和 Markdown 渲染**

Create `src/b08_model_core/real_data/diagnostics.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from b08_model_core.real_data.fu13_config import FU13RealDataConfig


@dataclass(frozen=True)
class FU13DiagnosticsReport:
    rows: int
    sensors: int
    stages: int
    quality_counts: dict[str, int]
    sensor_summary: pd.DataFrame
    stage_summary: pd.DataFrame
    scenario_summary: pd.DataFrame


def build_fu13_diagnostics(df: pd.DataFrame, cfg: FU13RealDataConfig) -> FU13DiagnosticsReport:
    sensor_scenario = {sensor.sensor_id: sensor.scenario for sensor in cfg.sensors}
    enriched = df.copy()
    enriched["scenario"] = enriched["sensor_id"].map(sensor_scenario)
    sensor_summary = (
        enriched.groupby("sensor_id")["value"]
        .agg(["count", "min", "median", "max"])
        .reset_index()
    )
    stage_summary = enriched.groupby("stage").size().reset_index(name="rows")
    scenario_summary = (
        enriched.groupby("scenario")
        .agg(rows=("value", "size"), invalid_rows=("quality_flag", lambda s: int((s == "invalid").sum())))
        .reset_index()
    )
    return FU13DiagnosticsReport(
        rows=len(df),
        sensors=int(df["sensor_id"].nunique()),
        stages=int(df["stage"].nunique()),
        quality_counts={str(k): int(v) for k, v in df["quality_flag"].value_counts().items()},
        sensor_summary=sensor_summary,
        stage_summary=stage_summary,
        scenario_summary=scenario_summary,
    )


def render_fu13_diagnostics(report: FU13DiagnosticsReport) -> str:
    lines = [
        "# Real FU13 Data Diagnostics",
        "",
        f"- rows: {report.rows}",
        f"- sensors: {report.sensors}",
        f"- stages: {report.stages}",
        f"- quality_counts: {report.quality_counts}",
        "",
        "## Sensor Summary",
        report.sensor_summary.to_markdown(index=False),
        "",
        "## Stage Summary",
        report.stage_summary.to_markdown(index=False),
        "",
        "## Scenario Summary",
        report.scenario_summary.to_markdown(index=False),
        "",
        "## Interpretation Boundary",
        "This report describes data quality and candidate abnormal signals. It does not validate real failure prediction.",
    ]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: 测试通过并提交**

Run:

```bash
uv run python -m pytest tests/test_fu13_diagnostics.py -v
```

Expected: PASS.

Commit:

```bash
git add src/b08_model_core/real_data/diagnostics.py tests/test_fu13_diagnostics.py
git commit -m "feat: report fu13 real data diagnostics"
```

---

## Task 5: CLI 装配和诊断入口

**Files:**
- Modify: `src/b08_model_core/cli.py`
- Test: `tests/test_cli_fu13_real_data.py`

- [ ] **Step 1: 写失败测试：assemble-fu13 和 diagnose-fu13**

Create `tests/test_cli_fu13_real_data.py` with subprocess tests using small temp files. Keep it similar to `tests/test_cli_real_data_validate.py`.

Core assertions:

```python
assert assemble.returncode == 0
assert output_parquet.exists()
assert validation_report.exists()
assert "Real FU13 Data Validation" in validation_report.read_text(encoding="utf-8")

assert diagnose.returncode == 0
assert diagnostics_report.exists()
assert "Real FU13 Data Diagnostics" in diagnostics_report.read_text(encoding="utf-8")
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
uv run python -m pytest tests/test_cli_fu13_real_data.py -v
```

Expected: FAIL because CLI subcommands do not exist.

- [ ] **Step 3: 实现 CLI subcommands**

Modify `src/b08_model_core/cli.py`:

```python
from b08_model_core.real_data.diagnostics import build_fu13_diagnostics, render_fu13_diagnostics
from b08_model_core.real_data.fu13_config import load_fu13_real_data_config
from b08_model_core.real_data.fu13_loader import assemble_fu13_observations
from b08_model_core.tasks.schema import validate_observation_frame
```

Add under `real-data` subparser:

```python
assemble_fu13 = real_data_sub.add_parser("assemble-fu13")
assemble_fu13.add_argument("--input-dir", required=True)
assemble_fu13.add_argument("--config", required=True)
assemble_fu13.add_argument("--output", required=True)
assemble_fu13.add_argument("--report", required=True)

diagnose_fu13 = real_data_sub.add_parser("diagnose-fu13")
diagnose_fu13.add_argument("--dataset", required=True)
diagnose_fu13.add_argument("--config", required=True)
diagnose_fu13.add_argument("--output", required=True)
```

Add dispatch:

```python
if args.command == "real-data" and args.real_data_command == "assemble-fu13":
    observations, cycle_summary = assemble_fu13_observations(args.input_dir, args.config)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    observations.to_parquet(output, index=False)
    validation = validate_observation_frame(observations)
    report = [
        "# Real FU13 Data Validation",
        "",
        f"- schema_valid: {validation.valid}",
        f"- rows: {len(observations)}",
        f"- sensors: {observations['sensor_id'].nunique()}",
        f"- stages: {observations['stage'].nunique()}",
        f"- cycle_summary: {cycle_summary}",
        f"- quality_counts: {dict(observations['quality_flag'].value_counts())}",
    ]
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return 0 if validation.valid else 1

if args.command == "real-data" and args.real_data_command == "diagnose-fu13":
    cfg = load_fu13_real_data_config(args.config)
    df = pd.read_parquet(args.dataset)
    report = build_fu13_diagnostics(df, cfg)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_fu13_diagnostics(report), encoding="utf-8")
    return 0
```

Also import `Path` and `pandas as pd` if needed.

- [ ] **Step 4: 测试通过并提交**

Run:

```bash
uv run python -m pytest tests/test_cli_fu13_real_data.py -v
```

Expected: PASS.

Commit:

```bash
git add src/b08_model_core/cli.py tests/test_cli_fu13_real_data.py
git commit -m "feat: add fu13 real data cli"
```

---

## Task 6: 真实数据 baseline 和 TTM 对比报告

**Files:**
- Create: `src/b08_model_core/real_data/forecasting.py`
- Modify: `src/b08_model_core/cli.py`
- Test: `tests/test_real_data_forecasting.py`

- [ ] **Step 1: 写失败测试：baseline 报告按 sensor/scenario/window mode 输出**

Create `tests/test_real_data_forecasting.py`:

```python
import numpy as np
import pandas as pd

from b08_model_core.real_data.forecasting import run_real_data_forecasting, render_real_data_forecasting_report


def _dataset(path):
    timestamps = pd.date_range("2026-05-01", periods=220, freq="5s", tz="UTC")
    rows = []
    for i, ts in enumerate(timestamps):
        stage = "溶解" if i < 110 else "浇筑"
        for sensor, domain, scenario, value in [
            ("O2Content", "atmosphere", "atmosphere_detection", -20 + np.sin(i / 10)),
            ("SysSelfPressure", "hydraulic", "hydraulic_system_detection", 10 + np.cos(i / 10)),
        ]:
            rows.append(
                {
                    "timestamp": ts,
                    "device_id": "FU13",
                    "batch_id": "cycle_0001",
                    "stage": stage,
                    "sensor_id": sensor,
                    "value": value,
                    "unit": "%",
                    "domain": domain,
                    "quality_flag": "good",
                    "degradation_label": "normal",
                    "failure_proxy": False,
                }
            )
    pd.DataFrame(rows).to_parquet(path, index=False)


def test_real_data_forecasting_baseline_report_breaks_down_metrics(tmp_path):
    dataset = tmp_path / "real.parquet"
    _dataset(dataset)

    result = run_real_data_forecasting(
        dataset,
        model="baseline",
        window_mode="cross-stage",
        context_length=32,
        prediction_length=8,
        max_windows=8,
        allow_download=False,
        model_cache_dir=None,
    )
    text = render_real_data_forecasting_report(result)

    assert "Real FU13 Forecasting" in text
    assert "window_mode: cross-stage" in text
    assert "O2Content" in text
    assert "SysSelfPressure" in text
    assert "atmosphere_detection" in text
    assert "hydraulic_system_detection" in text
```

- [ ] **Step 2: 写失败测试：TTM 被尝试但可报告 missing dependency**

Add:

```python
def test_real_data_forecasting_ttm_missing_dependency_is_reported(tmp_path):
    dataset = tmp_path / "real.parquet"
    _dataset(dataset)

    result = run_real_data_forecasting(
        dataset,
        model="ttm",
        window_mode="cross-stage",
        context_length=32,
        prediction_length=8,
        max_windows=8,
        allow_download=False,
        model_cache_dir=None,
        dependency_checker=lambda name: False,
    )
    text = render_real_data_forecasting_report(result)

    assert "model: TTM" in text
    assert "missing_dependency" in text
    assert "Baseline Comparison" in text
```

- [ ] **Step 3: 运行测试确认失败**

Run:

```bash
uv run python -m pytest tests/test_real_data_forecasting.py -v
```

Expected: FAIL because `real_data/forecasting.py` does not exist.

- [ ] **Step 4: 实现真实数据 forecasting runner**

Create `src/b08_model_core/real_data/forecasting.py`.

Minimal structure:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from b08_model_core.adapters.ttm_adapter import TTMForecastAdapter
from b08_model_core.baselines.robust_forecaster import RobustStageForecaster
from b08_model_core.baselines.seasonal_naive import StageSeasonalNaiveForecaster
from b08_model_core.evaluation.metrics import forecasting_metrics
from b08_model_core.experiments.forecasting import BaselineOnlyAdapter
from b08_model_core.foundation import FoundationForecastResult, FoundationModelStatus
from b08_model_core.tasks.window_builder import ModelWindow, build_model_windows


@dataclass(frozen=True)
class RealForecastingResult:
    model: str
    window_mode: str
    train_windows: int
    test_windows: int
    baseline_metrics: dict[str, dict[str, float | None]]
    foundation_result: FoundationForecastResult
    sensor_metrics: pd.DataFrame
    scenario_metrics: pd.DataFrame


def run_real_data_forecasting(
    dataset_path: str | Path,
    *,
    model: str,
    window_mode: str,
    context_length: int,
    prediction_length: int,
    max_windows: int,
    allow_download: bool,
    model_cache_dir: str | None,
    dependency_checker: Callable[[str], bool] | None = None,
) -> RealForecastingResult:
    df = pd.read_parquet(dataset_path)
    allow_cross_stage = window_mode == "cross-stage"
    windows = build_model_windows(
        df,
        context_length=context_length,
        prediction_length=prediction_length,
        stride=prediction_length,
        allow_cross_stage=allow_cross_stage,
    )[:max_windows]
    if len(windows) < 2:
        raise ValueError(f"not enough real data windows: {len(windows)}")
    split = max(1, int(len(windows) * 0.7))
    train = windows[:split]
    test = windows[split:]
    robust = RobustStageForecaster().fit(train).predict(test)
    seasonal = StageSeasonalNaiveForecaster().fit(train).predict(test)
    baseline_metrics = {
        "RobustStageForecaster": forecasting_metrics(robust, test),
        "StageSeasonalNaiveForecaster": forecasting_metrics(seasonal, test),
    }
    adapter = BaselineOnlyAdapter() if model == "baseline" else TTMForecastAdapter(dependency_checker=dependency_checker)
    foundation_result = adapter.predict(
        test,
        context_length=context_length,
        prediction_length=prediction_length,
        allow_download=allow_download,
        model_cache_dir=model_cache_dir,
    )
    predictions = foundation_result.predictions() if foundation_result.succeeded else robust
    if foundation_result.succeeded:
        foundation_result.metrics = forecasting_metrics(predictions, test)
    sensor_metrics = _metrics_by_sensor(predictions, test)
    scenario_metrics = _metrics_by_scenario(sensor_metrics, df)
    return RealForecastingResult(
        model=foundation_result.model_name,
        window_mode=window_mode,
        train_windows=len(train),
        test_windows=len(test),
        baseline_metrics=baseline_metrics,
        foundation_result=foundation_result,
        sensor_metrics=sensor_metrics,
        scenario_metrics=scenario_metrics,
    )
```

Implement helper functions:

```python
def _metrics_by_sensor(predictions: dict[str, np.ndarray], windows: list[ModelWindow]) -> pd.DataFrame:
    truth = np.stack([window.y for window in windows], axis=0)
    y_hat = predictions["y_hat"]
    sensors = windows[0].sensor_token
    rows = []
    for idx, sensor in enumerate(sensors):
        error = y_hat[:, :, idx] - truth[:, :, idx]
        rows.append({"sensor_id": sensor, "mae": float(np.mean(np.abs(error))), "rmse": float(np.sqrt(np.mean(error**2)))})
    return pd.DataFrame(rows)


def _metrics_by_scenario(sensor_metrics: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    sensor_domain = df.drop_duplicates("sensor_id")[["sensor_id", "domain"]]
    # First implementation uses domain as a stable fallback grouping if scenario is not embedded in canonical schema.
    merged = sensor_metrics.merge(sensor_domain, on="sensor_id", how="left")
    return merged.groupby("domain").agg(mae=("mae", "mean"), rmse=("rmse", "mean")).reset_index().rename(columns={"domain": "scenario"})
```

Render:

```python
def render_real_data_forecasting_report(result: RealForecastingResult) -> str:
    lines = [
        "# Real FU13 Forecasting",
        "",
        f"- model: {result.model}",
        f"- window_mode: {result.window_mode}",
        f"- train_windows: {result.train_windows}",
        f"- test_windows: {result.test_windows}",
        "",
        "## Foundation Model Status",
        f"- status: {result.foundation_result.status.value}",
        f"- reason: {result.foundation_result.reason or 'not_available'}",
        "",
        "## Baseline Comparison",
    ]
    for name, metrics in result.baseline_metrics.items():
        lines.append(f"- {name}: {metrics}")
    lines.extend(["", "## Sensor Metrics", result.sensor_metrics.to_markdown(index=False), "", "## Scenario Metrics", result.scenario_metrics.to_markdown(index=False)])
    return "\n".join(lines) + "\n"
```

If tests need scenario names instead of domains, add an optional `sensor_scenario` map parameter or merge config in a later step. Keep first implementation minimal but report grouping clearly.

- [ ] **Step 5: 增加 CLI `forecast-fu13`**

Modify `src/b08_model_core/cli.py` with subcommand:

```python
forecast_fu13 = real_data_sub.add_parser("forecast-fu13")
forecast_fu13.add_argument("--dataset", required=True)
forecast_fu13.add_argument("--output", required=True)
forecast_fu13.add_argument("--model", choices=["baseline", "ttm"], required=True)
forecast_fu13.add_argument("--window-mode", choices=["stage-local", "cross-stage"], default="cross-stage")
forecast_fu13.add_argument("--context-length", type=_positive_int, default=90)
forecast_fu13.add_argument("--prediction-length", type=_positive_int, default=16)
forecast_fu13.add_argument("--max-windows", type=_positive_int, default=40)
forecast_fu13.add_argument("--model-cache-dir")
download = forecast_fu13.add_mutually_exclusive_group()
download.add_argument("--allow-download", action="store_true", dest="allow_download")
download.add_argument("--no-download", action="store_false", dest="allow_download")
forecast_fu13.set_defaults(allow_download=False)
```

Dispatch:

```python
if args.command == "real-data" and args.real_data_command == "forecast-fu13":
    result = run_real_data_forecasting(...)
    Path(args.output).write_text(render_real_data_forecasting_report(result), encoding="utf-8")
    if args.model == "ttm" and result.foundation_result.status != FoundationModelStatus.AVAILABLE_AND_RAN:
        return 1
    return 0
```

- [ ] **Step 6: 测试通过并提交**

Run:

```bash
uv run python -m pytest tests/test_real_data_forecasting.py tests/test_cli_fu13_real_data.py -v
```

Expected: PASS.

Commit:

```bash
git add src/b08_model_core/real_data/forecasting.py src/b08_model_core/cli.py tests/test_real_data_forecasting.py tests/test_cli_fu13_real_data.py
git commit -m "feat: forecast fu13 real data"
```

---

## Task 7: 真实数据手工闭环验证

**Files:**
- Local outputs only:
  - `data/processed/fu13_real_observations.parquet`
  - `reports/real_data_validation.md`
  - `reports/real_scenario_diagnostics.md`
  - `reports/real_baseline_forecasting.md`
  - `reports/real_ttm_forecasting.md`
- Modify if needed: `.gitignore`

- [ ] **Step 1: 确认派生产物忽略规则**

Run:

```bash
git check-ignore -v data/processed/fu13_real_observations.parquet reports/real_data_validation.md hf_cache 2>/dev/null || true
```

Expected: generated data/cache should be ignored. If `data/processed/*.parquet` is not ignored, add it to `.gitignore`.

- [ ] **Step 2: 运行真实数据装配**

Run:

```bash
uv run b08-model-core real-data assemble-fu13 \
  --input-dir data/real \
  --config configs/fu13_real_data_schema.yaml \
  --output data/processed/fu13_real_observations.parquet \
  --report reports/real_data_validation.md
```

Expected: command exits `0`; report contains `Real FU13 Data Validation`, 8 sensors, nonzero rows, cycle summary, quality counts.

- [ ] **Step 3: 运行场景诊断**

Run:

```bash
uv run b08-model-core real-data diagnose-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --config configs/fu13_real_data_schema.yaml \
  --output reports/real_scenario_diagnostics.md
```

Expected: command exits `0`; report contains all four scenarios or their stable grouping names.

- [ ] **Step 4: 运行 baseline 真实数据 forecasting**

Run:

```bash
uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --output reports/real_baseline_forecasting.md \
  --model baseline \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40
```

Expected: command exits `0`; report includes baseline metrics, sensor metrics, scenario metrics.

- [ ] **Step 5: 运行 TTM 真实数据 forecasting**

If optional dependencies are missing, first run:

```bash
uv sync --extra dev --extra foundation-ttm
```

Then run offline/cache mode first:

```bash
HF_HOME=hf_cache uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --output reports/real_ttm_forecasting.md \
  --model ttm \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --model-cache-dir hf_cache \
  --no-download
```

Expected:

- If cache/dependencies are present, report contains `available_and_ran` and TTM metrics.
- If blocked, command exits nonzero and report states the precise blocker.

If cache is missing and network download is acceptable for this run:

```bash
HF_HOME=hf_cache uv run b08-model-core real-data forecast-fu13 \
  --dataset data/processed/fu13_real_observations.parquet \
  --output reports/real_ttm_forecasting.md \
  --model ttm \
  --window-mode cross-stage \
  --context-length 90 \
  --prediction-length 16 \
  --max-windows 40 \
  --model-cache-dir hf_cache \
  --allow-download
```

Expected: `available_and_ran` or a specific, reportable runtime/window/cache blocker. Do not treat failure as success.

- [ ] **Step 6: 检查真实报告内容**

Run:

```bash
rg -n "Real FU13|schema_valid|cycle|quality|Sensor Metrics|Scenario Metrics|TTM|available_and_ran|missing_dependency|runtime_failed|unsupported_window_shape" reports/real_data_validation.md reports/real_scenario_diagnostics.md reports/real_baseline_forecasting.md reports/real_ttm_forecasting.md
```

Expected: command finds the validation, diagnostics, baseline, and TTM evidence.

- [ ] **Step 7: 提交忽略规则变更，如果有**

Only if `.gitignore` changed:

```bash
git add .gitignore
git commit -m "chore: ignore real data generated artifacts"
```

---

## Task 8: 文档台账和全量验证

**Files:**
- Modify: `details.md`
- Optionally Modify: `README.md` if CLI commands need user-facing documentation.

- [ ] **Step 1: 更新 `details.md`**

Add a recent update entry:

```markdown
| 2026-06-02 | 进入真实数据验证闭环：新增 FU13 真实多 CSV 装配、连续炉 cycle 重构、数据质量与场景诊断，并要求在真实窗口上完成 baseline 与 TTM 同口径验证。 |
```

Update current conclusion to state:

- 项目已进入真实数据验证闭环。
- 完成该阶段后可确认从现场导出到模型实验的整体流程跑通。
- 后续重点将转向算法效果提升、模型适配和候选异常信号质量。

- [ ] **Step 2: 运行相关测试**

Run:

```bash
uv run python -m pytest tests/test_fu13_real_config.py tests/test_fu13_cycle_builder.py tests/test_fu13_loader.py tests/test_fu13_diagnostics.py tests/test_cli_fu13_real_data.py tests/test_real_data_forecasting.py -q
```

Expected: all selected tests pass.

- [ ] **Step 3: 运行全量测试**

Run:

```bash
uv run python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 4: 检查 git 状态**

Run:

```bash
git status --short
```

Expected: only intended source/docs changes are present. `data/real/` remains untracked user data and must not be staged unless explicitly requested.

- [ ] **Step 5: 提交文档更新**

Commit:

```bash
git add details.md README.md
git commit -m "docs: record real data validation loop progress"
```

Only include `README.md` if it actually changed.

---

## Final Verification Gate

Do not claim this stage is complete until all of the following are true:

- `uv run python -m pytest -q` passes.
- `real-data assemble-fu13` ran on `data/real`.
- `real-data diagnose-fu13` produced a scenario diagnostics report.
- baseline forecasting ran on real data and produced per-sensor/per-scenario metrics.
- TTM forecasting was attempted on real data and either:
  - ran with `available_and_ran`, or
  - produced a report with a precise blocker.
- No `data/real/`, generated parquet, model cache, or Hugging Face weights were staged.
- `details.md` reflects the project entering the real data validation loop.

## Execution Handoff

After this plan is reviewed and approved:

**Option 1: Subagent-Driven (recommended)**
Use `superpowers:subagent-driven-development`. Dispatch task-sized workers, review after each task, and keep write scopes disjoint.

**Option 2: Inline Execution**
Use `superpowers:executing-plans`. Execute the plan in this session with checkpoints between tasks.
