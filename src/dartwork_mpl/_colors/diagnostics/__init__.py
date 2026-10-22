"""Colour diagnostics: classify colormaps and draw the colour catalogues.

Responsibility: the visual inspection of the shipped colour assets —
classifying a colormap by kind, rendering the registered colormaps grouped
by family, and rendering the registered colour libraries as swatch grids.
``dartwork_mpl.diagnostics`` re-exports this surface publicly.

Surface: ``classify_cmap``, ``render_cmap_catalog``, ``render_color_catalog``.
"""

from ._colormaps import classify_cmap, render_cmap_catalog
from ._colors import render_color_catalog

__all__ = ["classify_cmap", "render_cmap_catalog", "render_color_catalog"]
