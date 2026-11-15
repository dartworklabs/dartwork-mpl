"""``dm.simple_layout``: the margin fit, with what the other slices settle.

Large numbers on the ticks, bar labels, legends, line-end names and panel letters settle at
the size the layout fits, before it measures the margins; a legend outside
its Axes, a figure legend and a note line hold room the margins keep clear.
The layout slice runs them in its order from the functions given here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dartwork_mpl import layout, ticks
from dartwork_mpl.labels import (
    note_gap_pt,
    settle_bars,
    settle_panels,
    space_line_ends,
)
from dartwork_mpl.legend import figure_reserve, outside_edge, settle
from dartwork_mpl.style import active_locale

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.gridspec import GridSpecBase, SubplotSpec

    from dartwork_mpl.layout import MarginInput

__all__ = ["simple_layout"]


def prepare_ticks(fig: Figure) -> None:
    """The preset's large numbers, in the units of its locale."""
    ticks.prepare(fig, active_locale())


NEIGHBOURS = layout.Neighbours(
    prepare_ticks=prepare_ticks,
    settle_bars=settle_bars,
    settle_legends=settle,
    space_line_ends=space_line_ends,
    settle_panels=settle_panels,
    outside_edge=outside_edge,
    figure_reserve=figure_reserve,
    note_gap_pt=note_gap_pt,
)


def simple_layout(
    fig: Figure,
    gs: GridSpecBase | SubplotSpec | None = None,
    *,
    margin: MarginInput = "1mm",
    ml: MarginInput | None = None,
    mr: MarginInput | None = None,
    mt: MarginInput | None = None,
    mb: MarginInput | None = None,
    fit_labels: bool = True,
) -> None:
    """Place every Axes' content ``margin`` from the figure edges.

    ``margin`` (and per side ``ml``, ``mr``, ``mt``, ``mb``) is a
    :class:`~dartwork_mpl.Length` (``dm.mm(2)``), a unit string (``"2mm"``),
    a percentage (``"2%"``) or a figure fraction (``0.02``). The default keeps
    1 mm clear, because glyphs flush with the canvas edge are cut; ``0`` puts
    the content flush with the edges. ``gs`` names the grid to fit (its root
    GridSpec), default the first Axes'; every Axes is measured. A
    suptitle, ``fig.text`` note or figure legend keeps its edge clear.

    ``dm.label_bars`` values, ``dm.place_legend`` legends,
    ``dm.label_line_ends`` names and ``dm.label_axes`` letters settle at the
    size being fitted.

    With ``fit_labels`` (default), text that still collides once the
    margins hold is fitted: crowded bottom tick labels wrap at their spaces
    (or turn 30, 45 or 90 degrees when they cannot), an axis name longer
    than its plot and in the way wraps, and panels whose content meets
    across spacing nobody set move apart. A round that leaves a plot under
    30 % of its width or height is undone. Text you rotated, broke into
    lines or wrote as mathtext is left alone.

    Calling it again first undoes what the last call set where it is
    still as set, so it draws the same figure. A figure with no Axes is
    left alone; one without a GridSpec (``fig.add_axes``) is left alone
    with a warning. A margin that is not finite
    raises ``ValueError``.
    """
    layout.simple_layout(
        fig,
        gs,
        margin=margin,
        ml=ml,
        mr=mr,
        mt=mt,
        mb=mb,
        fit_labels=fit_labels,
        given=NEIGHBOURS,
    )
