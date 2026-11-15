"""Short labels at a point, in a corner or on a horizontal line, and the
figure's note line."""

from __future__ import annotations

import itertools
import weakref
from typing import TYPE_CHECKING, Any

import matplotlib as mpl
import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text

from ..style import fs, fw
from . import decide
from .measure import (
    drawn_renderer,
    line_boxes,
    measure_try,
    patch_boxes,
    point_boxes,
    text_boxes,
)
from .model import (
    CORNERS,
    LINE_ENDS,
    SIDES,
    Corner,
    FirstFree,
    HAlign,
    LineAnchor,
    LineSide,
    Side,
    Tries,
    Try,
    VAlign,
    parse_corner,
    parse_line_side,
    parse_line_x,
    parse_side,
)

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.transforms import Bbox

_SIDE_SPECS: dict[Side, tuple[tuple[float, float], HAlign, VAlign]] = {
    "above": ((0.0, 1.0), "center", "bottom"),
    "below": ((0.0, -1.0), "center", "top"),
    "right": ((1.0, 0.0), "left", "center"),
    "left": ((-1.0, 0.0), "right", "center"),
}
# label_hline: the offset's sign off the line, and the alignment facing it.
_LINE_SIDES: dict[LineSide, tuple[float, VAlign]] = {
    "above": (1.0, "bottom"),
    "below": (-1.0, "top"),
}


def _side_offset(
    side: Side, offset_pt: float
) -> tuple[tuple[float, float], HAlign, VAlign]:
    (dx, dy), ha, va = _SIDE_SPECS[side]
    return (dx * offset_pt, dy * offset_pt), ha, va


def _put(
    ann: Annotation,
    xyann: tuple[float, float],
    ha: HAlign,
    va: VAlign | None = None,
) -> None:
    ann.xyann = xyann
    ann.set_horizontalalignment(ha)
    if va is not None:
        ann.set_verticalalignment(va)


def _obstacles(
    ax: Axes, texts: list[Text], renderer: RendererBase, lines: bool = True
) -> list[Bbox]:
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
    asked = parse_side(side)
    kw.setdefault("fontweight", kw.pop("weight", fw(1)))
    existing = list(ax.texts)
    first: Side = "above" if isinstance(asked, FirstFree) else asked
    offset, ha, va = _side_offset(first, float(offset_pt))
    ann = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
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
    if not isinstance(asked, FirstFree):
        return ann
    renderer = drawn_renderer(ax)
    frame = ax.get_window_extent(renderer)
    obstacles = _obstacles(ax, existing, renderer)
    tries: list[Try] = []
    for candidate in SIDES:
        _put(ann, *_side_offset(candidate, float(offset_pt)))
        tries.append(
            measure_try(ann.get_window_extent(renderer), frame, obstacles)
        )
    chosen = SIDES[decide.value_side(Tries(tuple(tries))).index]
    _put(ann, *_side_offset(chosen, float(offset_pt)))
    return ann


_CORNER_SPECS: dict[
    Corner, tuple[tuple[float, float], tuple[float, float], HAlign, VAlign]
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
    corner = parse_corner(loc)
    existing = list(ax.texts)
    anchor, (dx, dy), ha, va = _CORNER_SPECS[corner]
    ann = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
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
    i = CORNERS.index(corner)
    order = (corner, *CORNERS[:i], *CORNERS[i + 1 :])
    tries: list[Try] = []
    for candidate in order:
        _corner(ann, candidate, float(inset_pt))
        tries.append(
            measure_try(ann.get_window_extent(renderer), frame, obstacles)
        )
    _corner(
        ann,
        order[decide.first_free(Tries(tuple(tries))).index],
        float(inset_pt),
    )
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
    ax: Axes, y: float, x: LineAnchor | float, renderer: RendererBase
) -> tuple[float, HAlign]:
    """The data x and alignment for anchor ``x`` on the line at ``y``."""
    left, right = _hline_span(ax, y, renderer)
    ha: HAlign
    if not isinstance(x, str):
        frame = ax.get_window_extent(renderer)
        shown, ha = frame.x0 + frame.width * float(x), "center"
    else:
        ends: dict[LineAnchor, float] = {
            "left": left,
            "right": right,
            "center": (left + right) / 2,
        }
        shown, ha = ends[x], x
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
    toward, va = _LINE_SIDES[parse_line_side(side)]
    anchor = parse_line_x(x)
    existing = list(ax.texts)
    renderer = drawn_renderer(ax)
    first: LineAnchor | float = (
        LINE_ENDS[0] if isinstance(anchor, FirstFree) else anchor
    )
    x_pos, ha = _hline_x(ax, y, first, renderer)
    ann = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
        text,
        xy=(x_pos, y),
        xycoords="data",
        xytext=(0.0, toward * float(gap_pt)),
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", va),
        fontsize=fs(-2) if fontsize is None else fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )
    if not isinstance(anchor, FirstFree):
        return ann
    frame = ax.get_window_extent(renderer)
    obstacles = _obstacles(ax, existing, renderer, lines=False)
    tries: list[Try] = []
    for end in LINE_ENDS:
        x_pos, ha = _hline_x(ax, y, end, renderer)
        ann.xy = (x_pos, y)
        ann.set_horizontalalignment(ha)
        tries.append(
            measure_try(ann.get_window_extent(renderer), frame, obstacles)
        )
    x_pos, ha = _hline_x(
        ax, y, LINE_ENDS[decide.first_free(Tries(tuple(tries))).index], renderer
    )
    ann.xy = (x_pos, y)
    ann.set_horizontalalignment(ha)
    return ann


def add_note(fig: Figure, text: str, **kw: Any) -> Text:
    """A source or note line at the figure's lower left, ``dm.fs(-1)``.

    ``dm.simple_layout`` keeps the plot above it, ``axes.labelpad`` apart::

        dm.add_note(fig, "Source: internal web logs")
    """
    style: dict[str, Any] = {"ha": "left", "va": "bottom", "fontsize": fs(-1)}
    note = fig.text(0.0, 0.0, text, **{**style, **kw})  # pyright: ignore[reportUnknownMemberType]
    _NOTE_GAPS[note] = float(mpl.rcParams["axes.labelpad"])
    return note


#: The gap (pt) ``simple_layout`` reserves above each ``add_note`` line.
_NOTE_GAPS: weakref.WeakKeyDictionary[Text, float] = weakref.WeakKeyDictionary()


def note_gap_pt(artist: object) -> float | None:
    """The gap (pt) the layout keeps above an ``add_note`` line, else ``None``."""
    return _NOTE_GAPS.get(artist) if isinstance(artist, Text) else None
