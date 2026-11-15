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

from ..vocab import Edge, Reserve

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.legend import Legend

    #: Places what it owns at the drawn size; whether anything moved.
    Settle = Callable[[Figure, RendererBase], bool]


@dataclass(frozen=True)
class Neighbours:
    """The other slices' steps and records, in the order the layout uses them.

    Before the fit: ``prepare_ticks`` writes the preset's large numbers on
    axes nobody formatted. At each step, after a draw: ``settle_bars`` (bar value labels), then
    rounds of ``settle_legends`` and ``space_line_ends``, then
    ``settle_panels`` (panel letters).

    While measuring: ``outside_edge`` is the edge of its Axes a legend sits
    outside of, ``figure_reserve`` the figure edge a figure legend holds,
    ``note_gap_pt`` the gap kept above a note line.
    """

    prepare_ticks: Callable[[Figure], None]
    settle_bars: Settle
    settle_legends: Callable[[Figure, RendererBase, Sequence[Axes]], bool]
    space_line_ends: Settle
    settle_panels: Settle
    outside_edge: Callable[[Legend], Edge | None]
    figure_reserve: Callable[[Artist], Reserve | None]
    note_gap_pt: Callable[[Artist], float | None]
