"""General-purpose helper utilities for dartwork-mpl.

Composition helpers that sit above the low-level matplotlib and
dartwork-mpl primitives. This module is organised into submodules:

- ``data``: data validation and cleaning.
- ``colors``: palette selection.
- ``labels``: axis-label / legend / value-annotation helpers.
- ``quality``: figure quality checks and chart-type suggestion.
- ``io``: styled figure creation and optimised save.
"""

from .colors import auto_select_colors
from .data import validate_data
from .io import create_figure_with_style, save_figure
from .labels import add_value_labels, format_axis_labels, optimize_legend
from .quality import check_figure_quality, suggest_chart_type

__all__ = [
    # Data validation
    "validate_data",
    # Color utilities
    "auto_select_colors",
    # Formatting utilities
    "format_axis_labels",
    "optimize_legend",
    "add_value_labels",
    # I/O utilities
    "save_figure",
    "create_figure_with_style",
    # Quality checks
    "suggest_chart_type",
    "check_figure_quality",
]
