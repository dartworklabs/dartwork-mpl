"""Read what matplotlib has registered: the facts the literal-name rules check."""

from __future__ import annotations

from matplotlib import colormaps
from matplotlib.colors import get_named_colors_mapping

from .model import Known


def known() -> Known:
    """Every colour name (lower case) and colormap registered right now.

    Read on each call: importing dartwork-mpl, or a user's own code, can
    register more names after the first lint.
    """
    return Known(
        colors=frozenset(name.lower() for name in get_named_colors_mapping()),
        colormaps=frozenset(colormaps),
    )
