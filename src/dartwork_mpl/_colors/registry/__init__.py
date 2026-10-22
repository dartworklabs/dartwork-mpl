"""Colour registry: publish the shipped colours to matplotlib's name space.

Responsibility: the idempotent, thread-safe registration of the bundled
colour libraries (``oc.``, ``tw.``, ``dc.`` …) as named colours, of the
catalogue colormaps and cycles, and of the locale-aware semantic tokens
(``dc.pos``/``neg``/``ref``/``hl``).

Surface: ``ensure_loaded``, ``ensure_registered``, ``apply_semantic``,
``SEMANTIC_TOKEN_NAMES`` and ``COLOR_LIBRARIES`` (the registered library
table, a tuple of ``ColorLibrary`` rows: key, prefix, source, label).
"""

from ._loader import COLOR_LIBRARIES, ColorLibrary, ensure_loaded
from ._register import ensure_registered
from ._semantic import SEMANTIC_TOKEN_NAMES, apply_semantic

__all__ = [
    "COLOR_LIBRARIES",
    "SEMANTIC_TOKEN_NAMES",
    "ColorLibrary",
    "apply_semantic",
    "ensure_loaded",
    "ensure_registered",
]
