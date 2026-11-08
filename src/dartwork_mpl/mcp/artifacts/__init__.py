"""Durable plot artifacts: the MCP render/retrieve/delete routes and their storage.

The surface is what server wiring needs: ``configure_store`` resolves the
artifact root (or returns a ``ConfigurationError`` whose ``reason`` the server
reports on stderr), ``ArtifactRuntime`` owns the optional input lifecycle and
``register_artifacts`` binds the tools and resources. Everything else is
internal to this slice; its values, use cases and policies live in the
submodules (``policy``, ``store``, ``delivery``, ``inputs``, ``input_*``,
``lifecycle``, ``transport``), which tests import directly.
"""

from .lifecycle import ArtifactRuntime
from .policy import ConfigurationError
from .store import configure_store
from .transport import register_artifacts

__all__ = [
    "ArtifactRuntime",
    "ConfigurationError",
    "configure_store",
    "register_artifacts",
]
