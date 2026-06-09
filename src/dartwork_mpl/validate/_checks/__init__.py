"""Individual visual-validation checks.

Each module exposes one ``check_<name>(fig, renderer)`` (or
``check_<name>(fig)`` for the no-renderer ones) returning
``list[VisualWarning]``. The orchestrator in
:mod:`dartwork_mpl.validate._orchestrator` builds the public
``validate_figure`` from this registry.

Public re-exports keep the internal ``_check_*`` names available for
backwards compatibility with code that imported them directly.
"""

from __future__ import annotations

from .clipped_text import check_clipped_text
from .cross_axes import check_cross_axes_overlap
from .empty_axes import check_empty_axes
from .legend import check_legend_overflow
from .margin import check_margin_asymmetry
from .overflow import check_overflow
from .overlap import check_overlap
from .pie_label import check_pie_label_offset
from .tick_crowd import check_tick_crowding

__all__ = [
    "check_clipped_text",
    "check_cross_axes_overlap",
    "check_empty_axes",
    "check_legend_overflow",
    "check_margin_asymmetry",
    "check_overflow",
    "check_overlap",
    "check_pie_label_offset",
    "check_tick_crowding",
]
