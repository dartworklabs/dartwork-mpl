"""Content-aware margins: :func:`simple_layout`, ``dm.simple_layout`` once
``compose.layout`` gives it the other slices' steps.

The root GridSpec's edges are set so the drawn content of every Axes (tick
labels, axis names, titles, texts, legends) sits ``margin`` from the canvas
edge, past what figure-level text and legends reserve, measured again until
no edge moves by half a pixel. No optimiser: the same figure gives the same
layout every time.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from . import loop, report
from .given import Neighbours
from .measure import grid_of, unlisted_twin_hosts
from .model import Flush, parse_margin

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from ..length import Length

__all__ = ["Flush", "Neighbours", "simple_layout"]

NO_GRID = (
    "simple_layout: no GridSpec found (figure uses fig.add_axes or "
    "manually placed axes); layout unchanged. Build axes via "
    "plt.subplots / fig.add_gridspec to use content-aware margins."
)


def simple_layout(
    fig: Figure, *, margin: Length | str | Flush, given: Neighbours
) -> None:
    """``dm.simple_layout`` (``compose.layout``), the other slices' steps and
    records ``given``. A figure with no Axes is left alone, one whose first
    Axes is on no GridSpec with a warning, one with twins it does not list
    (``mpl_toolkits`` parasite axes) with a report line."""
    if not fig.axes:
        return
    grid = grid_of(fig.axes[0])
    if grid is None:
        warnings.warn(NO_GRID, stacklevel=3)
        return
    hosts = unlisted_twin_hosts(fig)
    if hosts:
        report.unlisted_twins(hosts)
        return
    size = fig.get_size_inches()
    margins = parse_margin(margin, (float(size[0]), float(size[1])))
    loop.run(fig, grid, margins, given)
