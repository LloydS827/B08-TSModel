from b08_model_core.adapters.open_models import _DependencyFirstOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class ChronosOpenModelAdapter(_DependencyFirstOpenModelAdapter):
    model_id = "chronos"
    display_name = "Chronos / Chronos-Bolt"
    required_modules = ("chronos",)
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "Chronos / Chronos-Bolt interface needs review"
