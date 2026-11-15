"""Hand the shipped colours to matplotlib: names, colormaps, role colours,
and the colour cycle ``dm.set_colors`` sets."""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from cycler import Cycler, cycler
from matplotlib.axes import Axes

from .model import Catalog, Semantic

LINESTYLES = ("-", "--", ":")


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


def register(catalog: Catalog) -> None:
    """Register every name and colormap; a map already there must be ours.

    Idempotent, so a re-import is harmless. A different map under one of
    the names raises ``ValueError`` before anything is registered.
    """
    mcolors.get_named_colors_mapping().update(catalog.named)
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


def apply_semantic(tokens: Semantic) -> None:
    """Bind ``dc.pos``/``neg``/``ref``/``hl`` in matplotlib's named colours."""
    mcolors.get_named_colors_mapping().update(tokens.names())


def color_cycle(colours: Sequence[str], styles: bool) -> Cycler[str, str]:
    """A colour cycle, multiplied by three line styles when ``styles``."""
    cycle = cycler(color=list(colours))
    return cycler(linestyle=list(LINESTYLES)) * cycle if styles else cycle


def set_cycle(cycle: Cycler[str, str], ax: Axes | None) -> None:
    """Set ``cycle`` on ``ax``, or as the global default."""
    if ax is not None:
        ax.set_prop_cycle(cycle)  # pyright: ignore[reportUnknownMemberType]
        return
    plt.rcParams["axes.prop_cycle"] = cycle
