"""Agent utility functions for dartwork-mpl.

Helper functions to assist AI agents in creating consistent,
high-quality visualizations.

This module is organized into submodules:
- data: Data validation and cleaning
- colors: Color selection and management
- formatting: Axis labels, legends, and annotations
- quality: Quality checks and suggestions
- io: Figure creation and saving
"""

from .colors import auto_select_colors
from .data import validate_data
from .formatting import add_value_labels, format_axis_labels, optimize_legend
from .io import create_figure_with_style, save_figure
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
