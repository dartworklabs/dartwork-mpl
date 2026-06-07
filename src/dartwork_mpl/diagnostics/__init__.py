"""Asset diagnostics — visualize registered colormaps, colors, and fonts.

This package houses the four visualization helpers that inspect the
available dartwork-mpl assets:

- :func:`classify_colormap` — categorize a matplotlib colormap.
- :func:`plot_colormaps` — render registered colormaps grouped by type.
- :func:`plot_colors` — render named color libraries (OpenColor,
  Tailwind, Material Design, etc.) as swatch grids.
- :func:`plot_fonts` — render registered font families with weight
  spectrum and pangram samples.

The implementation is split across ``_colormaps`` / ``_colors`` /
``_fonts`` submodules (#235); import from this package (or the top-level
:mod:`dartwork_mpl` namespace) rather than the submodules directly.

These functions used to live in the :mod:`dartwork_mpl.asset_viz`
subpackage. That import path still works but emits a
:class:`DeprecationWarning`.
"""

from __future__ import annotations

from ._colormaps import classify_colormap, plot_colormaps

# Re-exported for backwards compatibility: tests and a few callers import
# this private swatch-grid helper from ``dartwork_mpl.diagnostics``
# directly (it predates the package split, #235).
from ._colors import (
    _plot_single_library,  # noqa: F401  (re-export)
    plot_colors,
)
from ._fonts import plot_fonts

__all__ = ["classify_colormap", "plot_colormaps", "plot_colors", "plot_fonts"]
