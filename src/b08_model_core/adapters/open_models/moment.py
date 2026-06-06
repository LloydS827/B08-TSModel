from b08_model_core.adapters.open_models._representation_imputation import (
    _RepresentationImputationOpenModelAdapter,
)
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class MomentOpenModelAdapter(_RepresentationImputationOpenModelAdapter):
    model_id = "moment"
    display_name = "MOMENT"
    required_modules = ("momentfm",)
    supported_tasks = (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION)
    model_ref = "AutonLab/MOMENT-1-large"
    official_api_detail = (
        "Official MOMENT docs use `from momentfm import MOMENTPipeline`; "
        "representation uses task_name='embedding' and imputation/reconstruction "
        "uses task_name='reconstruction'."
    )
