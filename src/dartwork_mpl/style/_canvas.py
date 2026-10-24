"""The active preset's default canvas: one size per chart kind and density.

When a request names no size, :func:`figsize_for` picks it, so the same
request gets the same canvas whoever writes the code. Widths are four report
tiers, 9 / 12 / 14.5 / 17 cm (17 cm is the A4 text width with 2 cm margins),
chosen from the chart kind and two density hints:

- ``n_points <= 6`` and ``n_series <= 2`` on one axis: 9 cm;
- a second y axis, ``n_series >= 4`` or ``n_points > 12``: 14.5 cm;
- otherwise the kind's width. ``"matrix"``, ``"dense"``, ``"strip"``,
  ``"slide"`` and panel grids ignore the hints.

Every kind but ``matrix``, ``dense``, ``strip`` and ``slide`` is 4:3, the
:func:`~dartwork_mpl.figsize` default, so a request that names only a width
(``dm.figsize(dm.col1)``) gets the same shape. ``"slide"`` is one full 16:9
slide, 25.4 cm wide, under any preset.

``scientific`` presets map the tiers onto journal columns (9 or 17 cm);
``presentation`` and ``poster`` scale them by their font size over the
report's 8 pt, so text fills the same share of the canvas. Any other preset,
or none, uses the report tiers.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..units import ASPECT_TOKENS, figsize

__all__ = ["CANVAS_KINDS", "figsize_for", "grid_shape"]

_REPORT_FONT_PT = 8.0
_MAX_TIER_CM = 17.0
_COLUMNS_CM = (9.0, 17.0)
# Tallest grid canvas: an A4 text block (25.7 cm) less a caption; on slides,
# 16:9 of the widest tier.
_MAX_HEIGHT_CM = 24.0
_SLIDE_RATIO = 9.0 / 16.0


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
    # One whole 16:9 slide (10 in, the Google Slides and Keynote width).
    "slide": _Kind(25.4, "slide", fixed=True, absolute=True),
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
    """``("paper" | "slides" | "report", scale)`` for the active preset."""
    from . import load_style_dict

    for name in names:
        base = name.removesuffix("-kr")
        if base == "scientific":
            return "paper", 1.0
        if base in ("presentation", "poster"):
            font_pt = float(load_style_dict(f"font-{base}")["font.size"])
            return "slides", font_pt / _REPORT_FONT_PT
        if base in ("report", "web", "minimal", "dark"):
            return "report", 1.0
    return "report", 1.0


def _half_cm(value: float) -> float:
    """Round to the nearest 0.5 cm, halves up."""
    return math.floor(value * 2 + 0.5) / 2


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
        strip) or ``"slide"`` (one whole 16:9 slide).
    n_points : int, optional
        Positions along the category or time axis (bars per group count
        once). Leave out for scatter, histograms and other point clouds.
    n_series : int, optional
        Plotted series: lines, bar colours, stacked layers.
    dual_axis : bool, optional
        True when a second y axis (``twinx``) is drawn.
    nrows, ncols : int, optional
        Panel grid; :func:`grid_shape` picks them for ``n`` panels. Any grid
        larger than one panel takes the widest tier; every panel keeps the
        kind's aspect, up to a 24 cm tall canvas (16:9 of the width on
        slides).

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
    cap = width * _SLIDE_RATIO if family == "slides" else _MAX_HEIGHT_CM
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
