"""The active preset's default canvas: one size per chart kind and density.

When a request names no size, :func:`figsize_for` picks it, so the same
request gets the same canvas whoever writes the code. Widths are four report
tiers, 9 / 12 / 14.5 / 17 cm (17 cm is the A4 text width with 2 cm margins),
chosen from the chart kind and two density hints:

- ``n_points <= 6`` and ``n_series <= 2`` on one axis: 9 cm;
- a second y axis, ``n_series >= 4`` or ``n_points > 12``: 14.5 cm;
- otherwise the kind's width. ``"matrix"``, ``"dense"``, ``"strip"``,
  ``"slide"``, ``"full_slide"`` and panel grids ignore the hints.

``"grouped"`` (``n_series`` bars side by side in each of ``n_points``
groups) also counts the bars, ``n_points * n_series``: each takes a value
label's room, so the width is at least the narrowest that holds that many
labelled bars (:data:`_GROUPED_BARS`), and never narrower than the
``"default"`` width for the same hints.

Every kind but ``matrix``, ``dense``, ``strip``, ``slide`` and
``full_slide`` is 4:3, the
:func:`~dartwork_mpl.figsize` default, so a request that names only a width
(``dm.figsize(dm.col1)``) gets the same shape.

``scientific`` presets use journal columns: one column (9 cm) for a single
panel whatever its density, two (17 cm) for grids and the full-width kinds
(``"dense"``, ``"strip"``). ``presentation`` presets draw under a 16:9
slide's title, 10.5 cm tall: up to 4 x positions half the 23.4 cm body
(11.4 cm), up to 6 two thirds (15.4 cm), anything denser the full body;
``"compact"`` takes half of it and ``"matrix"`` a 10.5 cm square.
``"slide"`` is the full body under any preset; ``"full_slide"`` is the whole
16:9 slide (25.4 x 14.29 cm, no title band), the slide the presentation
sizes assume. ``poster`` scales the tiers by its font size over the report's
8 pt, so text fills the same share of the canvas. Any other preset, or none,
uses the report tiers.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

from ..units import ASPECT_TOKENS, figsize

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase

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
# Most grouped bars a width holds with every ``dm.label_bars`` value shown
# (three-digit values at the preset's own sizes; measured over 2-8 groups of
# 2-5 bars, I-O1 round 6): (width cm, bars). Wider than the last, the widest
# width; the report tiers scale with the font on posters.
_GROUPED_BARS_SLIDE = ((_SLIDE_HALF_CM, 10), (_SLIDE_TWO_THIRDS_CM, 15))
_GROUPED_BARS = ((9.0, 16), (12.0, 24), (14.5, 32))
# The widths ``labels`` may pick from: the report tiers (scaled on posters)
# and the slide widths. No other width is ever made.
_REPORT_TIERS_CM = (9.0, 12.0, 14.5, _MAX_TIER_CM)
_SLIDE_TIERS_CM = (_SLIDE_HALF_CM, _SLIDE_TWO_THIRDS_CM, _SLIDE_BODY_CM[0])
# Room flat neighbouring names need, in ems of the tick label font: the
# layout's own target (``layout._fit_labels._TARGET_EM``), which wraps or
# turns names that come closer.
_LABEL_CLEARANCE_EM = 0.5
# The canvas a plot does not get (y tick labels, the y name, pads, margins),
# in ems of the tick label font, and the share of plot width over names that
# one position gets (bar margins). Measured (I-O1 follow-up 8, PR 3) on the
# shipped templates and the stress corpus' category charts laid out flat:
# with 4.5 em and 0.96 the estimate tells whether names stand half an em
# apart exactly as the drawn charts do, in all 240 (median error 0.01 em);
# where it errs, the layout's wrap and turn still take over.
_CANVAS_OVERHEAD_EM = 4.5
_SPACING_SHARE = 0.96

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
    # Grouped bars: n_series bars side by side in each of n_points groups.
    "grouped": _Kind(12.0, "standard"),
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


def _grouped_cm(
    table: Sequence[tuple[float, int]],
    n_points: int | None,
    n_series: int | None,
    widest: float,
) -> float:
    """The narrowest width of ``table`` that holds ``n_points * n_series``
    value-labelled bars (``widest`` past its last); 0 when a count is
    unknown."""
    if n_points is None or n_series is None:
        return 0.0
    bars = n_points * max(n_series, 1)
    for width, most in table:
        if bars <= most:
            return width
    return widest


_ORDERED = "in axis order (a list, tuple, array or index)"


def _names(labels: Iterable[object] | None) -> list[str]:
    """``labels`` as strings, in their axis order.

    One string is not names, a set or a mapping has no axis order (its
    neighbours are no neighbours), and a number is not a sequence: each is a
    ``TypeError`` that names ``labels``.
    """
    if labels is None:
        return []
    if isinstance(labels, (str, bytes)):
        raise TypeError(
            f"labels must be the category names {_ORDERED}, not one string; "
            f"got {labels!r}"
        )
    if isinstance(labels, (AbstractSet, Mapping)):
        raise TypeError(
            f"labels must be the category names {_ORDERED}; a "
            f"{type(labels).__name__} has none, so pass list(...) of the "
            "names in the order they are plotted"
        )
    if not isinstance(labels, Iterable):
        raise TypeError(
            f"labels must be the category names {_ORDERED}; got "
            f"{type(labels).__name__} {labels!r}"
        )
    return [str(label) for label in labels]


def _name_widths_pt(names: Sequence[str]) -> tuple[list[float], float] | None:
    """Each name's width (pt) as the active rc draws it as an x tick label,
    and that label's font size (pt); ``None`` when a name cannot be laid out.

    Each name is laid out as the tick label itself is: a ``Text`` at
    ``xtick.labelsize`` in the rc font, whose extent Agg measures at the
    preset's figure dpi. So the text it reads is
    the drawn one: ``'\\$'`` a dollar, ``'$...$'`` math unless
    ``text.parse_math`` is off, TeX under ``text.usetex``, the widest of
    several lines, a font's fallback glyphs. A fixed renderer and dpi give
    the same widths every time. ``None`` where matplotlib could not draw
    the label either: ``text.usetex`` with no TeX to run, or math the active
    engine cannot parse.
    """
    import matplotlib as mpl
    from matplotlib.backends.backend_agg import RendererAgg
    from matplotlib.figure import Figure
    from matplotlib.text import Text

    dpi = float(mpl.rcParams["figure.dpi"])
    figure = Figure(dpi=dpi)
    # backend_agg ships no type stubs: the renderer is a RendererBase
    renderer: RendererBase = RendererAgg(1, 1, dpi)  # type: ignore[no-untyped-call]
    size = 0.0
    widths = []
    for name in names:
        label = Text(0, 0, name, fontsize=mpl.rcParams["xtick.labelsize"])
        label.set_figure(figure)
        try:
            box = label.get_window_extent(renderer)
        except (RuntimeError, ValueError, OSError):
            return None
        widths.append(float(box.width) * 72.0 / dpi)
        size = float(label.get_fontsize())
    return widths, size


def _names_cm(
    names: Sequence[str], tiers: Sequence[float], width: float
) -> float:
    """The narrowest of ``tiers`` (cm) at least ``width`` at which ``names``
    stand flat, neighbours half an em apart; the widest past them all.

    The plot gets the canvas less ``_CANVAS_OVERHEAD_EM`` and each name
    ``_SPACING_SHARE`` of an equal share of it: neighbours ``i``, ``i + 1``
    fit when that share is at least half their widths plus half an em.
    ``width`` itself when there are fewer than two names, or when they
    cannot be laid out (matplotlib could not draw them either).
    """
    if len(names) < 2:
        return width
    measured = _name_widths_pt(names)
    if measured is None:
        return width
    widths, size = measured
    need = max((a + b) / 2 for a, b in pairwise(widths))
    need += _LABEL_CLEARANCE_EM * size
    for tier in tiers:
        if tier < width - 1e-9:
            continue
        plot = tier / 2.54 * 72.0 - _CANVAS_OVERHEAD_EM * size
        if _SPACING_SHARE * plot / len(names) >= need:
            return tier
    return max(width, tiers[-1])


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
    does every other kind. ``"grouped"`` is as wide as the wider of that
    and what its bars' value labels need: up to 10 bars 11.4 cm, up to 15
    15.4 cm, more the full body.
    """
    width, height = _SLIDE_BODY_CM
    if kind == "compact":
        return _SLIDE_HALF_CM, height
    if kind == "matrix":
        return height, height
    if kind not in ("default", "grouped") or n_points is None or dual_axis:
        return width, height
    if n_series is not None and n_series >= 4:
        return width, height
    if n_points <= _SLIDE_HALF_MAX_POINTS:
        chosen = _SLIDE_HALF_CM
    elif n_points <= _SLIDE_TWO_THIRDS_MAX_POINTS:
        chosen = _SLIDE_TWO_THIRDS_CM
    else:
        chosen = width
    if kind == "grouped":
        bars = _grouped_cm(_GROUPED_BARS_SLIDE, n_points, n_series, width)
        chosen = max(chosen, bars)
    return chosen, height


