"""Asset diagnostics for registered colormaps, colors, and fonts.

This package houses visualization helpers that inspect the available
dartwork-mpl assets:

- :func:`classify_cmap` — categorize a matplotlib colormap.
- :func:`render_cmap_catalog` — render registered colormaps grouped by type.
- :func:`render_color_catalog` — render named color libraries as swatch grids.
- :func:`plot_fonts` — render registered font families with weight
  spectrum and pangram samples.

This package is the public entry point: the colour diagnostics live in
the colour slice (``dartwork_mpl._colors.diagnostics``) and are
re-exported here; the font preview lives in ``_fonts``.

These functions used to live in the ``dartwork_mpl.asset_viz``
subpackage; that import path was removed in 0.5.4.
"""

from __future__ import annotations

from .._colors.diagnostics import (
    classify_cmap,
    render_cmap_catalog,
    render_color_catalog,
)
from ._fonts import plot_fonts

__all__ = [
    "classify_cmap",
    "plot_fonts",
    "render_cmap_catalog",
    "render_color_catalog",
]
