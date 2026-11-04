"""JSON-shaped value helpers shared by the gates and the comparison.

Responsibility: copy decoded JSON-like data (string-keyed mappings,
sequences, scalars) into deterministic immutable forms and back, and read
a mapping or a finite number from untrusted metric data without raising.
Used only inside ``verify``.
"""

import math
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import cast

__all__ = ["as_mapping", "finite_number", "freeze", "thaw"]


def freeze(value: object, *, subject: str) -> object:
    """Copy JSON-like data into key-sorted ``MappingProxyType`` and tuples.

    ``subject`` names the data in the ``TypeError`` raised for a
    non-string key or a value that is not JSON-like.
    """
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError(f"{subject} mappings require string keys")
        return MappingProxyType(
            {
                str(key): freeze(item, subject=subject)
                for key, item in sorted(value.items())
            }
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(freeze(item, subject=subject) for item in value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"unsupported {subject} value: {type(value).__name__}")


def thaw(value: object) -> object:
    """Return fresh, key-sorted JSON containers for frozen data."""
    if isinstance(value, Mapping):
        return {
            str(key): thaw(item)
            for key, item in sorted(
                value.items(), key=lambda pair: str(pair[0])
            )
        }
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value


def as_mapping(value: object) -> Mapping[str, object] | None:
    """Return a string-keyed mapping, or ``None`` for anything else."""
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        return None
    return cast(Mapping[str, object], value)


def finite_number(value: object) -> float | None:
    """Return one finite non-boolean number as ``float``, or ``None``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None
