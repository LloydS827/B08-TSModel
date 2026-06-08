from b08_model_core.adapters.open_models._forecasting import _ForecastingOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class ChronosOpenModelAdapter(_ForecastingOpenModelAdapter):
    model_id = "chronos"
    display_name = "Chronos / Chronos-Bolt"
    required_modules = ("chronos",)
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "amazon/chronos-2"
    target_model_ref = "amazon/chronos-2"
    fallback_model_ref = "amazon/chronos-bolt-base"
    target_package_hint = "chronos package with Chronos2Pipeline support"
    target_license_note = "Review Chronos-2 model card/license before weight use."
    target_resource_note = "Chronos-2 checkpoint loading may require local HF cache or explicit download approval."
    target_task_fit = "forecasting"
    official_api_detail = (
        "official README uses chronos.Chronos2Pipeline.from_pretrained"
        "('amazon/chronos-2') and predict_df(...)"
    )
