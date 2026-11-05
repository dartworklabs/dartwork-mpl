"""The library's tick numbers on axes nobody formatted.

Left to matplotlib, an axis prints ``1750`` and ``34000`` without separators
and ``0.5 … 2.5`` under a ``1e6`` corner label, so every agent or person
installs a formatter of their own and the same data reads differently from
figure to figure. :func:`apply_default_tick_format` settles it once:

- an axis whose visible ticks reach 1,000 gets thousands separators
  (``1,750``; ``34,000``) and the fewest exact decimals;
- from one million the axis takes the largest tick's unit (``0.5M …
  2.5M``; ``50만 … 250만`` in Korean figures, ``config.number_ladder``),
  unless that needs more than two decimals;
- x axes whose plotted data are integers 1900-2099 (annual lines, bars,
  scatter; twins and shared axes included) are year axes: ticks on whole
  years only (:class:`._years.WholeYearLocator`), read two digits (``16,
  18, 20``; four when two would print alike, or with
  ``config.tick_years = 4``); integer data in that range that are not years
  (elevations) read the same way, so give such an axis a formatter of
  your own;
- smaller axes (``0, 250 … 750``; ``0.5, 1.0``), other x axes whose ticks all
  sit in 1000-2999 (``1950.3`` elevations), log and category axes, colorbars
  and any axis with a formatter someone chose keep theirs;
- date axes nobody formatted (every preset sets ``date.converter:
  concise``) read whole two-digit dates, ``23.01, 23.05 … 26.01``
  (``23.01.15`` daily, ``23`` yearly); quarterly data reads ``23.Q1, 23.Q3``,
  decided from the plotted dates, and stays in quarters however far the axis
  is thinned. ``config.date_style = "concise"`` gives matplotlib's concise
  words with two-digit years (``23, May, Sep``; ``23, Q2, Q3``), and when the
  figure's axis labels, titles or legend are Korean ``23년, 5월, 9월`` so a
  Korean figure does not mix in English month names; with
  ``tick_years = 4`` too, matplotlib's own concise words (``2023, May``;
  ``2023년, 5월``). See
  :mod:`._dates` and :mod:`._quarters`.

``dm.simple_layout`` calls it before measuring (``format_ticks=False`` opts
out), so the numbers it fits are the numbers saved. After fitting it calls
:func:`thin_crowded_date_ticks`: matplotlib picks date ticks from the date
range alone, so on a narrow axis concise labels run into each other
(``2021년 5월 9월 2022년``); the locator then takes fewer ticks until
neighbouring labels are one em apart. Year axes thin the same way.

Bars and other category charts often stand for dates (``2024-01 …
2024-12`` under twelve bars). ``dm.format_axis_dates`` labels those
positions with the same date words through :class:`CategoryDateFormatter`
and :class:`CategoryDateLocator`, and the same thinning step labels every
second, third ... position (months: 1, 2, 3, 4, 6 or 12; quarters: 1, 2, 4
or 8, keeping Q1) until the labels are one em apart, instead of the labels
being rotated.
"""

from __future__ import annotations

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
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.figure import Figure
from matplotlib.text import Text

from .._figure_geometry import get_renderer
from ..config import config
from ._axis_wide import MYRIAD_LADDER, SI_LADDER, AxisUnitFormatter, Unit
from ._dates import (
    DateStyle,
    Digits,
    KoreanConciseDateFormatter,
    date_formatter,
    reads_quarters,
)
from ._decimals import fewest_exact_decimals
from ._quarters import (
    QUARTER_STEPS,
    QuarterDateFormatter,
    QuarterLocator,
    plotted_dates,
    quarter_anchor,
    quarter_words,
    quarterly,
)
from ._years import (
    WholeYearLocator,
    YearTickFormatter,
    requested_params,
    whole_years,
    year_data,
)

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


