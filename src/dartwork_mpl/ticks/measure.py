"""Read tick facts off a figure: the thin matplotlib shell before deciding."""

from __future__ import annotations

import datetime
import re
from collections.abc import Sequence
from itertools import pairwise
from typing import Any, Literal

import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.collections import FillBetweenPolyCollection, PathCollection
from matplotlib.container import BarContainer
from matplotlib.figure import Figure
from matplotlib.text import Text

from .._figure_geometry import same_position_axes, shared_axes, with_insets
from .model import (
    AxesFacts,
    AxisFacts,
    Digits,
    Ems,
    Kind,
    LadderChoice,
    Language,
    Side,
    TickValues,
    TwinFacts,
    parse_digits,
)

Which = Literal["x", "y"]
_HANGUL = re.compile("[가-힣]")
FIRST_YEAR, LAST_YEAR = 1900, 2099
WHOLE_TOL = 1e-6  # bar centres rebuilt as x + width / 2 sit a few ulps off
QUARTER_DAYS = (89.0, 92.0)
SETTLED: dict[Side, str] = {
    "right": "_dm_twin_spine_right_settled",
    "top": "_dm_twin_spine_top_settled",
}


def axis_of(ax: Axes, which: Which) -> Axis:
    """``ax.xaxis`` or ``ax.yaxis``."""
    return ax.xaxis if which == "x" else ax.yaxis


def in_view(axis: Axis, values: Sequence[float]) -> list[float]:
    """The values inside the axis view, a limit's float noise included."""
    low, high = sorted(float(v) for v in axis.get_view_interval())
    slack = 1e-12 * (high - low)
    low -= 1e-9 * abs(low) + slack
    high += 1e-9 * abs(high) + slack
    return [float(v) for v in values if low <= float(v) <= high]


def draws_linearly(axis: Axis) -> bool:
    """Whether ``axis`` draws on a linear scale (one unit fits its ticks)."""
    return axis.get_scale() == "linear"


def tick_values(
    axis: Axis, values: Sequence[float] | None = None
) -> TickValues:
    """The given (or current major) tick values inside the view."""
    locs = list(axis.get_majorticklocs()) if values is None else list(values)
    return TickValues.of(in_view(axis, locs), linear=draws_linearly(axis))


def korean_labels(fig: Figure | None, extra: str = "") -> bool:
    """Whether the figure's axis labels, titles or legends (or ``extra``) are Korean."""
    texts = [extra]
    if fig is not None:
        for ax in fig.axes:
            texts += [ax.get_xlabel(), ax.get_ylabel()]
            texts += [
                ax.get_title(loc=loc) for loc in ("left", "center", "right")
            ]
            legend = ax.get_legend()
            if legend is not None:
                texts += [t.get_text() for t in legend.get_texts()]
        for legend in fig.legends:
            texts += [t.get_text() for t in legend.get_texts()]
        for name in ("_suptitle", "_supxlabel", "_supylabel"):
            artist = getattr(fig, name, None)
            if artist is not None:
                texts.append(artist.get_text())
    return any(_HANGUL.search(t) for t in texts)


def language(fig: Figure | None, extra: str = "") -> Language:
    """``config.number_ladder`` and whether the figure reads Korean."""
    from ..config import config  # the root config: lazy, as layout reads it

    asked = LadderChoice.parse(config.number_ladder)
    return Language(
        asked, asked is LadderChoice.AUTO and korean_labels(fig, extra)
    )


def config_digits() -> Digits:
    """``config.tick_years``."""
    from ..config import config

    return parse_digits(config.tick_years, "config.tick_years")


# -- plotted data -------------------------------------------------------------


def _bar_positions(
    container: BarContainer, which: Which, slot: bool
) -> npt.NDArray[np.float64]:
    """Bar centres; with ``slot`` a bar inside one unit slot stands for it.

    Bars grouped side by side at ``year -/+ w/2`` stand for the year.
    """
    patches = container.patches
    if which == "x":
        start = np.array([p.get_x() for p in patches], dtype=float)
        end = start + np.array([p.get_width() for p in patches], dtype=float)
    else:
        start = np.array([p.get_y() for p in patches], dtype=float)
        end = start + np.array([p.get_height() for p in patches], dtype=float)
    centre: npt.NDArray[np.float64] = (start + end) / 2
    if not slot:
        return centre
    near = np.rint(centre)
    low, high = np.minimum(start, end), np.maximum(start, end)
    inside = (low >= near - 0.5 - 1e-6) & (high <= near + 0.5 + 1e-6)
    return np.where(inside, near, centre)


