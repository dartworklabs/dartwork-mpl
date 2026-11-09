"""The box each Axes grid of a figure with SubFigures is fitted in.

``simple_layout`` fits a grid as fractions of the box of the (Sub)Figure
that holds it: the canvas, or a SubFigure's box, which matplotlib places
(``subfigures(width_ratios=..., wspace=...)``) and which is not moved here.

- :func:`held_grids`: each (holder, grid) to fit, parents before children;
- :func:`holder_margins`: the margins of one holder's box, the caller's
  ``margin`` on the sides that touch the canvas, half the panel gap on a
  side that meets another SubFigure, nothing where the caller parted them;
- :func:`place_subfigure_title`: a SubFigure title the library places
  goes under the figure-level text above it, by ``Text.set_y``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

import matplotlib as mpl
from matplotlib.figure import SubFigure
from matplotlib.gridspec import GridSpec

from .._figure_geometry import (
    drawn_in_tree,
    figure_tree,
    get_renderer,
    iter_figure_level_extents,
)
from ._fit_labels import _TARGET_EM
from ._margins import _Sides

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.text import Text
    from matplotlib.transforms import Bbox, BboxBase

#: Where ``SubFigure.suptitle`` puts a title given no ``y``.
_TITLE_Y = 0.98
#: The ``y`` this module gave a SubFigure title, while it is still that.
_PLACED: WeakKeyDictionary[Text, float] = WeakKeyDictionary()
#: How often a SubFigure title moves under the text it meets, at most.
_TITLE_TRIES = 8
_TOUCH_PX = 0.5


def _grid_of(ax: Axes) -> GridSpec | None:
    spec = ax.get_subplotspec()
    grid = (
        None if spec is None else spec.get_topmost_subplotspec().get_gridspec()
    )
    return grid if isinstance(grid, GridSpec) else None


def held_grids(fig: Figure) -> list[tuple[Figure | SubFigure, GridSpec]]:
    """Each grid with the (Sub)Figure that holds it, in tree order.

    A hidden SubFigure draws nothing and is left as it is.
    """
    found: list[tuple[Figure | SubFigure, GridSpec]] = []
    for holder in figure_tree(fig):
        if holder is not fig and not drawn_in_tree(holder):
            continue
        for ax in fig.axes:
            if ax.get_figure(root=False) is not holder:
                continue
            grid = _grid_of(ax)
            if grid is not None and all(grid is not g for _h, g in found):
                found.append((holder, grid))
    return found


def holder_of(fig: Figure, grid: GridSpec) -> SubFigure | None:
    """The SubFigure ``grid`` is laid out in, ``None`` for the canvas."""
    holder = getattr(grid, "figure", None)
    return holder if isinstance(holder, SubFigure) else None


def _related(a: Figure | SubFigure, b: Figure | SubFigure) -> bool:
    """Whether one of ``a`` and ``b`` holds the other."""
    for one, other in ((a, b), (b, a)):
        parent: Figure | SubFigure | None = one
        while parent is not None:
            if parent is other:
                return True
            above = parent.get_figure(root=False)
            parent = None if above is parent else above
    return False


def _meets(box: BboxBase, other: BboxBase, side: str) -> bool:
    """Whether ``other`` starts where ``box``'s ``side`` ends, alongside it."""
    if side in ("left", "right"):
        edge = box.x0 - other.x1 if side == "left" else other.x0 - box.x1
        along = min(box.y1, other.y1) - max(box.y0, other.y0)
    else:
        edge = box.y0 - other.y1 if side == "bottom" else other.y0 - box.y1
        along = min(box.x1, other.x1) - max(box.x0, other.x0)
    return bool(abs(edge) < _TOUCH_PX and along > _TOUCH_PX)


