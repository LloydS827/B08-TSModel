from b08_model_core.adapters.open_models import _DependencyFirstOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class TTMOpenModelAdapter(_DependencyFirstOpenModelAdapter):
    model_id = "ttm"
    display_name = "TTM / TinyTimeMixer"
    required_modules = ("tsfm_public",)
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "TTM / TinyTimeMixer interface needs review"
