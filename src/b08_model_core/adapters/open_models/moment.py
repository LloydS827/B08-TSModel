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
    target_model_ref = "AutonLab/MOMENT-1-large"
    fallback_model_ref = None
    target_package_hint = "momentfm package with MOMENTPipeline support"
    target_license_note = "Review MOMENT model card/license before weight use."
    target_resource_note = "MOMENT large checkpoint loading may require local HF cache or explicit download approval."
    target_task_fit = "representation and imputation"
    official_api_detail = (
        "Official MOMENT docs use `from momentfm import MOMENTPipeline`; "
        "representation uses task_name='embedding' and imputation/reconstruction "
        "uses task_name='reconstruction'."
    )
