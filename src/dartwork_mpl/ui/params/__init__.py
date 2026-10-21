"""The viewer's parameter controls: the user's model, its controls and the active values.

``ParamModel`` is the public base class users subclass. The descriptors
derived from it are the ``/api/descriptors`` wire DTOs the page renders as
controls; ``parse_active`` turns a request's active values into a model
instance. Needs the ``ui`` extra (pydantic).
"""

from ._active import InvalidRequest, parse_active
from ._descriptors import ParamDescriptor, descriptors_from_model
from ._model import ParamModel
from ._signature import extract_param_model

__all__ = [
    "InvalidRequest",
    "ParamDescriptor",
    "ParamModel",
    "descriptors_from_model",
    "extract_param_model",
    "parse_active",
]