def _date_style(
    years: object = None, style: object = None
) -> tuple[Digits, DateStyle]:
    """The year digits and date style asked for, else ``dm.config``'s.

    Raises
    ------
    ValueError
        Naming ``years`` / ``style`` (or ``config.tick_years`` /
        ``config.date_style`` when the value came from the config) unless
        they are 2 or 4 and ``"period"`` or ``"concise"``.
    """
    years_name, style_name = "years", "style"
    if years is None:
        years, years_name = config.tick_years, "config.tick_years"
    if style is None:
        style, style_name = config.date_style, "config.date_style"
    if years not in (2, 4):
        raise ValueError(f"{years_name} must be 2 or 4, got {years!r}")
    if style not in ("period", "concise"):
        raise ValueError(
            f"{style_name} must be 'period' or 'concise', got {style!r}"
        )
    digits: Digits = 2 if years == 2 else 4
    chosen: DateStyle = "period" if style == "period" else "concise"
    return digits, chosen


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


_CONFIG_LADDERS = ("auto", "si", "myriad")


def config_ladder(fig: Figure | None, extra_text: str = "") -> tuple[Unit, ...]:
    """The ladder ``config.number_ladder`` picks for ``fig``.

    ``"si"`` and ``"myriad"`` are fixed; ``"auto"`` picks 만/억/조 when the
    figure's labels, titles or legends (or ``extra_text``) hold Hangul, else SI.
    Any other configured value raises :class:`ValueError`.
    """
    configured = config.number_ladder
    if configured not in _CONFIG_LADDERS:
        raise ValueError(
            "config.number_ladder must be 'auto', 'si' or 'myriad', "
            f"got {configured!r}"
        )
    if configured == "si":
        return SI_LADDER
    if configured == "myriad":
        return MYRIAD_LADDER
    korean = bool(_HANGUL.search(extra_text)) or (
        isinstance(fig, Figure) and _korean_labels(fig)
    )
    return MYRIAD_LADDER if korean else SI_LADDER


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
            day = np.datetime64("NaT", "s")
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
    """Every ``step``-th of ``n`` category positions, from its start, in view.

    ``steps`` lists the steps :func:`thin_crowded_date_ticks` may move
    through, smallest first; ``step`` starts at the first. ``starts`` gives
    each step's first position (default 0): quarterly dates start every
    step on a quarter that keeps Q1 labelled. The grid of positions is the
    same whatever the view, so a bar chart's ticks stay under bars; only the
    ones inside the view are returned, so the words and the thinning follow
    the dates someone can see.
    """

    def __init__(
        self,
        n: int,
        steps: Sequence[int],
        *,
        starts: Sequence[int] | None = None,
    ) -> None:
        if n < 1 or not steps or any(s < 1 for s in steps):
            raise ValueError("CategoryDateLocator needs n >= 1 and steps >= 1")
        if starts is None:
            starts = [0] * len(steps)
        if len(starts) != len(steps) or any(s < 0 for s in starts):
            raise ValueError(
                "CategoryDateLocator needs one start >= 0 for every step"
            )
        self.n = n
        self.steps = tuple(steps)
        self.step = self.steps[0]
        self._starts = dict(zip(self.steps, starts, strict=True))

    def _positions(self) -> range:
        return range(self._starts.get(self.step, 0), self.n, self.step)

    def __call__(self) -> list[float]:
        """Return the positions ``start, start + step ... < n`` inside the view."""
        axis = getattr(self, "axis", None)
        if axis is None:
            return [float(i) for i in self._positions()]
        return self.tick_values(*axis.get_view_interval())

    def tick_values(self, vmin: float, vmax: float) -> list[float]:
        """Return the positions ``start, start + step ... < n`` in ``[vmin, vmax]``."""
        return [float(i) for i in self._positions() if _within(i, vmin, vmax)]


def _category_locator(
    dates: npt.NDArray[np.datetime64], *, quarters: bool
) -> CategoryDateLocator:
    """The locator for dated categories; quarter steps when ``quarters``.

    Quarterly positions step by 1, 2, 4 or 8 quarters, each step starting on
    the first position whose quarter (counted from year 0) it divides, so
    steps 2 show Q1 and Q3 and larger steps Q1.
    """
    if not quarters:
        return CategoryDateLocator(len(dates), _steps_for(dates))
    index = [
        moment.year * 4 + (moment.month - 1) // 3
        for moment in mdates.num2date(mdates.date2num(dates))  # type: ignore[no-untyped-call]
    ]
    starts = [
        next((p for p, q in enumerate(index) if q % step == 0), len(index))
        for step in QUARTER_STEPS
    ]
    return CategoryDateLocator(len(dates), QUARTER_STEPS, starts=starts)


