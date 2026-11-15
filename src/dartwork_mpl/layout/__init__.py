"""Content-aware margins: ``dm.simple_layout(fig)``.

The root GridSpec's edges are set so the drawn content of every Axes (tick
labels, axis names, titles, texts, legends) sits ``margin`` from the canvas
edge, past what figure-level text and legends reserve, measured again until
no edge moves by half a pixel. No optimiser: the same figure gives the same
layout every time.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from .. import labels
from ..edgecase import settle
from . import decide, loop, measure
from .edges import EDGES
from .model import MarginInput, Refuse, Request, parse_margins

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.gridspec import GridSpecBase, SubplotSpec

__all__ = ["simple_layout"]


def simple_layout(
    fig: Figure,
    gs: GridSpecBase | SubplotSpec | None = None,
    *,
    margin: MarginInput = 0,
    ml: MarginInput | None = None,
    mr: MarginInput | None = None,
    mt: MarginInput | None = None,
    mb: MarginInput | None = None,
    fit_labels: bool = True,
) -> None:
    """Place every Axes' content ``margin`` from the figure edges.

    ``margin`` (and per side ``ml``, ``mr``, ``mt``, ``mb``) is a
    :class:`~dartwork_mpl.Length` (``dm.mm(2)``), a unit string (``"2mm"``),
    a percentage (``"2%"``) or a figure fraction (``0.02``); ``0`` puts the
    content flush with the edges. ``gs`` names the grid to fit (its root
    GridSpec), default the first Axes'; every Axes is measured. A
    suptitle, ``fig.text`` note or figure legend keeps its edge clear.

    Before measuring, axes nobody formatted get the library's tick numbers
    and dates (:func:`dartwork_mpl.ticks.prepare`), and ``dm.label_bars``
    values, ``dm.place_legend`` legends, ``dm.label_line_ends`` names and
    ``dm.label_axes`` letters settle at the size being fitted.

    With ``fit_labels`` (default), text that still collides once the
    margins hold is fitted: crowded bottom tick labels wrap at their spaces
    (or turn 30, 45 or 90 degrees when they cannot), an axis name longer
    than its plot and in the way wraps, and panels whose content meets
    across spacing nobody set move apart. A round that leaves a plot under
    30 % of its width or height is undone. Text you rotated, broke into
    lines or wrote as mathtext is left alone.

    Calling it again first undoes what the last call set where it is
    still as set, so it draws the same figure. A figure with no Axes is
    left alone; one without a GridSpec (``fig.add_axes``) or with
    SubFigures is left alone with a warning. A margin that is not finite
    raises ``ValueError``.
    """
    grid = measure.root_grid(fig, gs)
    request = Request(
        has_axes=bool(fig.axes),
        has_grid=grid is not None,
        has_subfigures=bool(fig.subfigs),
    )
    answer = settle(request, decide.answer(request), EDGES).plan
    if isinstance(answer, Refuse):
        if answer.warning is not None:
            warnings.warn(answer.warning, stacklevel=2)
        return
    assert grid is not None
    size = fig.get_size_inches()
    margins = parse_margins(
        margin, (ml, mr, mt, mb), (float(size[0]), float(size[1]))
    )
    loop.run(fig, grid, margins, fit_labels)
    labels.warn_hidden(fig, stacklevel=2)
