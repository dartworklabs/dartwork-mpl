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

import matplotlib.colors as mcolors

from ._generated import PALETTE

__all__ = ["SEMANTIC_TOKEN_NAMES", "apply_semantic"]

# Every named-color key ``apply_semantic`` writes. Callers that need to
# snapshot/restore the semantic mapping (e.g. ``Style.context``) iterate
# this tuple rather than re-deriving the key set.
SEMANTIC_TOKEN_NAMES: tuple[str, ...] = (
    "dc.pos",
    "dc.neg",
    "dc.ref",
    "dc.hl",
    "dm.pos",
    "dm.neg",
    "dm.ref",
    "dm.hl",
)

_MAPS: dict[str, dict[str, str]] = {
    # Korean financial convention: gains = red, losses = blue.
    "kr": {"dc.pos": PALETTE["red"][5], "dc.neg": PALETTE["blue"][6]},
    # Default (most other locales): gains = green, losses = red.
    "default": {"dc.pos": PALETTE["green"][6], "dc.neg": PALETTE["red"][6]},
}
_COMMON: dict[str, str] = {
    "dc.ref": PALETTE["gray"][6],
    "dc.hl": PALETTE["violet"][6],
}


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
    Registers both the ``dc.*`` token and its ``dm.*`` alias (e.g.
    ``dc.pos`` and ``dm.pos``) into
    ``matplotlib.colors.get_named_colors_mapping()``, so either prefix can
    be used in ``color="dc.pos"`` / ``color="dm.pos"`` calls.
    """
    mapping = mcolors.get_named_colors_mapping()
    sem = {**_COMMON, **_MAPS.get(locale, _MAPS["default"])}
    for token, hexval in sem.items():
        mapping[token] = hexval
        mapping["dm." + token[3:]] = hexval