def _within(position: float, vmin: float, vmax: float) -> bool:
    """Whether a category position lies in the view ``[vmin, vmax]``."""
    low, high = sorted((float(vmin), float(vmax)))
    return low - 1e-9 <= position <= high + 1e-9


class CategoryDateFormatter(ticker.Formatter):
    """The library's date words for category positions.

    Position ``i`` stands for ``dates[i]``; positions outside the dates or
    the view get no label. Words are the ones a real date axis gets, worded
    over the ticks shown: ``24.01, 24.03 …`` in the period style; in the
    concise style matplotlib's concise words with the year on January or in
    the axis-corner offset (``24, Mar, May …``; ``2024, Mar …`` with
    four-digit years), Korean (``24년, 3월, 5월 …``) when the figure's axis
    labels, titles or legends are Korean at drawing time. Quarterly dates
    read quarters: ``23.Q1, 23.Q3 …``; concise ``23, Q2, Q3 …``
    (``23년, Q2 …``). With four-digit years and the concise style they read
    as months, matplotlib's own concise words.

    ``years`` (2 or 4) and ``style`` (``"period"`` or ``"concise"``) are
    fixed when the formatter is made; ``None`` takes ``dm.config``'s
    ``tick_years`` / ``date_style`` at that moment.
    """

    def __init__(
        self,
        dates: npt.NDArray[np.datetime64],
        *,
        years: Literal[2, 4] | None = None,
        style: Literal["period", "concise"] | None = None,
    ) -> None:
        self.years, self.style = _date_style(years, style)
        self._nums: list[float] = [
            float(v)
            for v in mdates.date2num(dates)  # type: ignore[no-untyped-call]
        ]
        # Quarters when the positions run through consecutive quarters.
        self.quarters = (
            reads_quarters(self.years, self.style)
            and quarterly(self._nums)
            and bool(np.all(np.diff(self._nums) > 0))
        )
        self._offset = ""

    def _words(self, nums: list[float]) -> tuple[list[str], str]:
        """Words and corner label for the dates shown together."""
        axis = getattr(self, "axis", None)
        fig = axis.get_figure(root=True) if axis is not None else None
        korean = isinstance(fig, Figure) and _korean_labels(fig)
        if self.quarters:
            return quarter_words(
                mdates.num2date(nums),  # type: ignore[no-untyped-call]
                style=self.style,
                digits=self.years,
                korean=korean,
            )
        concise = date_formatter(
            mdates.AutoDateLocator(),  # type: ignore[no-untyped-call]
            years=self.years,
            style=self.style,
            korean=korean,
        )
        words: list[str] = concise.format_ticks(nums)  # type: ignore[no-untyped-call]
        return words, str(concise.get_offset())  # type: ignore[no-untyped-call]

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
        words, self._offset = self._words([self._nums[i] for i in inside])
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


def _plain_numbers(axis: Axis) -> bool:
    """A linear axis of plain numbers: no dates, categories or other units."""
    return axis.get_scale() == "linear" and axis.get_converter() is None


def _same_formats(
    a: mdates.ConciseDateFormatter, b: mdates.ConciseDateFormatter
) -> bool:
    """Same class and the same format strings."""
    return type(a) is type(b) and all(
        list(getattr(a, name)) == list(getattr(b, name))
        for name in ("formats", "zero_formats", "offset_formats")
    )


def _stock(fmt: mdates.ConciseDateFormatter) -> bool:
    """Whether a concise formatter is a stock one with its own format strings.

    Matplotlib's English one, or the four-digit Korean one. Code that edits
    the strings (a two-digit ``%y`` year, say) or picks another class chose
    its dates, and keeps them.
    """
    locator = mdates.AutoDateLocator()  # type: ignore[no-untyped-call]
    stock: list[mdates.ConciseDateFormatter] = [
        mdates.ConciseDateFormatter(locator),  # type: ignore[no-untyped-call]
        KoreanConciseDateFormatter(locator),
    ]
    return any(_same_formats(fmt, reference) for reference in stock)


