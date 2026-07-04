"""Font management utilities for Matplotlib.

Registers custom fonts from the package's asset/font directory with
matplotlib's internal font manager.
"""

import threading
import warnings
from pathlib import Path

from matplotlib import font_manager

__all__ = ["ensure_loaded"]

# Rough sanity floor for the bundled font set. We expect at least a
# handful of files spanning Roboto + Paperlogy + NotoSansCJK +
# NotoSansMath cores. Falling below this hints that the install is
# missing assets — likely a slim install or accidental deletion.
_EXPECTED_MIN_FONTS: int = 5

# Bundled font directory — single source, also consumed by
# ``diagnostics._fonts.plot_fonts`` (which used to rebuild the same
# path with os.path idioms).
_FONT_DIR: Path = Path(__file__).parent / "asset" / "font"


def _promote_bundled_fonts() -> None:
    """Move bundled font entries to the front of ``fontManager.ttflist``.

    ``FontManager.addfont`` *appends* each bundled ``FontEntry`` to
    ``ttflist``, so the bundled entries land *after* the system fonts
    that matplotlib scanned when it built the manager. But
    :meth:`FontManager._findfont_cached` scores every entry and keeps the
    **first** among equal best scores (``if score < best_score`` — a
    strict inequality). A system-installed copy of a bundled family
    (e.g. ``/Library/Fonts/Roboto-Regular.ttf``) therefore ties the
    bundled copy on family+style and, being earlier, silently wins —
    masking the shipped assets and breaking the eager-registration
    contract on any machine with same-named system fonts.

    Partitioning ``ttflist`` so the bundled entries sit first makes them
    deterministically win those ties. This changes **only** tie-breaks:
    a system font that scores *strictly* better for a different
    family/style still has the minimum score and still wins regardless of
    position. The relative order of bundled entries (and of non-bundled
    entries) is preserved, so nothing else reshuffles.

    Idempotent: once the bundled entries are already at the front this is
    a no-op (no reordering, no cache clear), so repeated registration
    paths never reshuffle endlessly.
    """
    ttflist = font_manager.fontManager.ttflist
    bundle_dir = _FONT_DIR.resolve()

    bundled: list[font_manager.FontEntry] = []
    others: list[font_manager.FontEntry] = []
    for entry in ttflist:
        try:
            fname = Path(entry.fname).resolve()
            is_bundled = fname.is_relative_to(bundle_dir)
        except (OSError, ValueError):
            is_bundled = False
        (bundled if is_bundled else others).append(entry)

    if not bundled:
        return

    # Already at the front (same objects, same order)? Leave untouched so
    # the operation is a fixed point under repeated calls.
    already_front = len(ttflist) >= len(bundled) and all(
        existing is promoted
        for existing, promoted in zip(
            ttflist[: len(bundled)], bundled, strict=True
        )
    )
    if already_front:
        return

    # In-place slice assignment preserves the list object matplotlib's
    # fontManager holds a reference to.
    ttflist[:] = bundled + others
    # Mirror ``addfont``: any cached resolution predates the new order.
    font_manager.fontManager._findfont_cached.cache_clear()  # type: ignore[attr-defined]


def _add_fonts() -> None:
    """Register bundled custom fonts with matplotlib's font manager.

    Scans the ``asset/font`` directory for font files and registers them
    with matplotlib's font manager so they can be used in charts, then
    promotes them ahead of same-named system fonts so the eager
    registration contract holds even on machines where those families are
    installed system-wide (see :func:`_promote_bundled_fonts`). Emits a
    :class:`UserWarning` when the bundle looks emptied so that the
    Korean/CJK fallback chain degradation is visible to users.

    Notes
    -----
    This function is called automatically once when the library is
    imported; users do not need to call it directly.
    """
    found = font_manager.findSystemFonts([_FONT_DIR])
    for font in found:
        font_manager.fontManager.addfont(font)

    # ``addfont`` appends, so bundled entries lose score ties to earlier
    # system fonts of the same family. Promote them to the front so the
    # shipped assets deterministically win those ties.
    _promote_bundled_fonts()

    # Graceful warning if the bundle looks emptied. This catches
    # accidental asset deletion and any future slim-install variant
    # (e.g. a [fonts] extra) that shipped without the bundled corpus.
    if len(found) < _EXPECTED_MIN_FONTS:
        warnings.warn(
            f"dartwork-mpl found only {len(found)} bundled font file(s) "
            f"in {_FONT_DIR}. The Korean/CJK fallback chain may "
            f"degrade to system fonts. Reinstall the package to "
            f"restore the bundled assets.",
            UserWarning,
            # Points at the ``_add_fonts()`` call inside
            # ``ensure_loaded`` — a stable in-package frame. The
            # previous ``stacklevel=3`` walked one frame further into
            # whatever happened to import the package, which was never
            # a useful location.
            stacklevel=2,
        )


_loaded: bool = False
_lock: threading.Lock = threading.Lock()


def ensure_loaded() -> None:
    """Ensure custom fonts are loaded and registered.

    Thread-safe: uses double-checked locking to avoid duplicate
    font registration when called concurrently from multiple threads.
    """
    global _loaded

    # Fast path: skip lock once already loaded.
    if _loaded:
        return

    with _lock:
        if _loaded:
            return
        _add_fonts()
        _loaded = True
