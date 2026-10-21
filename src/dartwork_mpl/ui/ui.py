"""Dartwork interactive figure viewer — FastAPI server.

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

import base64
import inspect
import io
import os
import sys
import tempfile
import textwrap
import threading
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar, cast
from uuid import uuid4

import matplotlib
import matplotlib.pyplot as plt
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.figure import Figure
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import ClientDisconnect
from starlette.routing import Match

from ..util import save_formats
from ._boundary import (
    ROUTE_POLICY,
    InputFailure,
    ModelRequest,
    ParsedRequest,
    PresetRequest,
    SaveRequest,
    StateRequest,
    parse_output,
    parse_request,
)
from ._config import ConfigLoaded, PresetNotFound, PresetsLoaded, ViewerState
from ._files import (
    FileFailure,
    FixedStateStore,
    MissingState,
    PreparedSave,
    SaveReceipt,
    StateWritten,
    commit_save,
    prepare_save,
)
from .page import get_html
from .params import (
    InvalidRequest,
    ParamModel,
    descriptors_from_model,
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
    PartialSave,
    RootScope,
    open_roots,
)
from .platform.json_bounds import (
    MAX_REQUEST_BYTES,
    JsonValue,
    LimitExceeded,
    MalformedInput,
    decode_json,
)

matplotlib.use("Agg")
_SUPPORTED_EXPORT_FORMATS: frozenset[str] = frozenset(
    FigureCanvasBase.get_supported_filetypes()
)


def _figure_to_bytes(
    figure_fn: Callable[[Any], Figure], model: Any, fmt: str
) -> bytes:
    """Render ``figure_fn(model)`` to ``fmt`` bytes, always closing the figure.

    The figure is closed in a ``finally`` so a ``savefig`` failure (bad
    format, non-finite data, …) can't leak it. Render/export are hot
    paths (fired on every param change), so an un-closed figure per
    failure accumulates unboundedly in pyplot's global figure registry.
    """
    fig = figure_fn(model)
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt)
        return buf.getvalue()
    finally:
        plt.close(fig)


def _refusal_response(
    failure: InputFailure | AccessDenied | FileFailure | PresetNotFound,
) -> JSONResponse:
    """Map named refusals once, exposing stable codes and relative partial paths only."""
    body: dict[str, Any] = {"detail": failure.detail, "code": failure.code}
    if isinstance(failure, PartialSave):
        body["paths"] = list(failure.paths)
    return JSONResponse(body, status_code=failure.status_code)


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


async def _request_json(
    request: Request,
) -> JsonValue | InputFailure | JSONResponse:
    """Read once with a streaming byte cap and require plain UTF-8 JSON media."""
    media = request.headers.getlist("content-type")
    if len(media) != 1 or request.headers.getlist("content-encoding"):
        return JSONResponse(
            {
                "detail": "Use unencoded application/json with UTF-8.",
                "code": "unsupported_media_type",
            },
            status_code=415,
        )
    parts = [part.strip().lower() for part in media[0].split(";")]
    if (
        parts[0] != "application/json"
        or any(
            part not in {"charset=utf-8", 'charset="utf-8"'}
            for part in parts[1:]
        )
        or len(parts) > 2
    ):
        return JSONResponse(
            {
                "detail": "Use unencoded application/json with UTF-8.",
                "code": "unsupported_media_type",
            },
            status_code=415,
        )
    chunks: list[bytes] = []
    size = 0
    try:
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_REQUEST_BYTES:
                return LimitExceeded()
            chunks.append(chunk)
    except ClientDisconnect:
        return MalformedInput()
    return decode_json(b"".join(chunks), max_bytes=MAX_REQUEST_BYTES)


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
    descriptors = descriptors_from_model(param_model)
    descriptor_dicts = [descriptor.to_dict() for descriptor in descriptors]

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
            return _refusal_response(access)
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
        return _refusal_response(InvalidRequest())

    async def parsed_body(
        request: Request, template: str
    ) -> ParsedRequest | JSONResponse:
        """Recognize the complete bounded endpoint language without downstream raw reads."""
        value = await _request_json(request)
        if isinstance(value, JSONResponse):
            return value
        if isinstance(value, InputFailure):
            return _refusal_response(value)
        parsed = parse_request(template, value, param_model, descriptors)
        return (
            _refusal_response(parsed)
            if isinstance(parsed, InputFailure)
            else parsed
        )

    def state() -> ViewerState | FileFailure:
        """Borrow the lifespan-owned state capability, including startup refusal values."""
        return cast(ViewerState | FileFailure, app.state.viewer_state)

    def render_bytes(model: ParamModel, fmt: str) -> bytes | JSONResponse:
        """Run callbacks synchronously in the event loop and contain trusted callback errors."""
        try:
            return _figure_to_bytes(figure_fn, model, fmt)
        except Exception:  # noqa: BLE001 -- trusted callbacks may raise arbitrary errors
            return JSONResponse(
                {
                    "detail": "The figure callback failed.",
                    "code": "callback_failed",
                },
                status_code=500,
            )

    def save_image(
        parsed: SaveRequest, fmt: str
    ) -> SaveReceipt | FileFailure | InputFailure | JSONResponse:
        """Plan every sink before a callback; stage unchanged save_formats bytes privately."""
        roots = cast(RootScope | FileFailure, app.state.viewer_roots)
        if not isinstance(roots, RootScope):
            return roots
        name = (
            parsed.output.filename
            if parsed.output
            else f"{figure_fn.__name__}_{_timestamp_slug()}"
        )
        for extension in (".png", ".svg", ".pdf"):
            if name.lower().endswith(extension):
                fmt, name = extension[1:], name[: -len(extension)]
                break
        output = parse_output(f"{name}.{fmt}")
        if isinstance(output, InputFailure):
            return output
        plan = prepare_save(roots, output, include_copies=True)
        if not isinstance(plan, PreparedSave):
            return plan
        result: SaveReceipt | FileFailure | InputFailure | JSONResponse
        try:
            with tempfile.TemporaryDirectory(
                prefix="dartwork-viewer-"
            ) as staging:
                fig = figure_fn(parsed.model)
                try:
                    basename = Path(output.filename).name
                    stem = Path(staging) / basename[: -len(fmt) - 1]
                    save_formats(
                        fig, str(stem), formats=(fmt,), bbox_inches=None
                    )
                finally:
                    plt.close(fig)
                with (Path(staging) / basename).open("rb") as source:
                    result = commit_save(plan, source)
        except Exception:  # noqa: BLE001 -- contain arbitrary trusted callback/source failures
            result = JSONResponse(
                {
                    "detail": "The figure callback or image export failed.",
                    "code": "callback_failed",
                },
                status_code=500,
            )
        finally:
            cleanup = plan.close()
        return cleanup if cleanup is not None else result

    def save_script(
        parsed: SaveRequest,
    ) -> SaveReceipt | FileFailure | InputFailure | JSONResponse:
        """Prepare the primary script sink before source generation and create it exclusively."""
        roots = cast(RootScope | FileFailure, app.state.viewer_roots)
        if not isinstance(roots, RootScope):
            return roots
        name = (
            parsed.output.filename
            if parsed.output
            else f"{figure_fn.__name__}_{_timestamp_slug()}"
        )
        if name.lower().endswith(".py"):
            name = name[:-3]
        output = parse_output(f"{name}.py")
        if isinstance(output, InputFailure):
            return output
        plan = prepare_save(roots, output, include_copies=False)
        if not isinstance(plan, PreparedSave):
            return plan
        result: SaveReceipt | FileFailure | InputFailure | JSONResponse
        try:
            code = _generate_script(
                parsed.model, param_model, figure_fn, script_root
            )
            result = commit_save(plan, io.BytesIO(code.encode("utf-8")))
        except Exception:  # noqa: BLE001 -- contain arbitrary trusted callback/source failures
            result = JSONResponse(
                {
                    "detail": "Script generation failed.",
                    "code": "callback_failed",
                },
                status_code=500,
            )
        finally:
            cleanup = plan.close()
        return cleanup if cleanup is not None else result

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        """Serve the existing viewer client with its escaped configured title."""
        return get_html(title=title)

    @app.get("/api/descriptors")
    async def get_descriptors() -> list[dict[str, Any]]:
        """Expose supported controls and defaults from the supplied model."""
        return descriptor_dicts

    @app.post("/api/render", response_model=None)
    async def render(request: Request) -> dict[str, str] | JSONResponse:
        """Render the parsed active model once as the existing base64 PNG response."""
        parsed = await parsed_body(request, "/api/render")
        if isinstance(parsed, JSONResponse):
            return parsed
        assert isinstance(parsed, ModelRequest)
        data = render_bytes(parsed.model, "png")
        return (
            data
            if isinstance(data, JSONResponse)
            else {"image": base64.b64encode(data).decode("ascii")}
        )

    @app.post("/api/export/{fmt}", response_model=None)
    async def export(fmt: str, request: Request) -> Response:
        """Download one supported format from the same validated active model language."""
        _validate_export_format(fmt)
        fmt = fmt.lower()
        parsed = await parsed_body(request, "/api/export/{fmt}")
        if isinstance(parsed, JSONResponse):
            return parsed
        assert isinstance(parsed, ModelRequest)
        data = render_bytes(parsed.model, fmt)
        return (
            data
            if isinstance(data, JSONResponse)
            else Response(
                data,
                media_type={
                    "png": "image/png",
                    "svg": "image/svg+xml",
                    "pdf": "application/pdf",
                }.get(fmt, "application/octet-stream"),
                headers={
                    "Content-Disposition": f'attachment; filename="figure.{fmt}"'
                },
            )
        )

    @app.get("/api/config", response_model=None)
    async def get_config() -> dict[str, JsonValue] | JSONResponse:
        """Project stored config without rewriting drift or malformed bytes."""
        store = state()
        if not isinstance(store, ViewerState):
            return _refusal_response(store)
        result = store.load_config()
        if isinstance(result, MissingState):
            return {}
        return (
            result.value
            if isinstance(result, ConfigLoaded)
            else _refusal_response(result)
        )

    @app.get("/api/meta")
    async def get_meta() -> dict[str, str]:
        """Preserve the frontend's configured function-name default."""
        return {"function_name": figure_fn.__name__}

    @app.post("/api/config", response_model=None)
    @app.post("/api/save-state", response_model=None)
    async def post_config(request: Request) -> dict[str, str] | JSONResponse:
        """Update only fixed config from a complete active/config-tab request."""
        template = cast(str, request.scope["route"].path)
        parsed = await parsed_body(request, template)
        if isinstance(parsed, JSONResponse):
            return parsed
        assert isinstance(parsed, StateRequest)
        store = state()
        if not isinstance(store, ViewerState):
            return _refusal_response(store)
        result = store.save_config(parsed, figure_fn.__name__)
        return (
            {"status": "ok"}
            if isinstance(result, StateWritten)
            else _refusal_response(result)
        )

    @app.post("/api/preset", response_model=None)
    async def save_preset_endpoint(
        request: Request,
    ) -> dict[str, str] | JSONResponse:
        """Append a validated preset without projecting unrelated historical entries."""
        parsed = await parsed_body(request, "/api/preset")
        if isinstance(parsed, JSONResponse):
            return parsed
        assert isinstance(parsed, PresetRequest)
        store = state()
        if not isinstance(store, ViewerState):
            return _refusal_response(store)
        result = store.save_preset(parsed)
        return (
            {"status": "ok"}
            if isinstance(result, StateWritten)
            else _refusal_response(result)
        )

    @app.get("/api/presets", response_model=None)
    async def get_presets() -> list[dict[str, JsonValue]] | JSONResponse:
        """Preserve list success shape and explicitly refuse unsafe stored-state reads."""
        store = state()
        if not isinstance(store, ViewerState):
            return _refusal_response(store)
        result = store.load_presets()
        return (
            result.value
            if isinstance(result, PresetsLoaded)
            else _refusal_response(result)
        )

    @app.delete("/api/preset/{index}", response_model=None)
    async def delete_preset_endpoint(
        index: int,
    ) -> dict[str, str] | JSONResponse:
        """Delete one fixed-state preset, accepting a bodyless request and named misses."""
        store = state()
        if not isinstance(store, ViewerState):
            return _refusal_response(store)
        result = store.delete_preset(index)
        return (
            {"status": "ok"}
            if isinstance(result, StateWritten)
            else _refusal_response(result)
        )

    @app.get("/api/defaults")
    async def get_defaults() -> dict[str, Any]:
        """Return usable model defaults independently of stored-state corruption or drift."""
        return {
            descriptor.name: descriptor.default for descriptor in descriptors
        }

    @app.post("/api/script", response_model=None)
    async def generate_script(request: Request) -> Response:
        """Download source after bounded active-model validation without persistence."""
        parsed = await parsed_body(request, "/api/script")
        if isinstance(parsed, JSONResponse):
            return parsed
        assert isinstance(parsed, ModelRequest)
        try:
            code = _generate_script(
                parsed.model, param_model, figure_fn, script_root
            )
        except Exception:  # noqa: BLE001 -- contain arbitrary trusted callback/source failures
            return JSONResponse(
                {
                    "detail": "Script generation failed.",
                    "code": "callback_failed",
                },
                status_code=500,
            )
        return Response(
            code.encode("utf-8"),
            media_type="text/x-python",
            headers={
                "Content-Disposition": 'attachment; filename="generate_figure.py"'
            },
        )

    @app.post("/api/save-server/image/{fmt}", response_model=None)
    async def save_image_server(
        fmt: str, request: Request
    ) -> dict[str, Any] | JSONResponse:
        """Save one staged image to every prechecked create-only destination."""
        _validate_export_format(fmt)
        parsed = await parsed_body(request, "/api/save-server/image/{fmt}")
        if isinstance(parsed, JSONResponse):
            return parsed
        assert isinstance(parsed, SaveRequest)
        result = save_image(parsed, fmt.lower())
        if isinstance(result, JSONResponse):
            return result
        if not isinstance(result, SaveReceipt):
            return _refusal_response(result)
        return {
            "status": "ok",
            "path": result.primary_display,
            "filename": result.primary,
            "copied_to": list(result.copy_displays),
        }

    @app.post("/api/save-server/script", response_model=None)
    async def save_script_server(
        request: Request,
    ) -> dict[str, str] | JSONResponse:
        """Save source only below the script root, preserving every existing target."""
        parsed = await parsed_body(request, "/api/save-server/script")
        if isinstance(parsed, JSONResponse):
            return parsed
        assert isinstance(parsed, SaveRequest)
        result = save_script(parsed)
        if isinstance(result, JSONResponse):
            return result
        if not isinstance(result, SaveReceipt):
            return _refusal_response(result)
        return {
            "status": "ok",
            "path": result.primary_display,
            "filename": result.primary,
        }

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

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        """Retain the frontend heartbeat independently of persistence capability."""
        return {"status": "ok"}

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


