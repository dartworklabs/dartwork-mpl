"""Server-save requests: the validated parameters, with or without a chosen output name.

A body that names its output (``NamedSave``) and one that leaves the name to
the viewer (``AutoNamedSave``) are different requests: only the second needs
a generated, timestamped name. Surface (through the ``saving`` package):
``AutoNamedSave``, ``NamedSave``, ``SaveRequest``, ``SaveInputFailure``,
``parse_save_request``, ``requested_name`` and ``timestamp_slug``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias
from uuid import uuid4

from ..params import (
    InputFailure,
    InvalidRequest,
    ParamDescriptor,
    ParamModel,
    parse_active,
    request_object,
)
from ..platform.json_bounds import JsonValue
from ._output import InvalidOutput, RelativeOutput, parse_output

SaveInputFailure: TypeAlias = InputFailure | InvalidOutput


@dataclass(frozen=True)
class AutoNamedSave:
    """A server save whose body named no output; the viewer generates the name."""

    model: ParamModel


@dataclass(frozen=True)
class NamedSave:
    """A server save to the parsed relative output name the body supplied."""

    model: ParamModel
    output: RelativeOutput


SaveRequest: TypeAlias = AutoNamedSave | NamedSave


def parse_save_request(
    value: JsonValue,
    model_cls: type[ParamModel],
    descriptors: list[ParamDescriptor],
) -> SaveRequest | SaveInputFailure:
    """Parse a server-save body: ``params`` and an optional ``filename``.

    An absent or ``null`` filename yields ``AutoNamedSave``; a string that is a
    safe relative path yields ``NamedSave``. Refusals: ``LimitExceeded`` for a
    tree over the size bounds, ``InvalidRequest`` for a non-object, unknown
    keys, missing ``params``, a non-string filename or invalid parameters, and
    ``InvalidOutput`` for an unsafe filename. Pure: no I/O.
    """
    body = request_object(value)
    if not isinstance(body, dict):
        return body
    if "params" not in body or body.keys() - {"params", "filename"}:
        return InvalidRequest()
    model = parse_active(body["params"], model_cls, descriptors)
    if isinstance(model, InvalidRequest):
        return model
    filename = body.get("filename")
    if filename is None:
        return AutoNamedSave(model)
    if not isinstance(filename, str):
        return InvalidRequest()
    output = parse_output(filename)
    return (
        output
        if isinstance(output, InvalidOutput)
        else NamedSave(model, output)
    )


def requested_name(request: SaveRequest, function_name: str) -> str:
    """Return the relative name a save asked for, or a fresh ``<function>_<timestamp>`` one.

    The result has no extension rule applied; each saving route fixes its own
    extension before parsing the final name with ``parse_output``.
    """
    match request:
        case NamedSave(output=output):
            return output.filename
        case AutoNamedSave():
            return f"{function_name}_{timestamp_slug()}"


def timestamp_slug() -> str:
    """Return a compact timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:12]
