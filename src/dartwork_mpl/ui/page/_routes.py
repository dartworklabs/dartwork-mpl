"""The page routes: the HTML client, its function-name default and the heartbeat.

Surface (through the ``page`` package): ``routes`` and ``GRANTS``.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..platform.access import Grant
from ._template import get_html

# Local-only grants for the routes below (the entry point composes them).
GRANTS: dict[tuple[str, str], Grant] = {
    ("GET", "/"): "local-read",
    ("GET", "/api/meta"): "local-read",
    ("GET", "/api/health"): "local-read",
}


def routes(*, title: str, function_name: str) -> APIRouter:
    """Serve the page titled ``title`` for the figure function ``function_name``."""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index() -> str:
        """Serve the existing viewer client with its escaped configured title."""
        return get_html(title=title)

    @router.get("/api/meta")
    async def get_meta() -> dict[str, str]:
        """Preserve the frontend's configured function-name default."""
        return {"function_name": function_name}

    @router.get("/api/health")
    async def health() -> dict[str, str]:
        """Retain the frontend heartbeat independently of persistence capability."""
        return {"status": "ok"}

    return router
