"""Colour verification: gate and compare a compiled catalogue.

Responsibility: judge a ``CatalogSnapshot`` against the frozen quality
baseline (gates) and against the frozen v5 catalogue (exact and quality
comparison, HTML report), scoring with the independent oracle in
``_colors/_compatibility_metrics.py``, whose path and bytes are pinned by the
shipped authority. It never imports the colour model, so the oracle stays
independent of the code it grades.

Surface: ``evaluate_catalog``, ``load_quality_baseline``, ``GateReport``,
``compare_exact_surfaces``, ``compare_catalog``, ``render_comparison_html``.
"""

from ._comparison import (
    compare_catalog,
    compare_exact_surfaces,
    render_comparison_html,
)
from ._gates import GateReport, evaluate_catalog, load_quality_baseline

__all__ = [
    "GateReport",
    "compare_catalog",
    "compare_exact_surfaces",
    "evaluate_catalog",
    "load_quality_baseline",
    "render_comparison_html",
]
