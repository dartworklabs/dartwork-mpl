"""Pure size decisions for the ordinary figure: domain types in, plan out.

A default canvas starts from the chart's kind and is moved by its density:
few points and series take the narrow 9 cm report tier, many (or a second y
axis) the 14.5 cm one. The active page then maps it: a journal sets one panel
in one 9 cm column and everything wider in two (17 cm); a slide draws under
its title in a 10.5 cm tall body, and a grid of two or more rows fills the
whole slide; a poster scales the report tiers with its font. Panel grids
take the widest tier, each row as tall as its cell's aspect, with room for
its text on top once the plots would be too small to share it. Category
names that would not stand flat are an edge case in ``edges.py``.
"""

from __future__ import annotations

import math
from typing import assert_never

from ..length import Length, cm
from .canvas import (
    BROAD,
    MEDIUM,
    NARROW,
    WIDEST,
    ByPositions,
    Canvas,
    CanvasRequest,
    FullSlideCanvas,
    HalfBody,
    Page,
    Paper,
    Poster,
    Report,
    Slides,
    SquareBody,
    WholeBody,
)
from .model import ASPECTS, Aspect, FigureSize, Grid

# Journal columns: one panel in one column, wider content across two.
COLUMN, TWO_COLUMNS = cm(9), cm(17)
# The slide less 1 cm side margins, a 2.8 cm title band and a 1 cm bottom
# margin: what a chart fills under a slide title.
SLIDE_BODY = Canvas(cm(23.4), cm(10.5))
# The whole slide: a grid of two or more rows under a slide title leaves
# each plot a 1.8 cm band, so it takes the title's room too.
FULL_SLIDE = Canvas(FullSlideCanvas.spec.width, FullSlideCanvas.spec.aspect)
# Half the body, 0.6 cm apart (two charts side by side), and two of three
# 7.4 cm columns with their gutter (a chart beside a text column).
SLIDE_HALF, SLIDE_TWO_THIRDS = cm(11.4), cm(15.4)
SLIDE_TIERS = (SLIDE_HALF, SLIDE_TWO_THIRDS, cm(23.4))
# Most x positions whose labels fit the half and two-thirds widths at the
# slide's 18.2 pt ticks (six company names fit 15.4 cm with 9 pt to spare).
SLIDE_HALF_POINTS, SLIDE_TWO_THIRDS_POINTS = 4, 6
# What a grid spends on its text at report text, measured with shared axes:
# the first row 1.5 cm on its title, tick labels and axis names (a 4.5 cm
# report row draws a 3.0 cm plot), each further row half that on its titles
# and gap, the x tick labels and name being shared under the bottom row.
ROW_TEXT, FURTHER_ROW_TEXT = cm(1.5), cm(0.75)
# The least plot a grid's cells keep at their aspect: what a 4.5 cm row
# draws. Below it the plot keeps the aspect and each row adds its text.
LEAST_PLOT = cm(3.0)


def figure_size(width: Length, height: Aspect | Length) -> FigureSize:
    """The figure a physical width and an aspect or height describe."""
    return Canvas(width, height).size()


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
    spec = request.kind.spec
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
    a second y axis, any other kind and a one-row grid take the full body;
    a grid of two or more rows takes the whole slide.
    """
    height = SLIDE_BODY.height
    points, series = request.n_points, request.n_series
    if request.grid.nrows > 1:
        return FULL_SLIDE
    if not request.grid.single:
        return SLIDE_BODY
    match request.kind.slide:
        case HalfBody():
            return Canvas(SLIDE_HALF, height)
        case SquareBody():
            return Canvas(cm(10.5), height)
        case ByPositions():
            pass
        case WholeBody():
            return SLIDE_BODY
        case _:
            assert_never(request.kind.slide)
    if points is None or request.dual_axis:
        return SLIDE_BODY
    if (series is not None and series >= 4) or points > SLIDE_TWO_THIRDS_POINTS:
        return SLIDE_BODY
    if points <= SLIDE_HALF_POINTS:
        return Canvas(SLIDE_HALF, height)
    return Canvas(SLIDE_TWO_THIRDS, height)


def grid_height(grid: Grid, cell: Length, aspect: Aspect, page: Page) -> Length:
    """A grid's rows over ``cell`` wide columns: each cell keeps ``aspect``.

    Where the grid's text (``ROW_TEXT`` once, ``FURTHER_ROW_TEXT`` per
    further row, scaled with the page's font) would leave each plot under
    ``LEAST_PLOT``, the plot keeps the aspect instead and each row adds
    ``ROW_TEXT`` on top, at least ``LEAST_PLOT`` plus that text.
    """
    rows, text = grid.nrows, ROW_TEXT.cm * page.scale
    kept = cell.cm * aspect.ratio
    spent = text + (rows - 1) * FURTHER_ROW_TEXT.cm * page.scale
    least = LEAST_PLOT.cm * page.scale
    if (rows * kept - spent) / rows >= least:
        return cm(rows * kept)
    return cm(rows * max(kept + text, least + text))


def grid_canvas(
    request: CanvasRequest, width: Length, page: Page, tallest: Aspect
) -> Canvas:
    """A panel grid ``width`` wide, as tall as :func:`grid_height` gives, the
    whole no taller than ``tallest`` (a share of the width) allows."""
    grid, aspect = request.grid, request.kind.spec.aspect
    rows = grid_height(grid, cm(width.cm / grid.ncols), aspect, page)
    most = cm(width.cm * tallest.ratio)
    return Canvas(width, min(half_cm(rows), half_cm(most)))


def canvas(request: CanvasRequest, page: Page) -> Canvas:
    """The ordinary default canvas for ``request`` on ``page``."""
    spec = request.kind.spec
    if spec.absolute:
        return Canvas(spec.width, spec.aspect)
    single = request.grid.single
    # The tallest a grid canvas may be, as a share of its width.
    tallest = Aspect(1.0)
    match page.family:
        case Slides():
            return slide_canvas(request)
        case Paper():
            full = not single or (spec.fixed and spec.width.cm > MEDIUM.cm)
            width = TWO_COLUMNS if full else COLUMN
        case Report():
            width = scaled(density_width(request) if single else WIDEST, page)
        case Poster():
            width = scaled(density_width(request) if single else WIDEST, page)
            tallest = ASPECTS["slide"]
        case _:
            assert_never(page.family)
    if single:
        return Canvas(width, spec.aspect)
    return grid_canvas(request, width, page, tallest)
