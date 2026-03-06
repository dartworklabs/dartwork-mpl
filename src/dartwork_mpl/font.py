"""Font management utilities for matplotlib.

This module handles registration of custom fonts from the package's
asset directory with matplotlib's font manager.
"""

from pathlib import Path

from matplotlib import font_manager


def _add_fonts() -> None:
    """
    Add custom fonts from the asset directory to matplotlib's font manager.

    This function searches for font files in the asset/font directory
    and registers them with matplotlib's font manager, making them
    available for use in plots.

    Notes
    -----
    This function is automatically called when the module is imported.
    """
    font_dir: list[Path] = [
        Path(__file__).parent / "asset/font",
    ]
    for font in font_manager.findSystemFonts(font_dir):
        font_manager.fontManager.addfont(font)

_loaded: bool = False


def ensure_loaded() -> None:
    """Ensure custom fonts are loaded and registered."""
    global _loaded
    if not _loaded:
        _add_fonts()
        _loaded = True
