"""The layout's tick hooks: apply the plans, thin crowded dates, put them back.

``simple_layout`` calls :func:`prepare` once before measuring (so the text
it fits is the text saved) and :func:`thin_dates` after the margins
converge; :func:`remember_dates` records what thinning may lower.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from functools import partial

import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.backend_bases import RendererBase
from matplotlib.figure import Figure

from ..edgecase import settle
from ..geometry import get_renderer
from . import decide
from .dates import (
    CategoryDateLocator,
    PeriodDateFormatter,
    QuarterDateFormatter,
    QuarterLocator,
)
from .edges import AXES_EDGES, LADDER_EDGES, THIN_EDGES
from .formatters import AxisUnitFormatter, WholeYearLocator, YearTickFormatter
from .measure import (
    axes_facts,
    boxes,
    config_digits,
    converter_locator,
    date_zone,
    in_view,
    label_gap,
    language,
    plain,
    rotated,
    settle_twin_spine,
    with_insets,
)
from .model import (
    AxesPlan,
    AxisPlan,
    Candidate,
    Crowding,
    DefaultUnit,
    Ladder,
    Leave,
    Numbers,
    NumberStyle,
    PeriodDates,
    QuarterDates,
    TwoDigits,
    YearTicks,
)


def figure_ladder(fig: Figure | None, extra: str = "") -> Ladder:
    """The large-number ladder ``config.number_ladder`` picks for ``fig``."""
    facts = language(fig, extra)
    return settle(facts, decide.ladder(facts), LADDER_EDGES).plan


def _formats(ax: Axes, fig: Figure) -> bool:
    """Whether the library formats ``ax``'s ticks: a plain figure Axes.

    A colorbar's Axes is one too; its long axis carries the colorbar's own
    formatter and its short axis no ticks, so the plans leave both.
    """
    return ax in fig.axes and plain(ax)


def _apply_axis(axis: Axis, plan: AxisPlan, ladder: Ladder) -> None:
    fmt, locator = axis.get_major_formatter(), axis.get_major_locator()
    match plan:
        case Numbers():
            axis.set_major_formatter(
                AxisUnitFormatter(NumberStyle(ladder, DefaultUnit()))
            )
        case PeriodDates(digits=digits):
            if isinstance(fmt, mdates.ConciseDateFormatter):
                axis.set_major_formatter(
                    PeriodDateFormatter(
                        locator,
                        date_zone(locator),
                        digits=digits,
                        show_offset=fmt.show_offset,
                    )
                )
        case QuarterDates(digits=digits, ends=ends):
            tz = date_zone(locator)
            axis.set_major_locator(QuarterLocator(ends=ends, tz=tz))
            axis.set_major_formatter(QuarterDateFormatter(digits, tz))
        case YearTicks(digits=digits, locator=whole, formatter=words):
            if whole:
                axis.set_major_locator(WholeYearLocator())
            if words:
                axis.set_major_formatter(YearTickFormatter(digits))
        case Leave():
            pass


def _apply_spines(ax: Axes, plan: AxesPlan) -> None:
    for side in plan.spines:
        ax.spines[side.spine].set_visible(True)
        settle_twin_spine(ax, side)  # once: a spine hidden later stays hidden


def prepare(fig: Figure, *, numbers: bool = True) -> None:
    """Ready every axis of ``fig`` before the layout measures it.

    With ``numbers``, the library's tick numbers and dates on axes nobody
    formatted; always, the spine of each twin scale.
    """
    digits = config_digits() if numbers else TwoDigits()
    ladder = figure_ladder(fig) if numbers else None
    twins = boxes(fig)
    for ax in with_insets(fig.axes):
        if not plain(ax):
            continue
        facts = axes_facts(ax, digits, twins.get(ax, ()))
        plan = settle(facts, decide.axes_plan(facts), AXES_EDGES).plan
        if numbers and ladder is not None and _formats(ax, fig):
            _apply_axis(ax.xaxis, plan.x, ladder)
            _apply_axis(ax.yaxis, plan.y, ladder)
        _apply_spines(ax, plan)


# -- thinning ----------------------------------------------------------------------


def _visible(axis: Axis, locator: ticker.Locator) -> list[float] | None:
    """Ticks in view, or ``None`` when matplotlib would warn (no interval fits)."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            locs = locator()
        except UserWarning:
            return None
    return in_view(axis, locs)


