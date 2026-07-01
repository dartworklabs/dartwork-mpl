"""General-purpose helper utilities for dartwork-mpl.

Composition helpers that sit above the low-level matplotlib and
dartwork-mpl primitives. This module is organised into submodules:

- ``data``: data validation and cleaning.
- ``colors``: palette selection.
- ``labels``: axis-label / legend / value-annotation helpers.
- ``quality``: figure quality checks and chart-type suggestion.
"""

from .colors import get_palette, make_palette, set_cycle
from .data import validate_data
from .labels import optimize_legend
from .quality import check_figure_quality, suggest_chart_type

__all__ = [
    "check_figure_quality",
    "get_palette",
    "make_palette",
    "optimize_legend",
    "set_cycle",
    "suggest_chart_type",
    "validate_data",
]
