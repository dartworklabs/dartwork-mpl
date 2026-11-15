"""Short labels at a point, in a corner or on a horizontal line, and the
figure's note line."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any

import matplotlib as mpl
import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text

from ..scale import fs, fw
from . import decide
from .measure import (
    drawn_renderer,
    line_boxes,
    measure_try,
    patch_boxes,
    point_boxes,
    text_boxes,
)
from .model import CORNERS, SIDES, Corner, Side, Tries

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

# Between a bar end (a point) and its label, in points.
OFFSET_PT = 3.0
# How far (px) an anchor may sit past the view and still show.
EDGE_TOL_PX = 1.0
# How far (px) a label on its bar may reach past the bar's sides.
FIT_TOL_PX = 0.5
# Clear space between neighbouring bar labels, in points.
GAP_PT = 1.5
FAMILIES_ATTR = "_dm_bar_labels"
LINE_ENDS_ATTR = "_dm_line_end_labels"


# ------------------------------------------------------------ point labels
def _side_offset(
    side: Side, offset_pt: float
) -> tuple[tuple[float, float], str, str]:
    return {
        "above": ((0.0, offset_pt), "center", "bottom"),
        "below": ((0.0, -offset_pt), "center", "top"),
        "right": ((offset_pt, 0.0), "left", "center"),
        "left": ((-offset_pt, 0.0), "right", "center"),
    }[side]


def _put(
    ann: Annotation, xyann: tuple[float, float], ha: str, va: str | None = None
) -> None:
    ann.xyann = xyann
    ann.set_horizontalalignment(ha)
    if va is not None:
        ann.set_verticalalignment(va)


def _obstacles(
    ax: Axes, texts: list[Text], renderer: RendererBase, lines: bool = True
) -> list[Any]:
    found = line_boxes(ax) if lines else []
    return [
        *found,
        *patch_boxes(ax),
        *point_boxes(ax),
        *text_boxes(texts, renderer),
    ]


def annotate_value(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    *,
    side: str = "auto",
    offset_pt: float = 3.0,
    fontsize: float | None = None,
    **kw: Any,
) -> Text:
    """Label one data value, ``offset_pt`` points from its point.

    ``side="auto"`` takes the first of above, below, right, left that stays
    inside the axes clear of the data and other text; else the least
    covered side inside the axes. A label that would leave the axes above
    its point moves sideways rather than below. ``dm.fs(-1)`` text, one
    weight step heavier (``dm.fw(1)``); keywords go to ``ax.annotate``.
    """
    if side not in ("auto", *SIDES):
        raise ValueError(
            "side must be 'auto', 'above', 'below', 'left', or 'right'"
        )
    kw.setdefault("fontweight", kw.pop("weight", fw(1)))
    existing = list(ax.texts)
    offset, ha, va = _side_offset(
        "above" if side == "auto" else side, float(offset_pt)
    )  # type: ignore[arg-type]
    ann = ax.annotate(
        text,
        xy=(x, y),
        xycoords="data",
        xytext=offset,
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", va),
        fontsize=fs(-1) if fontsize is None else fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )
    if side != "auto":
        return ann
    renderer = drawn_renderer(ax)
    frame = ax.get_window_extent(renderer)
    obstacles = _obstacles(ax, existing, renderer)
    tries = []
    for candidate in SIDES:
        _put(ann, *_side_offset(candidate, float(offset_pt)))
        tries.append(
            measure_try(ann.get_window_extent(renderer), frame, obstacles)
        )
    chosen = SIDES[decide.value_side(Tries(tuple(tries))).index]
    _put(ann, *_side_offset(chosen, float(offset_pt)))
    return ann


_CORNER_SPECS: dict[
    Corner, tuple[tuple[float, float], tuple[float, float], str, str]
] = {
    "upper left": ((0.0, 1.0), (1.0, -1.0), "left", "top"),
    "upper right": ((1.0, 1.0), (-1.0, -1.0), "right", "top"),
    "lower left": ((0.0, 0.0), (1.0, 1.0), "left", "bottom"),
    "lower right": ((1.0, 0.0), (-1.0, 1.0), "right", "bottom"),
}


def _corner(ann: Annotation, loc: Corner, inset_pt: float) -> None:
    anchor, (dx, dy), ha, va = _CORNER_SPECS[loc]
    ann.xy = anchor
    _put(ann, (dx * inset_pt, dy * inset_pt), ha, va)


def annotate_corner(
    ax: Axes,
    text: str,
    *,
    loc: str = "upper left",
    inset_pt: float = 3.0,
    avoid_overlap: bool = True,
    fontsize: float | None = None,
    **kw: Any,
) -> Text:
    """Narrative text inside an axes corner, ``inset_pt`` points in.

    With ``avoid_overlap`` the first corner clear of the data and other
    text wins, ``loc`` first, then upper left, upper right, lower left,
    lower right. ``dm.fs(-2)`` text; keywords go to ``ax.annotate``.
    """
    if loc not in CORNERS:
        raise ValueError(
            "loc must be 'upper left', 'upper right', 'lower left', or 'lower right'"
        )
    existing = list(ax.texts)
    anchor, (dx, dy), ha, va = _CORNER_SPECS[loc]  # type: ignore[index]
    ann = ax.annotate(
        text,
        xy=anchor,
        xycoords="axes fraction",
        xytext=(dx * float(inset_pt), dy * float(inset_pt)),
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", va),
        fontsize=fs(-2) if fontsize is None else fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )
    if not avoid_overlap:
        return ann
    renderer = drawn_renderer(ax)
    frame = ax.get_window_extent(renderer)
    obstacles = _obstacles(ax, existing, renderer)
    order = [loc, *(c for c in CORNERS if c != loc)]
    tries = []
    for candidate in order:
        _corner(ann, candidate, float(inset_pt))  # type: ignore[arg-type]
        tries.append(
            measure_try(ann.get_window_extent(renderer), frame, obstacles)
        )
    _corner(
        ann,
        order[decide.first_free(Tries(tuple(tries))).index],
        float(inset_pt),
    )  # type: ignore[arg-type]
    return ann


def _hline_span(
    ax: Axes, y: float, renderer: RendererBase
) -> tuple[float, float]:
    """The display x extent of the visible horizontal line at ``y`` (2 px
    slack), or the axes' width when no line is drawn there."""
    frame = ax.get_window_extent(renderer)
    target = ax.transData.transform((ax.get_xlim()[0], y))[1]
    xs: list[float] = []
    for line in ax.lines:
        xy = np.asarray(line.get_xydata(), dtype=float)
        if not line.get_visible() or len(xy) < 2:
            continue
        points = line.get_transform().transform(xy)
        points = points[np.isfinite(points).all(axis=1)]
        for a, b in itertools.pairwise(points):
            if abs(a[1] - target) <= 2.0 and abs(b[1] - target) <= 2.0:
                x0, x1 = (
                    max(min(a[0], b[0]), frame.x0),
                    min(max(a[0], b[0]), frame.x1),
                )
                if x1 >= x0:
                    xs += [float(x0), float(x1)]
    return (min(xs), max(xs)) if xs else (frame.x0, frame.x1)


