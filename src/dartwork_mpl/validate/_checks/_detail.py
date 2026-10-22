"""Typed reads of a ``VisualWarning.detail`` dict at the fix-handler boundary.

Each check declares the exact shape of the ``detail`` it emits as a
``TypedDict`` (one per variant) and builds its dict through that type, so
the runtime dict and its keys stay what callers already read. A fix
handler receives any ``VisualWarning`` — including one a caller built by
hand — so it parses ``warning.detail`` back into the check's TypedDict
with these readers instead of re-reading keys with ``.get(key, default)``.

Contract of every reader: a key that is absent, or present with a value
of the wrong type, yields the documented default. ``bool`` counts as a
number, as it did for the arithmetic the handlers perform.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeAlias, TypeVar

Axis: TypeAlias = Literal["x", "y"]
"""The Axes axis a tick check reports on."""

Side: TypeAlias = Literal["left", "right", "bottom", "top"]
"""The figure edge a layout check reports on."""

AXES: tuple[Axis, ...] = ("x", "y")
SIDES: tuple[Side, ...] = ("left", "right", "bottom", "top")

_Choice = TypeVar("_Choice", bound=str)


def wire(detail: Mapping[str, object]) -> dict[str, Any]:
    """Return a check's typed detail as the plain dict ``VisualWarning`` holds."""
    return dict(detail)


def number(raw: Mapping[str, object], key: str, default: float) -> float:
    """Read a number unchanged (an ``int`` stays an ``int``), else ``default``."""
    value = raw.get(key)
    return value if isinstance(value, (int, float)) else default


def choice(
    raw: Mapping[str, object], key: str, choices: tuple[_Choice, ...]
) -> _Choice | None:
    """Read one of ``choices``; ``None`` when the key holds none of them."""
    value = raw.get(key)
    return next((option for option in choices if option == value), None)
