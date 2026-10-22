"""Colour construction: compile the shipped catalogue from the v6 authority.

Responsibility: everything that turns the validated v6 authority
(``_colors/_ssot.py``) and the curated/cycle specifications into catalogue
values — the NeutralTone recipe, palette and colormap compilers, the
candidate ``CatalogSnapshot`` (and the frozen v5 snapshot it is compared with),
and the renderer/atomic writer of ``_colors/_generated.py``. Runs without the
generated module and without the runtime registries.

Surface: ``CatalogSnapshot``, ``compile_candidate_snapshot``,
``load_v5_snapshot``, ``render_generated``,
``atomic_write_text``. The CLI is ``python -m dartwork_mpl._colors._build``.
(The package is not named ``build``: pytest skips directories of that name.)
"""

from ._catalog import (
    CatalogSnapshot,
    compile_candidate_snapshot,
    load_v5_snapshot,
)
from ._publish import atomic_write_text, render_generated

__all__ = [
    "CatalogSnapshot",
    "atomic_write_text",
    "compile_candidate_snapshot",
    "load_v5_snapshot",
    "render_generated",
]
