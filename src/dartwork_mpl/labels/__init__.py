"""Value labels, line-end names and panel letters: the hooks ``simple_layout`` calls.

Today these delegate to ``annotation``; the ``labels`` slice rebuild
replaces the bodies in ``apply`` and keeps the signatures, so ``layout``
does not change when it lands.
"""

from __future__ import annotations

from .apply import (
    hide_covered,
    settle_bars,
    settle_panels,
    space_line_ends,
    warn_hidden,
)

__all__ = [
    "hide_covered",
    "settle_bars",
    "settle_panels",
    "space_line_ends",
    "warn_hidden",
]