def _fill_outline(
    coll: FillBetweenPolyCollection, which: Which, data: Any
) -> npt.NDArray[np.float64] | None:
    """A ``fill_between`` area's outline along ``which``, if all on whole numbers."""
    if getattr(coll, "t_direction", None) != which:
        return None
    if not all(coll.get_transform().contains_branch_seperately(data)):
        return None  # span shading in axes fractions marks a period
    paths = coll.get_paths()
    if not paths:
        return None
    column = 0 if which == "x" else 1
    values = np.concatenate(
        [np.asarray(p.vertices, dtype=float)[:, column] for p in paths]
    )
    if not np.all(np.isfinite(values)) or np.any(
        np.abs(values - np.rint(values)) > WHOLE_TOL
    ):
        return None  # interpolated crossings are outline, not data
    return values


def _offsets(coll: PathCollection) -> npt.NDArray[np.float64]:
    """Scatter offsets as an ``(n, 2)`` float array, masked points as NaN."""
    masked = np.ma.asarray(coll.get_offsets(), dtype=float)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    filled = np.ma.filled(masked, np.nan)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportUnknownArgumentType]
    return np.asarray(filled, dtype=float).reshape(-1, 2)


def plotted(
    ax: Axes, which: Which, *, bar_slot: bool = False
) -> npt.NDArray[np.float64]:
    """The x (or y) values the data sits on, over every Axes sharing that axis.

    Lines and scatter offsets in data units (an ``axvline`` marks a value,
    it plots none), bar centres of bars along ``which`` and the outline of
    ``fill_between`` / ``stackplot`` areas.
    """
    column = 0 if which == "x" else 1
    bars = "vertical" if which == "x" else "horizontal"
    chunks: list[npt.NDArray[np.float64]] = []
    for member in shared_axes(ax, which):
        data = member.transData
        for line in member.lines:
            if all(line.get_transform().contains_branch_seperately(data)):
                xy = np.asarray(line.get_xydata(), dtype=float)
                chunks.append(xy.reshape(-1, 2)[:, column])
        for coll in member.collections:
            if isinstance(coll, PathCollection):
                transform = coll.get_offset_transform()
                if transform.contains_branch_seperately(data)[column]:
                    chunks.append(_offsets(coll)[:, column])
            elif isinstance(coll, FillBetweenPolyCollection):
                outline = _fill_outline(coll, which, data)
                if outline is not None:
                    chunks.append(outline)
        chunks.extend(
            _bar_positions(c, which, bar_slot)
            for c in member.containers
            if isinstance(c, BarContainer) and c.orientation == bars
        )
    if not chunks:
        return np.empty(0, dtype=float)
    values = np.concatenate(chunks)
    return values[np.isfinite(values)]


def are_years(values: npt.ArrayLike) -> bool:
    """Two or more distinct values, all integers in 1900-2099."""
    data = np.asarray(values, dtype=float).ravel()
    if data.size < 2:
        return False
    low, high = float(data.min()), float(data.max())
    if not (FIRST_YEAR <= low < high <= LAST_YEAR):
        return False
    return bool(np.all(np.abs(data - np.rint(data)) <= WHOLE_TOL))


def is_quarterly(nums: npt.ArrayLike) -> bool:
    """Two or more distinct date numbers, 89-92 days apart."""
    values = np.unique(np.asarray(nums, dtype=float))
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return False
    gaps = np.diff(values)
    return bool(np.all((gaps >= QUARTER_DAYS[0]) & (gaps <= QUARTER_DAYS[1])))


def num2date(value: float, tz: Any = None) -> datetime.datetime:
    """One matplotlib date number as a ``datetime``."""
    moment: datetime.datetime = mdates.num2date(value, tz=tz)  # pyright: ignore[reportUnknownMemberType]
    return moment


def quarter_ends(nums: npt.ArrayLike, tz: Any = None) -> bool:
    """Whether every date is a quarter's last day."""
    days = {
        num2date(float(v), tz).date()
        for v in np.unique(np.asarray(nums, dtype=float))
    }
    return bool(days) and all(
        (d.month, d.day) in ((3, 31), (6, 30), (9, 30), (12, 31)) for d in days
    )


# -- formatter and locator state ----------------------------------------------


