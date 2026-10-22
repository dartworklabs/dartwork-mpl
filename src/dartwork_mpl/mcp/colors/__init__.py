"""Colour lookups for the MCP colour tools and palette resource.

``color_value`` resolves a colour name to hex, ``mix`` blends two colours
exactly as ``dm.mix_colors`` does, ``list_families`` summarises the
registered colours per library prefix and ``palette`` lists them all (the
``dartwork-mpl://palette/colors`` resource). Each returns the reply string.
"""

from .lookup import color_value, list_families, mix, palette

__all__ = ["color_value", "list_families", "mix", "palette"]
