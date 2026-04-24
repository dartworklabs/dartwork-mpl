"""Deprecated alias for :mod:`dartwork_mpl.diagnostics`.

The four asset-inspection helpers (``classify_colormap``,
``plot_colormaps``, ``plot_colors``, ``plot_fonts``) moved to the
top-level :mod:`dartwork_mpl.diagnostics` module in v0.3.x as the
final step of the v0.2.0 folder restructuring (see issue #57).
Importing from this path still works but emits a
``DeprecationWarning`` so callers can migrate.
"""

from __future__ import annotations

import warnings

from ..diagnostics import (
    classify_colormap,
    plot_colormaps,
    plot_colors,
    plot_fonts,
)

warnings.warn(
    "dartwork_mpl.asset_viz is deprecated; import from "
    "dartwork_mpl.diagnostics (or the top-level dartwork_mpl "
    "namespace) instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["classify_colormap", "plot_colormaps", "plot_colors", "plot_fonts"]