def _stock_concise(fmt: ticker.Formatter) -> bool:
    """Matplotlib's own concise date formatter with its own format strings."""
    if type(fmt) is not mdates.ConciseDateFormatter:
        return False
    fresh = mdates.ConciseDateFormatter(mdates.AutoDateLocator())
    return all(
        list(getattr(fmt, n)) == list(getattr(fresh, n))
        for n in ("formats", "zero_formats", "offset_formats")
    )


def converter_locator(locator: ticker.Locator) -> bool:
    """The ``AutoDateLocator`` matplotlib's date converter made, unconfigured."""
    if type(locator) is not mdates.AutoDateLocator:
        return False
    fresh = mdates.AutoDateLocator()
    return (
        locator.minticks == fresh.minticks
        and locator.maxticks == fresh.maxticks
        and bool(locator.interval_multiples)
    )


_LOCATOR_PARAMS = ("_nbins", "_steps", "_prune", "_symmetric", "_min_n_ticks")


def configured(locator: ticker.Locator) -> bool:
    """Whether someone changed matplotlib's own locator in place (``locator_params``)."""
    if type(locator) is not ticker.AutoLocator:
        return False
    fresh = vars(ticker.AutoLocator())
    return any(
        not np.array_equal(
            np.asarray(vars(locator).get(n)), np.asarray(fresh.get(n))
        )
        for n in _LOCATOR_PARAMS
    )


def _kind(axis: Axis) -> Kind:
    fmt = axis.get_major_formatter()
    if isinstance(fmt, mdates.ConciseDateFormatter):
        dated = isinstance(axis.get_major_locator(), mdates.DateLocator)
        return Kind.DATES if dated and _stock_concise(fmt) else Kind.OTHER
    if axis.get_scale() == "linear" and axis.get_converter() is None:
        return Kind.NUMBERS
    return Kind.OTHER


def axis_facts(ax: Axes, which: Which) -> AxisFacts:
    """One axis as the library's default format reads it."""
    axis = axis_of(ax, which)
    kind = _kind(axis)
    fmt, locator = axis.get_major_formatter(), axis.get_major_locator()
    own_locator = axis.isDefault_majloc and not configured(locator)
    fixed = isinstance(fmt, ticker.FixedFormatter)
    pinnable = fixed and len(axis.get_majorticklocs()) == len(fmt.seq)
    years, ends = False, None
    if kind is Kind.NUMBERS and which == "x":
        years = are_years(plotted(ax, "x", bar_slot=True))
    if (
        kind is Kind.DATES
        and axis.isDefault_majloc
        and converter_locator(locator)
    ):
        dates = plotted(ax, which)
        if is_quarterly(dates):
            ends = quarter_ends(dates, getattr(locator, "tz", None))
    return AxisFacts(
        x=which == "x",
        kind=kind,
        ticks=tick_values(axis),
        own_formatter=axis.isDefault_majfmt,
        own_locator=own_locator,
        fixed_texts=fixed,
        pinnable=pinnable,
        years=years,
        quarter_ends=ends,
    )


# -- twin scales ----------------------------------------------------------------

_SIDES: dict[Side, tuple[Which, Which, str]] = {
    # the side: the axis whose scale sits there, the axis a twin hides, the near side
    "right": ("y", "x", "left"),
    "top": ("x", "y", "bottom"),
}


def _rectilinear(ax: Axes) -> bool:
    return ax.get_visible() and ax.name == "rectilinear"


def boxes(fig: Figure) -> dict[Axes, list[Axes]]:
    """Each visible rectilinear Axes drawn in a box with others, and that box.

    Walked with insets, depth first: an inset is not in ``fig.axes`` but its
    ``twinx`` is, so the inset finds its twin and the twin its box.
    """
    found: dict[Axes, list[Axes]] = {}
    for ax in with_insets(fig.axes):
        if ax in found or not _rectilinear(ax):
            continue
        group = [m for m in same_position_axes(ax) if _rectilinear(m)]
        if len(group) >= 2:
            found.update(dict.fromkeys(group, group))
    return found


def _owns(ax: Axes, group: Sequence[Axes], scale: Which) -> bool:
    """``ax`` shows its ``scale`` axis, which no box member shares while the other is shared."""
    other: Which = "x" if scale == "y" else "y"
    shared_other, shared_scale = shared_axes(ax, other), shared_axes(ax, scale)
    return axis_of(ax, scale).get_visible() and any(
        m is not ax and m in shared_other and m not in shared_scale
        for m in group
    )


def _far_side(axis: Axis) -> bool:
    """Tick labels (else marks) show on the right / top and not the left / bottom."""
    tick = (axis.get_major_ticks() or axis.get_major_ticks(1))[0]
    labels = (tick.label1.get_visible(), tick.label2.get_visible())
    marks = (tick.tick1line.get_visible(), tick.tick2line.get_visible())
    near, far = labels if any(labels) else marks
    return far and not near


