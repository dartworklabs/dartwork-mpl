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

from .._curated import CURATED, CURATED_QUALITATIVE_ORDER
from ..catalog import CMAPS_256, CYCLES

__all__ = ["ensure_registered"]

# Stable across module reloads; this is a provenance convention, not security.
_OWNER_ATTRIBUTE = "_dartwork_mpl_registration"
_OWNER_TAG = "dartwork-mpl-v5"
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


def _expected_maps() -> list[mcolors.ListedColormap]:
    """Build the shipped maps in registration order without global mutation."""
    maps: list[mcolors.ListedColormap] = []
    # Store colors as RGBA tuples (not the raw hex strings) so `cmap.colors`
    # matches the convention of every other cmap in the package (the bundled
    # .txt cmaps parse to float RGB) — downstream code that indexes a color as
    # a tuple (e.g. the docs asset generator's `color[:3]`) would otherwise
    # crash on a hex string. The LUT is identical either way.
    for name, hexes in CMAPS_256.items():
        rgba = [mcolors.to_rgba(h) for h in hexes]
        maps.append(mcolors.ListedColormap(rgba, name=f"dc.{name}"))
        maps.append(mcolors.ListedColormap(rgba[::-1], name=f"dc.{name}_r"))
    for cmap_name, key, legacy_bootstrap in _CYCLE_CMAPS:
        maps.append(
            mcolors.ListedColormap(
                [
                    mcolors.to_rgba(h)
                    for h in _cycle_hexes(key, legacy_bootstrap)
                ],
                name=cmap_name,
            )
        )
    maps.extend(
        mcolors.ListedColormap(
            [mcolors.to_rgba(h) for h in CURATED[key]], name=f"dc.{key}"
        )
        for key in CURATED_QUALITATIVE_ORDER
    )
    return maps


def _register() -> None:
    """Preflight every name, then add missing maps without overwriting conflicts.

    Reuse only package-tagged maps with the exact native type, name, size and
    equality (including LUT/extremes/extend metadata). Old untagged maps in a
    live process require a restart. Static conflicts add nothing; concurrent
    external registry mutations are outside this preflight guarantee.
    """
    missing = []
    for expected in _expected_maps():
        if expected.name not in mpl.colormaps:
            missing.append(expected)
            continue
        current = mpl.colormaps[expected.name]
        if not (
            getattr(current, _OWNER_ATTRIBUTE, None) == _OWNER_TAG
            and type(current) is type(expected)
            and current.name == expected.name
            and current.N == expected.N
            and current == expected
        ):
            raise ValueError(
                f"Colormap {expected.name!r} conflicts with dartwork-mpl. "
                "Remove the conflicting external map or restart the process; "
                "existing maps are never overwritten."
            )
    for cmap in missing:
        setattr(cmap, _OWNER_ATTRIBUTE, _OWNER_TAG)
        mpl.colormaps.register(cmap)


def ensure_registered() -> None:
    """Register shipped maps once; unloaded/reload retries reuse exact own maps.

    Return None on success. A conflicting existing map raises ValueError
    before any missing map is registered and leaves this pass retryable.
    """
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        _register()
        _loaded = True