def _restyle_dates(
    ax: Axes,
    which: Literal["x", "y"],
    axis: Axis,
    fmt: mdates.ConciseDateFormatter,
    *,
    years: Digits,
    style: DateStyle,
    korean: bool,
) -> int:
    """Give a stock concise date axis the chosen style; 1 if it changed.

    Quarterly data on the converter's own locator reads quarters
    (:class:`QuarterLocator`, :class:`QuarterDateFormatter`); everything
    else keeps its locator and gets :func:`date_formatter`'s formatter with
    the same time zone, offset and TeX choice.
    """
    locator = axis.get_major_locator()
    if not _stock(fmt) or not isinstance(locator, mdates.DateLocator):
        return 0
    if (
        reads_quarters(years, style)
        and axis.isDefault_majloc
        and _converter_locator(locator)
    ):
        dates = plotted_dates(ax, which)
        if quarterly(dates):
            axis.set_major_locator(
                QuarterLocator(
                    anchor=quarter_anchor(dates, locator.tz), tz=locator.tz
                )
            )
            axis.set_major_formatter(
                QuarterDateFormatter(
                    style=style,
                    digits=years,
                    korean=korean,
                    tz=fmt._tz,
                    show_offset=fmt.show_offset,
                )
            )
            return 1
    chosen = date_formatter(
        locator,
        years=years,
        style=style,
        korean=korean,
        tz=fmt._tz,
        show_offset=fmt.show_offset,
        usetex=fmt._usetex,
    )
    if _same_formats(chosen, fmt):
        return 0
    axis.set_major_formatter(chosen)
    return 1


def _year_axis(ax: Axes, axis: Axis, digits: Digits, suffix: str) -> int:
    """Whole-year ticks and year labels on an x axis whose data are years.

    The data decide (:func:`year_data` over :func:`plotted_dates`, twins and
    shared axes included), not the ticks: ``dm.simple_layout`` refits the
    margins after this call and the ticks move with them. Matplotlib's own
    locator gives way to :class:`WholeYearLocator`, which carries what
    someone asked of it in place (``ax.locator_params(axis="x", nbins=3)``),
    and its own formatter to :class:`YearTickFormatter` when every tick is
    a whole year whatever the refit does (:func:`_ticks_whole_years`). A
    locator or formatter someone set stays; under a locator someone set
    (``MaxNLocator``) matplotlib's formatter stays too, so every tick reads
    its value (``2005, 2007.5``). Returns 1 if anything changed.
    """
    if not year_data(plotted_dates(ax, "x")):
        return 0
    changed = 0
    if axis.isDefault_majloc:
        asked = requested_params(axis.get_major_locator())
        axis.set_major_locator(WholeYearLocator(**asked))
        changed = 1
    if axis.isDefault_majfmt and _ticks_whole_years(axis.get_major_locator()):
        axis.set_major_formatter(YearTickFormatter(digits, suffix))
        changed = 1
    return changed


def _ticks_whole_years(locator: ticker.Locator) -> bool:
    """Whether every tick the locator gives is a whole year.

    The library's :class:`WholeYearLocator`, or ticks someone pinned
    (``set_xticks``) that are all whole years. Any other locator can land
    between years once the margins are refitted.
    """
    if isinstance(locator, WholeYearLocator):
        return True
    if not isinstance(locator, ticker.FixedLocator):
        return False
    pins = locator.tick_values(-np.inf, np.inf)  # every pin, any view
    return whole_years([float(v) for v in pins])


def apply_default_tick_format(fig: Figure) -> int:
    """Install the library's tick numbers on every axis nobody formatted.

    One rule decides what is "nobody formatted": matplotlib's own flags.
    A formatter goes in only while ``axis.isDefault_majfmt`` holds and a
    locator only while ``axis.isDefault_majloc`` holds; ``set_major_formatter``
    and ``set_major_locator`` clear them (on every axes sharing the ticker),
    so anything someone set, of any class, a stock ``ConciseDateFormatter``
    or ``ScalarFormatter`` included, is never replaced.

    Returns the number of axes changed. Safe to call again: what this call
    installs clears the same flags.
    """
    tick_years, date_style = _date_style()
    changed = 0
    korean = _korean_labels(fig)
    ladder = config_ladder(fig)
    for ax in fig.axes:
        if (
            ax.name != "rectilinear"
            or getattr(ax, "_colorbar", None) is not None
        ):
            continue
        pairs: tuple[tuple[Literal["x", "y"], Axis], ...] = (
            ("x", ax.xaxis),
            ("y", ax.yaxis),
        )
        for which, axis in pairs:
            fmt = axis.get_major_formatter()
            if isinstance(fmt, mdates.ConciseDateFormatter):
                if axis.isDefault_majfmt:
                    changed += _restyle_dates(
                        ax,
                        which,
                        axis,
                        fmt,
                        years=tick_years,
                        style=date_style,
                        korean=korean,
                    )
                continue
            if not _plain_numbers(axis):
                continue
            if which == "x":
                suffix = "년" if korean and date_style == "concise" else ""
                changed += _year_axis(ax, axis, tick_years, suffix)
            if not axis.isDefault_majfmt:
                continue
            ticks = _visible_ticks(axis)
            if not ticks or max(abs(t) for t in ticks) < _SEPARATOR_FROM:
                continue
            if which == "x" and all(_YEARS[0] <= t <= _YEARS[1] for t in ticks):
                continue  # years: 2024, not 2,024
            axis.set_major_formatter(DefaultNumberFormatter(ladder))
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


