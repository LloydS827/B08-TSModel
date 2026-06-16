from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from b08_model_core.evaluation.metrics import (
    forecasting_residual_ranking,
    nasa_rul_score,
    rul_regression_metrics,
)
from b08_model_core.experiments.c31_cmapss_minimal_ingestion import (
    C31RawSchemaMismatch,
    load_cmapss_rul_baseline_dataset,
)


def test_rul_regression_metrics_include_nasa_score():
    truth = np.array([10.0, 20.0, 30.0])
    prediction = np.array([12.0, 18.0, 30.0])

    metrics = rul_regression_metrics(prediction, truth)

    assert metrics["mae"] == 4.0 / 3.0
    assert metrics["rmse"] == math.sqrt(8.0 / 3.0)
    assert metrics["nasa_score"] == nasa_rul_score(prediction, truth)
    assert metrics["count"] == 3


def test_forecasting_residual_ranking_groups_by_sensor():
    truth = np.zeros((2, 2, 3))
    prediction = np.array(
        [
            [[1.0, 0.0, 3.0], [1.0, 0.0, 3.0]],
            [[2.0, 0.0, 1.0], [2.0, 0.0, 1.0]],
        ]
    )

    ranking = forecasting_residual_ranking(
        {"y_hat": prediction},
        truth,
        ["s1", "s2", "s3"],
        top_k=2,
    )

    assert ranking == (
        {"rank": 1, "sensor_id": "s3", "mean_abs_residual": 2.0},
        {"rank": 2, "sensor_id": "s1", "mean_abs_residual": 1.5},
    )


def _write_fd001_fixture(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True)
    train_rows = [
        "1 1 0 0 0 " + " ".join(["1"] * 21),
        "1 2 0 0 0 " + " ".join(["1"] * 21),
        "1 3 0 0 0 " + " ".join(["1"] * 21),
        "2 1 0 0 0 " + " ".join(["2"] * 21),
        "2 2 0 0 0 " + " ".join(["2"] * 21),
    ]
    test_rows = [
        "1 1 0 0 0 " + " ".join(["3"] * 21),
        "1 2 0 0 0 " + " ".join(["3"] * 21),
        "2 1 0 0 0 " + " ".join(["4"] * 21),
    ]
    (raw_dir / "train_FD001.txt").write_text(
        "\n".join(train_rows) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "test_FD001.txt").write_text(
        "\n".join(test_rows) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "RUL_FD001.txt").write_text("7\n5\n", encoding="utf-8")


def test_load_cmapss_rul_baseline_dataset_from_local_raw(tmp_path):
    raw_dir = tmp_path / "data/public/cmapss/raw"
    _write_fd001_fixture(raw_dir)

    dataset = load_cmapss_rul_baseline_dataset(raw_dir, subsets=("FD001",))

    assert dataset.subsets == ("FD001",)
    assert len(dataset.train_records) == 5
    assert len(dataset.test_final_records) == 2
    assert dataset.test_final_records[0].rul == 7
    assert dataset.test_final_records[1].rul == 5


def test_load_cmapss_rul_baseline_dataset_reports_schema_mismatch(tmp_path):
    raw_dir = tmp_path / "data/public/cmapss/raw"
    _write_fd001_fixture(raw_dir)
    (raw_dir / "train_FD001.txt").write_text("1 1 0\n", encoding="utf-8")

    with pytest.raises(C31RawSchemaMismatch, match="expected 26 columns"):
        load_cmapss_rul_baseline_dataset(raw_dir, subsets=("FD001",))
