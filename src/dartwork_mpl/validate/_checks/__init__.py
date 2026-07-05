"""Individual visual-validation checks.

Each module exposes one ``check_<name>(fig, renderer)`` returning
``list[VisualWarning]`` and self-registers with ``@register_check`` (see
:mod:`._registry`). The orchestrator in
:mod:`dartwork_mpl.validate._orchestrator` iterates ``registered_checks()``
rather than a hand-maintained dict, so a new check cannot drift out of
sync with the orchestrator.

Importing this package runs every check module, which is what populates
the registry — so ``from ._checks import registered_checks`` is enough to
have all checks available.

Public re-exports keep the ``check_*`` names available for backwards
compatibility with code that imported them directly.
"""

from __future__ import annotations

from ._registry import RegisteredCheck, register_check, registered_checks
from .clipped_text import check_clipped_text
from .cross_axes import check_cross_axes_overlap
from .empty_axes import check_empty_axes
from .grayscale_safety import check_grayscale_safety
from .legend import check_legend_overflow
from .margin import check_margin_asymmetry
from .min_font_size import check_min_font_size
from .overflow import check_overflow
from .overlap import check_overlap
from .pie_label import check_pie_label_offset
from .text_contrast import check_text_contrast
from .tick_crowd import check_tick_crowding

__all__ = [
    "RegisteredCheck",
    "check_clipped_text",
    "check_cross_axes_overlap",
    "check_empty_axes",
    "check_grayscale_safety",
    "check_legend_overflow",
    "check_margin_asymmetry",
    "check_min_font_size",
    "check_overflow",
    "check_overlap",
    "check_pie_label_offset",
    "check_text_contrast",
    "check_tick_crowding",
    "register_check",
    "registered_checks",
]
