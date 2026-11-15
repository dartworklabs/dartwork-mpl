"""Value labels, panel letters and notes.

Public: :func:`label_bars`, :func:`annotate_value`, :func:`annotate_corner`,
:func:`label_hline`, :func:`label_axes`, :func:`label_line_ends`,
:func:`add_note`. The layout's hooks (:func:`settle_bars`,
:func:`space_line_ends`, :func:`settle_panels`, :func:`warn_hidden`) settle them at the size ``dm.simple_layout`` fits;
``check`` reads the placed letters from ``geometry.panel_letters``.
"""

from __future__ import annotations

from .bar_layout import settle_bars
from .bars import label_bars
from .ends import label_line_ends, space_line_ends
from .letters import label_axes, settle_panels
from .notes import (
    add_note,
    annotate_corner,
    annotate_value,
    label_hline,
    note_gap_pt,
)

__all__ = [
    "add_note",
    "annotate_corner",
    "annotate_value",
    "label_axes",
    "label_bars",
    "label_hline",
    "label_line_ends",
    "note_gap_pt",
    "settle_bars",
    "settle_panels",
    "space_line_ends",
]
