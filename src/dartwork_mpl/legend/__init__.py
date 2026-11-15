"""Legend placement: the hooks ``simple_layout`` calls.

Today these delegate to ``annotation`` and the platform's outside anchor;
the ``legend`` slice rebuild replaces the bodies in ``apply`` and keeps the
signatures, so ``layout`` does not change when it lands.
"""

from __future__ import annotations

from .apply import outside_side, place_figure_legends, settle

__all__ = ["outside_side", "place_figure_legends", "settle"]
