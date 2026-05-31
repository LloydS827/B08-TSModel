# B08 设备时序基础模型

本仓库聚焦 B08 的核心时序基础模型研究沙盒，不展开完整预测性维护系统。

主要阅读请打开：

- [docs/index.html](docs/index.html)

HTML 入口中包含：

- 模型核心 brainstorming 阶段收束成果
- 核心时序模型最终实施 plan
- 真空速凝炉模拟数据场景
- 原始材料和前期草稿归档入口

## 可运行沙盒

需要 Python 3.11+。

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

生成 45 天 FU13 模拟数据：

```bash
.venv/bin/b08-model-core simulate --days 45 --seed 42 --output data/simulated/furnace_fu13_45d.parquet
```

生成模型路线评估摘要：

```bash
.venv/bin/b08-model-core benchmark --dataset data/simulated/furnace_fu13_45d.parquet --output reports/model_core_evaluation.md
```

验证真实数据导出：

```bash
.venv/bin/b08-model-core real-data validate --input path/to/real_export.csv --schema-map configs/real_data_schema_map.template.yaml --output reports/real_data_validation.md
```

运行第一轮 forecasting 实验脚手架：

```bash
.venv/bin/b08-model-core experiment forecasting --dataset data/simulated/furnace_fu13_45d.parquet --output reports/forecasting_experiment.md
```
