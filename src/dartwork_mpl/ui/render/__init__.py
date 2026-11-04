"""Rendering the user's figure: the live preview, format downloads and server image saves.

Surface: ``routes`` (``/api/render``, ``/api/export/{fmt}``,
``/api/save-server/image/{fmt}``), ``GRANTS``, ``RenderRefusal`` (what the
routes hand to their ``refuse`` edge) and ``UnsupportedFormat``.
"""

from ._figure import UnsupportedFormat
from ._routes import GRANTS, RenderRefusal, routes

__all__ = ["GRANTS", "RenderRefusal", "UnsupportedFormat", "routes"]