def _draws(ax: Axes, group: Sequence[Axes], side: Side) -> bool:
    """``ax`` draws its own scale on ``side``: ticks and label there (one, for a twin)."""
    scale, other, _near = _SIDES[side]
    if not _owns(ax, group, scale):
        return False
    axis = axis_of(ax, scale)
    ticks, label = _far_side(axis), str(axis.get_label_position()) == side
    if axis_of(ax, other).get_visible():
        return ticks and label
    return ticks or label


def twin_facts(ax: Axes, group: Sequence[Axes]) -> TwinFacts:
    """How ``ax`` and its box draw twin scales on the right and the top."""
    if len(group) < 2:
        return TwinFacts()
    draws: set[Side] = set()
    hides: set[Side] = set()
    twin_draws: set[Side] = set()
    for side, (_scale, other, _near) in _SIDES.items():
        if _draws(ax, group, side):
            draws.add(side)
        if not axis_of(ax, other).get_visible():
            hides.add(side)
        if any(
            _draws(m, group, side) and not axis_of(m, other).get_visible()
            for m in group
        ):
            twin_draws.add(side)
    return TwinFacts(
        frozenset(draws),
        frozenset(hides),
        frozenset(twin_draws),
        settled_twin_spines(ax),
    )


def axes_facts(ax: Axes, digits: Digits, box: Sequence[Axes] = ()) -> AxesFacts:
    """An Axes before the layout, drawn in ``box`` with its twins."""
    twin = twin_facts(ax, box)
    return AxesFacts(axis_facts(ax, "x"), axis_facts(ax, "y"), digits, twin)


def drawn_like_twin(ax: Axes) -> bool:
    """Whether ``ax`` is drawn as a twin is, read from public state.

    An earlier Axes in its box shares exactly one axis with it, and ``ax``
    hides that axis: ``ax.twinx()`` hides the twin's x, ``twiny`` its y.
    """
    fig = ax.get_figure(root=True)
    if fig is None or not _rectilinear(ax):
        return False
    order = with_insets(fig.axes)
    if ax not in order:
        return False
    earlier = [
        m
        for m in order[: order.index(ax)]
        if _rectilinear(m) and ax in same_position_axes(m)
    ]
    sx, sy = shared_axes(ax, "x"), shared_axes(ax, "y")
    return any(
        (m in sx and m not in sy and not ax.xaxis.get_visible())
        or (m in sy and m not in sx and not ax.yaxis.get_visible())
        for m in earlier
    )


def settled_twin_spines(ax: Axes) -> frozenset[Side]:
    """The sides of ``ax`` whose twin spine a layout showed (or found showing)."""
    return frozenset(
        side for side, attr in SETTLED.items() if getattr(ax, attr, False)
    )


# -- crowding --------------------------------------------------------------------


def label_gap(axis: Axis, locs: Sequence[float], renderer: Any) -> Ems:
    """Smallest gap between neighbouring tick labels at ``locs``, in ems."""
    if len(locs) < 2:
        return Ems(float("inf"))
    ax = axis.axes
    fig = ax.get_figure(root=True)
    assert fig is not None
    font = axis.get_major_ticks(1)[0].label1.get_fontproperties()
    texts = axis.get_major_formatter().format_ticks(list(locs))
    along_x = axis is ax.xaxis
    if along_x:
        centres = ax.get_xaxis_transform().transform([(v, 0.0) for v in locs])[
            :, 0
        ]
    else:
        centres = ax.get_yaxis_transform().transform([(0.0, v) for v in locs])[
            :, 1
        ]
    spans: list[tuple[float, float]] = []
    for centre, text in zip(centres, texts, strict=True):
        probe = Text(0, 0, text, fontproperties=font)
        probe.set_figure(fig)
        box = probe.get_window_extent(renderer)
        half = (box.width if along_x else box.height) / 2
        spans.append((centre - half, centre + half))
    spans.sort()
    gap = min(b[0] - a[1] for a, b in pairwise(spans))
    return Ems(float(gap / (font.get_size_in_points() * fig.dpi / 72.0)))


def rotated(axis: Axis) -> bool:
    """Whether the x tick labels are turned (thinning leaves them alone)."""
    label = axis.get_major_ticks(1)[0].label1
    return axis is axis.axes.xaxis and bool(label.get_rotation() % 180)