def figsize_for(
    kind: str = "default",
    *,
    n_points: int | None = None,
    n_series: int | None = None,
    labels: Iterable[object] | None = None,
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
        scatter, distributions), ``"grouped"`` (grouped bars: ``n_series``
        bars side by side in each of ``n_points`` groups; the width also
        holds the ``n_points * n_series`` bars' value labels, at least as
        wide as ``"default"``), ``"barh"`` (long category labels),
        ``"compact"`` (insets, half-width panels), ``"matrix"`` (heatmaps),
        ``"dense"`` (long dense timelines), ``"strip"`` (a full-width
        strip), ``"slide"`` (a chart filling a 16:9 slide under its
        title, 23.4 x 10.5 cm, under any preset) or ``"full_slide"`` (a
        chart that is the whole 16:9 slide, 25.4 x 14.29 cm, under any
        preset: "a full-slide chart").
    n_points : int, optional
        Positions along the category or time axis (bars per group count
        once; ``"grouped"`` counts them through ``n_series``). Leave out for
        scatter, histograms and other point clouds. Under ``presentation``
        presets it picks a 11.4, 15.4 or 23.4 cm wide slide chart (up to 4,
        up to 6, more positions).
    n_series : int, optional
        Plotted series: lines, bar colours, stacked layers; for
        ``"grouped"``, the bars in each group.
    labels : sequence, optional
        The category names under the x axis, one per position, when you
        know them (``labels=countries``), in axis order: a list, tuple,
        array, index or other ordered iterable; each name is ``str()`` of
        its item. A single string, a set or a mapping (no axis order; pass
        ``list(...)``) and a non-iterable raise ``TypeError``.
        ``"default"`` and ``"grouped"`` then take the narrowest width of
        the preset's own table at least as wide as without them (report 9 /
        12 / 14.5 / 17 cm, slides 11.4 / 15.4 / 23.4 cm) at which the names,
        laid out as the tick labels draw them (escaped dollars, math,
        ``text.parse_math``, ``text.usetex``), stand flat half an em apart;
        past the widest, the widest, and the layout wraps or turns them. No
        names, names that fit, or names matplotlib could not draw either
        (``text.usetex`` with no TeX) give the same canvas as without them.
        A ``scientific`` panel keeps its journal column, and the other kinds
        their width.
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
    names = _names(labels)
    spec = CANVAS_KINDS[kind]

    from . import _active_preset

    if spec.absolute:
        return figsize(f"{spec.width_cm:g}cm", spec.aspect)
    family, scale = _family(_active_preset)
    grid = nrows * ncols > 1
    # the kinds whose width follows the x positions
    by_names = bool(names) and kind in ("default", "grouped") and not grid
    if family == "slides":
        if grid:
            width, height = _SLIDE_BODY_CM
        else:
            width, height = _slide_canvas(kind, n_points, n_series, dual_axis)
        if by_names:
            width = _names_cm(names, _SLIDE_TIERS_CM, width)
        return figsize(f"{width:g}cm", f"{height:g}cm")
    width = (
        _MAX_TIER_CM if grid else _tier_cm(spec, n_points, n_series, dual_axis)
    )
    if kind == "grouped" and not grid:
        bars = _grouped_cm(_GROUPED_BARS, n_points, n_series, _MAX_TIER_CM)
        width = max(width, bars)
    if family == "paper":
        # A journal sets one panel in one column, however dense it is.
        full = grid or (spec.fixed and spec.width_cm > 12.0)
        width = _COLUMNS_CM[1] if full else _COLUMNS_CM[0]
    else:
        width = _half_cm(width * scale)
        if by_names:
            tiers = [_half_cm(tier * scale) for tier in _REPORT_TIERS_CM]
            width = _names_cm(names, tiers, width)

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