def _hline_x(
    ax: Axes, y: float, x: str | float, renderer: RendererBase
) -> tuple[float, str]:
    """The data x and alignment for anchor ``x`` on the line at ``y``."""
    left, right = _hline_span(ax, y, renderer)
    if isinstance(x, str):
        shown, ha = {
            "left": (left, "left"),
            "right": (right, "right"),
            "center": ((left + right) / 2, "center"),
        }[x]
    else:
        frame = ax.get_window_extent(renderer)
        shown, ha = frame.x0 + frame.width * float(x), "center"
    display_y = ax.transData.transform((ax.get_xlim()[0], y))[1]
    return float(ax.transData.inverted().transform((shown, display_y))[0]), ha


def label_hline(
    ax: Axes,
    y: float,
    text: str,
    *,
    x: str | float = "right",
    side: str = "above",
    gap_pt: float = 2.0,
    fontsize: float | None = None,
    **kw: Any,
) -> Text:
    """A label against the horizontal line at ``y``, ``gap_pt`` points off it.

    ``x``: the drawn line's ``"right"`` / ``"left"`` end or ``"center"``, an
    axes fraction, or ``"auto"`` (the clearer end). ``dm.fs(-2)`` text.
    """
    if side not in ("above", "below"):
        raise ValueError("side must be 'above' or 'below'")
    if isinstance(x, str) and x not in ("auto", "left", "center", "right"):
        raise ValueError(
            "x must be 'auto', 'left', 'center', 'right', or a float"
        )
    existing = list(ax.texts)
    renderer = drawn_renderer(ax)
    x_pos, ha = _hline_x(ax, y, "right" if x == "auto" else x, renderer)
    ann = ax.annotate(
        text,
        xy=(x_pos, y),
        xycoords="data",
        xytext=(0.0, float(gap_pt) if side == "above" else -float(gap_pt)),
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", "bottom" if side == "above" else "top"),
        fontsize=fs(-2) if fontsize is None else fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )
    if x != "auto":
        return ann
    frame = ax.get_window_extent(renderer)
    obstacles = _obstacles(ax, existing, renderer, lines=False)
    ends = ("right", "left")
    tries = []
    for end in ends:
        x_pos, ha = _hline_x(ax, y, end, renderer)
        ann.xy = (x_pos, y)
        ann.set_horizontalalignment(ha)
        tries.append(
            measure_try(ann.get_window_extent(renderer), frame, obstacles)
        )
    x_pos, ha = _hline_x(
        ax, y, ends[decide.first_free(Tries(tuple(tries))).index], renderer
    )
    ann.xy = (x_pos, y)
    ann.set_horizontalalignment(ha)
    return ann


# ------------------------------------------------------------ note
def add_note(fig: Figure, text: str, **kw: Any) -> Text:
    """A source or note line at the figure's lower left, ``dm.fs(-1)``.

    ``dm.simple_layout`` keeps the plot above it, ``axes.labelpad`` apart::

        dm.add_note(fig, "Source: internal web logs")
    """
    note = fig.text(
        0.0,
        0.0,
        text,
        **{"ha": "left", "va": "bottom", "fontsize": fs(-1), **kw},
    )
    # simple_layout reserves this gap above the note (the layout reads it).
    note._dm_layout_gap_pt = float(mpl.rcParams["axes.labelpad"])  # type: ignore[attr-defined]
    return note
