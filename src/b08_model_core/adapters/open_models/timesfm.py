from b08_model_core.adapters.open_models import _DependencyFirstOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class TimesFMOpenModelAdapter(_DependencyFirstOpenModelAdapter):
    model_id = "timesfm"
    display_name = "TimesFM"
    required_modules = ("timesfm",)
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "TimesFM interface needs review"
