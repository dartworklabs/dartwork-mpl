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


def _add_fonts() -> None:
    """Register bundled custom fonts with matplotlib's font manager.

    Scans the ``asset/font`` directory for font files and registers them
    with matplotlib's font manager so they can be used in charts. Emits
    a :class:`UserWarning` when the bundle looks emptied so that the
    Korean/CJK fallback chain degradation is visible to users.

    Notes
    -----
    This function is called automatically once when the library is
    imported; users do not need to call it directly.
    """
    found = font_manager.findSystemFonts([_FONT_DIR])
    for font in found:
        font_manager.fontManager.addfont(font)

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
