"""Short labels at a point, in a corner or on a horizontal line, and the
figure's note line."""

from __future__ import annotations

import itertools
import weakref
from typing import TYPE_CHECKING, Unpack

import matplotlib as mpl
import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text

from ..align import HAlign
from . import decide
from .given import PresetText
from .measure import (
    drawn_renderer,
    line_boxes,
    measure_try,
    patch_boxes,
    point_boxes,
    text_boxes,
)
from .model import (
    Corner,
    LinePlace,
    NoteStyle,
    Side,
    Span,
    TextStyle,
    Tries,
    Try,
    VAlign,
    corner_order,
    parse_corner,
    parse_line_side,
    parse_line_x,
    parse_side,
)

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.transforms import Bbox


def _side_offset(side: Side, offset_pt: float) -> tuple[float, float]:
    dx, dy = side.offset
    return dx * offset_pt, dy * offset_pt


def _put(
    ann: Annotation,
    xyann: tuple[float, float],
    ha: HAlign,
    va: VAlign | None = None,
) -> None:
    ann.xyann = xyann
    ann.set_horizontalalignment(ha.mpl)
    if va is not None:
        ann.set_verticalalignment(va.mpl)


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
    preset: PresetText,
    **kw: Unpack[NoteStyle],
) -> Text:
    """``dm.annotate_value``, its text sized by ``preset``."""
    sides = parse_side(side).tries
    existing = list(ax.texts)
    first = sides[0]
    style = (
        NoteStyle(
            ha=first.ha.mpl,
            va=first.va.mpl,
            annotation_clip=False,
            fontweight=kw.pop("weight", preset.weight(1)),
        )
        | kw
    )
    ann = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
        text,
        xy=(x, y),
        xycoords="data",
        xytext=_side_offset(first, float(offset_pt)),
        textcoords="offset points",
        fontsize=preset.size(-1) if fontsize is None else fontsize,
        **style,
    )
    if len(sides) < 2:
        return ann
    renderer = drawn_renderer(ax)
    frame = ax.get_window_extent(renderer)
    obstacles = _obstacles(ax, existing, renderer)
    tries: list[Try] = []
    for candidate in sides:
        _put(
            ann,
            _side_offset(candidate, float(offset_pt)),
            candidate.ha,
            candidate.va,
        )
        tries.append(
            measure_try(ann.get_window_extent(renderer), frame, obstacles)
        )
    chosen = sides[decide.value_side(Tries(tuple(tries))).index]
    _put(ann, _side_offset(chosen, float(offset_pt)), chosen.ha, chosen.va)
    return ann


def _corner(ann: Annotation, loc: Corner, inset_pt: float) -> None:
    dx, dy = loc.inward
    ann.xy = loc.anchor
    _put(ann, (dx * inset_pt, dy * inset_pt), loc.ha, loc.va)


def annotate_corner(
    ax: Axes,
    text: str,
    *,
    loc: str = "upper left",
    inset_pt: float = 3.0,
    avoid_overlap: bool = True,
    fontsize: float | None = None,
    preset: PresetText,
    **kw: Unpack[NoteStyle],
) -> Text:
    """``dm.annotate_corner``, its text sized by ``preset``."""
    corner = parse_corner(loc)
    existing = list(ax.texts)
    dx, dy = corner.inward
    ann = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
        text,
        xy=corner.anchor,
        xycoords="axes fraction",
        xytext=(dx * float(inset_pt), dy * float(inset_pt)),
        textcoords="offset points",
        fontsize=preset.size(-2) if fontsize is None else fontsize,
        **(
            NoteStyle(ha=corner.ha.mpl, va=corner.va.mpl, annotation_clip=False)
            | kw
        ),
    )
    if not avoid_overlap:
        return ann
    renderer = drawn_renderer(ax)
    frame = ax.get_window_extent(renderer)
    obstacles = _obstacles(ax, existing, renderer)
    order = corner_order(corner)
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


def _hline_x(ax: Axes, y: float, x: LinePlace, renderer: RendererBase) -> float:
    """The data x of place ``x`` on the line at ``y``."""
    left, right = _hline_span(ax, y, renderer)
    frame = ax.get_window_extent(renderer)
    shown = x.shown(left, right, Span(float(frame.x0), float(frame.x1)))
    display_y = ax.transData.transform((ax.get_xlim()[0], y))[1]
    return float(ax.transData.inverted().transform((shown, display_y))[0])


def label_hline(
    ax: Axes,
    y: float,
    text: str,
    *,
    x: str | float = "right",
    side: str = "above",
    gap_pt: float = 2.0,
    fontsize: float | None = None,
    preset: PresetText,
    **kw: Unpack[NoteStyle],
) -> Text:
    """``dm.label_hline``, its text sized by ``preset``."""
    off = parse_line_side(side)
    places = parse_line_x(x).tries
    existing = list(ax.texts)
    renderer = drawn_renderer(ax)
    first = places[0]
    ann = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
        text,
        xy=(_hline_x(ax, y, first, renderer), y),
        xycoords="data",
        xytext=(0.0, off.offset[1] * float(gap_pt)),
        textcoords="offset points",
        fontsize=preset.size(-2) if fontsize is None else fontsize,
        **(
            NoteStyle(ha=first.ha.mpl, va=off.va.mpl, annotation_clip=False)
            | kw
        ),
    )
    if len(places) < 2:
        return ann
    frame = ax.get_window_extent(renderer)
    obstacles = _obstacles(ax, existing, renderer, lines=False)
    tries: list[Try] = []
    for end in places:
        ann.xy = (_hline_x(ax, y, end, renderer), y)
        ann.set_horizontalalignment(end.ha.mpl)
        tries.append(
            measure_try(ann.get_window_extent(renderer), frame, obstacles)
        )
    chosen = places[decide.first_free(Tries(tuple(tries))).index]
    ann.xy = (_hline_x(ax, y, chosen, renderer), y)
    ann.set_horizontalalignment(chosen.ha.mpl)
    return ann


def add_note(
    fig: Figure, text: str, *, preset: PresetText, **kw: Unpack[TextStyle]
) -> Text:
    """``dm.add_note``, its text sized by ``preset``."""
    style = TextStyle(ha="left", va="bottom", fontsize=preset.size(-1)) | kw
    note = fig.text(0.0, 0.0, text, **style)  # pyright: ignore[reportUnknownMemberType]
    _NOTE_GAPS[note] = float(mpl.rcParams["axes.labelpad"])
    return note


#: The gap (pt) ``simple_layout`` reserves above each ``add_note`` line.
_NOTE_GAPS: weakref.WeakKeyDictionary[Text, float] = weakref.WeakKeyDictionary()


def note_gap_pt(artist: object) -> float | None:
    """The gap (pt) the layout keeps above an ``add_note`` line, else ``None``."""
    return _NOTE_GAPS.get(artist) if isinstance(artist, Text) else None
