"""Hand the shipped colours to matplotlib: names, colormaps, role colours."""

from __future__ import annotations

import logging
from collections.abc import Mapping

import matplotlib as mpl
import matplotlib.colors as mcolors

from .model import Catalog, Semantic

LOG = logging.getLogger("dartwork_mpl.color")


def colormaps(catalog: Catalog) -> list[mcolors.ListedColormap]:
    """``dc.<family>`` (and ``_r`` for continuous ones) for every family."""
    maps: list[mcolors.ListedColormap] = []
    for family in catalog.families.values():
        name = f"dc.{family.name}"
        if not family.kind.continuous:
            rgba = [mcolors.to_rgba(h) for h in family.stops]
            maps.append(mcolors.ListedColormap(rgba, name=name))
            continue
        rgba = [mcolors.to_rgba(h) for h in family.cmap]
        maps.append(mcolors.ListedColormap(rgba, name=name))
        maps.append(mcolors.ListedColormap(rgba[::-1], name=f"{name}_r"))
    return maps


def bind(names: Mapping[str, str]) -> None:
    """Set each name in matplotlib's named colours.

    One at a time: the mapping drops its cache of resolved colours when an
    item is set, and ``dict.update`` goes around that, so a name looked up
    before a rebind would keep its old colour.
    """
    named = mcolors.get_named_colors_mapping()
    for name, value in names.items():
        named[name] = value


def register(catalog: Catalog) -> None:
    """Register every name and colormap; a map already there must be ours.

    Idempotent, so a re-import is harmless. A different map under one of
    the names raises ``ValueError`` before anything is registered.
    """
    bind(catalog.named)
    missing: list[mcolors.ListedColormap] = []
    for cmap in colormaps(catalog):
        if cmap.name not in mpl.colormaps:
            missing.append(cmap)
        elif mpl.colormaps[cmap.name] != cmap:
            raise ValueError(
                f"Colormap {cmap.name!r} conflicts with dartwork-mpl. Remove "
                "the other map or restart the process."
            )
    for cmap in missing:
        mpl.colormaps.register(cmap)
    if missing:
        LOG.debug(
            "registered %d colour names (dc.*, tw.*, md.* and other "
            "prefixed libraries) and %d dc.* colormaps with matplotlib, so "
            "the presets and your code can name them; none replaces a "
            "matplotlib name",
            len(catalog.named),
            len(missing),
        )


def apply_semantic(tokens: Semantic) -> None:
    """Bind ``dc.pos``/``neg``/``ref``/``hl`` in matplotlib's named colours."""
    bind(tokens.names())
