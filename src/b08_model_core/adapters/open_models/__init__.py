"""C2.1 open model adapter contract.

Concrete adapters are intentionally not imported here because they may require
optional model packages that are absent in the default offline workflow.
"""

from b08_model_core.adapters.open_models.base import (
    AdapterExecutionContext,
    AdapterFailure,
    AdapterReadiness,
    AdapterTaskOutput,
    OpenModelAdapter,
    OpenModelAdapterStatus,
    dependency_status,
)

__all__ = [
    "AdapterExecutionContext",
    "AdapterFailure",
    "AdapterReadiness",
    "AdapterTaskOutput",
    "OpenModelAdapter",
    "OpenModelAdapterStatus",
    "dependency_status",
]
