"""``style`` joined with the role colours.

The style slice writes rcParams and knows no colours. A preset's locale picks
the role colours ``dc.pos`` / ``dc.neg``, so the colour slice binds them each
time a preset is applied.
"""

from __future__ import annotations

from dartwork_mpl import style
from dartwork_mpl.color import apply_semantic

__all__ = ["join"]


def join() -> None:
    """Bind the role colours whenever a preset is applied from now on."""
    style.join(apply_semantic)
