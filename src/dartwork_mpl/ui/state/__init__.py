"""Viewer state: the last-used config and named presets stored next to the user's script.

Owns the two fixed files ``.dartwork_ui_config.json`` and
``.dartwork_ui_presets.json``, their JSON shapes and the routes that read
and edit them. Surface: ``ViewerState`` and ``FixedStateStore`` (built by
the entry point at startup), ``FileFailure``, ``routes`` and ``GRANTS``.
"""

from ._routes import GRANTS, routes
from ._store import FileFailure, FixedStateStore
from ._viewer_state import ViewerState

__all__ = ["GRANTS", "FileFailure", "FixedStateStore", "ViewerState", "routes"]
