"""The library's tick numbers on axes nobody formatted.

Left to matplotlib, an axis prints ``1750`` and ``34000`` without separators
and ``0.5 … 2.5`` under a ``1e6`` corner label, so every agent or person
installs a formatter of their own and the same data reads differently from
figure to figure. :func:`apply_default_tick_format` settles it once:

- an axis whose visible ticks reach 1,000 gets thousands separators
  (``1,750``; ``34,000``) and the fewest exact decimals;
- from one million the axis takes the largest tick's SI unit (``0.5M …
  2.5M``), as ``dm.format_axis_si`` does, unless that needs more than two
  decimals;
- smaller axes (``0, 250 … 750``; ``0.5, 1.0``), x axes whose ticks all sit
  in 1000-2999 (years), log and category axes, colorbars and any axis with a
  formatter someone chose keep theirs;
- date axes are concise in every preset (``date.converter: concise``:
  ``2024, Mar, May … 2025``); when the figure's axis labels, titles or legend
  are Korean they read ``2024년, 3월, 5월 … 2025년`` so a Korean figure does
  not mix in English month names.

``dm.simple_layout`` calls it before measuring (``format_ticks=False`` opts
out), so the numbers it fits are the numbers saved. After fitting it calls
:func:`thin_crowded_date_ticks`: matplotlib picks date ticks from the date
range alone, so on a narrow axis concise labels run into each other
(``2021년 5월 9월 2022년``); the locator then takes fewer ticks until
neighbouring labels are one em apart.

Bars and other category charts often stand for dates (``2024-01 …
2024-12`` under twelve bars). ``dm.format_axis_dates`` labels those
positions with the same concise words through :class:`CategoryDateFormatter`
and :class:`CategoryDateLocator`, and the same thinning step labels every
second, third ... position (months: 1, 2, 3, 4, 6 or 12) until the labels
are one em apart, instead of the labels being rotated.
"""

from __future__ import annotations

import datetime
import numbers
import re
import warnings
from collections.abc import Sequence
from itertools import pairwise
from typing import Any, Literal

import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import numpy as np
import numpy.typing as npt
from matplotlib.axis import Axis
from matplotlib.figure import Figure
from matplotlib.text import Text

from ._axis_wide import AxisUnitFormatter, Unit
from ._decimals import fewest_exact_decimals

__all__ = [
    "CategoryDateFormatter",
    "CategoryDateLocator",
    "DefaultNumberFormatter",
    "KoreanConciseDateFormatter",
    "apply_default_tick_format",
    "category_dates",
    "thin_crowded_date_ticks",
]

_SEPARATOR_FROM = 1_000.0
_UNIT_FROM = 1_000_000.0
_MAX_UNIT_DECIMALS = 2
_YEARS = (1_000.0, 2_999.0)
# Neighbouring date labels keep at least this many ems between them.
_MIN_DATE_GAP_EM = 1.0
# How many category positions a thinned dated axis may step over. Monthly
# data keeps calendar rhythm (every 2nd, quarter, 4 months, half year,
# year); other spacings count on.
_MONTH_STEPS = (1, 2, 3, 4, 6, 12)
_OTHER_STEPS = (1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 15, 20, 25, 30, 50, 100)
# Neighbouring dates this many days apart count as monthly data.
_MONTH_DAYS = (28.0, 31.0)


class DefaultNumberFormatter(AxisUnitFormatter):
    """Thousands separators below one million, the largest tick's unit above."""

    def __init__(self, ladder: Sequence[Unit]) -> None:
        super().__init__(ladder, "max")

    def _axis_unit(self, values: Sequence[float]) -> Unit:
        top = max(abs(v) for v in values)
        if top < _UNIT_FROM * (1 - 1e-9):
            return self._ladder[0]
        unit = self._max_unit(top)
        scaled = [abs(v) / unit.factor for v in values]
        if fewest_exact_decimals(scaled) > _MAX_UNIT_DECIMALS:
            return self._ladder[0]
        return unit


