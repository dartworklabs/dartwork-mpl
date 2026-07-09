"""v5 cmap/cycle registration into matplotlib's global registry.

Registers the 43 v5 colormaps (from ``_generated.CMAPS_256``) as
``dc.<name>`` + ``dc.<name>_r``, plus qualitative cycles and curated
qualitative sets as base ``dc.<name>`` ListedColormaps. Access is
matplotlib-native — there
is no bespoke accessor: use ``cmap="dc.aurora"`` in any plotting call,
or ``plt.colormaps["dc.aurora"]`` / ``mpl.colormaps["dc.aurora"]`` to
fetch the object (the same idiom existing code and docs already use for
the rest of Matplotlib's colormap registry).
"""

from __future__ import annotations

import threading

import matplotlib as mpl
import matplotlib.colors as mcolors

from ._curated import CURATED, CURATED_QUALITATIVE_ORDER
from ._generated import CMAPS_256, CYCLES

__all__ = ["ensure_registered"]

_loaded = False
_lock = threading.Lock()
_CYCLE_CMAPS = (
    ("dc.octave", "octave", "octave"),
    ("dc.octave_print", "octave_print", "octave_print"),
)


def _cycle_hexes(canonical: str, legacy_bootstrap: str) -> tuple[str, ...]:
    """Resolve cycle colors while a pre-regeneration artifact may still exist."""
    if canonical in CYCLES:
        return CYCLES[canonical]
    return CYCLES[legacy_bootstrap]


def _register() -> None:
    # Store colors as RGBA tuples (not the raw hex strings) so `cmap.colors`
    # matches the convention of every other cmap in the package (the bundled
    # .txt cmaps parse to float RGB) — downstream code that indexes a color as
    # a tuple (e.g. the docs asset generator's `color[:3]`) would otherwise
    # crash on a hex string. The LUT is identical either way.
    for name, hexes in CMAPS_256.items():
        rgba = [mcolors.to_rgba(h) for h in hexes]
        mpl.colormaps.register(mcolors.ListedColormap(rgba, name=f"dc.{name}"))
        mpl.colormaps.register(
            mcolors.ListedColormap(rgba[::-1], name=f"dc.{name}_r")
        )
    for cmap_name, key, legacy_bootstrap in _CYCLE_CMAPS:
        mpl.colormaps.register(
            mcolors.ListedColormap(
                [
                    mcolors.to_rgba(h)
                    for h in _cycle_hexes(key, legacy_bootstrap)
                ],
                name=cmap_name,
            )
        )
    for key in CURATED_QUALITATIVE_ORDER:
        mpl.colormaps.register(
            mcolors.ListedColormap(
                [mcolors.to_rgba(h) for h in CURATED[key]], name=f"dc.{key}"
            )
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
