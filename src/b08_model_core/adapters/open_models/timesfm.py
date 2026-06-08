from b08_model_core.adapters.open_models._forecasting import _ForecastingOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class TimesFMOpenModelAdapter(_ForecastingOpenModelAdapter):
    model_id = "timesfm"
    display_name = "TimesFM"
    required_modules = ("timesfm",)
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "google/timesfm-2.5-200m-pytorch"
    target_model_ref = "google/timesfm-2.5-200m-pytorch"
    fallback_model_ref = None
    target_package_hint = "timesfm package with TimesFM 2.5 PyTorch support"
    target_license_note = "Review TimesFM 2.5 model card/license before weight use."
    target_resource_note = "TimesFM 2.5 checkpoint loading may require local HF cache or explicit download approval."
    target_task_fit = "forecasting"
    official_api_detail = (
        "official README uses timesfm.TimesFM_2p5_200M_torch.from_pretrained"
        "('google/timesfm-2.5-200m-pytorch'), compile(ForecastConfig), and forecast"
    )