_TITLE_LOCS: tuple[Literal["left", "center", "right"], ...] = (
    "left",
    "center",
    "right",
)
_HANGUL = re.compile("[\uac00-\ud7a3]")
# "03월" -> "3월", "08일" -> "8일": Korean dates drop the zero padding.
_PADDED = re.compile(r"(?<!\d)0(\d)(?=[월일])")


class KoreanConciseDateFormatter(mdates.ConciseDateFormatter):
    """Matplotlib's concise date ticks with Korean year, month and day units."""

    def __init__(
        self,
        locator: mdates.DateLocator,
        tz: datetime.tzinfo | str | None = None,
        *,
        show_offset: bool = True,
        usetex: bool | None = None,
    ) -> None:
        super().__init__(  # type: ignore[no-untyped-call]
            locator,
            tz=tz,
            show_offset=show_offset,
            usetex=usetex,
            formats=["%Y년", "%m월", "%d일", "%H:%M", "%H:%M", "%S.%f"],
            zero_formats=["", "%Y년", "%m월", "%m월 %d일", "%H:%M", "%H:%M"],
            offset_formats=[
                "",
                "%Y년",
                "%Y년 %m월",
                "%Y년 %m월 %d일",
                "%Y년 %m월 %d일",
                "%Y년 %m월 %d일 %H:%M",
            ],
        )

    def format_ticks(self, values: Sequence[float]) -> list[str]:
        """Format the ticks, without zero padding before 월 and 일."""
        labels: list[str] = super().format_ticks(values)  # type: ignore[no-untyped-call]
        return [_PADDED.sub(r"\1", label) for label in labels]

    def get_offset(self) -> str:
        """The corner label, without zero padding before 월 and 일."""
        offset: str = super().get_offset()  # type: ignore[no-untyped-call]
        return _PADDED.sub(r"\1", offset)


def _korean_labels(fig: Figure) -> bool:
    """Whether the figure's axis labels, titles or legends are Korean."""
    texts: list[str] = []
    for ax in fig.axes:
        texts += [ax.get_xlabel(), ax.get_ylabel()]
        texts += [ax.get_title(loc=loc) for loc in _TITLE_LOCS]
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


def category_dates(
    dates: Sequence[Any] | npt.NDArray[Any],
) -> npt.NDArray[np.datetime64]:
    """Read the dates that category positions 0, 1, ... stand for.

    Accepts ISO strings (``"2024-01"``, ``"2024-01-15"``), ``datetime`` /
    ``date`` values, pandas timestamps or a ``datetime64`` array or Series
    of any unit, in position order. Returns a ``datetime64[s]`` array of the
    same length.

    Raises
    ------
    ValueError
        If there are no dates, or one is missing or not a date
        (``"2024/01"``, ``"Jan"``, ``None``, ``NaT``, or a number such as a
        bare year ``2024``, which stays a number on a numeric axis).
    """
    dtype = getattr(dates, "dtype", None)
    if isinstance(dtype, np.dtype) and dtype.kind == "M":
        # Convert the array itself: an object view of datetime64[ns] holds
        # nanosecond integers, which would read back as seconds.
        values = list(np.asarray(dates).astype("datetime64[s]").ravel())
    else:
        values = list(np.asarray(dates, dtype=object).ravel())
    if not values:
        raise ValueError("format_axis_dates needs at least one date")
    parsed = []
    for position, value in enumerate(values):
        try:
            if isinstance(value, (numbers.Number, np.number, np.bool_)):
                raise TypeError("a number is not a date")
            day = np.datetime64(value, "s")
        except (TypeError, ValueError):
            day = np.datetime64("NaT")
        if np.isnat(day):
            raise ValueError(
                f"format_axis_dates: position {position} ({value!r}) is not "
                "a date; pass ISO strings such as '2024-01' or datetimes"
            )
        parsed.append(day)
    return np.array(parsed, dtype="datetime64[s]")


def _steps_for(dates: npt.NDArray[np.datetime64]) -> tuple[int, ...]:
    """Position steps a thinned axis may take: calendar ones for months."""
    if len(dates) < 2:
        return (1,)
    days = np.diff(dates).astype("timedelta64[s]").astype(float) / 86_400.0
    low, high = _MONTH_DAYS
    if bool(np.all((days >= low) & (days <= high))):
        return _MONTH_STEPS
    return _OTHER_STEPS


