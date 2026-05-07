"""General-purpose helper utilities for dartwork-mpl.

Composition helpers that sit above the low-level matplotlib and
dartwork-mpl primitives. This module is organised into submodules:

- ``data``: data validation and cleaning.
- ``colors``: palette selection.
- ``labels``: axis-label / legend / value-annotation helpers.
- ``quality``: figure quality checks and chart-type suggestion.
- ``io``: styled figure creation and optimised save.
"""

from .colors import make_palette
from .data import validate_data
from .labels import optimize_legend
from .quality import check_figure_quality, suggest_chart_type

__all__ = [
    "check_figure_quality",
    "make_palette",
    "optimize_legend",
    "suggest_chart_type",
    "validate_data",
]
