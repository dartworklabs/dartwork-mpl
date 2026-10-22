"""The reproducing script: a standalone Python file with the model, the figure function and the active values.

Surface: ``routes`` (``/api/script``, ``/api/save-server/script``) and
``GRANTS``.
"""

from ._routes import GRANTS, routes

__all__ = ["GRANTS", "routes"]
