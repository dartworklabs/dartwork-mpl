"""Dartwork interactive figure viewer — FastAPI server (entry point).

This module only wires: it opens the output roots and state store at
startup, applies the local-only policy to every request, and mounts each
sub-slice's routes (``page``, ``params``, ``render``, ``state``,
``script``) plus the restart route.

Usage
-----
::

    from dartwork_mpl.ui import ParamModel, run
    from pydantic import Field

    class Params(ParamModel):
        n: int = Field(default=100, ge=10, le=1000)
        alpha: float = Field(default=0.5, ge=0.0, le=1.0)

    def my_plot(params: Params) -> Figure:
        ...
        return fig

    run(my_plot, Params)  # Explicit parameter model
    run(my_plot)           # Auto-extract from type hints
"""

import os
import sys
import threading
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, TypeVar, cast

import matplotlib
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from matplotlib.figure import Figure
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

from . import page, params, render, script
from ._boundary import ROUTE_POLICY
from .params import (
    InvalidRequest,
    ParamModel,
    controls_from_model,
    extract_param_model,
)
from .platform.access import (
    AccessDenied,
    StartupRejected,
    authorize_request,
    normalize_bind,
)
from .platform.fs import (
    FilesystemCapabilities,
    FsFailure,
    RootScope,
    open_roots,
)
from .platform.http import refusal_response
from .state import FileFailure, FixedStateStore, ViewerState
from .state import routes as state_routes

matplotlib.use("Agg")


def _matched_route(app: FastAPI, request: Request) -> str | None:
    """Match actual registrations before routing; method/path misses have no grant."""
    path_exists = False
    for route in app.routes:
        match, _ = route.matches(request.scope)
        if match is Match.FULL:
            return cast(str, getattr(route, "path", None))
        path_exists = path_exists or match is Match.PARTIAL
    if not path_exists and request.method in {"GET", "HEAD"}:
        return "<unmatched>"
    return None


