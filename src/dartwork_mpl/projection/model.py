"""An Axes' projection, read once from the name matplotlib gives it.

``ax.name`` is ``"rectilinear"`` for the plain 2D Axes, ``"3d"`` for a 3D
one and something else for polar, geographic or a registered projection.
Each variant says what the slices ask of it: ``flat``, the plain x/y Axes
whose text is fitted and checked; ``spatial``, a 3D Axes that places its
text by projecting it while it draws.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeAlias


@dataclass(frozen=True)
class Rectilinear:
    """matplotlib's plain 2D Axes."""

    flat: ClassVar[bool] = True
    spatial: ClassVar[bool] = False


@dataclass(frozen=True)
class ThreeD:
    """A 3D Axes (``projection="3d"``)."""

    flat: ClassVar[bool] = False
    spatial: ClassVar[bool] = True


@dataclass(frozen=True)
class Curved:
    """Any other projection: polar, geographic, a registered one."""

    flat: ClassVar[bool] = False
    spatial: ClassVar[bool] = False


Projection: TypeAlias = Rectilinear | ThreeD | Curved


def parse_projection(name: str) -> Projection:
    """The projection matplotlib names ``name`` (``Axes.name``)."""
    if name == "rectilinear":
        return Rectilinear()
    if name == "3d":
        return ThreeD()
    return Curved()