class CategoryDateLocator(ticker.Locator):
    """Every ``step``-th of ``n`` category positions, from position 0, in view.

    ``steps`` lists the steps :func:`thin_crowded_date_ticks` may move
    through, smallest first; ``step`` starts at the first. The grid of
    positions is the same whatever the view, so a bar chart's ticks stay
    under bars; only the ones inside the view are returned, so the words
    and the thinning follow the dates someone can see.
    """

    def __init__(self, n: int, steps: Sequence[int]) -> None:
        if n < 1 or not steps or any(s < 1 for s in steps):
            raise ValueError("CategoryDateLocator needs n >= 1 and steps >= 1")
        self.n = n
        self.steps = tuple(steps)
        self.step = self.steps[0]

    def __call__(self) -> list[float]:
        """Return the positions ``0, step, 2*step ... < n`` inside the view."""
        axis = getattr(self, "axis", None)
        if axis is None:
            return [float(i) for i in range(0, self.n, self.step)]
        return self.tick_values(*axis.get_view_interval())

    def tick_values(self, vmin: float, vmax: float) -> list[float]:
        """Return the positions ``0, step, 2*step ... < n`` in ``[vmin, vmax]``."""
        return [
            float(i)
            for i in range(0, self.n, self.step)
            if _within(i, vmin, vmax)
        ]


def _within(position: float, vmin: float, vmax: float) -> bool:
    """Whether a category position lies in the view ``[vmin, vmax]``."""
    low, high = sorted((float(vmin), float(vmax)))
    return low - 1e-9 <= position <= high + 1e-9


class CategoryDateFormatter(ticker.Formatter):
    """The library's concise date words for category positions.

    Position ``i`` stands for ``dates[i]``; positions outside the dates or
    the view get no label. Words come from matplotlib's concise date labels
    over the ticks shown (``2024, Mar, May …``; the year appears on January or in
    the axis-corner offset), Korean (``2024년, 3월, 5월 …``) when the
    figure's axis labels, titles or legends are Korean at drawing time.
    """

    def __init__(self, dates: npt.NDArray[np.datetime64]) -> None:
        self._nums: list[float] = [
            float(v)
            for v in mdates.date2num(dates)  # type: ignore[no-untyped-call]
        ]
        self._offset = ""

    def _concise(self) -> mdates.ConciseDateFormatter:
        axis = getattr(self, "axis", None)
        fig = axis.get_figure(root=True) if axis is not None else None
        if isinstance(fig, Figure) and _korean_labels(fig):
            return KoreanConciseDateFormatter(mdates.AutoDateLocator())  # type: ignore[no-untyped-call]
        return mdates.ConciseDateFormatter(mdates.AutoDateLocator())  # type: ignore[no-untyped-call]

    def _shown(self, index: Sequence[int]) -> list[int]:
        """The positions that stand for a date and lie in the view."""
        axis = getattr(self, "axis", None)
        view = axis.get_view_interval() if axis is not None else None
        return [
            i
            for i in index
            if 0 <= i < len(self._nums) and (view is None or _within(i, *view))
        ]

    def format_ticks(self, values: Sequence[float]) -> list[str]:
        """Words for the given positions in view, worded together as one axis."""
        index = [round(float(v)) for v in values]
        inside = self._shown(index)
        if not inside:
            self._offset = ""
            return ["" for _ in index]
        concise = self._concise()
        words: list[str] = concise.format_ticks(  # type: ignore[no-untyped-call]
            [self._nums[i] for i in inside]
        )
        self._offset = str(concise.get_offset())  # type: ignore[no-untyped-call]
        by_position = dict(zip(inside, words, strict=True))
        return [by_position.get(i, "") for i in index]

    def __call__(self, x: float, pos: int | None = None) -> str:
        """One position's word, worded together with every position in view."""
        everything = list(range(len(self._nums)))
        words = dict(
            zip(everything, self.format_ticks(everything), strict=True)
        )
        return words.get(round(float(x)), "")

    def get_offset(self) -> str:
        """The corner label of the last ``format_ticks`` (year, if not in ticks)."""
        return self._offset


