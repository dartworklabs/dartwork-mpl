"""What an axis draws along it and who chose where its ticks go.

Thin matplotlib shell for :func:`decide.reads_as_years`: the data of the
lines and points along one axis, and whether its major ticks are still
matplotlib's own linear locator.
"""

from __future__ import annotations

import numpy as np
from matplotlib import ticker
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.collections import PathCollection
from matplotlib.transforms import Transform

from ..geometry import BBOX_ERRORS, shared_axes
from ..vocab import Which
from .model import AxisData


def _along_data(transform: Transform, ax: Axes, which: Which) -> bool:
    """Drawn in data units along ``which`` (an ``axhline`` spans the
    Axes, not the data)."""
    try:
        x, y = transform.contains_branch_seperately(ax.transData)
    except BBOX_ERRORS:
        return False
    return bool(which.pick(x, y))


def data_along(ax: Axes, which: Which) -> AxisData:
    """Where the lines and points of ``ax`` and of every Axes sharing its
    ``which`` axis sit along it. Bars, areas and text do not count."""
    values: list[float] = []
    for member in shared_axes(ax, which):
        for line in member.get_lines():
            if line.get_visible() and _along_data(
                line.get_transform(), member, which
            ):
                xy = np.asarray(line.get_xydata(), dtype=float).reshape(-1, 2)
                values += [float(v) for v in xy[:, which.column]]
        for points in member.collections:
            if (
                isinstance(points, PathCollection)
                and points.get_visible()
                and _along_data(points.get_offset_transform(), member, which)
            ):
                xy = np.asarray(points.get_offsets(), dtype=float).reshape(
                    -1, 2
                )
                values += [float(v) for v in xy[:, which.column]]
    return AxisData.of(values)


def default_locator(axis: Axis) -> bool:
    """Nobody chose where ``axis``'s major ticks go and its scale is linear:
    matplotlib's own ``AutoLocator`` (``set_xticks``, a locator, a log, date
    or category scale each replace it)."""
    return axis.isDefault_majloc and isinstance(
        axis.get_major_locator(), ticker.AutoLocator
    )


def whole_number_locator() -> ticker.MaxNLocator:
    """Matplotlib's own linear locator (``AutoLocator``'s bins and steps),
    ticking at whole numbers only."""
    return ticker.MaxNLocator(
        nbins="auto", steps=[1, 2, 2.5, 5, 10], integer=True
    )
