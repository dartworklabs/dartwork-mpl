"""``dm.simple_layout``: the margin fit, with what the other slices settle.

Large numbers on the ticks, bar labels, legends, line-end names and panel
letters settle at the size the layout fits, before it measures the margins;
a figure legend and a note line hold room the margins keep clear. The
layout slice runs them in its order from the functions given here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dartwork_mpl import layout, ticks
from dartwork_mpl.labels import (
    note_gap_pt,
    place_notes,
    report_bars,
    report_panels,
    settle_bars,
    settle_panels,
    space_line_ends,
)
from dartwork_mpl.legend import (
    figure_reserve,
    report_legends,
    settle,
    stack_under_texts,
)
from dartwork_mpl.style import active_locale

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from dartwork_mpl.length import Length

__all__ = ["simple_layout"]


def prepare_ticks(fig: Figure) -> None:
    """The preset's large numbers, in the units of its locale."""
    ticks.prepare(fig, active_locale())


NEIGHBOURS = layout.Neighbours(
    prepare_ticks=prepare_ticks,
    place_notes=place_notes,
    settle_bars=settle_bars,
    settle_legends=settle,
    space_line_ends=space_line_ends,
    settle_panels=settle_panels,
    stack_figure_legends=stack_under_texts,
    figure_reserve=figure_reserve,
    note_gap_pt=note_gap_pt,
    report_bars=report_bars,
    report_legends=report_legends,
    report_panels=report_panels,
)


def simple_layout(
    fig: Figure, *, margin: Length | str | layout.Flush = "1mm"
) -> None:
    """Place every Axes' content ``margin`` from the figure edges.

    ``margin`` is a :class:`~dartwork_mpl.Length` (``dm.mm(3)``) or a unit
    string (``"3mm"``); the default keeps 1 mm clear, because glyphs flush
    with the canvas edge are cut. ``margin=0`` puts the content flush with
    the edge, for a figure placed inside another document. Every Axes on the first Axes' GridSpec is
    placed; a suptitle, ``fig.text`` note or figure legend keeps its edge
    clear. A ``dm.add_note`` line moves to ``margin`` from the left and
    bottom edges, unless you moved it.

    ``dm.label_bars`` values, ``dm.place_legend`` legends,
    ``dm.label_line_ends`` names and ``dm.label_axes`` letters settle at the
    size being fitted.

    Text that still collides once the margins hold is fitted: crowded
    bottom tick labels wrap at their spaces (or turn 30, 45 or 90 degrees
    when they cannot), an axis name longer than its plot and in the way
    wraps, and panels whose content meets across spacing nobody set move
    apart. Text you rotated, broke into lines or wrote as mathtext, and
    spacing you set, are left alone.

    A figure with no Axes is left alone; one without a GridSpec
    (``fig.add_axes``) is left alone with a warning, and one with
    ``mpl_toolkits`` parasite axes (``host_subplot``), which do not move with
    their host, is left alone and says so.
    """
    layout.simple_layout(fig, margin=margin, given=NEIGHBOURS)
