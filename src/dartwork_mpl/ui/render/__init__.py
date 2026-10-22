"""Rendering the user's figure: the live preview, format downloads and server image saves.

Surface: ``routes`` (``/api/render``, ``/api/export/{fmt}``,
``/api/save-server/image/{fmt}``) and ``GRANTS``.
"""

from ._routes import GRANTS, routes

__all__ = ["GRANTS", "routes"]
