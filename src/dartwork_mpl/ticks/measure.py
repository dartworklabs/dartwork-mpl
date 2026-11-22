"""What an axis draws along it and who chose where its ticks go.

Thin matplotlib shell for :func:`decide.reads_whole`: where everything drawn
in data units along one axis sits, and whether its major ticks are still
matplotlib's own linear locator or the whole-number one this slice placed.
"""

from __future__ import annotations

import weakref

import numpy as np
from matplotlib import ticker
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.collections import Collection, QuadMesh
from matplotlib.container import BarContainer
from matplotlib.patches import Rectangle
from matplotlib.path import Path
from matplotlib.transforms import Transform
from numpy.typing import NDArray

from ..geometry import BBOX_ERRORS, shared_axes
from ..vocab import Which, bars_along
from .model import AxisData

#: The whole-number locators this slice placed; any other locator on an axis
#: that is not matplotlib's own was set by someone else.
PLACED: weakref.WeakSet[ticker.Locator] = weakref.WeakSet()

Points = NDArray[np.float64]
"""``(n, 2)`` positions in data units."""

UNDRAWN = (Path.CLOSEPOLY, Path.STOP)  # codes whose vertex draws nothing


def _along_data(transform: Transform, ax: Axes, which: Which) -> bool:
    """Drawn in data units along ``which`` (an ``axhline`` spans the
    Axes, not the data)."""
    try:
        x, y = transform.contains_branch_seperately(ax.transData)
    except BBOX_ERRORS:
        return False
    return bool(which.pick(x, y))


def _xy(points: object) -> Points:
    return np.asarray(points, dtype=float).reshape(-1, 2)


def _vertices(path: Path) -> Points:
    """A path's drawn vertices (a ``CLOSEPOLY`` vertex is a placeholder)."""
    xy = _xy(path.vertices)
    if path.codes is None:
        return xy
    return xy[~np.isin(path.codes, UNDRAWN)]


def _collection(points: Collection, ax: Axes, which: Which) -> list[Points]:
    """A scatter's points where its offsets sit in data units; an area, a
    mesh or a set of segments where its paths do."""
    found: list[Points] = []
    if _along_data(points.get_offset_transform(), ax, which):
        found.append(_xy(points.get_offsets()))
    if _along_data(points.get_transform(), ax, which):
        if isinstance(points, QuadMesh):
            found.append(_xy(points.get_coordinates()))
        else:
            found += [_vertices(p) for p in points.get_paths()]
    return found


def _bar(bar: Rectangle, standing: Which | None, which: Which) -> list[float]:
    """Along the axis a bar stands on, its centre; along its value axis,
    its two ends."""
    x, y = bar.get_xy()
    start, size = which.pick((x, bar.get_width()), (y, bar.get_height()))
    if standing == which:
        return [start + size / 2]
    return [start, start + size]


def _member(ax: Axes, which: Which) -> list[float]:
    values: list[float] = []
    bars: set[int] = set()
    for container in ax.containers:
        if not isinstance(container, BarContainer):
            continue
        standing = bars_along(container.orientation)
        for bar in container.patches:
            bars.add(id(bar))
            if bar.get_visible() and _along_data(
                bar.get_data_transform(), ax, which
            ):
                values += _bar(bar, standing, which)
    found: list[Points] = [
        _xy(line.get_xydata())
        for line in ax.get_lines()
        if line.get_visible() and _along_data(line.get_transform(), ax, which)
    ]
    for points in ax.collections:
        if points.get_visible():
            found += _collection(points, ax, which)
    for patch in ax.patches:
        if (
            id(patch) not in bars
            and patch.get_visible()
            and _along_data(patch.get_data_transform(), ax, which)
        ):
            outline = _vertices(patch.get_path())
            found.append(_xy(patch.get_patch_transform().transform(outline)))
    for image in ax.images:
        if image.get_visible() and _along_data(
            image.get_transform(), ax, which
        ):
            left, right, bottom, top = image.get_extent()
            found.append(_xy([[left, bottom], [right, top]]))
    for xy in found:
        values += xy[:, which.column].tolist()
    return values


def data_along(ax: Axes, which: Which) -> AxisData:
    """Where everything ``ax`` and every Axes sharing its ``which`` axis
    draw in data units sits along it: the points of lines and scatters, the
    outlines of areas, meshes and patches, the edges of images, and of a bar
    its centre along the axis it stands on and its two ends along the other.
    Text does not count."""
    values: list[float] = []
    for member in shared_axes(ax, which):
        values += _member(member, which)
    return AxisData.of(np.unique(np.asarray(values, dtype=float)).tolist())


def default_locator(axis: Axis) -> bool:
    """Nobody chose where ``axis``'s major ticks go and its scale is linear:
    matplotlib's own ``AutoLocator`` (``set_xticks``, a locator, a log, date
    or category scale each replace it)."""
    return axis.isDefault_majloc and isinstance(
        axis.get_major_locator(), ticker.AutoLocator
    )


def placed_whole(axis: Axis) -> bool:
    """``axis`` still ticks with the whole-number locator this slice set."""
    return axis.get_major_locator() in PLACED
