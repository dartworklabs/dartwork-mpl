"""v5 cmap/cycle registration into matplotlib's global registry.

Registers the 42 v5 colormaps (from ``_generated.CMAPS_256``) as
``dc.<name>`` + ``dc.<name>_r``, plus the two qualitative cycles as
``dc.cycle`` / ``dc.cycle_print``. Access is matplotlib-native — there
is no bespoke accessor: use ``cmap="dc.aurora"`` in any plotting call,
or ``plt.colormaps["dc.aurora"]`` / ``mpl.colormaps["dc.aurora"]`` to
fetch the object (the same idiom existing code and docs already use for
the legacy ``asset/cmap/*.txt`` maps). ``dartwork_mpl.cmap`` stays the
legacy-loader *module*, untouched.
"""

from __future__ import annotations

import threading

import matplotlib as mpl
import matplotlib.colors as mcolors

from ._generated import CMAPS_256, CYCLES

__all__ = ["ensure_registered"]

_loaded = False
_lock = threading.Lock()


def _register() -> None:
    for name, hexes in CMAPS_256.items():
        mpl.colormaps.register(
            mcolors.ListedColormap(list(hexes), name=f"dc.{name}")
        )
        mpl.colormaps.register(
            mcolors.ListedColormap(list(hexes)[::-1], name=f"dc.{name}_r")
        )
    mpl.colormaps.register(
        mcolors.ListedColormap(list(CYCLES["default"]), name="dc.cycle")
    )
    mpl.colormaps.register(
        mcolors.ListedColormap(list(CYCLES["print"]), name="dc.cycle_print")
    )


def ensure_registered() -> None:
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        _register()
        _loaded = True
