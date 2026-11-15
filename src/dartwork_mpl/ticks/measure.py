"""Read tick facts off a figure: the thin matplotlib shell before deciding."""

from __future__ import annotations

import datetime
import re
from collections.abc import Sequence
from itertools import pairwise
from typing import Protocol, runtime_checkable

import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.backend_bases import RendererBase
from matplotlib.collections import FillBetweenPolyCollection, PathCollection
from matplotlib.container import BarContainer
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import IdentityTransform, Transform

from ..axis import Which, X, Y, bars_along, parse_which
from ..geometry import axes_titles, axis_of, shared_axes
from .axis_plans import AxisFacts, AxisKind, DateAxis, NumberAxis, OtherAxis
from .defaults import config
from .model import (
    Asked,
    ByFigure,
    Ems,
    FollowFigure,
    Ladder,
    Language,
    TickValues,
    YearDigits,
    Zone,
    parse_digits,
    parse_number_ladder,
)

_HANGUL = re.compile("[가-힣]")
FIRST_YEAR, LAST_YEAR = 1900, 2099
WHOLE_TOL = 1e-6  # bar centres rebuilt as x + width / 2 sit a few ulps off
QUARTER_DAYS = (89.0, 92.0)


def with_insets(axes: Sequence[Axes]) -> list[Axes]:
    """Return ``axes``, each followed by its inset Axes, nested ones too.

    ``ax.inset_axes`` keeps an inset in ``ax.child_axes``, not in
    ``fig.axes``, while a ``twinx`` of that inset lands in ``fig.axes``.
    ``secondary_xaxis`` / ``secondary_yaxis`` children are not Axes and are
    left out.
    """
    out: list[Axes] = []
    for ax in axes:
        out.append(ax)
        out.extend(
            with_insets([c for c in ax.child_axes if isinstance(c, Axes)])
        )
    return out


def in_view(axis: Axis, values: Sequence[float]) -> list[float]:
    """The values inside the axis view, a limit's float noise included."""
    low, high = sorted(float(v) for v in axis.get_view_interval())
    slack = 1e-12 * (high - low)
    low -= 1e-9 * abs(low) + slack
    high += 1e-9 * abs(high) + slack
    return [float(v) for v in values if low <= float(v) <= high]


def tick_values(
    axis: Axis, values: Sequence[float] | None = None
) -> TickValues:
    """The given (or current major) tick values inside the view."""
    locs = list(axis.get_majorticklocs()) if values is None else list(values)
    return TickValues.of(in_view(axis, locs))


def korean_labels(fig: Figure | None, extra: str = "") -> bool:
    """Whether the figure's axis labels, titles or legends (or ``extra``) are Korean."""
    texts = [extra]
    if fig is not None:
        for ax in fig.axes:
            texts += [ax.get_xlabel(), ax.get_ylabel()]
            texts += [t.get_text() for t in axes_titles(ax).values()]
            legend = ax.get_legend()
            if legend is not None:
                texts += [t.get_text() for t in legend.get_texts()]
        for legend in fig.legends:
            texts += [t.get_text() for t in legend.get_texts()]
        texts += [fig.get_suptitle(), fig.get_supxlabel(), fig.get_supylabel()]
    return any(_HANGUL.search(t) for t in texts)


def language(fig: Figure | None, extra: str = "") -> Language:
    """``config.number_ladder`` and whether the figure reads Korean."""
    match parse_number_ladder(config.number_ladder):
        case FollowFigure():
            return ByFigure(korean_labels(fig, extra))
        case Ladder() as asked:
            return Asked(asked)


def config_digits() -> YearDigits:
    """``config.tick_years``."""
    return parse_digits(config.tick_years, "config.tick_years")


# -- plotted data -------------------------------------------------------------


def _bar_positions(
    container: BarContainer, which: Which, slot: bool
) -> npt.NDArray[np.float64]:
    """Bar centres; with ``slot`` a bar inside one unit slot stands for it.

    Bars grouped side by side at ``year -/+ w/2`` stand for the year.
    """
    patches = container.patches
    match which:
        case X():
            start = np.array([p.get_x() for p in patches], dtype=float)
            end = start + np.array(
                [p.get_width() for p in patches], dtype=float
            )
        case Y():
            start = np.array([p.get_y() for p in patches], dtype=float)
            end = start + np.array(
                [p.get_height() for p in patches], dtype=float
            )
    centre: npt.NDArray[np.float64] = (start + end) / 2
    if not slot:
        return centre
    near = np.rint(centre)
    low, high = np.minimum(start, end), np.maximum(start, end)
    inside = (low >= near - 0.5 - 1e-6) & (high <= near + 0.5 + 1e-6)
    return np.where(inside, near, centre)


@runtime_checkable
class Directed(Protocol):
    """A ``fill_between`` area: ``t_direction`` names the axis it runs along
    (public on matplotlib's class, missing from its stub)."""

    t_direction: str


