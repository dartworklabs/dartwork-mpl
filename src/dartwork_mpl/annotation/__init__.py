"""Axes-based annotation helper module.

Provides ``label_axes`` for adding standard alphabetic sub-labels to figure
panels, ``annotate_value`` / ``annotate_corner`` / ``label_hline`` for compact
in-axes labels, ``label_bars`` for value labels on bars, ``place_legend`` for
axes legends, ``figure_legend`` for one legend for every panel, and
``arrow_axis`` for drawing bidirectional Low-High arrow axes. ``settle_bar_labels`` is the layout's pass over the bar labels
(crowding, headroom); ``dm.simple_layout`` runs it, then
``warn_hidden_bar_labels`` once its fit is done. ``settle_legends`` is the
layout's pass over ``place_legend``'s legends at the size it settles on;
``settle_figure_legends`` puts a SubFigure's ``figure_legend`` legend past
that SubFigure's title once the layout has placed it.
"""

from __future__ import annotations

__all__ = [
    "add_note",
    "annotate_corner",
    "annotate_value",
    "arrow_axis",
    "bar_values_past_limits",
    "clear_bar_labels",
    "figure_legend",
    "label_axes",
    "label_bars",
    "label_hline",
    "label_line_ends",
    "make_offset",
    "optimize_legend",
    "place_legend",
    "settle_bar_labels",
    "settle_figure_legends",
    "settle_legends",
    "warn_hidden_bar_labels",
    "wrap_axis_label",
    "wrap_axis_labels",
]

from ._axis_labels import arrow_axis, wrap_axis_label, wrap_axis_labels
from ._bar_label_settle import (
    bar_values_past_limits,
    clear_bar_labels,
    settle_bar_labels,
    warn_hidden_bar_labels,
)
from ._bar_labels import label_bars
from ._figure_legend import figure_legend, settle_figure_legends
from ._figure_text import add_note, make_offset
from ._legend_settle import settle_legends
from ._line_end_labels import label_line_ends
from ._optimize_legend import optimize_legend
from ._panel_labels import label_axes
from ._place_legend import place_legend
from ._point_labels import HorizontalAlign as HorizontalAlign
from ._point_labels import VerticalAlign as VerticalAlign
from ._point_labels import annotate_corner, annotate_value, label_hline
