"""Figure-level text: the source/note line and point-unit offsets."""

from __future__ import annotations

from typing import Any

import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import ScaledTranslation

from ..scale import fs


def add_note(fig: Figure, text: str, **kw: Any) -> Text:
    """Add a source or note line under the plot, in the preset's note style.

    One call for "add a source note" / "그림 아래에 출처를 적어줘", so every
    agent draws the same line: the figure's lower-left corner, left-aligned,
    one step below the preset font (``dm.fs(-1)``) in the preset text colour.
    :func:`dartwork_mpl.simple_layout` keeps the axes, tick labels and axis
    labels above it with the preset's ``axes.labelpad`` between them. A
    ``fontsize=``, ``color=`` or other ``Text`` keyword the user names wins::

        dm.add_note(fig, "Source: internal web logs")
        dm.simple_layout(fig)

    Returns the :class:`~matplotlib.text.Text`.
    """

    style: dict[str, Any] = {"ha": "left", "va": "bottom", "fontsize": fs(-1)}
    style.update(kw)
    note = fig.text(0.0, 0.0, text, **style)
    # simple_layout reserves this gap above the note (layout slice reads it).
    note._dm_layout_gap_pt = float(mpl.rcParams["axes.labelpad"])  # type: ignore[attr-defined]
    return note


def make_offset(x: float, y: float, fig: Figure) -> ScaledTranslation:
    """Return a point-unit offset transform for the figure's DPI.

    ``ScaledTranslation(x / 72, y / 72, fig.dpi_scale_trans)``: the offset is
    given in points and converted to pixels by the Figure's
    ``dpi_scale_trans``, so it keeps its physical size at any DPI. Add it to
    another transform (``ax.transData + dm.make_offset(0, 4, fig)``) to nudge
    text or markers.

    Parameters
    ----------
    x : float
        Horizontal offset in points.
    y : float
        Vertical offset in points.
    fig : matplotlib.figure.Figure
        The Figure whose DPI scale is used.

    Returns
    -------
    matplotlib.transforms.ScaledTranslation
        A translation transform that can be added to other transforms.
    """
    dx, dy = x / 72, y / 72
    return ScaledTranslation(dx, dy, fig.dpi_scale_trans)
