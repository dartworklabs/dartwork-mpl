"""The reproducing script: a standalone Python file with the model, the figure function and the active values.

Surface: ``routes`` (``/api/script``, ``/api/save-server/script``),
``GRANTS`` and ``ScriptRefusal`` (what the routes hand to their ``refuse``
edge).
"""

from ._routes import GRANTS, ScriptRefusal, routes

__all__ = ["GRANTS", "ScriptRefusal", "routes"]
