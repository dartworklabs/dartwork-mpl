"""The viewer's parameter controls: the user's model, its controls and the active values.

``ParamModel`` is the public base class users subclass. The controls derived
from it (``Control``, one variant per kind) are what the page renders;
``controls_wire`` projects them onto the ``/api/descriptors`` wire DTOs.
``parse_active`` turns a request's active values into a model instance.
``routes`` serves the descriptors and defaults. Needs the ``ui``
extra: pydantic always, fastapi only once ``routes``/``GRANTS`` are used.
"""

from typing import TYPE_CHECKING, Any

from ._active import InvalidRequest, parse_active
from ._descriptors import Control, controls_from_model, controls_wire
from ._model import ParamModel
from ._requests import (
    InputFailure,
    ModelRequest,
    parse_model_request,
    request_object,
)
from ._signature import extract_param_model

if TYPE_CHECKING:
    from ._routes import GRANTS, routes

__all__ = [
    "GRANTS",
    "Control",
    "InputFailure",
    "InvalidRequest",
    "ModelRequest",
    "ParamModel",
    "controls_from_model",
    "controls_wire",
    "extract_param_model",
    "parse_active",
    "parse_model_request",
    "request_object",
    "routes",
]


def __getattr__(name: str) -> Any:
    """Load the HTTP routes only on use, so ``ParamModel`` imports without fastapi."""
    if name in {"GRANTS", "routes"}:
        from . import _routes

        return getattr(_routes, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
