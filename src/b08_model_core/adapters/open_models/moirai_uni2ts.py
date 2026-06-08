from b08_model_core.adapters.open_models._forecasting import _ForecastingOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class MoiraiUni2TSOpenModelAdapter(_ForecastingOpenModelAdapter):
    model_id = "moirai_uni2ts"
    display_name = "Moirai / Uni2TS"
    required_modules = ("uni2ts",)
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "Salesforce/moirai-2.0-R-small"
    target_model_ref = "Salesforce/moirai-2.0-R-small"
    fallback_model_ref = "Salesforce/moirai-1.1-R-small"
    target_package_hint = "uni2ts package with current Moirai 2.0 support"
    target_license_note = "Review Moirai 2.0 model card/license before weight use."
    target_resource_note = "Moirai 2.0 checkpoint loading may require local HF cache or explicit download approval."
    target_task_fit = "probabilistic forecasting"
    official_api_detail = (
        "official README uses uni2ts.model.moirai.MoiraiModule.from_pretrained"
        "('Salesforce/moirai-2.0-R-small') with MoiraiForecast.create_predictor(...).predict"
    )
