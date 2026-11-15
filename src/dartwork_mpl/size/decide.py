"""Pure size decisions for the ordinary figure: domain types in, plan out.

A default canvas starts from the chart's kind and is moved by its density:
few points and series take the narrow 9 cm report tier, many (or a second y
axis) the 14.5 cm one. The active page then maps it: a journal sets one panel
in one 9 cm column and everything wider in two (17 cm); a slide draws under
its title in a 10.5 cm tall body; a poster scales the report tiers with its
font. Panel grids take the widest tier. Special cases (grouped bars' value
labels, category names, stacked panels, slide grids) are in ``edges.py``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from .model import (
    ASPECTS,
    Aspect,
    Canvas,
    CanvasKind,
    CanvasRequest,
    Family,
    FigureSize,
    Grid,
    KindSpec,
    Length,
    Page,
    Panels,
    cm,
)

# The report tiers: 17 cm is the A4 text width with 2 cm margins.
NARROW, MEDIUM, BROAD, WIDEST = cm(9), cm(12), cm(14.5), cm(17)
REPORT_TIERS = (NARROW, MEDIUM, BROAD, WIDEST)
# Journal columns: one panel in one column, wider content across two.
COLUMN, TWO_COLUMNS = cm(9), cm(17)
# A 10 in 16:9 slide, 25.4 x 14.29 cm. A larger slide (13.33 in) would show
# the same text 25 % smaller on screen.
SLIDE = Canvas(cm(25.4), ASPECTS["slide"])
# The slide less 1 cm side margins, a 2.8 cm title band and a 1 cm bottom
# margin: what a chart fills under a slide title.
SLIDE_BODY = Canvas(cm(23.4), cm(10.5))
# Half the body, 0.6 cm apart (two charts side by side), and two of three
# 7.4 cm columns with their gutter (a chart beside a text column).
SLIDE_HALF, SLIDE_TWO_THIRDS = cm(11.4), cm(15.4)
SLIDE_TIERS = (SLIDE_HALF, SLIDE_TWO_THIRDS, cm(23.4))
# Most x positions whose labels fit the half and two-thirds widths at the
# slide's 18.2 pt ticks (six company names fit 15.4 cm with 9 pt to spare).
SLIDE_HALF_POINTS, SLIDE_TWO_THIRDS_POINTS = 4, 6

KINDS: Mapping[CanvasKind, KindSpec] = {
    CanvasKind.DEFAULT: KindSpec(MEDIUM, ASPECTS["standard"]),
    CanvasKind.GROUPED: KindSpec(MEDIUM, ASPECTS["standard"]),
    CanvasKind.BARH: KindSpec(BROAD, ASPECTS["standard"]),
    CanvasKind.COMPACT: KindSpec(NARROW, ASPECTS["standard"]),
    CanvasKind.MATRIX: KindSpec(MEDIUM, ASPECTS["square"], fixed=True),
    CanvasKind.DENSE: KindSpec(WIDEST, ASPECTS["cinema"], fixed=True),
    CanvasKind.STRIP: KindSpec(WIDEST, Aspect(0.45), fixed=True),
    CanvasKind.SLIDE: KindSpec(
        cm(23.4), Aspect(10.5 / 23.4), fixed=True, absolute=True
    ),
    CanvasKind.FULL_SLIDE: KindSpec(
        cm(25.4), ASPECTS["slide"], fixed=True, absolute=True
    ),
}
# The tallest a grid canvas may be, as a share of its width.
TALLEST: Mapping[Family, Aspect] = {
    Family.REPORT: Aspect(1.0),
    Family.PAPER: Aspect(1.0),
    Family.POSTER: ASPECTS["slide"],
}


def figure_size(width: Length, height: Aspect | Length) -> FigureSize:
    """The figure a physical width and an aspect or height describe."""
    return Canvas(width, height).size()


def grid_for(panels: Panels) -> Grid:
    """Rows and columns for ``panels`` small multiples.

    Up to three sit in one row; more fill a near-square grid with
    ``ceil(sqrt(n))`` columns, wider than tall.
    """
    if panels.n <= 3:
        return Grid(1, panels.n)
    ncols = math.ceil(math.sqrt(panels.n))
    return Grid(math.ceil(panels.n / ncols), ncols)


def half_cm(length: Length) -> Length:
    """``length`` rounded to the nearest half centimetre, halves up.

    The tolerance keeps a half that went through inches (12.75 cm read back
    as 12.749999...) rounding up, as the same number in centimetres does.
    """
    return cm(math.floor(length.cm * 2 + 0.5 + 1e-9) / 2)


def scaled(length: Length, page: Page) -> Length:
    """A report width on ``page``: scaled with its font, to half a cm."""
    return half_cm(cm(length.cm * page.scale))


def density_width(request: CanvasRequest) -> Length:
    """The report tier the kind and density hints pick for one panel."""
    spec = KINDS[request.kind]
    points, series = request.n_points, request.n_series
    if spec.fixed:
        return spec.width
    sparse = (
        points is not None
        and series is not None
        and points <= 6
        and series <= 2
        and not request.dual_axis
    )
    if sparse:
        return NARROW
    busy = (series is not None and series >= 4) or (
        points is not None and points > 12
    )
    if request.dual_axis or busy:
        return BROAD
    return spec.width


def slide_canvas(request: CanvasRequest) -> Canvas:
    """A chart under a slide title: 10.5 cm tall, as wide as it needs.

    ``"compact"`` takes half the body and ``"matrix"`` a 10.5 cm square. A
    default chart takes half the body up to 4 x positions and two thirds up
    to 6; more positions, unknown positions (point clouds), 4 or more series,
    a second y axis, any other kind and any grid take the full body.
    """
    height = SLIDE_BODY.height
    points, series = request.n_points, request.n_series
    if not request.grid.single:
        return SLIDE_BODY
    if request.kind is CanvasKind.COMPACT:
        return Canvas(SLIDE_HALF, height)
    if request.kind is CanvasKind.MATRIX:
        return Canvas(cm(10.5), height)
    plain = request.kind in (CanvasKind.DEFAULT, CanvasKind.GROUPED)
    if not plain or points is None or request.dual_axis:
        return SLIDE_BODY
    if (series is not None and series >= 4) or points > SLIDE_TWO_THIRDS_POINTS:
        return SLIDE_BODY
    if points <= SLIDE_HALF_POINTS:
        return Canvas(SLIDE_HALF, height)
    return Canvas(SLIDE_TWO_THIRDS, height)


def grid_canvas(request: CanvasRequest, page: Page, width: Length) -> Canvas:
    """A panel grid ``width`` wide: each panel keeps the kind's aspect, and
    the whole is no taller than the page allows."""
    grid, aspect = request.grid, KINDS[request.kind].aspect
    rows = cm(width.cm / grid.ncols * aspect.ratio * grid.nrows)
    tallest = cm(width.cm * TALLEST[page.family].ratio)
    return Canvas(width, min(half_cm(rows), half_cm(tallest)))


def canvas(request: CanvasRequest, page: Page) -> Canvas:
    """The ordinary default canvas for ``request`` on ``page``."""
    spec = KINDS[request.kind]
    if spec.absolute:
        return Canvas(spec.width, spec.aspect)
    if page.family is Family.SLIDES:
        return slide_canvas(request)
    single = request.grid.single
    if page.family is Family.PAPER:
        full = not single or (spec.fixed and spec.width.cm > MEDIUM.cm)
        width = TWO_COLUMNS if full else COLUMN
    else:
        width = scaled(density_width(request) if single else WIDEST, page)
    if single:
        return Canvas(width, spec.aspect)
    return grid_canvas(request, page, width)
