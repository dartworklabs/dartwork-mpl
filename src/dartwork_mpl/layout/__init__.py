"""Layout utilities for Matplotlib figures.

Provides ``simple_layout`` — a deterministic, content-aware GridSpec
layout. It measures the union extent of every visible artist on each
axes (texts, title, axis labels, view-limited tick labels, axis
offset text, legend) and arithmetically computes GridSpec edges that
place that union extent at the requested distance from each figure
edge. No optimizer is involved.
"""

from __future__ import annotations

__all__ = [
    "adopt_axis_label_font",
    "get_bounding_box",
    "simple_layout",
    "tight_crop",
]

from ._crop import get_bounding_box, tight_crop
from ._orphan_tick_font import adopt_axis_label_font
from ._simple_layout import simple_layout
