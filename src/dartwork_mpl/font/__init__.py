"""Bundled fonts: registered with matplotlib on ``import dartwork_mpl``.

The presets name these families in their ``font.family`` chains; this slice
owns only the files and their registration.
"""

from .apply import ensure_loaded
from .measure import font_dir as get_font_dir

__all__ = ["ensure_loaded", "get_font_dir"]
