"""Bounded JSON for the viewer's wire and state bytes: the value type, the limits and the decoder.

Mechanism only: it knows JSON trees and their size bounds, not routes,
parameter models or state files. Surface: ``JsonValue``, the shared limits,
``MalformedInput`` / ``LimitExceeded``, ``bounded`` (check a decoded tree)
and ``decode_json``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import TypeAlias

__all__ = [
    "MAX_CONTAINER",
    "MAX_DEPTH",
    "MAX_REQUEST_BYTES",
    "MAX_STRING_BYTES",
    "MAX_VALUES",
    "JsonValue",
    "LimitExceeded",
    "MalformedInput",
    "bounded",
    "decode_json",
]

JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)

MAX_REQUEST_BYTES = 1024 * 1024
MAX_DEPTH = 16
MAX_VALUES = 65536
MAX_CONTAINER = 4096
MAX_STRING_BYTES = 65536


@dataclass(frozen=True)
class MalformedInput:
    """The bytes do not express one unambiguous finite UTF-8 JSON value."""

    detail: str = "Input must be unambiguous finite UTF-8 JSON."


@dataclass(frozen=True)
class LimitExceeded:
    """An input or proposed serialized state exceeds an approved bound."""

    detail: str = "Input exceeds the viewer limits."


class _BadJson(ValueError):
    """Internal stdlib parser signal converted to a named malformed-input value."""


class _JsonLimit(ValueError):
    """Internal stdlib parser signal converted to a named limit refusal."""


def _pairs(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    """Reject duplicate object keys at every nesting level during JSON decoding."""
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise _BadJson
        result[key] = value
    return result


def _integer(token: str) -> int:
    """Bound integer work independently of the interpreter-wide digit setting."""
    if len(token.lstrip("-")) > 640:
        raise _JsonLimit
    return int(token)


def _float(token: str) -> float:
    """Reject numeric overflow as well as explicit nonfinite JSON constants."""
    value = float(token)
    if not math.isfinite(value):
        raise _BadJson
    return value


def _constant(token: str) -> JsonValue:
    """Stdlib's permissive NaN/Infinity tokens are outside this JSON language."""
    raise _BadJson


def bounded(value: object) -> MalformedInput | LimitExceeded | None:
    """Iteratively bound full JSON trees, including object keys and Unicode bytes."""
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > MAX_VALUES or depth > MAX_DEPTH:
            return LimitExceeded()
        if isinstance(item, str):
            try:
                if len(item.encode("utf-8")) > MAX_STRING_BYTES:
                    return LimitExceeded()
            except UnicodeEncodeError:
                return MalformedInput()
        elif isinstance(item, (list, dict)):
            if len(item) > MAX_CONTAINER:
                return LimitExceeded()
            if isinstance(item, dict):
                for key in item:
                    if not isinstance(key, str):
                        return MalformedInput()
                    try:
                        if len(key.encode("utf-8")) > MAX_STRING_BYTES:
                            return LimitExceeded()
                    except UnicodeEncodeError:
                        return MalformedInput()
                pending.extend((child, depth + 1) for child in item.values())
            else:
                pending.extend((child, depth + 1) for child in item)
        elif isinstance(item, float):
            if not math.isfinite(item):
                return MalformedInput()
        elif isinstance(item, int):
            if abs(item) >= 10**640:
                return LimitExceeded()
        elif item is not None and not isinstance(item, (int, bool)):
            return MalformedInput()
    return None


def decode_json(
    raw: bytes, *, max_bytes: int
) -> JsonValue | MalformedInput | LimitExceeded:
    """Decode one bounded JSON value; malformed syntax is 400 and bounds are 413."""
    if len(raw) > max_bytes:
        return LimitExceeded()
    try:
        value: JsonValue = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_int=_integer,
            parse_float=_float,
            parse_constant=_constant,
        )
    except _JsonLimit:
        return LimitExceeded()
    except (UnicodeDecodeError, json.JSONDecodeError, _BadJson, RecursionError):
        return MalformedInput()
    refusal = bounded(value)
    return refusal if refusal is not None else value