def holder_margins(fig: Figure, holder: SubFigure, margins: _Sides) -> _Sides:
    """``margins`` (fractions of the canvas) as fractions of ``holder``'s box.

    A side on the canvas edge keeps the caller's margin; a side that meets
    another SubFigure keeps half the panel gap (``_TARGET_EM``), so the two
    contents are a gap apart as panels of one grid are; a side the caller
    parted from the next SubFigure (``subfigures(wspace=...)``) adds nothing.
    An explicit ``wspace=0`` / ``hspace=0`` leaves the boxes touching as the
    default does, and matplotlib offers no public way to tell the two apart:
    those sides keep the half gap too (the boxes themselves stay).
    """
    canvas, box = fig.bbox, holder.bbox
    w, h = box.width, box.height
    half_gap = (
        _TARGET_EM * float(mpl.rcParams["font.size"]) * fig.dpi / 72.0 / 2
    )
    others = [
        sub.bbox
        for sub in figure_tree(fig)
        if isinstance(sub, SubFigure) and not _related(sub, holder)
    ]
    sides = {
        "left": (box.x0 - canvas.x0, margins.left * canvas.width, w),
        "right": (canvas.x1 - box.x1, margins.right * canvas.width, w),
        "bottom": (box.y0 - canvas.y0, margins.bottom * canvas.height, h),
        "top": (canvas.y1 - box.y1, margins.top * canvas.height, h),
    }
    out: dict[str, float] = {}
    for side, (from_canvas, margin_px, size) in sides.items():
        if abs(from_canvas) < _TOUCH_PX:
            px = margin_px
        elif any(_meets(box, other, side) for other in others):
            px = half_gap
        else:
            px = 0.0
        out[side] = px / size
    return _Sides(**out)


def place_subfigure_title(fig: Figure, holder: Figure | SubFigure) -> None:
    """Put ``holder``'s title under the figure-level text above it.

    Only a title whose ``y`` the library owns moves: matplotlib's own place
    (``suptitle`` given no ``y``) or the place this module gave it last
    time. A ``y`` the caller gave is kept; a check reports what it covers.
    """
    if not isinstance(holder, SubFigure):
        return
    title: Text | None = getattr(holder, "_suptitle", None)
    if (
        title is None
        or not drawn_in_tree(title)
        or not title.get_text().strip()
    ):
        return
    y = float(title.get_position()[1])
    if y != _TITLE_Y and _PLACED.get(title) != y:
        return
    title.set_y(_TITLE_Y)
    _PLACED.pop(title, None)
    fig.canvas.draw()
    renderer = get_renderer(fig)
    box = holder.bbox
    gap = _TARGET_EM * float(title.get_fontsize()) * fig.dpi / 72.0
    # The figure-level texts above it that lie over its box (they stay put).
    above: list[Bbox] = []
    owner: Figure | SubFigure | None = holder.get_figure(root=False)
    while owner is not None:
        above += [
            ext
            for _art, ext in iter_figure_level_extents(
                owner, renderer, subfigures=False
            )
            if ext.x0 < box.x1 and ext.x1 > box.x0
        ]
        parent = owner.get_figure(root=False)
        owner = None if parent is owner else parent
    # Under whatever shares its band, then again from there (a subtitle
    # under the figure title), a few times at most; a check reports the rest.
    for _ in range(_TITLE_TRIES):
        own = title.get_window_extent(renderer)
        met = [
            ext.y0 - gap for ext in above if ext.y0 < own.y1 and ext.y1 > own.y0
        ]
        if not met:
            return
        placed = (min(met) - box.y0) / box.height
        title.set_y(placed)
        _PLACED[title] = placed
        fig.canvas.draw()
        renderer = get_renderer(fig)


def shown_subfigures(fig: Figure) -> list[SubFigure]:
    """Every SubFigure of ``fig`` no hidden SubFigure hides, parents first."""
    return [
        sub
        for sub in figure_tree(fig)
        if isinstance(sub, SubFigure) and drawn_in_tree(sub)
    ]


def titles_above(holder: SubFigure) -> list[SubFigure]:
    """``holder`` and the SubFigures above it, the outermost first."""
    chain: list[SubFigure] = []
    sub: Figure | SubFigure | None = holder
    while isinstance(sub, SubFigure):
        chain.append(sub)
        parent = sub.get_figure(root=False)
        sub = None if parent is sub else parent
    return chain[::-1]
