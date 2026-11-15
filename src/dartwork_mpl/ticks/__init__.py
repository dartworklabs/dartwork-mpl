"""Tick numbers and dates: the hooks ``simple_layout`` calls.

Today these delegate to ``formatting``; the ``ticks`` slice rebuild replaces
the bodies in ``apply`` and keeps the signatures, so ``layout`` does not
change when it lands.
"""

from __future__ import annotations

from .apply import prepare, remember_dates, thin_dates

__all__ = ["prepare", "remember_dates", "thin_dates"]
