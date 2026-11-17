"""The locator this slice places on an axis of whole numbers, and putting
matplotlib's own back when the data stop being whole."""

from __future__ import annotations

from matplotlib import ticker
from matplotlib.axis import Axis

from .measure import PLACED
from .model import TickCount


def tick_whole(axis: Axis, fewest: TickCount) -> None:
    """Matplotlib's own linear locator (``AutoLocator``'s bins and steps),
    ticking at whole numbers only and keeping ``fewest`` ticks in view,
    remembered as this slice's."""
    locator = ticker.MaxNLocator(
        nbins="auto", steps=[1, 2, 2.5, 5, 10], integer=True, min_n_ticks=fewest
    )
    axis.set_major_locator(locator)
    PLACED.add(locator)


def tick_default(axis: Axis) -> None:
    """Matplotlib's own locator again, as if nobody had set one."""
    axis.set_major_locator(ticker.AutoLocator())
    axis.isDefault_majloc = True
