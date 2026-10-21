"""Server-save requests: the validated parameters plus the output name, if one was given.

Surface (through the ``saving`` package): ``SaveRequest``,
``SaveInputFailure``, ``parse_save_request`` and ``timestamp_slug`` (the
default output name's suffix).
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
)
from ..platform.json_bounds import JsonValue
from ._output import InvalidOutput, RelativeOutput, parse_output

SaveInputFailure: TypeAlias = InputFailure | InvalidOutput


@dataclass(frozen=True)
class SaveRequest:
    """A server save carries a validated model and an optional parsed output name."""

    model: ParamModel
    output: RelativeOutput | None = None


def parse_save_request(
    value: dict[str, JsonValue],
    model_cls: type[ParamModel],
    descriptors: list[ParamDescriptor],
) -> SaveRequest | SaveInputFailure:
    """Read a server-save body: the active parameters and an optional output name."""
    if "params" not in value or value.keys() - {"params", "filename"}:
        return InvalidRequest()
    model = parse_active(value["params"], model_cls, descriptors)
    if isinstance(model, InvalidRequest):
        return model
    filename = value.get("filename")
    if filename is None:
        return SaveRequest(model)
    if not isinstance(filename, str):
        return InvalidRequest()
    output = parse_output(filename)
    return (
        output
        if isinstance(output, SaveInputFailure)
        else SaveRequest(model, output)
    )


def timestamp_slug() -> str:
    """Return a compact timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:12]
