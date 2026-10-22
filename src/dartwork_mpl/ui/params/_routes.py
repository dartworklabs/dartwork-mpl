"""The parameter-control routes: the descriptor list the page renders and the model defaults.

Surface (through the ``params`` package): ``routes`` and ``GRANTS``.
"""

from typing import Any

from fastapi import APIRouter

from ..platform.access import Grant
from ._descriptors import ParamDescriptor

# Local-only grants for the routes below (the entry point composes them).
GRANTS: dict[tuple[str, str], Grant] = {
    ("GET", "/api/descriptors"): "local-read",
    ("GET", "/api/defaults"): "local-read",
}


def routes(descriptors: list[ParamDescriptor]) -> APIRouter:
    """Serve the controls and defaults derived once from the user's model."""
    router = APIRouter()
    descriptor_dicts = [descriptor.to_dict() for descriptor in descriptors]

    @router.get("/api/descriptors")
    async def get_descriptors() -> list[dict[str, Any]]:
        """Expose supported controls and defaults from the supplied model."""
        return descriptor_dicts

    @router.get("/api/defaults")
    async def get_defaults() -> dict[str, Any]:
        """Return usable model defaults independently of stored-state corruption or drift."""
        return {
            descriptor.name: descriptor.default for descriptor in descriptors
        }

    return router
