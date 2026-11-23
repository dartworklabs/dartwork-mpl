"""Measure tick rows, their axis names and drawn minus signs."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from matplotlib.category import StrCategoryFormatter
from matplotlib.dates import DateLocator
from matplotlib.ticker import FixedFormatter, FixedLocator, FuncFormatter
from matplotlib.transforms import IdentityTransform

from ..geometry import drawn_tick_labels, shared_axes, text_inks
from . import roles
from .model import AXES, Text, TickRow, TickValues, unicode_minus_tick
from .overlap import tick_label_overlaps

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.gridspec import SubplotSpec
    from matplotlib.text import Text as MplText

    from ..vocab import Which

TextReader = Callable[["MplText", roles.Role, int], Text | None]


def tick_row(
    i: int,
    ax: Axes,
    which: Which,
    renderer: RendererBase,
    read: TextReader,
    parent: Axes | None = None,
) -> TickRow | None:
    """One axis' drawn major labels and how many neighbours collide.
    ``parent`` is the Axes an inset sits in."""
    drawn = drawn_tick_labels(ax, which)
    labels = tuple(
        x for x in (read(t, roles.TickLabel(), i) for t in drawn) if x
    )
    if not labels:
        return None
    pairs, deepest = tick_label_overlaps(ax, which, renderer)
    axis = which.pick(ax.xaxis, ax.yaxis)
    formatter, locator = (axis.get_major_formatter(), axis.get_major_locator())
    names = isinstance(formatter, FixedFormatter | StrCategoryFormatter) or (
        isinstance(formatter, FuncFormatter)
        and isinstance(locator, FixedLocator)
    )  # set_xticks(ticks, labels) prints names
    numbers = not names and not isinstance(locator, DateLocator)
    at = TickValues(
        tuple(
            float(loc)
            for loc, tick in zip(
                axis.get_majorticklocs(), axis.get_major_ticks(), strict=False
            )
            if tick.label1 in drawn or tick.label2 in drawn
        ),
        linear=isinstance(axis.get_transform(), IdentityTransform),
    )
    return TickRow(
        ax,
        i,
        which,
        labels,
        pairs,
        float(deepest),
        numbers=numbers and any(t.value for t in labels),
        named=named(ax, which)
        or (parent is not None and zooms(ax, parent) and named(parent, which)),
        at=at,
    )


def minus_tick(axes: list[tuple[int, Axes]], read: TextReader) -> Text | None:
    """A visible numeric tick with a Unicode minus, on any Axes."""
    for i, ax in axes:
        for which in AXES:
            for label in (
                *drawn_tick_labels(ax, which),
                *drawn_tick_labels(ax, which, minor=True),
            ):
                if (
                    unicode_minus_tick(label.get_text())
                    and text_inks(label)
                    and (tick := read(label, roles.TickLabel(), i)) is not None
                ):
                    return tick
    return None


def zooms(inset: Axes, parent: Axes) -> bool:
    """The inset shows a part of what its parent shows: its view lies on
    the parent's view, on both axes and on the parent's kind of scale. Its
    numbers are then in the parent's units."""

    def meet(a: tuple[float, float], b: tuple[float, float]) -> bool:
        (a0, a1), (b0, b1) = sorted(a), sorted(b)
        return a0 < b1 and b0 < a1

    return (
        inset.get_xscale() == parent.get_xscale()
        and inset.get_yscale() == parent.get_yscale()
        and meet(inset.get_xlim(), parent.get_xlim())
        and meet(inset.get_ylim(), parent.get_ylim())
    )


def named(ax: Axes, which: Which) -> bool:
    """A label names ``ax``'s axis: its own, one of an Axes sharing it or
    in its grid row (y) or column (x), or the figure's sup label."""
    fig = ax.get_figure(root=False)
    spec = ax.get_subplotspec()
    if fig is None:
        return False

    def line(s: SubplotSpec) -> range:
        return which.pick(s.colspan, s.rowspan)

    grid = [
        other
        for other in fig.axes
        if spec is not None
        and (s := other.get_subplotspec()) is not None
        and s.get_gridspec() is spec.get_gridspec()
        and line(s) == line(spec)
    ]
    sup = which.pick(fig.get_supxlabel(), fig.get_supylabel())
    return bool(sup.strip()) or any(
        which.pick(o.xaxis, o.yaxis).label.get_text().strip()
        for o in (*shared_axes(ax, which), *grid)
    )
