"""What the layout is given by the slices that place things at its size.

Bar labels, legends, line-end names and panel letters are other slices'
work, but they settle at the size the layout fits, before it
measures the margins, and some hold room the margins must keep clear. The
layout takes them as typed functions in a :class:`Neighbours` record and
runs them in its own order (``loop.one_step``); ``compose.layout`` fills
the record with the labels and legend slices' functions.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..vocab import Reserve

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

    #: Places what it owns at the drawn size; whether anything moved.
    Settle = Callable[[Figure, RendererBase], bool]


@dataclass(frozen=True)
class Neighbours:
    """The other slices' steps and records, in the order the layout uses them.

    Before the fit: ``prepare_ticks`` writes the preset's large numbers on
    axes nobody formatted, and ``place_notes`` puts note lines at the left
    and bottom margins (figure fractions). At each step, after a draw: ``settle_bars`` (bar value labels), then
    rounds of ``settle_legends`` and ``space_line_ends``, then
    ``settle_panels`` (panel letters), then ``stack_figure_legends``
    (a figure legend in from its edge past the figure texts there).

    While measuring: ``figure_reserve`` the room a figure legend keeps
    from the panels, ``note_gap_pt`` the gap kept above a note line.

    After the fit: ``report_bars``, ``report_legends`` and
    ``report_panels`` say what the settling of bar labels, legends and
    panel letters changed.
    """

    prepare_ticks: Callable[[Figure], None]
    place_notes: Callable[[Figure, float, float], None]
    settle_bars: Settle
    settle_legends: Callable[[Figure, RendererBase, Sequence[Axes]], bool]
    space_line_ends: Settle
    settle_panels: Settle
    stack_figure_legends: Settle
    figure_reserve: Callable[[Artist], Reserve | None]
    note_gap_pt: Callable[[Artist], float | None]
    report_bars: Callable[[Figure], None]
    report_legends: Callable[[Figure], None]
    report_panels: Callable[[Figure], None]
