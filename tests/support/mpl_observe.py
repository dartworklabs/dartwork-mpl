"""Observe drawn Matplotlib figures the way a reader sees them.

These are the tests' independent oracles: they draw through the figure's own
canvas and read public extents, so they never borrow the production renderer
or geometry helpers (``dartwork_mpl._figure_geometry``) under test.
"""

from __future__ import annotations

from matplotlib.backend_bases import RendererBase
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.patches import Rectangle

# Corner ``loc`` names in Matplotlib's code order (1-4).
CORNERS = ("upper right", "upper left", "lower left", "lower right")


def drawn_renderer(fig: Figure) -> RendererBase:
    """Draw ``fig`` on its own canvas and return that canvas's renderer."""
    fig.canvas.draw()
    renderer: RendererBase = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    return renderer


def legend_gap_px(legend: Legend) -> float:
    """The legend's ``borderaxespad`` in pixels: its own font size units.

    ``legend.prop`` is the legend's public font; Matplotlib pads a corner
    legend from its anchor by ``borderaxespad`` of this size.
    """
    fig = legend.get_figure(root=True)
    assert fig is not None
    size: float = legend.prop.get_size_in_points()
    gap: float = legend.borderaxespad * size * fig.dpi / 72.0
    return gap


def legend_corner(legend: Legend, tol_px: float = 0.5) -> str | None:
    """Name the anchor corner the drawn legend is pinned to, else ``None``.

    A corner ``loc`` puts the legend's matching corner ``borderaxespad``
    inside the same corner of ``get_bbox_to_anchor()`` (the axes, or a point
    such as ``(1.02, 1)``). This reads that from the drawn extents instead of
    the private ``Legend._loc`` code. ``None`` means no corner matched, for
    example a centred legend.
    """
    fig = legend.get_figure(root=True)
    assert fig is not None
    box = legend.get_window_extent(drawn_renderer(fig))
    anchor = legend.get_bbox_to_anchor()
    pad = legend_gap_px(legend)
    offsets = {
        "upper right": (anchor.x1 - pad - box.x1, anchor.y1 - pad - box.y1),
        "upper left": (box.x0 - anchor.x0 - pad, anchor.y1 - pad - box.y1),
        "lower left": (box.x0 - anchor.x0 - pad, box.y0 - anchor.y0 - pad),
        "lower right": (anchor.x1 - pad - box.x1, box.y0 - anchor.y0 - pad),
    }
    matched = [
        corner
        for corner, (dx, dy) in offsets.items()
        if abs(dx) <= tol_px and abs(dy) <= tol_px
    ]
    return matched[0] if len(matched) == 1 else None


def pinned_legend_corner(legend: Legend) -> str | None:
    """:func:`legend_corner`, but only if the legend keeps it once data fills it.

    Matplotlib's ``loc="best"`` re-picks its spot on every draw, so a legend
    that only happened to land on a corner moves when that corner of the
    axes fills up. This puts an opaque patch over the observed corner (40%
    of the axes each way, axes coordinates, so data limits stay), redraws,
    and returns the corner only if the legend stayed. The patch is removed
    again either way.

    Only a legend anchored to its axes is checked this way. A legend anchored
    outside them (``bbox_to_anchor=(1.02, 1)``) is not under the patch, so
    its corner comes back unchecked: a ``"best"`` there is not caught by this
    helper. ``test_helpers_labels.py::TestOptimizeLegend::
    test_outside_placement_sets_anchor`` catches it for ``optimize_legend``
    (its data makes ``"best"`` pick another corner on the first draw).
    """
    corner = legend_corner(legend)
    ax = legend.axes
    if corner is None or ax is None:
        return corner
    x0 = 0.0 if corner.endswith("left") else 0.6
    y0 = 0.6 if corner.startswith("upper") else 0.0
    occupant = Rectangle((x0, y0), 0.4, 0.4, transform=ax.transAxes)
    ax.add_patch(occupant)
    try:
        return corner if legend_corner(legend) == corner else None
    finally:
        occupant.remove()


def legend_ncols(legend: Legend) -> int:
    """The legend's requested column count.

    Matplotlib has ``Legend.set_ncols`` but no public getter (3.11), so this
    reads ``Legend._ncols``. Counting drawn columns is no substitute: it
    cannot tell ``ncols=4`` from ``ncols=3`` with three entries. This is the
    one place tests read it; replace it here when Matplotlib adds a getter.
    """
    ncols: int = legend._ncols  # type: ignore[attr-defined]
    return ncols
