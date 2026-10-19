"""Private strict JSON mechanics for the MCP data-validation capability.

Numeric lexemes remain exact and resource scanning precedes semantic decoding.
This module performs no I/O and knows no report or plotting rules.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TypeAlias

_INPUT_BYTES = 65_536
_DEPTH = 16
_TOKENS = 10_000
_REPORT_BYTES = 1_048_576


@dataclass(frozen=True)
class _Number:
    """A parser-owned JSON numeric lexeme that must be emitted verbatim."""

    token: str


_Json: TypeAlias = (
    None
    | bool
    | str
    | int
    | float
    | _Number
    | list["_Json"]
    | dict[str, "_Json"]
)


@dataclass(frozen=True)
class _Limit:
    """A budget refusal records an observed count or conservative lower bound."""

    name: str
    maximum: int
    observed: int
    field: str = "data_json"
    field_bytes: int | None = None


class _DuplicateKey(ValueError):
    """Adapt the standard decoder's pair hook to a typed duplicate refusal."""


class _NonfiniteToken(ValueError):
    """Adapt the standard decoder's constant hook to a typed token refusal."""


def _pairs(pairs: list[tuple[str, _Json]]) -> dict[str, _Json]:
    """Build one object while rejecting duplicate decoded member names."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey
        result[key] = value
    return result


def _constant(token: str) -> _Json:
    """Reject JavaScript nonfinite constants rather than admitting them as JSON."""
    raise _NonfiniteToken(token)


def _preflight(raw: str) -> _Limit | None:
    """Bound UTF-8 size, container depth and value/key tokens before decoding."""
    size = len(raw.encode("utf-8"))
    if size > _INPUT_BYTES:
        return _Limit("input_bytes", _INPUT_BYTES, size)
    depth = tokens = position = 0
    while position < len(raw):
        char = raw[position]
        if char in " \t\r\n,:}]":
            if char in "}]":
                depth -= 1
            position += 1
            continue
        tokens += 1
        if tokens > _TOKENS:
            return _Limit("tokens", _TOKENS, tokens)
        if char in "[{":
            depth += 1
            if depth > _DEPTH:
                return _Limit("depth", _DEPTH, depth)
            position += 1
        elif char == '"':
            position += 1
            while position < len(raw):
                current = raw[position]
                position += 1
                if current == "\\":
                    position += 1
                elif current == '"':
                    break
        else:
            position += 1
            while position < len(raw) and raw[position] not in ' \t\r\n,:{}[]"':
                position += 1
    return None


def _unicode_valid(data: _Json) -> bool:
    """Require decoded keys and strings to be valid Unicode scalar sequences."""
    if isinstance(data, str):
        return not any(0xD800 <= ord(char) <= 0xDFFF for char in data)
    if isinstance(data, list):
        return all(_unicode_valid(value) for value in data)
    if isinstance(data, dict):
        return all(
            _unicode_valid(key) and _unicode_valid(value)
            for key, value in data.items()
        )
    return True


def _string_size(value: str) -> int:
    """Count ASCII-escaped JSON string bytes, stopping at the report bound."""
    total = 2
    for char in value:
        ordinal = ord(char)
        total += (
            2
            if char in '\\"\b\f\n\r\t'
            else 6
            if ordinal < 32 or 127 <= ordinal <= 65535
            else 12
            if ordinal > 65535
            else 1
        )
        if total > _REPORT_BYTES:
            break
    return total


def _chunks(value: _Json) -> Iterator[str]:
    """Emit strict JSON fragments without converting retained numeric tokens."""
    if isinstance(value, _Number):
        yield value.token
    elif isinstance(value, dict):
        yield "{"
        for index, (key, item) in enumerate(value.items()):
            if index:
                yield ","
            yield json.dumps(key, ensure_ascii=True)
            yield ":"
            yield from _chunks(item)
        yield "}"
    elif isinstance(value, list):
        yield "["
        for index, item in enumerate(value):
            if index:
                yield ","
            yield from _chunks(item)
        yield "]"
    else:
        yield json.dumps(
            value, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        )


def _encode(value: _Json) -> tuple[str, int]:
    """Stop collecting output once its ASCII byte size exceeds the hard bound."""
    chunks = []
    total = 0
    for chunk in _chunks(value):
        total += len(chunk)
        if total > _REPORT_BYTES:
            return "", total
        chunks.append(chunk)
    return "".join(chunks), total
