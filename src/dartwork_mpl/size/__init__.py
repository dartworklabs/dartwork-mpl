"""Physical units and figure size: what "13 cm wide, standard aspect" means.

``dm.figsize(width, aspect)`` turns a physical width and an aspect (or a
height) into matplotlib's inch tuple. ``dm.figsize_for(...)`` picks the active
preset's canvas when the request names no size, and ``dm.grid_shape(n)`` the
rows and columns for ``n`` panels. Each call parses its input into the
slice's types (``model``), decides (``decide`` and the named ``edges``) and
hands back plain inches.
"""

from __future__ import annotations

from ..edgecase import settle
from . import decide, measure
from .canvas import CanvasFacts, CanvasRequest, parse_canvas_kind, parse_names
from .edges import EDGES
from .model import (
    ASPECTS,
    STANDARD,
    Grid,
    Length,
    Panels,
    cm,
    col1,
    col2,
    inch,
    mm,
    parse_height,
    pt,
)

__all__ = [
    "Length",
    "cm",
    "col1",
    "col2",
    "figsize",
    "figsize_for",
    "grid_shape",
    "inch",
    "list_aspect_tokens",
    "mm",
    "pt",
]


def figsize(width: object, aspect: object = STANDARD) -> tuple[float, float]:
    """Return matplotlib's ``figsize`` for a physical width and an aspect.

    ``width`` is a unit string (``"13cm"``, ``"5in"``, ``"170mm"``,
    ``"24pt"``) or a :class:`Length` (``dm.cm(13)``, ``dm.col1``); a bare
    number raises ``TypeError``. ``aspect`` is an aspect token (``"wide"``;
    see :func:`list_aspect_tokens`), a ``"W:H"`` string (``"16:9"``), a
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
) -> tuple[float, float]:
    """Return the active preset's canvas for a chart that names no size.

    The same arguments under the same preset always give the same canvas.
    ``kind``: ``"default"`` (lines, bars, scatter...), ``"grouped"`` (grouped
    bars), ``"barh"``, ``"compact"``, ``"matrix"`` (heatmaps), ``"dense"``,
    ``"strip"``, ``"slide"`` (under a slide title, 23.4 x 10.5 cm) or
    ``"full_slide"`` (the whole 16:9 slide). ``n_points`` (x positions) and
    ``n_series`` move the width between the preset's tiers; ``labels`` (the
    category names, in axis order) widens it until they stand flat;
    ``dual_axis`` marks a ``twinx``; ``nrows`` / ``ncols`` a panel grid (see
    :func:`grid_shape`). Raises ``ValueError`` for an unknown kind or a count
    below its minimum, ``TypeError`` for a count that is not an int or
    labels without an axis order (a string, set or mapping)::

        fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=len(years)))
    """
    request = CanvasRequest(
        kind=parse_canvas_kind(kind),
        n_points=n_points,
        n_series=n_series,
        dual_axis=dual_axis,
        grid=Grid(nrows, ncols),
        names=parse_names(labels),
    )
    page = measure.active_page()
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


def list_aspect_tokens() -> dict[str, float]:
    """Return the aspect tokens as ``{name: height / width}``, tallest first."""
    ratios = {name: aspect.ratio for name, aspect in ASPECTS.items()}
    return dict(sorted(ratios.items(), key=lambda item: -item[1]))
