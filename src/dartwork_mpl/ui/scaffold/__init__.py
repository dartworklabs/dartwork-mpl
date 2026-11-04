"""``dartwork-mpl-ui init``: copy a ready-to-run viewer project from ``templates/``.

Runs on a base install, so it imports neither pydantic nor fastapi.
Surface: ``scaffold``, its outcomes (``Scaffolded``, ``TargetNotEmpty``,
``UnknownExample``, ``ScaffoldRefusal``) and the offered ``EXAMPLES``.
"""

from ._scaffold import (
    EXAMPLES,
    Scaffolded,
    ScaffoldRefusal,
    TargetNotEmpty,
    UnknownExample,
    scaffold,
)

__all__ = [
    "EXAMPLES",
    "ScaffoldRefusal",
    "Scaffolded",
    "TargetNotEmpty",
    "UnknownExample",
    "scaffold",
]
