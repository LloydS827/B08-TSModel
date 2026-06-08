from b08_model_core.adapters.open_models._representation_imputation import (
    _RepresentationImputationOpenModelAdapter,
)
from b08_model_core.experiments.c21_executable_open_model_evaluation import C21TaskId


class UniTSOpenModelAdapter(_RepresentationImputationOpenModelAdapter):
    model_id = "units"
    display_name = "UniTS"
    required_modules = ("units",)
    supported_tasks = (C21TaskId.REPRESENTATION, C21TaskId.IMPUTATION)
    model_ref = "mims-harvard/UniTS"
    target_model_ref = "mims-harvard/UniTS"
    fallback_model_ref = None
    target_package_hint = "units package or reviewed UniTS runtime entrypoint"
    target_license_note = "Review UniTS repository/model license before weight use."
    target_resource_note = "UniTS weight loading may require local cache or explicit download approval."
    target_task_fit = "representation and imputation"
    official_api_detail = (
        "Official UniTS materials describe a unified model for forecasting, "
        "classification, imputation, and anomaly detection, but a stable pip/API "
        "entrypoint for safe offline execution still needs review."
    )
