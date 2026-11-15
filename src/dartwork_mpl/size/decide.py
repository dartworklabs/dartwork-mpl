"""Pure size decisions for the ordinary figure: domain types in, plan out.

A default canvas starts from the chart's kind and is moved by its density:
few points and series take the narrow 9 cm report tier, many (or a second y
axis) the 14.5 cm one. The active page then maps it: a journal sets one panel
in one 9 cm column and everything wider in two (17 cm); a slide draws under
its title in a 10.5 cm tall body; a poster scales the report tiers with its
font. Panel grids take the widest tier. Category names that would not stand
flat are an edge case in ``edges.py``.
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
    HalfBody,
    Page,
    Paper,
    Poster,
    Report,
    Slides,
    SquareBody,
    WholeBody,
)
from .model import ASPECTS, Aspect, FigureSize

# Journal columns: one panel in one column, wider content across two.
COLUMN, TWO_COLUMNS = cm(9), cm(17)
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
    a second y axis, any other kind and any grid take the full body.
    """
    height = SLIDE_BODY.height
    points, series = request.n_points, request.n_series
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


def grid_canvas(request: CanvasRequest, width: Length, page: Aspect) -> Canvas:
    """A panel grid ``width`` wide: each panel keeps the kind's aspect, and
    the whole is no taller than ``page`` (a share of the width) allows."""
    grid, aspect = request.grid, request.kind.spec.aspect
    rows = cm(width.cm / grid.ncols * aspect.ratio * grid.nrows)
    tallest = cm(width.cm * page.ratio)
    return Canvas(width, min(half_cm(rows), half_cm(tallest)))


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
    return grid_canvas(request, width, tallest)