# ============================================================================
# Helpers
# ============================================================================


def _validate_export_format(fmt: str) -> None:
    """Reject an unsupported export format with a 400 (not a 500).

    Without this, ``savefig(format=<bogus>)`` raises deep in matplotlib
    and FastAPI returns an opaque 500.
    """
    if fmt.lower() not in _SUPPORTED_EXPORT_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported export format {fmt!r}. Supported: "
                f"{', '.join(sorted(_SUPPORTED_EXPORT_FORMATS))}."
            ),
        )


def _timestamp_slug() -> str:
    """Return a compact timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:12]


def _generate_script(
    model: ParamModel,
    model_cls: type[ParamModel],
    figure_fn: Callable[..., Any],
    script_dir: Path,
) -> str:
    """Generate a standalone Python script that reproduces the figure.

    The script includes the figure function source, the ParamModel class
    source, and the current parameter values.
    """
    # Get source of the figure function and model class
    try:
        fn_source = textwrap.dedent(inspect.getsource(figure_fn))
    except (OSError, TypeError):
        fn_source = f"# Could not retrieve source for {figure_fn.__name__}"

    try:
        model_source = textwrap.dedent(inspect.getsource(model_cls))
    except (OSError, TypeError):
        model_source = f"# Could not retrieve source for {model_cls.__name__}"

    # Get the module where figure_fn is defined for imports
    fn_module = inspect.getmodule(figure_fn)
    try:
        module_source = inspect.getsource(fn_module)  # type: ignore[arg-type]
        # Extract import lines from the top of the module
        import_lines = []
        for line in module_source.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                # Skip the 'run' function import (not needed in standalone)
                if "import run" in stripped or "import run," in stripped:
                    # Keep ParamModel but drop run
                    cleaned = stripped.replace(", run", "").replace("run, ", "")
                    if "import" in cleaned and cleaned != stripped:
                        import_lines.append(cleaned)
                else:
                    import_lines.append(line)
            elif (
                stripped
                and not stripped.startswith(("#", '"""', "'''", '"'))
                and import_lines
                and not stripped.startswith(("import ", "from "))
            ):
                # Stop after the import block ends
                break
        imports_block = "\n".join(import_lines)
    except (OSError, TypeError):
        imports_block = (
            "import matplotlib.pyplot as plt\n"
            "from matplotlib.figure import Figure\n"
            "from dartwork_mpl.ui import ParamModel"
        )

    # Serialize current params
    params_dict = model.model_dump()
    params_lines = []
    for key, val in params_dict.items():
        params_lines.append(f"    {key}={val!r},")
    params_str = "\n".join(params_lines)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return f'''"""Auto-generated figure script.

Generated at: {ts}
Parameters: {model_cls.__name__}
Function:   {figure_fn.__name__}
"""

{imports_block}
from pydantic import Field

from dartwork_mpl.util import save_formats


{model_source}


{fn_source}


if __name__ == "__main__":
    params = {model_cls.__name__}(
{params_str}
    )
    fig = {figure_fn.__name__}(params)
    save_formats(fig, "{figure_fn.__name__}")
    print("Saved: {figure_fn.__name__}.[svg|png|pdf|eps]")
    plt.show()
'''
