"""Colour families API: ``dm.colors``, ``set_colors``, ``list_colors``, ``show_colors``.

Responsibility: resolve a family or palette name to colours, a colormap or
a cycler, list and show the families. Re-exported unchanged by
``dartwork_mpl._colors`` and ``dartwork_mpl``.

Surface: ``colors``, ``set_colors``, ``list_colors``, ``show_colors``.
"""

from ._api import colors, list_colors, set_colors, show_colors

__all__ = ["colors", "list_colors", "set_colors", "show_colors"]
