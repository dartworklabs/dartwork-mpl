"""Asset diagnostics for registered colormaps, colors, and fonts.

This package houses visualization helpers that inspect the available
dartwork-mpl assets:

- :func:`classify_cmap` — categorize a matplotlib colormap.
- :func:`render_cmap_catalog` — render registered colormaps grouped by type.
- :func:`render_color_catalog` — render named color libraries as swatch grids.
- :func:`plot_fonts` — render registered font families with weight
  spectrum and pangram samples.

The implementation is split across ``_colormaps`` / ``_colors`` /
``_fonts`` submodules (#235).

These functions used to live in the ``dartwork_mpl.asset_viz``
subpackage; that import path was removed in 0.5.4.
"""

from __future__ import annotations

from ._colormaps import classify_cmap, render_cmap_catalog

# Re-exported for backwards compatibility: tests and a few callers import
# this private swatch-grid helper from ``dartwork_mpl.diagnostics``
# directly (it predates the package split, #235).
from ._colors import (
    _plot_single_library,  # noqa: F401  (re-export)
    render_color_catalog,
)
from ._fonts import plot_fonts

__all__ = [
    "classify_cmap",
    "plot_fonts",
    "render_cmap_catalog",
    "render_color_catalog",
]
