"""The ``dc.*`` colour families: each one's kind, and how many colours its
designed discrete form has."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from .space import Hex


@dataclass(frozen=True)
class Sequential:
    """A 10-step lightness ladder and its colormap."""

    value: ClassVar[str] = "sequential"
    continuous: ClassVar[bool] = True
    open_ended: ClassVar[bool] = False
    ladder: ClassVar[bool] = True
    most: ClassVar[int | None] = 10


@dataclass(frozen=True)
class MultiHue:
    """A colormap through several hues; every ``n`` up to 8 is designed."""

    value: ClassVar[str] = "multi-hue"
    continuous: ClassVar[bool] = True
    open_ended: ClassVar[bool] = True
    ladder: ClassVar[bool] = False
    most: ClassVar[int | None] = 8


@dataclass(frozen=True)
class Diverging:
    """Two ladders meeting at a light midpoint."""

    value: ClassVar[str] = "diverging"
    continuous: ClassVar[bool] = True
    open_ended: ClassVar[bool] = False
    ladder: ClassVar[bool] = False
    most: ClassVar[int | None] = 9


@dataclass(frozen=True)
class Cyclic:
    """A colormap whose ends meet; every ``n`` up to 24 is designed."""

    value: ClassVar[str] = "cyclic"
    continuous: ClassVar[bool] = True
    open_ended: ClassVar[bool] = True
    ladder: ClassVar[bool] = False
    most: ClassVar[int | None] = 24


@dataclass(frozen=True)
class Qualitative:
    """A set of distinct colours, no colormap."""

    value: ClassVar[str] = "qualitative"
    continuous: ClassVar[bool] = False
    open_ended: ClassVar[bool] = False
    ladder: ClassVar[bool] = False
    most: ClassVar[int | None] = None


#: A colour family's kind. ``value`` is its public label; ``continuous``:
#: it has a 256-step colormap; ``open_ended``: any ``n`` up to the limit is
#: designed; ``ladder``: its stops are a lightness ladder; ``most``: the
#: largest ``n`` its discrete form has (None: as many as its stops).
Kind = Sequential | MultiHue | Diverging | Cyclic | Qualitative

KINDS: tuple[Kind, ...] = (
    Sequential(),
    MultiHue(),
    Diverging(),
    Cyclic(),
    Qualitative(),
)


def parse_kind(text: object) -> Kind:
    """``"sequential"``... as a kind; ``ValueError`` names the five."""
    for kind in KINDS:
        if text == kind.value:
            return kind
    expected = ", ".join(k.value for k in KINDS)
    raise ValueError(
        f"Unknown color kind {text!r}; expected one of: {expected}."
    )


@dataclass(frozen=True)
class Family:
    """A ``dc.*`` family: its name, kind, and the values its forms draw on.

    ``stops`` is the designed row: the 10-step ladder (sequential), the
    8-stop canonical row (diverging), or the set (qualitative). ``cmap`` is
    the 256-step colormap (empty for qualitative). ``picks`` holds the
    frozen colormap indices of a multi-hue family's forms, by ``n``.
    """

    name: str
    kind: Kind
    stops: tuple[Hex, ...] = ()
    cmap: tuple[Hex, ...] = ()
    picks: tuple[tuple[int, ...], ...] = ()

    @property
    def size(self) -> int | None:
        """Stops in the designed form; None for multi-hue and cyclic."""
        if self.kind.open_ended:
            return None
        return len(self.stops)

    @property
    def most(self) -> int:
        """The largest ``n`` the family's discrete form accepts."""
        return self.kind.most or len(self.stops)


@dataclass(frozen=True)
class Count:
    """How many colours a discrete form has: a whole number, at least 1."""

    n: int

    @classmethod
    def parse(cls, value: object, family: Family) -> Count:
        """``value`` as a count ``family``'s form has; else ``ValueError``."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"n must be an integer for {family.name!r}")
        if not 1 <= value <= family.most:
            raise ValueError(
                f"{family.name!r} is a {family.kind.value} family with max "
                f"n={family.most}; got n={value}"
            )
        return cls(value)