def _fill_outline(
    coll: FillBetweenPolyCollection, which: Which, data: Transform
) -> npt.NDArray[np.float64] | None:
    """A ``fill_between`` area's outline along ``which``, if all on whole numbers."""
    if not isinstance(coll, Directed) or parse_which(coll.t_direction) != which:
        return None
    if not all(coll.get_transform().contains_branch_seperately(data)):
        return None  # span shading in axes fractions marks a period
    paths = coll.get_paths()
    if not paths:
        return None
    column = which.column
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
    column = which.column
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
            if isinstance(c, BarContainer)
            and bars_along(c.orientation) == which
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


def num2date(value: float, tz: Zone = None) -> datetime.datetime:
    """One matplotlib date number as a ``datetime``."""
    moment: datetime.datetime = mdates.num2date(value, tz=tz)  # pyright: ignore[reportUnknownMemberType]
    return moment


def quarter_ends(nums: npt.ArrayLike, tz: Zone = None) -> bool:
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
    assert isinstance(fmt, mdates.ConciseDateFormatter)
    fresh = mdates.ConciseDateFormatter(mdates.AutoDateLocator())
    return _format_strings(fmt) == _format_strings(fresh)


def _format_strings(
    fmt: mdates.ConciseDateFormatter,
) -> tuple[list[str], list[str], list[str]]:
    """A concise formatter's tick, zero and offset format strings."""
    formats: list[str] = list(fmt.formats)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    zeros: list[str] = list(fmt.zero_formats)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    offsets: list[str] = list(fmt.offset_formats)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    return formats, zeros, offsets


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


#: Views matplotlib's own ``AutoLocator`` is compared on: narrow and wide,
#: from zero and away from it, uneven about zero (``symmetric``), years.
_PROBES = (
    (0.0, 1.0),
    (0.0, 7.0),
    (0.13, 0.97),
    (-3.0, 10.0),
    (-1.0, 0.2),
    (0.0, 1000.0),
    (1.0, 2e6),
    (1990.0, 2024.0),
)


def configured(locator: ticker.Locator) -> bool:
    """Whether someone changed matplotlib's own locator in place (``locator_params``).

    ``set_params`` keeps what it is given in private attributes with no
    getter, so the locator is asked what it does instead: it is configured
    when it picks other ticks than a fresh ``AutoLocator`` on the same axis,
    on its own view or on any of a few others.
    """
    if type(locator) is not ticker.AutoLocator:
        return False
    fresh = ticker.AutoLocator()
    views = list(_PROBES)
    if locator.axis is not None:
        fresh.set_axis(locator.axis)
        low, high = locator.axis.get_view_interval()
        views.append((float(low), float(high)))
    return any(
        not np.array_equal(
            np.asarray(locator.tick_values(a, b), dtype=float),
            np.asarray(fresh.tick_values(a, b), dtype=float),
        )
        for a, b in views
    )


def _years(ax: Axes, which: Which) -> bool:
    """x data that are integer years (y data are never read as years)."""
    match which:
        case X():
            return are_years(plotted(ax, which, bar_slot=True))
        case Y():
            return False


def _quarter_ends(ax: Axes, which: Which, axis: Axis) -> bool | None:
    """Quarterly dates on the converter's locator: on quarter ends or not."""
    locator = axis.get_major_locator()
    if not (axis.isDefault_majloc and converter_locator(locator)):
        return None
    dates = plotted(ax, which)
    if not is_quarterly(dates):
        return None
    return quarter_ends(dates, date_zone(locator))


def date_zone(locator: ticker.Locator) -> datetime.tzinfo | None:
    """The time zone a date locator reads its dates in (``None``: UTC)."""
    return locator.tz if isinstance(locator, mdates.DateLocator) else None


def _kind(ax: Axes, which: Which) -> AxisKind:
    axis = axis_of(ax, which)
    fmt = axis.get_major_formatter()
    if isinstance(fmt, mdates.ConciseDateFormatter):
        dated = isinstance(axis.get_major_locator(), mdates.DateLocator)
        if dated and _stock_concise(fmt):
            return DateAxis(_quarter_ends(ax, which, axis))
        return OtherAxis()
    linear = isinstance(axis.get_transform(), IdentityTransform)
    if linear and axis.get_converter() is None:
        return NumberAxis(_years(ax, which))
    return OtherAxis()


def axis_facts(ax: Axes, which: Which) -> AxisFacts:
    """One axis as the library's default format reads it."""
    axis = axis_of(ax, which)
    fmt, locator = axis.get_major_formatter(), axis.get_major_locator()
    return AxisFacts(
        x=which.horizontal,
        kind=_kind(ax, which),
        ticks=tick_values(axis),
        own_formatter=axis.isDefault_majfmt,
        own_locator=axis.isDefault_majloc and not configured(locator),
        fixed_texts=isinstance(fmt, ticker.FixedFormatter),
    )


# -- crowding --------------------------------------------------------------------


def label_gap(axis: Axis, locs: Sequence[float], renderer: RendererBase) -> Ems:
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
