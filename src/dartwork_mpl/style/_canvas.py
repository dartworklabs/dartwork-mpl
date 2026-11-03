"""The active preset's default canvas: one size per chart kind and density.

When a request names no size, :func:`figsize_for` picks it, so the same
request gets the same canvas whoever writes the code. Widths are four report
tiers, 9 / 12 / 14.5 / 17 cm (17 cm is the A4 text width with 2 cm margins),
chosen from the chart kind and two density hints:

- ``n_points <= 6`` and ``n_series <= 2`` on one axis: 9 cm;
- a second y axis, ``n_series >= 4`` or ``n_points > 12``: 14.5 cm;
- otherwise the kind's width. ``"matrix"``, ``"dense"``, ``"strip"``,
  ``"slide"``, ``"full_slide"`` and panel grids ignore the hints.

Every kind but ``matrix``, ``dense``, ``strip``, ``slide`` and
``full_slide`` is 4:3, the
:func:`~dartwork_mpl.figsize` default, so a request that names only a width
(``dm.figsize(dm.col1)``) gets the same shape.

``scientific`` presets map the tiers onto journal columns (9 or 17 cm).
``presentation`` presets draw under a 16:9 slide's title, 10.5 cm tall:
up to 4 x positions half the 23.4 cm body (11.4 cm), up to 6 two thirds
(15.4 cm), anything denser the full body; ``"compact"`` takes half of it
and ``"matrix"`` a 10.5 cm square. ``"slide"`` is the full body under any
preset; ``"full_slide"`` is the whole 16:9 slide (25.4 x 14.29 cm, no title
band), the slide the presentation sizes assume. ``poster`` scales the tiers by its font size over the
report's 8 pt, so text fills the same share of the canvas. Any other preset,
or none, uses the report tiers.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..units import ASPECT_TOKENS, figsize

__all__ = ["CANVAS_KINDS", "SLIDE_SCALE", "figsize_for", "grid_shape"]

_REPORT_FONT_PT = 8.0
_MAX_TIER_CM = 17.0
_COLUMNS_CM = (9.0, 17.0)
# Tallest grid canvas: an A4 text block (25.7 cm) less a caption; on posters,
# 16:9 of the widest tier.
_MAX_HEIGHT_CM = 24.0
_SLIDE_RATIO = 9.0 / 16.0
# A 10 in 16:9 slide, 25.4 x 14.29 cm: the slide the presentation sizes and
# SLIDE_SCALE assume. A chart that fills the slide ("a full-slide chart")
# takes all of it; a larger slide (13.33 in) would show the same text 25 %
# smaller on screen.
_SLIDE_CM = (25.4, 25.4 * _SLIDE_RATIO)
# The slide less 1 cm side margins, a 2.8 cm title band and a 1 cm bottom
# margin: the area a chart fills under a slide title.
_SLIDE_BODY_CM = (23.4, 10.5)
# Half the body, 0.6 cm apart: two charts side by side.
_SLIDE_HALF_CM = 11.4
# Two of three 7.4 cm columns with their 0.6 cm gutter: a chart beside a
# text column.
_SLIDE_TWO_THIRDS_CM = 15.4
# Most x positions whose labels fit the half and two-thirds widths at the
# slide's 18.2 pt ticks (six company names fit 15.4 cm with 9 pt to spare).
_SLIDE_HALF_MAX_POINTS = 4
_SLIDE_TWO_THIRDS_MAX_POINTS = 6

#: How much larger every point size is on slides than in a journal column:
#: the slide body's width over the column's, 23.4 / 9. The presentation
#: preset is the scientific one times this, and one ``dm.fs`` / ``dm.lw``
#: step there is this many points.
SLIDE_SCALE: float = round(_SLIDE_BODY_CM[0] / _COLUMNS_CM[0], 6)


@dataclass(frozen=True)
class _Kind:
    """Base width (cm), aspect and whether density hints may move it."""

    width_cm: float
    aspect: str | float
    fixed: bool = False
    absolute: bool = False  # the same physical size under every preset


CANVAS_KINDS: dict[str, _Kind] = {
    # Lines, bars, areas, scatter, distributions: everything not below.
    "default": _Kind(12.0, "standard"),
    # Horizontal bars: room for long category labels.
    "barh": _Kind(14.5, "standard"),
    # Insets and half-width panels.
    "compact": _Kind(9.0, "standard"),
    # Heatmaps and correlation matrices.
    "matrix": _Kind(12.0, "square", fixed=True),
    # Long, dense timelines (daily or monthly series over years).
    "dense": _Kind(17.0, "cinema", fixed=True),
    # A full-width strip, e.g. one row of a dashboard.
    "strip": _Kind(17.0, 0.45, fixed=True),
    # The body of a 16:9 slide under its title, under any preset.
    "slide": _Kind(
        _SLIDE_BODY_CM[0],
        _SLIDE_BODY_CM[1] / _SLIDE_BODY_CM[0],
        fixed=True,
        absolute=True,
    ),
    # A whole 16:9 slide, no title band, under any preset.
    "full_slide": _Kind(_SLIDE_CM[0], _SLIDE_RATIO, fixed=True, absolute=True),
}


def _ratio(aspect: str | float) -> float:
    return ASPECT_TOKENS[aspect] if isinstance(aspect, str) else aspect


def _check_count(name: str, value: int | None, minimum: int) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")


def _tier_cm(
    kind: _Kind, n_points: int | None, n_series: int | None, dual_axis: bool
) -> float:
    if kind.fixed:
        return kind.width_cm
    sparse = (
        n_points is not None
        and n_series is not None
        and n_points <= 6
        and n_series <= 2
        and not dual_axis
    )
    if sparse:
        return 9.0
    if (
        dual_axis
        or (n_series is not None and n_series >= 4)
        or (n_points is not None and n_points > 12)
    ):
        return 14.5
    return kind.width_cm


def _family(names: Sequence[str]) -> tuple[str, float]:
    """``("paper" | "slides" | "poster" | "report", scale)`` for the preset."""
    from . import load_style_dict

    for name in names:
        base = name.removesuffix("-kr")
        if base == "scientific":
            return "paper", 1.0
        if base == "presentation":
            return "slides", 1.0
        if base == "poster":
            font_pt = float(load_style_dict(f"font-{base}")["font.size"])
            return "poster", font_pt / _REPORT_FONT_PT
        if base in ("report", "web", "minimal", "dark"):
            return "report", 1.0
    return "report", 1.0


def _half_cm(value: float) -> float:
    """Round to the nearest 0.5 cm, halves up."""
    return math.floor(value * 2 + 0.5) / 2


def _slide_canvas(
    kind: str, n_points: int | None, n_series: int | None, dual_axis: bool
) -> tuple[float, float]:
    """Width and height (cm) of a chart under a slide title.

    The height is always the body's 10.5 cm, so text is the same size on
    every slide. ``"compact"`` takes half the width and ``"matrix"`` a
    10.5 cm square. A ``"default"`` chart is as wide as its x positions
    need at slide text size: up to 4 positions half the body (11.4 cm), up
    to 6 two thirds (15.4 cm). More positions, unknown positions (point
    clouds), 4 or more series or a second y axis take the full 23.4 cm, as
    does every other kind.
    """
    width, height = _SLIDE_BODY_CM
    if kind == "compact":
        return _SLIDE_HALF_CM, height
    if kind == "matrix":
        return height, height
    if kind != "default" or n_points is None or dual_axis:
        return width, height
    if n_series is not None and n_series >= 4:
        return width, height
    if n_points <= _SLIDE_HALF_MAX_POINTS:
        return _SLIDE_HALF_CM, height
    if n_points <= _SLIDE_TWO_THIRDS_MAX_POINTS:
        return _SLIDE_TWO_THIRDS_CM, height
    return width, height


def figsize_for(
    kind: str = "default",
    *,
    n_points: int | None = None,
    n_series: int | None = None,
    dual_axis: bool = False,
    nrows: int = 1,
    ncols: int = 1,
) -> tuple[float, float]:
    """Return the active preset's canvas for a chart, as a ``figsize`` tuple.

    Use it when the request names no size; a size the user gives goes to
    :func:`dartwork_mpl.figsize` instead. The result depends only on the
    arguments and the active preset, so the same request always gets the
    same canvas::

        dm.style.use("report")
        fig, ax = plt.subplots(
            figsize=dm.figsize_for(n_points=len(years), n_series=3)
        )
        fig, axes = plt.subplots(
            2, 3, figsize=dm.figsize_for(nrows=2, ncols=3)
        )

    Parameters
    ----------
    kind : str, optional
        A key of :data:`CANVAS_KINDS`: ``"default"`` (lines, bars, areas,
        scatter, distributions), ``"barh"`` (long category labels),
        ``"compact"`` (insets, half-width panels), ``"matrix"`` (heatmaps),
        ``"dense"`` (long dense timelines), ``"strip"`` (a full-width
        strip), ``"slide"`` (a chart filling a 16:9 slide under its
        title, 23.4 x 10.5 cm, under any preset) or ``"full_slide"`` (a
        chart that is the whole 16:9 slide, 25.4 x 14.29 cm, under any
        preset: "a full-slide chart").
    n_points : int, optional
        Positions along the category or time axis (bars per group count
        once). Leave out for scatter, histograms and other point clouds.
        Under ``presentation`` presets it picks a 11.4, 15.4 or 23.4 cm
        wide slide chart (up to 4, up to 6, more positions).
    n_series : int, optional
        Plotted series: lines, bar colours, stacked layers.
    dual_axis : bool, optional
        True when a second y axis (``twinx``) is drawn.
    nrows, ncols : int, optional
        Panel grid; :func:`grid_shape` picks them for ``n`` panels. Any grid
        larger than one panel takes the widest tier; every panel keeps the
        kind's aspect, up to a 24 cm tall canvas (16:9 of the width on
        posters). On slides a grid fills the body under the title.

    Returns
    -------
    tuple[float, float]
        ``(width, height)`` in inches, for ``plt.subplots(figsize=...)``.

    Raises
    ------
    ValueError
        If ``kind`` is unknown or a count is below its minimum.
    TypeError
        If a count is not an int.
    """
    if kind not in CANVAS_KINDS:
        known = ", ".join(sorted(CANVAS_KINDS))
        raise ValueError(f"unknown canvas kind {kind!r}; use one of: {known}")
    _check_count("n_points", n_points, 0)
    _check_count("n_series", n_series, 0)
    _check_count("nrows", nrows, 1)
    _check_count("ncols", ncols, 1)
    spec = CANVAS_KINDS[kind]

    from . import _active_preset

    if spec.absolute:
        return figsize(f"{spec.width_cm:g}cm", spec.aspect)
    family, scale = _family(_active_preset)
    grid = nrows * ncols > 1
    if family == "slides":
        if grid:
            width, height = _SLIDE_BODY_CM
        else:
            width, height = _slide_canvas(kind, n_points, n_series, dual_axis)
        return figsize(f"{width:g}cm", f"{height:g}cm")
    width = (
        _MAX_TIER_CM if grid else _tier_cm(spec, n_points, n_series, dual_axis)
    )
    if family == "paper":
        width = _COLUMNS_CM[0] if width <= 12.0 else _COLUMNS_CM[1]
    else:
        width = _half_cm(width * scale)

    if not grid:
        return figsize(f"{width:g}cm", spec.aspect)
    height = width / ncols * _ratio(spec.aspect) * nrows
    cap = width * _SLIDE_RATIO if family == "poster" else _MAX_HEIGHT_CM
    height = min(_half_cm(height), _half_cm(cap))
    return figsize(f"{width:g}cm", f"{height:g}cm")


def grid_shape(n: int) -> tuple[int, int]:
    """Return ``(nrows, ncols)`` for ``n`` small-multiple panels.

    Up to three panels sit in one row; more fill a near-square grid with
    ``ceil(sqrt(n))`` columns, wider than tall, so every agent lays out the
    same request the same way::

        nrows, ncols = dm.grid_shape(len(cities))  # 6 -> (2, 3)
        fig, axes = plt.subplots(
            nrows, ncols, figsize=dm.figsize_for(nrows=nrows, ncols=ncols)
        )

    Raises
    ------
    ValueError
        If ``n`` is below 1.
    TypeError
        If ``n`` is not an int.
    """
    _check_count("n", n, 1)
    if n <= 3:
        return 1, n
    ncols = math.ceil(math.sqrt(n))
    return math.ceil(n / ncols), ncols
