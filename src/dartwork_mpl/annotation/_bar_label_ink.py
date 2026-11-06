"""What colour a bar value label is drawn in.

* **Off the bar** (outside the bar end, and every stack total): the preset
  text colour.
* **On the bar** (a stack segment's label, ``where="inside"`` or
  ``"center"``): white or the preset text colour, whichever reads better on
  the bar as drawn (its face composited over what shows behind it), by
  ``dm.readable_text_color``. ``dc.blue7`` (``#1686e0``) takes the dark ink:
  5.52:1 against white's 3.80:1.
* **Series.** ``color="series"``: each bar's colour as drawn, darkened to
  4.5:1 against the background (``dm.ensure_contrast``). A total belongs to
  no single series and keeps the text colour.
* **Explicit.** Any other ``color=`` is used as given, totals included.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

import matplotlib as mpl
import matplotlib.colors as mcolors

from .._colors.contrast import ensure_contrast, readable_text_color
from .._figure_geometry import same_position_axes

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.patches import Rectangle

    from ._bar_labels import Kind, Placement

__all__ = ["is_series", "label_ink"]

RGB: TypeAlias = tuple[float, float, float]


def is_series(color: object) -> bool:
    """Whether ``color`` asks for each bar's series colour."""
    return isinstance(color, str) and color == "series"


def _over(top: tuple[float, float, float, float], below: RGB) -> RGB:
    alpha = top[3]
    r, g, b = (
        alpha * t + (1.0 - alpha) * u
        for t, u in zip(top[:3], below, strict=True)
    )
    return (r, g, b)


def _background(bar_axes: Axes) -> RGB:
    """What shows behind the bars: the figure, then each visible Axes patch."""
    below: RGB = (1.0, 1.0, 1.0)
    root = bar_axes.get_figure(root=True)
    parent = bar_axes.get_figure(root=False)
    for container in (root, parent if parent is not root else None):
        if container is not None and container.patch.get_visible():
            below = _over(mcolors.to_rgba(container.get_facecolor()), below)
    for member in sorted(
        same_position_axes(bar_axes), key=lambda m: m.get_zorder()
    ):
        if member.get_frame_on() and member.patch.get_visible():
            below = _over(mcolors.to_rgba(member.get_facecolor()), below)
    return below


def _series_ink(patch: Rectangle, background: RGB) -> str:
    """The bar's colour as drawn, darkened (or lightened) to 4.5:1 text."""
    face = mcolors.to_rgba(patch.get_facecolor())
    if face[3] == 0 and patch.get_linewidth() > 0:
        face = mcolors.to_rgba(patch.get_edgecolor())
    shown = mcolors.to_hex(_over(face, background))
    return ensure_contrast(shown, mcolors.to_hex(background))


def _on_bar_ink(patch: Rectangle, bar_axes: Axes) -> str:
    """White or the preset text colour, whichever reads better on the bar."""
    face = mcolors.to_rgba(patch.get_facecolor())
    shown = _over(face, _background(bar_axes))
    return readable_text_color(
        mcolors.to_hex(shown),
        light="white",
        dark=mcolors.to_hex(mpl.rcParams["text.color"]),
    )


def label_ink(
    color: object,
    kind: Kind,
    where: Placement,
    patch: Rectangle,
    bar_axes: Axes,
) -> object | None:
    """The colour for a label of ``kind`` at ``where`` on ``patch``.

    ``color`` is the call's ``color=``; ``None`` means the preset text colour
    (Text's own default), so nothing is set.
    """
    if color is None:
        return None if where == "outside" else _on_bar_ink(patch, bar_axes)
    if is_series(color):
        if kind == "total":
            return None
        return _series_ink(patch, _background(bar_axes))
    return color
