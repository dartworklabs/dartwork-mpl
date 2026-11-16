"""Value labels, panel letters and notes.

Public: :func:`label_bars`, :func:`annotate_value`, :func:`label_axes`, :func:`label_line_ends`,
:func:`add_note`. Each but ``label_line_ends`` takes the active preset's text
(:class:`PresetText`), and ``label_bars`` how ticks print numbers
(:class:`TickText`); ``compose.labels`` gives them, as ``dm`` exposes them. The layout's hooks (:func:`settle_bars`,
:func:`space_line_ends`, :func:`settle_panels`) settle them at the size ``dm.simple_layout`` fits;
``check`` reads the placed letters from ``geometry.panel_letters``.
"""

from __future__ import annotations

from .bar_layout import report_bars, settle_bars
from .bars import label_bars
from .ends import label_line_ends, space_line_ends
from .given import PresetText, TickText
from .letters import label_axes, settle_panels
from .notes import add_note, annotate_value, note_gap_pt

__all__ = [
    "PresetText",
    "TickText",
    "add_note",
    "annotate_value",
    "label_axes",
    "label_bars",
    "label_line_ends",
    "note_gap_pt",
    "report_bars",
    "settle_bars",
    "settle_panels",
    "space_line_ends",
]
