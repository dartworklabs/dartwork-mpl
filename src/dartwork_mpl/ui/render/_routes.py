"""The render routes: the live PNG preview, format downloads and server image saves.

Each route parses its own body language (the active model, or a save
request) and its ``{fmt}`` segment before any callback runs. Refusals go to
the injected ``refuse`` edge, which owns their HTTP status. Surface (through
the ``render`` package): ``routes``, ``GRANTS``, ``RenderRefusal`` and
``UnsupportedFormat``.
"""

import base64
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeAlias, TypeVar

import matplotlib.pyplot as plt
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from matplotlib.figure import Figure

from ...io import save_formats
from ..params import (
    Control,
    InputFailure,
    ModelRequest,
    ParamModel,
    parse_model_request,
)
from ..platform.access import Grant
from ..platform.fs import FsFailure, RootScope
from ..platform.http import CallbackFailed, UnsupportedMediaType, request_json
from ..platform.json_bounds import JsonValue
from ..saving import (
    PreparedSave,
    SaveInputFailure,
    SaveReceipt,
    SaveRequest,
    commit_save,
    parse_output,
    parse_save_request,
    prepare_save,
    requested_name,
)
from ._figure import (
    ExportFormat,
    UnsupportedFormat,
    _figure_to_bytes,
    parse_export_format,
)

_Parsed = TypeVar("_Parsed")

# Every refusal these routes can answer with.
RenderRefusal: TypeAlias = (
    UnsupportedMediaType
    | SaveInputFailure
    | UnsupportedFormat
    | FsFailure
    | CallbackFailed
)

# Local-only grants for the routes below (the entry point composes them).
GRANTS: dict[tuple[str, str], Grant] = {
    ("POST", "/api/render"): "local-effect",
    ("POST", "/api/export/{fmt}"): "local-effect",
    ("POST", "/api/save-server/image/{fmt}"): "local-effect",
}


def routes(
    *,
    figure_fn: Callable[[Any], Figure],
    param_model: type[ParamModel],
    descriptors: list[Control],
    roots: Callable[[], RootScope | FsFailure],
    refuse: Callable[[RenderRefusal], JSONResponse],
) -> APIRouter:
    """Serve renders of ``figure_fn``; ``roots`` borrows the lifespan-owned output roots.

    ``refuse`` turns each refusal into its error response.
    """
    router = APIRouter()

    async def parsed_body(
        request: Request,
        parse: Callable[[JsonValue], _Parsed | SaveInputFailure],
    ) -> _Parsed | JSONResponse:
        """Read the bounded body once and parse it with the route's own parser.

        Media, decoding and parser refusals come back as their error responses.
        """
        value = await request_json(request)
        if isinstance(value, UnsupportedMediaType | InputFailure):
            return refuse(value)
        parsed = parse(value)
        return (
            refuse(parsed) if isinstance(parsed, SaveInputFailure) else parsed
        )

    def model_request(value: JsonValue) -> ModelRequest | InputFailure:
        """Parse a body that is exactly the active parameters of ``param_model``."""
        return parse_model_request(value, param_model, descriptors)

    def save_request(value: JsonValue) -> SaveRequest | SaveInputFailure:
        """Parse a server-save body against ``param_model``."""
        return parse_save_request(value, param_model, descriptors)

    def render_bytes(model: ParamModel, fmt: str) -> bytes | CallbackFailed:
        """Run callbacks synchronously in the event loop and contain trusted callback errors."""
        try:
            return _figure_to_bytes(figure_fn, model, fmt)
        except Exception:  # noqa: BLE001 -- trusted callbacks may raise arbitrary errors
            return CallbackFailed("The figure callback failed.")

    def save_image(
        parsed: SaveRequest, fmt: str
    ) -> SaveReceipt | FsFailure | SaveInputFailure | CallbackFailed:
        """Plan every sink before a callback; stage unchanged save_formats bytes privately.

        A ``.png``/``.svg``/``.pdf`` suffix on the requested name overrides
        ``fmt``; otherwise ``fmt`` becomes the extension.
        """
        scope = roots()
        if not isinstance(scope, RootScope):
            return scope
        name = requested_name(parsed, figure_fn.__name__)
        for extension in (".png", ".svg", ".pdf"):
            if name.lower().endswith(extension):
                fmt, name = extension[1:], name[: -len(extension)]
                break
        output = parse_output(f"{name}.{fmt}")
        if isinstance(output, SaveInputFailure):
            return output
        plan = prepare_save(scope, output, include_copies=True)
        if not isinstance(plan, PreparedSave):
            return plan
        result: SaveReceipt | FsFailure | SaveInputFailure | CallbackFailed
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
            result = CallbackFailed(
                "The figure callback or image export failed."
            )
        finally:
            cleanup = plan.close()
        return cleanup if cleanup is not None else result

    @router.post("/api/render", response_model=None)
    async def render(request: Request) -> dict[str, str] | JSONResponse:
        """Render the parsed active model once as the existing base64 PNG response."""
        parsed = await parsed_body(request, model_request)
        if isinstance(parsed, JSONResponse):
            return parsed
        data = render_bytes(parsed.model, "png")
        if isinstance(data, CallbackFailed):
            return refuse(data)
        return {"image": base64.b64encode(data).decode("ascii")}

    @router.post("/api/export/{fmt}", response_model=None)
    async def export(fmt: str, request: Request) -> Response:
        """Download one supported format from the same validated active model language."""
        export_format = parse_export_format(fmt)
        if not isinstance(export_format, ExportFormat):
            return refuse(export_format)
        fmt = export_format.name
        parsed = await parsed_body(request, model_request)
        if isinstance(parsed, JSONResponse):
            return parsed
        data = render_bytes(parsed.model, fmt)
        return (
            refuse(data)
            if isinstance(data, CallbackFailed)
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

    @router.post("/api/save-server/image/{fmt}", response_model=None)
    async def save_image_server(
        fmt: str, request: Request
    ) -> dict[str, Any] | JSONResponse:
        """Save one staged image to every prechecked create-only destination."""
        export_format = parse_export_format(fmt)
        if not isinstance(export_format, ExportFormat):
            return refuse(export_format)
        parsed: SaveRequest | JSONResponse = await parsed_body(
            request, save_request
        )
        if isinstance(parsed, JSONResponse):
            return parsed
        result = save_image(parsed, export_format.name)
        if not isinstance(result, SaveReceipt):
            return refuse(result)
        return {
            "status": "ok",
            "path": result.primary_display,
            "filename": result.primary,
            "copied_to": list(result.copy_displays),
        }

    return router
