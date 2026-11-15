"""Short labels at a point, in a corner or on a horizontal line, and the
figure's note line."""

from __future__ import annotations

import weakref
from typing import TYPE_CHECKING, Unpack

import matplotlib as mpl
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text

from ..vocab import HAlign, VAlign
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
from .model import NoteStyle, TextStyle, parse_side
from .places import Side, Tries, Try

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
