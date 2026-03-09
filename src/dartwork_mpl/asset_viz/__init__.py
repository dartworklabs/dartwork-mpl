"""Asset visualization subpackage for dartwork-mpl.

This package provides functions to visualize available colormaps,
colors, and fonts in the matplotlib/dartwork-mpl ecosystem.

Re-exports
----------
classify_colormap : from ._cmap
    Classify a colormap by type.
plot_colormaps : from ._cmap
    Plot colormaps grouped by type.
plot_colors : from ._color
    Plot named color libraries.
plot_fonts : from ._font
    Plot available font families.
"""

from ._cmap import classify_colormap, plot_colormaps
from ._color import plot_colors
from ._font import plot_fonts

__all__ = ["classify_colormap", "plot_colormaps", "plot_colors", "plot_fonts"]
