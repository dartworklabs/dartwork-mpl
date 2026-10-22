"""Locale-aware semantic tokens — ``dc.pos``/``dc.neg``/``dc.ref``/``dc.hl``
(spec §10).

Registers role-based color tokens into matplotlib's named-color mapping so
plotting code can write ``color="dc.pos"`` instead of hardcoding a palette
hex. The positive/negative mapping flips per locale to match regional
financial conventions (Korean charts color gains red and losses blue; most
other locales use the reverse), while the reference/highlight tokens stay
constant across locales.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

import matplotlib.colors as mcolors

from ..catalog import PALETTE

__all__ = ["SEMANTIC_TOKEN_NAMES", "apply_semantic"]

# Every named-color key ``apply_semantic`` writes. Callers that need to
# snapshot/restore the semantic mapping (e.g. ``Style.context``) iterate
# this tuple rather than re-deriving the key set.
SEMANTIC_TOKEN_NAMES: tuple[str, ...] = ("dc.pos", "dc.neg", "dc.ref", "dc.hl")

# ``construction._catalog`` reads these two declarations from this file's
# AST (palette coordinates, not hex values): keep them literal
# ``MappingProxyType({...})`` calls over ``PALETTE["family"][index]``.
_MAPS: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        # Korean financial convention: gains = red, losses = blue.
        "kr": MappingProxyType(
            {"dc.pos": PALETTE["red"][5], "dc.neg": PALETTE["blue"][6]}
        ),
        # Default (most other locales): gains = green, losses = red.
        "default": MappingProxyType(
            {"dc.pos": PALETTE["green"][6], "dc.neg": PALETTE["red"][6]}
        ),
    }
)
_COMMON: Mapping[str, str] = MappingProxyType(
    {"dc.ref": PALETTE["gray"][6], "dc.hl": PALETTE["violet"][6]}
)


def apply_semantic(locale: str) -> None:
    """Register semantic color tokens for ``locale`` as mpl named colors.

    Parameters
    ----------
    locale : str
        ``"kr"`` for Korean financial convention (pos=red, neg=blue), any
        other value falls back to the default mapping (pos=green,
        neg=red). ``dc.ref``/``dc.hl`` are locale-invariant.

    Notes
    -----
    Registers the ``dc.*`` tokens into
    ``matplotlib.colors.get_named_colors_mapping()``.
    """
    mapping = mcolors.get_named_colors_mapping()
    sem = {**_COMMON, **_MAPS.get(locale, _MAPS["default"])}
    for token, hexval in sem.items():
        mapping[token] = hexval
