"""What colour a bar value label is drawn in.

* **Off the bar** (outside the bar end, and every stack total): the preset
  text colour.
* **On the bar** (a stack segment's label at its middle or inside its end,
  ``where="inside"`` or ``"center"``): white or the preset text colour,
  whichever reads better on the bar as drawn (its face composited over what
  shows behind it), by ``dm.readable_text_color``. ``dc.blue7``
  (``#1686e0``) takes the dark ink: 5.52:1 against white's 3.80:1.
* **Series.** ``color="series"`` colours the labels off their own bar (an
  outside label that is not a total): the bar's colour as drawn, darkened
  to 4.5:1 against the background (``dm.ensure_contrast``). A label on its
  own bar keeps the readable ink (the bar's own hue would not read on it);
  a total belongs to no single series and keeps the text colour.
* **Explicit.** Any other ``color=`` is used as given, everywhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

import matplotlib as mpl
import matplotlib.colors as mcolors

from .._colors.contrast import (
    composite_layers,
    composite_over,
    ensure_contrast,
    readable_text_color,
)
from .._figure_geometry import backdrop_layers, same_position_axes

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.patches import Rectangle

    from ._bar_label_options import Kind, Placement

__all__ = ["is_series", "label_ink"]

RGB: TypeAlias = tuple[float, float, float]


def is_series(color: object) -> bool:
    """Whether ``color`` asks for each bar's series colour."""
    return isinstance(color, str) and color == "series"


def _background(bar_axes: Axes) -> RGB:
    """What shows behind the bars: the figure, then each visible Axes patch."""
    return composite_layers(backdrop_layers(same_position_axes(bar_axes)))


def _series_ink(patch: Rectangle, background: RGB) -> str:
    """The bar's colour as drawn, darkened (or lightened) to 4.5:1 text."""
    face = mcolors.to_rgba(patch.get_facecolor())
    if face[3] == 0 and patch.get_linewidth() > 0:
        face = mcolors.to_rgba(patch.get_edgecolor())
    shown = mcolors.to_hex(composite_over(face, background))
    return ensure_contrast(shown, mcolors.to_hex(background))


def _on_bar_ink(patch: Rectangle, bar_axes: Axes) -> str:
    """White or the preset text colour, whichever reads better on the bar."""
    face = mcolors.to_rgba(patch.get_facecolor())
    shown = composite_over(face, _background(bar_axes))
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

    ``color`` is the call's ``color=``. ``None`` returned means the preset
    text colour (Text's own default), so nothing is set.
    """
    if color is not None and not is_series(color):
        return color
    if where != "outside":
        return _on_bar_ink(patch, bar_axes)
    if is_series(color) and kind != "total":
        return _series_ink(patch, _background(bar_axes))
    return None