def _visible_ticks(axis: Axis) -> list[float]:
    low, high = sorted(float(v) for v in axis.get_view_interval())
    return [
        float(t) for t in axis.get_majorticklocs() if low <= float(t) <= high
    ]


def _untouched(axis: Axis) -> bool:
    # Exactly matplotlib's default: a subclass or another formatter was chosen.
    return type(axis.get_major_formatter()) is ticker.ScalarFormatter


def _stock(fmt: mdates.ConciseDateFormatter) -> bool:
    """Whether a concise formatter still has matplotlib's own format strings.

    Code that edits them (a two-digit ``%y`` year, say) chose its dates; the
    Korean words replace only the stock English ones.
    """
    stock = mdates.ConciseDateFormatter(mdates.AutoDateLocator())  # type: ignore[no-untyped-call]
    return all(
        list(getattr(fmt, name)) == list(getattr(stock, name))
        for name in ("formats", "zero_formats", "offset_formats")
    )


def apply_default_tick_format(fig: Figure) -> int:
    """Install the library's tick numbers on every axis nobody formatted.

    Returns the number of axes changed. Safe to call again: an axis that
    already carries the default formatter is no longer ``ScalarFormatter``.
    """
    from . import _SI_LADDER  # defined after this module is imported

    changed = 0
    korean = _korean_labels(fig)
    for ax in fig.axes:
        if (
            ax.name != "rectilinear"
            or getattr(ax, "_colorbar", None) is not None
        ):
            continue
        for which, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            fmt = axis.get_major_formatter()
            if korean and type(fmt) is mdates.ConciseDateFormatter:
                locator = axis.get_major_locator()
                if isinstance(locator, mdates.DateLocator) and _stock(fmt):
                    # Same time zone, offset and TeX choice; only the words
                    # change.
                    axis.set_major_formatter(
                        KoreanConciseDateFormatter(
                            locator,
                            tz=fmt._tz,
                            show_offset=fmt.show_offset,
                            usetex=fmt._usetex,
                        )
                    )
                    changed += 1
                continue
            if not _untouched(axis) or axis.get_scale() != "linear":
                continue
            ticks = _visible_ticks(axis)
            if not ticks or max(abs(t) for t in ticks) < _SEPARATOR_FROM:
                continue
            if which == "x" and all(_YEARS[0] <= t <= _YEARS[1] for t in ticks):
                continue  # years: 2024, not 2,024
            axis.set_major_formatter(DefaultNumberFormatter(_SI_LADDER))
            changed += 1
    return changed


def _date_label_gap_em(
    axis: Axis, locs: Sequence[float], fig: Figure, renderer: Any
) -> float:
    """Smallest gap between neighbouring tick labels, in ems of their font."""
    if len(locs) < 2:
        return float("inf")
    ax = axis.axes
    label = axis.get_major_ticks(1)[0].label1
    labels = axis.get_major_formatter().format_ticks(list(locs))
    along_x = axis is ax.xaxis
    if along_x:
        transform = ax.get_xaxis_transform()
        points = [(v, 0.0) for v in locs]
    else:
        transform = ax.get_yaxis_transform()
        points = [(0.0, v) for v in locs]
    centres = transform.transform(points)[:, 0 if along_x else 1]
    spans = []
    for centre, text in zip(centres, labels, strict=True):
        probe = Text(0, 0, text, fontproperties=label.get_fontproperties())
        probe.set_figure(fig)
        box = probe.get_window_extent(renderer)
        half = (box.width if along_x else box.height) / 2
        spans.append((centre - half, centre + half))
    spans.sort()
    gap = min(b[0] - a[1] for a, b in pairwise(spans))
    em_px = label.get_fontproperties().get_size_in_points() * fig.dpi / 72.0
    return float(gap / em_px)


def _visible_locs(
    axis: Axis, locator: mdates.AutoDateLocator
) -> list[float] | None:
    """Ticks inside the view, or ``None`` when matplotlib would warn."""
    low, high = sorted(float(v) for v in axis.get_view_interval())
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            locs = locator()
        except UserWarning:
            return None  # no interval gives this few ticks
    return [float(v) for v in locs if low <= float(v) <= high]


