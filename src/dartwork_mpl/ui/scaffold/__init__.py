"""``dartwork-mpl-ui init``: copy a ready-to-run viewer project from ``templates/``.

Runs on a base install, so it imports neither pydantic nor fastapi.
Surface: ``scaffold``.
"""

from ._scaffold import scaffold

__all__ = ["scaffold"]
