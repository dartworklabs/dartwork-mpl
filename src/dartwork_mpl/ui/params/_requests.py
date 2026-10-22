"""Request bodies whose only payload is the active parameters.

Every viewer request body is first a bounded JSON object (``request_object``);
render, export and script downloads then carry nothing but the validated
active model (``ModelRequest``, parsed by ``parse_model_request``). Each
route calls the parser of its own body language; no parser dispatches on a
route string. Surface (through the ``params`` package): ``InputFailure``,
``ModelRequest``, ``request_object`` and ``parse_model_request``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from ..platform.json_bounds import (
    JsonValue,
    LimitExceeded,
    MalformedInput,
    bounded,
)
from ._active import InvalidRequest, parse_active
from ._descriptors import ParamDescriptor
from ._model import ParamModel

# The refusals a request body can produce before any route-specific rule.
InputFailure: TypeAlias = MalformedInput | LimitExceeded | InvalidRequest


@dataclass(frozen=True)
class ModelRequest:
    """A render/download request contains only the validated active model."""

    model: ParamModel


def request_object(
    value: JsonValue,
) -> dict[str, JsonValue] | LimitExceeded | InvalidRequest:
    """Require a bounded JSON object, the shape every viewer request body has."""
    refusal = bounded(value)
    if refusal is not None:
        return (
            refusal if isinstance(refusal, LimitExceeded) else InvalidRequest()
        )
    if not isinstance(value, dict):
        return InvalidRequest()
    return value


def parse_model_request(
    value: JsonValue,
    model_cls: type[ParamModel],
    descriptors: list[ParamDescriptor],
) -> ModelRequest | InputFailure:
    """Parse a decoded body that is exactly the active parameters.

    Returns ``LimitExceeded`` when the tree breaks a size bound and
    ``InvalidRequest`` when it is not an object or does not validate against
    ``model_cls`` (after the documented list-text and numeric-choice
    coercion). Pure: no I/O.
    """
    body = request_object(value)
    if not isinstance(body, dict):
        return body
    model = parse_active(body, model_cls, descriptors)
    if isinstance(model, InvalidRequest):
        return model
    return ModelRequest(model)
