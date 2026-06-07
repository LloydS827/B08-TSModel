from b08_model_core.adapters.open_models._forecasting import _ForecastingOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class ChronosOpenModelAdapter(_ForecastingOpenModelAdapter):
    model_id = "chronos"
    display_name = "Chronos / Chronos-Bolt"
    required_modules = ("chronos",)
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "amazon/chronos-2"
    official_api_detail = (
        "official README uses chronos.Chronos2Pipeline.from_pretrained"
        "('amazon/chronos-2') and predict_df(...)"
    )
