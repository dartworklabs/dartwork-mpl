"""The figure edges that suptitle, fig.text and fig.legend reserve for ``simple_layout``."""

from __future__ import annotations

from typing import Any, Literal, TypeAlias

from matplotlib.figure import Figure

from .._figure_geometry import iter_figure_level_extents
from ._margins import _Sides


def _holder_reservations(holder: Any, renderer: Any) -> _Sides:
    """Space (fraction of ``holder``'s box) each edge of a SubFigure's box
    keeps for the figure-level artists that lie over it.

    Those of ``holder`` and of every (Sub)Figure above it, each assigned to
    an edge by its own (Sub)Figure (:func:`_reservation_edge`): a figure
    suptitle over the top row of SubFigures pushes their grids down, a
    SubFigure's own suptitle its own grid.
    """
    box = holder.bbox
    w, h = box.width, box.height
    res = {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0}
    dpi = holder.get_figure(root=True).dpi
    owner = holder
    while owner is not None:
        ob = owner.bbox
        for art, ext in iter_figure_level_extents(
            owner, renderer, subfigures=False
        ):
            if (
                not art.get_in_layout()
                or not (ext.x0 < box.x1 and ext.x1 > box.x0)
                or not (ext.y0 < box.y1 and ext.y1 > box.y0)
            ):
                continue
            edge = _reservation_edge(
                owner,
                art,
                (ext.x0 - ob.x0) / ob.width,
                (ext.x1 - ob.x0) / ob.width,
                (ext.y0 - ob.y0) / ob.height,
                (ext.y1 - ob.y0) / ob.height,
            )
            gap = float(getattr(art, "_dm_layout_gap_pt", 0.0)) * dpi / 72.0
            reach = {
                "left": ext.x1 - box.x0 + gap,
                "right": box.x1 - ext.x0 + gap,
                "bottom": ext.y1 - box.y0 + gap,
                "top": box.y1 - ext.y0 + gap,
            }[edge]
            res[edge] = max(res[edge], reach)
        parent = owner.get_figure(root=False)
        owner = None if parent is owner else parent
    return _Sides(
        left=res["left"] / w,
        right=res["right"] / w,
        bottom=res["bottom"] / h,
        top=res["top"] / h,
    )


def _figure_artist_reservations(
    fig: Figure, renderer: Any, fw_px: float, fh_px: float, holder: Any = None
) -> _Sides:
    """Space (in figure fraction) each edge must reserve for fig-level artists.

    ``simple_layout`` sizes the GridSpec from per-*axes* content, so
    figure-level artists — ``fig.suptitle``, ``fig.legend``, ``fig.text``
    — are otherwise invisible to it and end up overlapping the axes once
    the gridspec is pushed flush to the edge. Each such artist is assigned
    to one figure edge (see :func:`_reservation_edge`) and that edge
    reserves the artist's extent so the axes region is pulled in to clear
    it. An artist carrying ``_dm_layout_gap_pt`` (``dm.add_note`` sets the
    preset's ``axes.labelpad``) also reserves that gap between itself and
    the content. Returns the reservation per edge in figure fraction; all
    zero when no figure-level artists are present (so the layout math is
    unchanged in the common case). A SubFigure's own suptitle, texts and
    legends reserve nothing here: they sit in its box, not on the edges of
    the root grid this sizes. A grid held by a SubFigure (``holder``) is
    sized in that SubFigure's box instead (:func:`_holder_reservations`).
    """
    if holder is not None and holder is not fig:
        return _holder_reservations(holder, renderer)
    res_l = res_r = res_b = res_t = 0.0
    for art, ext in iter_figure_level_extents(fig, renderer, subfigures=False):
        if not art.get_in_layout():
            continue
        x0f, x1f = ext.x0 / fw_px, ext.x1 / fw_px
        y0f, y1f = ext.y0 / fh_px, ext.y1 / fh_px
        gap_px = float(getattr(art, "_dm_layout_gap_pt", 0.0)) * fig.dpi / 72.0
        gx, gy = gap_px / fw_px, gap_px / fh_px
        edge = _reservation_edge(fig, art, x0f, x1f, y0f, y1f)
        if edge == "left":
            res_l = max(res_l, x1f + gx)
        elif edge == "right":
            res_r = max(res_r, 1.0 - x0f + gx)
        elif edge == "bottom":
            res_b = max(res_b, y1f + gy)
        else:  # top
            res_t = max(res_t, 1.0 - y0f + gy)
    return _Sides(left=res_l, right=res_r, bottom=res_b, top=res_t)


# Figure text whose centre lies in this outer band of the canvas height
# (horizontal text) or width (vertical text) reserves that band's edge.
# The centre is rebuilt from a pixel bbox, so text placed exactly on the
# boundary lands 1e-16 either side depending on dpi; the tolerance (in
# figure fraction) keeps the boundary inclusive at every dpi.
_EDGE_BAND = 0.15

_EDGE_BAND_TOL = 1e-9

_Edge: TypeAlias = Literal["left", "right", "bottom", "top"]

#: The figure edge each side of a ``dm.figure_legend`` legend reserves.
_SIDE_EDGES: dict[str, _Edge] = {
    "above": "top",
    "below": "bottom",
    "left": "left",
    "right": "right",
}


def _reservation_edge(
    fig: Figure, art: Any, x0f: float, x1f: float, y0f: float, y1f: float
) -> _Edge:
    """Pick the figure edge a figure-level artist reserves space on.

    The nearest edge by distance put a left-aligned suptitle at the
    top-left corner on the *left* edge and pushed the whole grid right.
    So roles come first: the suptitle reserves the top, the sup x/y labels
    the bottom/left, each while it sits on that half of the canvas. Other
    text in an outer ``_EDGE_BAND`` reserves along its reading direction:
    horizontal text (a subtitle, a source note) the top or bottom band,
    vertical text the left or right band. A ``dm.figure_legend`` legend
    reserves the edge it was placed on (``_dm_figure_side``): one almost as
    wide as the figure is nearer its left or right edge than its top.
    Everything else, other legends included, keeps the nearest edge.
    """
    side = getattr(art, "_dm_figure_side", None)
    if isinstance(side, str) and side in _SIDE_EDGES:
        return _SIDE_EDGES[side]
    xc, yc = (x0f + x1f) / 2, (y0f + y1f) / 2
    roles: tuple[tuple[str, _Edge, bool], ...] = (
        ("_suptitle", "top", yc >= 0.5),
        ("_supxlabel", "bottom", yc < 0.5),
        ("_supylabel", "left", xc < 0.5),
    )
    for attr, edge, on_side in roles:
        if on_side and art is getattr(fig, attr, None):
            return edge
    get_rotation = getattr(art, "get_rotation", None)
    if get_rotation is not None:
        vertical = 45.0 <= get_rotation() % 180.0 <= 135.0
        centre = xc if vertical else yc
        if centre <= _EDGE_BAND + _EDGE_BAND_TOL:
            return "left" if vertical else "bottom"
        if centre >= 1.0 - _EDGE_BAND - _EDGE_BAND_TOL:
            return "right" if vertical else "top"
    dists: dict[_Edge, float] = {
        "left": x0f,
        "right": 1.0 - x1f,
        "bottom": y0f,
        "top": 1.0 - y1f,
    }
    return min(dists, key=lambda k: dists[k])