def _create_app(
    figure_fn: Callable[[Any], Figure],
    param_model: type[ParamModel],
    *,
    title: str,
    script_root: Path,
    copy_to: str | os.PathLike[str] | list[str | os.PathLike[str]] | None,
    host: str,
    restart: Callable[[], None] | None = None,
    capabilities: FilesystemCapabilities | None = None,
) -> FastAPI:
    """Own local HTTP policy, root lifetimes and serial trusted callback effects.

    Invalid binds fail before filesystem access. Persistence startup refusals remain
    API values so missing capabilities do not disable rendering or downloads.
    ``restart`` is an owned observer seam; production passes delayed exec explicitly.
    """
    normalized_host = normalize_bind(host)
    if isinstance(normalized_host, StartupRejected):
        raise ValueError(normalized_host.detail)
    startup_cwd = Path.cwd()
    descriptors = controls_from_model(param_model)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Acquire roots once at startup and release every descriptor at shutdown."""
        roots = open_roots(
            script_root, copy_to, cwd=startup_cwd, capabilities=capabilities
        )
        application.state.viewer_roots = roots
        application.state.viewer_state = (
            ViewerState(
                FixedStateStore(roots), frozenset(param_model.model_fields)
            )
            if isinstance(roots, RootScope)
            else roots
        )
        try:
            yield
        finally:
            if isinstance(roots, RootScope):
                roots.close()

    app = FastAPI(title=title, lifespan=lifespan)

    @app.middleware("http")
    async def local_policy(request: Request, call_next: Any) -> Response:
        """Mediate every registered route and deny unknown effects before request parsing."""
        access = authorize_request(
            request.method,
            _matched_route(app, request),
            request.scope["headers"],
            normalized_host,
            ROUTE_POLICY,
        )
        if isinstance(access, AccessDenied):
            return refusal_response(access)
        return cast(Response, await call_next(request))

    @app.exception_handler(StarletteHTTPException)
    async def http_failure(
        _request: Request, failure: StarletteHTTPException
    ) -> JSONResponse:
        """Keep intentional transport errors in the detail/code error contract."""
        return JSONResponse(
            {
                "detail": failure.detail,
                "code": "not_found"
                if failure.status_code == 404
                else "invalid_request",
            },
            status_code=failure.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def request_failure(
        _request: Request, _failure: RequestValidationError
    ) -> JSONResponse:
        """Reject malformed route parameters without echoing untrusted values."""
        return refusal_response(InvalidRequest())

    def roots() -> RootScope | FsFailure:
        """Borrow the lifespan-owned output roots, including startup refusal values."""
        return cast(RootScope | FsFailure, app.state.viewer_roots)

    def state() -> ViewerState | FileFailure:
        """Borrow the lifespan-owned state capability, including startup refusal values."""
        return cast(ViewerState | FileFailure, app.state.viewer_state)

    app.include_router(
        page.routes(title=title, function_name=figure_fn.__name__)
    )
    app.include_router(params.routes(descriptors))
    app.include_router(
        render.routes(
            figure_fn=figure_fn,
            param_model=param_model,
            descriptors=descriptors,
            roots=roots,
        )
    )
    app.include_router(
        state_routes(
            param_model=param_model,
            descriptors=descriptors,
            function_name=figure_fn.__name__,
            state=state,
        )
    )
    app.include_router(
        script.routes(
            figure_fn=figure_fn,
            param_model=param_model,
            descriptors=descriptors,
            script_root=script_root,
            roots=roots,
        )
    )

    @app.post("/api/reload", response_model=None)
    async def reload_server() -> dict[str, str] | JSONResponse:
        """Invoke the owned restart capability once; no request body/code selects the effect."""
        if restart is not None:
            try:
                restart()
            except Exception:  # noqa: BLE001 -- contain arbitrary trusted callback/source failures
                return JSONResponse(
                    {
                        "detail": "Viewer restart failed.",
                        "code": "restart_failed",
                    },
                    status_code=500,
                )
        return {"status": "reloading"}

    return app


def _schedule_restart() -> None:
    """Defer the trusted process exec until the response can leave the socket."""

    def execute() -> None:
        """Restart the original executable/argv after the existing response delay."""
        time.sleep(0.3)
        os.execv(sys.executable, [sys.executable, *sys.argv])

    threading.Thread(target=execute, daemon=True).start()


_P = TypeVar("_P", bound=ParamModel)


def run(
    figure_fn: Callable[[_P], Figure],
    param_model: type[ParamModel] | None = None,
    *,
    title: str = "Dartwork Viewer",
    copy_to: str
    | os.PathLike[str]
    | list[str | os.PathLike[str]]
    | None = None,
    host: str = "127.0.0.1",
    port: int = 8501,
) -> None:
    """Launch the local FastAPI-based interactive figure viewer.

    Parameters
    ----------
    figure_fn : callable
        Trusted function accepting one ParamModel and returning a matplotlib Figure.
    param_model : type[ParamModel], optional
        Parameter class, extracted from the function annotations when omitted.
    title : str
        Page and app title.
    copy_to : str | os.PathLike[str] | list[str | os.PathLike[str]] | None
        Additional image-save directories. Expand ~ and resolve relative roots
        against startup CWD; deduplicate directory objects. Image/script outputs
        are create-only below the script directory; copies are create-only at
        every root. Choose a new relative filename on conflict (409). Scripts
        are not copied to copy_to.
    host : str
        Loopback literal (127.0.0.0/8 or ::1), or localhost (mapped directly to
        127.0.0.1). Other hosts reject before filesystem or server effects.
    port : int
        Initial server port; occupied ports retain the existing increment retry.

    Raises
    ------
    ValueError
        The bind is not an approved loopback address.
    TypeError
        Function annotations cannot supply a ParamModel subclass.

    Notes
    -----
    Local processes and callbacks are trusted; loopback does not identify a
    person. Hosted/proxy access is outside this contract. Required no-follow
    directory-handle primitives are checked; unavailable persistence returns
    501 (unsupported_filesystem_capability), while render/download stay usable.
    Saves use best-effort rollback, not a cross-root transaction. Crashes or
    failed cleanup may leave new files; partial-save 503 lists relative paths.
    Malicious same-owner directory moves and cleanup races are outside the
    guarantee. State updates serialize within one process; separate processes
    can lose updates (last replacement wins). Callbacks are serial without a
    hard CPU, memory or deadline bound. Failures expose detail/code; callback
    errors return 500 (callback_failed), without payload/traceback details.
    Requests/config: 1 MiB; presets: 8 MiB; JSON depth: 16; values: 65,536;
    container entries: 4,096; strings: 64 KiB; integer tokens: 640 digits;
    tabs: 64; presets: 1,000; labels: 256 bytes; output paths: 1,024 bytes
    plus platform component limits; active figWidth: 30..100. Corrupt state
    returns 409 (invalid_stored_state), preserving bytes. Reads project field
    drift with dropped_fields; retained invalid active values can return 422.
    Reset restores controls, not stored files. See docs/api/ui.rst and the
    interactive usage guide for schemas, statuses and recovery.
    """
    normalized = normalize_bind(host)
    if isinstance(normalized, StartupRejected):
        raise ValueError(normalized.detail)
    if param_model is None:
        param_model = extract_param_model(figure_fn)
    app = _create_app(
        figure_fn,
        param_model,
        title=title,
        script_root=Path(sys.argv[0]).resolve().parent,
        copy_to=copy_to,
        host=normalized,
        restart=_schedule_restart,
    )
    current_port = port
    while True:
        try:
            print("\n  Dartwork Viewer running at:")
            url_host = f"[{normalized}]" if ":" in normalized else normalized
            print(f"  \033[1;36mhttp://{url_host}:{current_port}\033[0m\n")
            uvicorn.run(
                app, host=normalized, port=current_port, log_level="warning"
            )
            break
        except SystemExit:
            current_port += 1
            print(f"  Port {current_port - 1} in use, trying {current_port}...")
