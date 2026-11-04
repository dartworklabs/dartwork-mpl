"""Curated palette lookup for dartwork-mpl.

`make_palette` returns a list of dartwork color names sized to the
requested series count and palette kind. The four built-in lists
(categorical, sequential blue at two cardinalities, diverging
red-blue at two cardinalities) are the dartwork-mpl recommended
series colors; they live inside this function so the project's
palette curation stays centralised.

Renamed from ``auto_select_colors`` in 0.5 (``#156`` Round 5):

- ``auto_`` prefix collided with ``auto_layout`` (measure-and-adjust).
- ``select_colors`` was a strong verb for what is structurally a list slice.
- Model B discrete family lookup now lives in ``dm.colors(..., n=...)`` and
  cycle application in ``dm.set_colors(...)``.
"""

from .._colors import make_palette as make_palette

__all__ = ["make_palette"]
