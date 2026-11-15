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
    "figure_legend",
    "optimize_legend",
    "place_legend",
    "settle_figure_legends",
    "settle_legends",
]

from ._figure_legend import figure_legend, settle_figure_legends
from ._legend_settle import settle_legends
from ._optimize_legend import optimize_legend
from ._place_legend import place_legend
