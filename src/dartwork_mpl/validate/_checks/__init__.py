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

The ``check_*`` functions are not re-exported here: they are reached
through ``registered_checks()`` or their own module. The module imports
below exist only for their registration side effect.
"""

from __future__ import annotations

from . import (  # noqa: F401  (imported to register their checks and fixes)
    clipped_text,
    cross_axes,
    empty_axes,
    grayscale_safety,
    legend,
    legend_on_data,
    legend_overlap,
    margin,
    min_font_size,
    overflow,
    overlap,
    pie_label,
    preset_override,
    slide_oversize,
    text_contrast,
    tick_corner,
    tick_crowd,
    tick_decimal,
    tick_overlap,
    tick_rotation,
    unit_dup,
    value_label_decimal,
    value_label_on_data,
)
from ._registry import RegisteredCheck, register_check, registered_checks

__all__ = ["RegisteredCheck", "register_check", "registered_checks"]