def _thin_by_steps(
    axis: Axis,
    locator: CategoryDateLocator | QuarterLocator,
    fig: Figure,
    renderer: Any,
) -> int:
    """Label every n-th dated category position (or quarter) until one em apart.

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


def _view_locs(axis: Axis, locs: Sequence[float]) -> list[float]:
    low, high = sorted(float(v) for v in axis.get_view_interval())
    return [float(v) for v in locs if low <= float(v) <= high]


def _thin_years(
    axis: Axis, locator: WholeYearLocator, fig: Figure, renderer: Any
) -> int:
    """Lower a year axis's tick count until its labels are one em apart.

    Leaves rotated x labels and a requested ``nbins`` alone. Tries ever
    fewer bins and keeps the first that gives two or more ticks
    :data:`_MIN_DATE_GAP_EM` ems apart; with none, the count it started
    from is restored (a repeat layout keeps an earlier thinning). Returns 1
    when it changed, else 0.
    """
    if "nbins" in locator.requested:
        return 0
    label = axis.get_major_ticks(1)[0].label1
    if axis is axis.axes.xaxis and label.get_rotation() % 180:
        return 0
    locs = _view_locs(axis, locator())
    if _date_label_gap_em(axis, locs, fig, renderer) >= _MIN_DATE_GAP_EM:
        return 0
    original = locator.nbins
    for nbins in range(max(len(locs) - 1, 1), 0, -1):
        locator.thin(nbins)
        candidate = _view_locs(axis, locator())
        if len(candidate) < 2 or candidate == locs:
            continue
        if _date_label_gap_em(axis, candidate, fig, renderer) >= (
            _MIN_DATE_GAP_EM
        ):
            return 1
    locator.thin(original)
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

    Acts only on axes matplotlib's date converter set up (its own
    ``AutoDateLocator``, ``axis.isDefault_majloc`` still set, with its
    default tick counts and concise labels) whose labels are not rotated, so
    a locator someone set or configured, or one already thinned, is kept.
    Each step lowers the locator's tick ceiling, skipping ceilings
    matplotlib cannot meet; the first that keeps neighbouring labels
    :data:`_MIN_DATE_GAP_EM` ems apart with two or more ticks wins. An axis
    with no such ceiling is left as it was.

    Axes labelled with ``dm.format_axis_dates`` (a
    :class:`CategoryDateLocator`) and quarterly date axes (a
    :class:`QuarterLocator`: 1, 2, 4, 8 … quarters, Q1 kept) are thinned
    the same way through the locator's steps, so the notation never
    changes; see :func:`_thin_by_steps`. Year axes (a
    :class:`WholeYearLocator`) take fewer whole-year ticks; see
    :func:`_thin_years`.
    """
    renderer = get_renderer(fig)
    changed = 0
    for ax in fig.axes:
        if ax.name != "rectilinear":
            continue
        for axis in (ax.xaxis, ax.yaxis):
            locator = axis.get_major_locator()
            if isinstance(locator, (CategoryDateLocator, QuarterLocator)):
                changed += _thin_by_steps(axis, locator, fig, renderer)
                continue
            if isinstance(locator, WholeYearLocator):
                changed += _thin_years(axis, locator, fig, renderer)
                continue
            if (
                not axis.isDefault_majloc
                or not _converter_locator(locator)
                or not isinstance(
                    axis.get_major_formatter(), mdates.ConciseDateFormatter
                )
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
