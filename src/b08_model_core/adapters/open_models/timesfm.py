from b08_model_core.adapters.open_models.chronos import _ForecastingOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class TimesFMOpenModelAdapter(_ForecastingOpenModelAdapter):
    model_id = "timesfm"
    display_name = "TimesFM"
    required_modules = ("timesfm",)
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "google/timesfm-2.5-200m-pytorch"
    official_api_detail = (
        "official README uses timesfm.TimesFM_2p5_200M_torch.from_pretrained"
        "('google/timesfm-2.5-200m-pytorch'), compile(ForecastConfig), and forecast"
    )
