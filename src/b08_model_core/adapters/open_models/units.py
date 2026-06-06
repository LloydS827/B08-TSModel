from b08_model_core.adapters.open_models import _DependencyFirstOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class UniTSOpenModelAdapter(_DependencyFirstOpenModelAdapter):
    model_id = "units"
    display_name = "UniTS"
    required_modules = ("units",)
    supported_tasks = (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION)
    model_ref = "UniTS interface needs review"
