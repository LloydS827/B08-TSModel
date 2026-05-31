import subprocess
import sys

import pandas as pd


def test_cli_simulates_dataset(tmp_path):
    out = tmp_path / "fu13.parquet"
    result = subprocess.run(
        [sys.executable, "-m", "b08_model_core.cli", "simulate", "--days", "3", "--seed", "11", "--output", str(out)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    df = pd.read_parquet(out)
    assert df["sensor_id"].nunique() >= 15
    assert df["batch_id"].nunique() >= 5
