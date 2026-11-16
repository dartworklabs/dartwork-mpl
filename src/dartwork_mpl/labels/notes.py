"""A short label at a data point, and the figure's note line."""

from __future__ import annotations

import weakref
from typing import TYPE_CHECKING

import matplotlib as mpl
from matplotlib.text import Text

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
from .model import SIDES, Side, Tries, Try

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.text import Annotation

# Between the point and its label, in points.
OFFSET_PT = 3.0


def _put(ann: Annotation, side: Side) -> None:
    dx, dy = side.offset
    ann.xyann = (dx * OFFSET_PT, dy * OFFSET_PT)
    ann.set_horizontalalignment(side.ha.mpl)
    ann.set_verticalalignment(side.va.mpl)


def annotate_value(
    ax: Axes, x: float, y: float, text: str, *, preset: PresetText
) -> Text:
    """``dm.annotate_value``, its text sized by ``preset``."""
    existing = list(ax.texts)
    ann = ax.annotate(  # pyright: ignore[reportUnknownMemberType]
        text,
        xy=(x, y),
        xycoords="data",
        xytext=(0.0, OFFSET_PT),
        textcoords="offset points",
        annotation_clip=False,
        fontsize=preset.size(-1),
        fontweight=preset.weight(1),
    )
    _put(ann, SIDES[0])
    renderer = drawn_renderer(ax)
    frame = ax.get_window_extent(renderer)
    obstacles = [
        *line_boxes(ax),
        *patch_boxes(ax),
        *point_boxes(ax),
        *text_boxes(existing, renderer),
    ]
    tries: list[Try] = []
    for side in SIDES:
        _put(ann, side)
        tries.append(
            measure_try(ann.get_window_extent(renderer), frame, obstacles)
        )
    _put(ann, SIDES[decide.value_side(Tries(tuple(tries))).index])
    return ann


def add_note(fig: Figure, text: str, *, preset: PresetText) -> Text:
    """``dm.add_note``, its text sized by ``preset``."""
    note = fig.text(  # pyright: ignore[reportUnknownMemberType]
        0.0, 0.0, text, ha="left", va="bottom", fontsize=preset.size(-1)
    )
    _NOTE_GAPS[note] = float(mpl.rcParams["axes.labelpad"])
    return note


#: The gap (pt) ``simple_layout`` reserves above each ``add_note`` line.
_NOTE_GAPS: weakref.WeakKeyDictionary[Text, float] = weakref.WeakKeyDictionary()


def note_gap_pt(artist: object) -> float | None:
    """The gap (pt) the layout keeps above an ``add_note`` line, else ``None``."""
    return _NOTE_GAPS.get(artist) if isinstance(artist, Text) else None
