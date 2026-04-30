"""Font management utilities for Matplotlib.

Registers custom fonts from the package's asset/font directory with
matplotlib's internal font manager.
"""

import threading
from pathlib import Path

from matplotlib import font_manager

__all__ = ["ensure_loaded"]


def _add_fonts() -> None:
    """Register bundled custom fonts with matplotlib's font manager.

    Scans the ``asset/font`` directory for font files and registers them
    with matplotlib's font manager so they can be used in charts.

    Notes
    -----
    This function is called automatically once when the library is
    imported; users do not need to call it directly.
    """
    font_dir: list[Path] = [Path(__file__).parent / "asset/font"]
    for font in font_manager.findSystemFonts(font_dir):
        font_manager.fontManager.addfont(font)


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
