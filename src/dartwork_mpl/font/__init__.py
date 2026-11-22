"""Bundled fonts: registered with matplotlib on ``import dartwork_mpl``.

The presets name these families in their ``font.family`` chains; this slice
owns the files, their registration, and the one face a mathtext string is
drawn in (:func:`lead_math_faces`, run by ``dm.simple_layout``).
"""

from .apply import ensure_loaded
from .mathface import lead_math_faces
from .measure import font_dir as get_font_dir

__all__ = ["ensure_loaded", "get_font_dir", "lead_math_faces"]
