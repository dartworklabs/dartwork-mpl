"""Say what one ``simple_layout`` call did to the text besides the margins.

Text fitting runs in rounds, and a later round can undo an earlier one (a
wrap that becomes a turn), so the layout looks once before it starts and
once when it is done, and reports the difference: tick labels turned or
wrapped, axis names wrapped, panels moved apart. Nothing here is read
unless the layout's logger is enabled.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..hidden import axes_name
from ..vocab import Which, X, Y
from .apply import WrappedTickFormatter, turned
from .measure import cartesian, grid_axes

if TYPE_CHECKING:
    from collections.abc import Mapping

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.gridspec import GridSpec

LOG = logging.getLogger("dartwork_mpl.layout")


def on() -> bool:
    """Whether anyone listens: else nothing is looked at."""
    return LOG.isEnabledFor(logging.INFO)


@dataclass(frozen=True)
class Text:
    """The text a layout may change, as it reads at one moment."""

    turns: Mapping[Axes, float]
    wraps: Mapping[Axes, Mapping[str, str]]
    names: Mapping[tuple[Axes, Which], str]
    spacing: tuple[float | None, float | None]


def _turn(ax: Axes) -> float:
    """The angle a layout turned ``ax``'s bottom tick labels to (0: none)."""
    return turned(ax.xaxis) or 0.0


def _wrap(ax: Axes) -> Mapping[str, str]:
    fmt = ax.xaxis.get_major_formatter()
    return dict(fmt.lines) if isinstance(fmt, WrappedTickFormatter) else {}


def look(fig: Figure, gs: GridSpec) -> Text:
    """The fitted text of ``fig``'s Axes on ``gs`` now."""
    axes = [ax for ax in grid_axes(fig, gs) if cartesian(ax)]
    return Text(
        turns={ax: _turn(ax) for ax in axes},
        wraps={ax: _wrap(ax) for ax in axes},
        names={
            (ax, which): which.pick(ax.xaxis, ax.yaxis).label.get_text()
            for ax in axes
            for which in (X(), Y())
        },
        spacing=(gs.wspace, gs.hspace),
    )


def _turns(before: Text, after: Text) -> None:
    for ax, angle in after.turns.items():
        old = before.turns.get(ax, 0.0)
        if angle == old:
            continue
        if angle:
            LOG.info(
                "turned the x tick labels of %s %g°: they overlapped flat; "
                "use a wider figure or shorter labels to keep them flat",
                axes_name(ax),
                angle,
            )
        else:
            LOG.info(
                "put the x tick labels of %s upright again: they fit flat "
                "at this size",
                axes_name(ax),
            )


def _wraps(before: Text, after: Text) -> None:
    by_axis: dict[int, list[Axes]] = {}
    for ax, lines in after.wraps.items():
        if lines and lines != before.wraps.get(ax, {}):
            fmt = ax.xaxis.get_major_formatter()
            by_axis.setdefault(id(fmt), []).append(ax)
    for axes in by_axis.values():
        LOG.info(
            "broke %d x tick labels of %s onto more lines at their spaces: "
            "they ran into each other on one line; break them yourself with "
            '"\\n" or use a wider figure to keep them on one line',
            len(after.wraps[axes[0]]),
            ", ".join(axes_name(ax) for ax in axes),
        )


def _names(before: Text, after: Text) -> None:
    for (ax, which), name in after.names.items():
        old = before.names.get((ax, which))
        if old is None or name == old or name.split() != old.split():
            continue  # not wrapped by the layout: renamed, or as it was
        LOG.info(
            "broke the %s axis name of %s onto %d lines: it was longer than "
            "its panel and ran into a neighbour or off the canvas; break it "
            'yourself with "\\n" or shorten it to choose the lines',
            which.letter,
            axes_name(ax),
            name.count("\n") + 1,
        )


def _spacing(before: Text, after: Text) -> None:
    for (old, new), (between, key) in zip(
        zip(before.spacing, after.spacing, strict=True),
        (("columns", "wspace"), ("rows", "hspace")),
        strict=True,
    ):
        if new is None or new == old:
            continue
        LOG.info(
            "moved the panel %s apart (%s %.2f): their tick labels or names "
            "ran into each other at matplotlib's spacing; set %s yourself "
            "(gridspec_kw or fig.subplots_adjust) to keep your own",
            between,
            key,
            new,
            key,
        )


def changes(before: Text, after: Text) -> None:
    """One line for each change from ``before`` to ``after``."""
    _turns(before, after)
    _wraps(before, after)
    _names(before, after)
    _spacing(before, after)


def unlisted_twins(hosts: list[Axes]) -> None:
    """Say the layout left a figure with twins it cannot move alone."""
    LOG.info(
        "left the margins of the figure as they were: %s has twin axes the "
        "figure does not list (mpl_toolkits host_subplot), which stay where "
        "they were made while the layout moves the plot, so fitting would "
        "squeeze it; use ax.twinx() instead, twice for a third y axis with "
        'the second twin\'s spine moved out: spines["right"].set_position('
        '("outward", 40))',
        " and ".join(axes_name(ax) for ax in hosts),
    )