def _thin_category_dates(
    axis: Axis, locator: CategoryDateLocator, fig: Figure, renderer: Any
) -> int:
    """Label every n-th dated category position until labels are one em apart.

    Leaves rotated x labels alone. Moves the locator's ``step`` through its
    larger ``steps`` and keeps the first whose labels are
    :data:`_MIN_DATE_GAP_EM` ems apart with two or more labels; with none,
    the step is restored. Returns 1 when the step changed, else 0. In a cut
    view a larger step can show more labels than a smaller one (view 3.5-8.5:
    step 3 shows 6, step 4 shows 4 and 8), so a step with one label in view
    is skipped, not the end of the search.
    """
    label = axis.get_major_ticks(1)[0].label1
    if axis is axis.axes.xaxis and label.get_rotation() % 180:
        return 0
    if _date_label_gap_em(axis, locator(), fig, renderer) >= _MIN_DATE_GAP_EM:
        return 0
    original = locator.step
    for step in (s for s in locator.steps if s > original):
        locator.step = step
        locs = locator()
        if len(locs) < 2:
            continue
        if _date_label_gap_em(axis, locs, fig, renderer) >= _MIN_DATE_GAP_EM:
            return 1
    locator.step = original
    return 0


def _converter_locator(locator: ticker.Locator) -> bool:
    """Whether the locator is the one matplotlib's date converter made."""
    if type(locator) is not mdates.AutoDateLocator:
        return False
    fresh = mdates.AutoDateLocator()  # type: ignore[no-untyped-call]
    return (
        locator.minticks == fresh.minticks
        and locator.maxticks == fresh.maxticks
        and bool(locator.interval_multiples)
    )


def thin_crowded_date_ticks(fig: Figure) -> int:
    """Give a crowded concise date axis fewer ticks; return the axes changed.

    Acts only on axes matplotlib's date converter set up (an
    ``AutoDateLocator`` with its default tick counts and concise labels)
    whose labels are not rotated, so a locator someone configured, or one
    already thinned, is kept.
    Each step lowers the locator's tick ceiling, skipping ceilings
    matplotlib cannot meet; the first that keeps neighbouring labels
    :data:`_MIN_DATE_GAP_EM` ems apart with two or more ticks wins. An axis
    with no such ceiling is left as it was.

    Axes labelled with ``dm.format_axis_dates`` (a
    :class:`CategoryDateLocator`) are thinned the same way through the
    locator's position steps; see :func:`_thin_category_dates`.
    """
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    changed = 0
    for ax in fig.axes:
        if ax.name != "rectilinear":
            continue
        for axis in (ax.xaxis, ax.yaxis):
            locator = axis.get_major_locator()
            if isinstance(locator, CategoryDateLocator):
                changed += _thin_category_dates(axis, locator, fig, renderer)
                continue
            if not _converter_locator(locator) or not isinstance(
                axis.get_major_formatter(), mdates.ConciseDateFormatter
            ):
                continue
            assert isinstance(locator, mdates.AutoDateLocator)
            label = axis.get_major_ticks(1)[0].label1
            if axis is ax.xaxis and label.get_rotation() % 180:
                continue
            locs = _visible_locs(axis, locator)
            if (
                locs is None
                or _date_label_gap_em(axis, locs, fig, renderer)
                >= _MIN_DATE_GAP_EM
            ):
                continue
            original = (locator.minticks, dict(locator.maxticks))
            for ceiling in range(max(locator.maxticks.values()) - 1, 1, -1):
                locator.maxticks = dict.fromkeys(locator.maxticks, ceiling)
                locator.minticks = min(original[0], ceiling - 1)
                candidate = _visible_locs(axis, locator)
                if candidate is None or len(candidate) < 2 or candidate == locs:
                    continue
                gap = _date_label_gap_em(axis, candidate, fig, renderer)
                if gap >= _MIN_DATE_GAP_EM:
                    changed += 1
                    break
            else:
                locator.minticks, locator.maxticks = original
    return changed
