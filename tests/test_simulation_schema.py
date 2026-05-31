import pandas as pd

from b08_model_core.tasks.schema import REQUIRED_OBSERVATION_COLUMNS, validate_observation_frame


def test_observation_schema_contains_model_required_fields():
    assert REQUIRED_OBSERVATION_COLUMNS == {
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
    }


def test_validate_observation_frame_rejects_missing_columns():
    df = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=2, freq="5s")})
    result = validate_observation_frame(df)
    assert not result.valid
    assert "sensor_id" in result.missing_columns
