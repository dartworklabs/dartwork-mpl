"""Deprecated alias for :mod:`dartwork_mpl.helpers.labels`.

The module was renamed to ``labels`` in the 0.3.x series to avoid a
name clash with the top-level :mod:`dartwork_mpl.formatting` module.
Importing from this path still works but emits a
``DeprecationWarning`` so callers can migrate.
"""

from __future__ import annotations

import warnings

from .labels import optimize_legend

warnings.warn(
    "dartwork_mpl.helpers.formatting is deprecated and will be removed in "
    "v0.6.0; use dartwork_mpl.helpers.labels instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["optimize_legend"]
