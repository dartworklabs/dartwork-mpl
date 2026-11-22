"""Value labels, panel letters and notes.

Public: :func:`label_bars`, :func:`annotate_value`, :func:`label_axes`, :func:`label_line_ends`,
:func:`add_note`, :func:`legible`. Each but ``label_line_ends`` takes the active preset's text
(:class:`PresetText`), and ``label_bars`` how ticks print numbers
(:class:`TickText`); ``compose.labels`` gives them, as ``dm`` exposes them. The layout's hooks (:func:`settle_bars`,
:func:`space_line_ends`, `settle_panels`, :func:`place_notes`) settle them, and :func:`report_bars` / :func:`report_panels` say what that changed at the size ``dm.simple_layout`` fits;
``check`` reads the placed letters from ``geometry.panel_letters``.
"""

from __future__ import annotations

from .alignment import align_texts
from .bar_layout import report_bars, settle_bars
from .bars import label_bars
from .ends import label_line_ends, space_line_ends
from .given import PresetText, TickText
from .legibility import legible
from .letters import label_axes, report_panels, settle_panels
from .notes import add_note, annotate_value, note_gap_pt, place_notes

__all__ = [
    "PresetText",
    "TickText",
    "add_note",
    "align_texts",
    "annotate_value",
    "label_axes",
    "label_bars",
    "label_line_ends",
    "legible",
    "note_gap_pt",
    "place_notes",
    "report_bars",
    "report_panels",
    "settle_bars",
    "settle_panels",
    "space_line_ends",
]
