"""Quality checks and chart type suggestions for dartwork-mpl agents.

This module provides functions for checking figure quality and
suggesting appropriate chart types based on data characteristics.
Native quality diagnostics are compatibility aliases of the validate owner.
"""

from __future__ import annotations

from ..recommend import suggest_chart_type as suggest_chart_type
from ..validate import MIN_RECOMMENDED_DPI, check_figure_quality

__all__ = ["MIN_RECOMMENDED_DPI", "check_figure_quality", "suggest_chart_type"]
