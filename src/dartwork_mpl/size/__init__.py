"""Figure size: what "13 cm wide, standard aspect" means.

``dm.figsize(width, aspect)`` turns a physical width and an aspect (or a
height) into matplotlib's inch tuple. :func:`figsize_for` picks the canvas
of the presets it is given when the request names no size, and
``dm.grid_shape(n)`` the rows and columns for ``n`` panels. Each call parses its input into the
slice's types (``model``), decides (``decide`` and the named ``edges``) and
hands back plain inches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..edgecase import settle
from ..length import Length
from . import decide, measure
from .canvas import CanvasFacts, CanvasRequest, parse_canvas_kind, parse_names
from .edges import EDGES
from .model import STANDARD, Grid, Panels, parse_height

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .measure import LayerReader

__all__ = ["figsize", "figsize_for", "grid_shape"]


def figsize(width: object, aspect: object = STANDARD) -> tuple[float, float]:
    """Return matplotlib's ``figsize`` for a physical width and an aspect.

    ``width`` is a unit string (``"13cm"``, ``"5in"``, ``"170mm"``,
    ``"24pt"``) or a :class:`Length` (``dm.cm(13)``, ``dm.col1``); a bare
    number raises ``TypeError``. ``aspect`` is an aspect token (``"wide"``;
    ``"square"``, ``"golden"``, ``"tall"``), a ``"W:H"`` string (``"16:9"``), a
    number (``height / width``), or a height as a unit string (``"8cm"``) or
    :class:`Length`. Default ``"standard"`` (4:3)::

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
    """
    size = decide.figure_size(Length.parse(width), parse_height(aspect))
    return size.inches


def figsize_for(
    kind: str = "default",
    *,
    n_points: int | None = None,
    n_series: int | None = None,
    labels: object = None,
    dual_axis: bool = False,
    nrows: int = 1,
    ncols: int = 1,
    presets: Sequence[str],
    layer: LayerReader,
) -> tuple[float, float]:
    """The canvas for a chart that names no size, on the page of the active
    ``presets`` (a poster's font read with ``layer``).

    ``dm.figsize_for`` is this given the style slice's active presets
    (``compose.size``); the other arguments are documented there.
    """
    request = CanvasRequest(
        kind=parse_canvas_kind(kind),
        n_points=n_points,
        n_series=n_series,
        dual_axis=dual_axis,
        grid=Grid(nrows, ncols),
        names=parse_names(labels),
    )
    page = measure.active_page(presets, layer)
    facts = CanvasFacts(request, page, measure.name_widths(request.names))
    plan = decide.canvas(request, page)
    return settle(facts, plan, EDGES).plan.size().inches


def grid_shape(n: int) -> tuple[int, int]:
    """Return ``(nrows, ncols)`` for ``n`` small-multiple panels.

    Up to three panels sit in one row; more fill a near-square grid,
    wider than tall (6 -> (2, 3), 10 -> (3, 4))::

        nrows, ncols = dm.grid_shape(len(cities))
    """
    grid = decide.grid_for(Panels(n))
    return (grid.nrows, grid.ncols)
