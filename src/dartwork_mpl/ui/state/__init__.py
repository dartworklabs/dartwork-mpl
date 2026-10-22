"""Viewer state: the last-used config and named presets stored next to the user's script.

Owns the two fixed files named by ``StateFile``, their JSON shapes and the
routes that read and edit them. Surface: ``StateFile``, ``ViewerState`` and
``FixedStateStore`` (built by the entry point at startup), ``FileFailure``,
``routes`` and ``GRANTS``. Only ``StateFile`` loads eagerly: the rest needs
the ``ui`` extra and is imported on first use.
"""

from typing import TYPE_CHECKING, Any

from ._files import StateFile

if TYPE_CHECKING:
    from ._routes import GRANTS, routes
    from ._store import FileFailure, FixedStateStore
    from ._viewer_state import ViewerState

__all__ = [
    "GRANTS",
    "FileFailure",
    "FixedStateStore",
    "StateFile",
    "ViewerState",
    "routes",
]

_LAZY = {
    "GRANTS": "_routes",
    "routes": "_routes",
    "FileFailure": "_store",
    "FixedStateStore": "_store",
    "ViewerState": "_viewer_state",
}


def __getattr__(name: str) -> Any:
    """Load the extra-dependent surface on use, so ``StateFile`` imports on a base install."""
    if name in _LAZY:
        from importlib import import_module

        return getattr(import_module(f".{_LAZY[name]}", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
