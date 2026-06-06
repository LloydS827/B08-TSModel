from b08_model_core.adapters.open_models import _DependencyFirstOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class MomentOpenModelAdapter(_DependencyFirstOpenModelAdapter):
    model_id = "moment"
    display_name = "MOMENT"
    required_modules = ("momentfm",)
    supported_tasks = (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION)
    model_ref = "MOMENT interface needs review"
