from b08_model_core.adapters.open_models import _DependencyFirstOpenModelAdapter
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class MoiraiUni2TSOpenModelAdapter(_DependencyFirstOpenModelAdapter):
    model_id = "moirai_uni2ts"
    display_name = "Moirai / Uni2TS"
    required_modules = ("uni2ts",)
    supported_tasks = (C21TaskId.FORECASTING,)
    model_ref = "Moirai / Uni2TS interface needs review"
