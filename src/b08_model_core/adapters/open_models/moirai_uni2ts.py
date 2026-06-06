from b08_model_core.adapters.open_models.chronos import _ForecastingOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class MoiraiUni2TSOpenModelAdapter(_ForecastingOpenModelAdapter):
    model_id = "moirai_uni2ts"
    display_name = "Moirai / Uni2TS"
    required_modules = ("uni2ts",)
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "Salesforce/moirai-1.1-R-small"
    official_api_detail = (
        "official README uses uni2ts.model.moirai.MoiraiModule.from_pretrained"
        "('Salesforce/moirai-1.1-R-small') with MoiraiForecast.create_predictor(...).predict"
    )