def _thin(
    axis: Axis,
    current: list[float],
    options: list[Callable[[], None]],
    restore: Callable[[], None],
    renderer: RendererBase,
) -> bool:
    """Measure each sparser option, take the one the edges pick; else put back.

    The options are measured only when the current labels are crowded.
    """
    facts = Crowding(label_gap(axis, current, renderer), ())
    if any(edge.applies(facts, decide.thinning(facts)) for edge in THIN_EDGES):
        locator = axis.get_major_locator()
        candidates: list[Candidate] = []
        for index, option in enumerate(options):
            option()
            locs = _visible(axis, locator)
            if locs is None or len(locs) < 2 or locs == current:
                continue
            candidates.append(Candidate(index, label_gap(axis, locs, renderer)))
        facts = Crowding(facts.gap, tuple(candidates))
    chosen = settle(facts, decide.thinning(facts), THIN_EDGES).plan.index
    if chosen is None:
        restore()
        return False
    options[chosen]()
    return True


def _thin_axis(axis: Axis, renderer: RendererBase) -> bool:
    """Fewer ticks on one crowded date, quarter, category-date or year axis."""
    if isinstance(axis.get_major_formatter(), ticker.FixedFormatter) or rotated(
        axis
    ):
        return False
    locator = axis.get_major_locator()
    if isinstance(locator, CategoryDateLocator | QuarterLocator):
        step = locator.step
        options = [partial(locator.take, s) for s in locator.steps if s > step]
        return _thin(
            axis,
            in_view(axis, locator()),
            options,
            partial(locator.take, step),
            renderer,
        )
    if isinstance(locator, WholeYearLocator):
        if locator.asked_nbins:
            return False
        current, nbins = in_view(axis, locator()), locator.nbins
        options = [
            partial(locator.thin, n)
            for n in range(max(len(current) - 1, 1), 0, -1)
        ]
        return _thin(
            axis, current, options, partial(locator.thin, nbins), renderer
        )
    if not (
        axis.isDefault_majloc
        and converter_locator(locator)
        and isinstance(axis.get_major_formatter(), mdates.ConciseDateFormatter)
    ):
        return False
    assert isinstance(locator, mdates.AutoDateLocator)
    current = _visible(axis, locator)
    if current is None:
        return False
    saved = (locator.minticks, _maxticks(locator))
    options = [
        partial(
            _ceilings,
            locator,
            min(saved[0], ceiling - 1),
            dict.fromkeys(saved[1], ceiling),
        )
        for ceiling in range(max(saved[1].values()) - 1, 1, -1)
    ]
    return _thin(
        axis, current, options, partial(_ceilings, locator, *saved), renderer
    )


def _maxticks(locator: mdates.AutoDateLocator) -> dict[int, int]:
    """The locator's tick ceilings per date unit (each set, never ``None``)."""
    return {unit: n for unit, n in locator.maxticks.items() if n is not None}


def _ceilings(
    locator: mdates.AutoDateLocator, minticks: int, maxticks: dict[int, int]
) -> None:
    locator.minticks = minticks
    locator.maxticks = dict(maxticks)


def thin_dates(fig: Figure) -> bool:
    """Give crowded date axes fewer ticks at the fitted size; whether one changed."""
    renderer = get_renderer(fig)
    changed = False
    for ax in fig.axes:
        if plain(ax):
            for axis in (ax.xaxis, ax.yaxis):
                changed |= _thin_axis(axis, renderer)
    return changed


def remember_dates(fig: Figure) -> Callable[[], None]:
    """Record the date tick counts :func:`thin_dates` may lower; the call puts them back."""
    saved: list[tuple[Axis, ticker.Locator, Callable[[], None]]] = []
    for ax in fig.axes:
        if not plain(ax):
            continue
        for axis in (ax.xaxis, ax.yaxis):
            locator = axis.get_major_locator()
            if isinstance(locator, CategoryDateLocator | QuarterLocator):
                restore = partial(locator.take, locator.step)
            elif isinstance(locator, WholeYearLocator):
                restore = partial(locator.thin, locator.nbins)
            elif type(locator) is mdates.AutoDateLocator:
                restore = partial(
                    _ceilings, locator, locator.minticks, _maxticks(locator)
                )
            else:
                continue
            saved.append((axis, locator, restore))

    def put_back() -> None:
        for axis, locator, restore in saved:
            if axis.get_major_locator() is locator:
                restore()

    return put_back
