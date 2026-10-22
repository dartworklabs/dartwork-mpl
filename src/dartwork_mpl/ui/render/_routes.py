"""The render routes: the live PNG preview, format downloads and server image saves.

Surface (through the ``render`` package): ``routes`` and ``GRANTS``.
"""

import base64
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from matplotlib.figure import Figure

from ...io import save_formats
from ..params import (
    InputFailure,
    InvalidRequest,
    ModelRequest,
    ParamDescriptor,
    ParamModel,
    parse_model_request,
    request_object,
)
from ..platform.access import Grant
from ..platform.fs import FsFailure, RootScope
from ..platform.http import refusal_response, request_json
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
    timestamp_slug,
)
from ._figure import _figure_to_bytes, _validate_export_format

# Local-only grants for the routes below (the entry point composes them).
GRANTS: dict[tuple[str, str], Grant] = {
    ("POST", "/api/render"): "local-effect",
    ("POST", "/api/export/{fmt}"): "local-effect",
    ("POST", "/api/save-server/image/{fmt}"): "local-effect",
}


def parse_request(
    route_template: str,
    value: JsonValue,
    model_cls: type[ParamModel],
    descriptors: list[ParamDescriptor],
) -> ModelRequest | SaveRequest | SaveInputFailure:
    """Consume the entire endpoint schema and return values the shell can use directly."""
    body = request_object(value)
    if not isinstance(body, dict):
        return body
    if route_template in {"/api/render", "/api/export/{fmt}"}:
        return parse_model_request(body, model_cls, descriptors)
    if route_template == "/api/save-server/image/{fmt}":
        return parse_save_request(body, model_cls, descriptors)
    return InvalidRequest()


def routes(
    *,
    figure_fn: Callable[[Any], Figure],
    param_model: type[ParamModel],
    descriptors: list[ParamDescriptor],
    roots: Callable[[], RootScope | FsFailure],
) -> APIRouter:
    """Serve renders of ``figure_fn``; ``roots`` borrows the lifespan-owned output roots."""
    router = APIRouter()

    async def parsed_body(
        request: Request, template: str
    ) -> ModelRequest | SaveRequest | JSONResponse:
        """Recognize the complete bounded endpoint language without downstream raw reads."""
        value = await request_json(request)
        if isinstance(value, JSONResponse):
            return value
        if isinstance(value, InputFailure):
            return refusal_response(value)
        parsed = parse_request(template, value, param_model, descriptors)
        return (
            refusal_response(parsed)
            if isinstance(parsed, SaveInputFailure)
            else parsed
        )

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
    ) -> SaveReceipt | FsFailure | SaveInputFailure | JSONResponse:
        """Plan every sink before a callback; stage unchanged save_formats bytes privately."""
        scope = roots()
        if not isinstance(scope, RootScope):
            return scope
        name = (
            parsed.output.filename
            if parsed.output
            else f"{figure_fn.__name__}_{timestamp_slug()}"
        )
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
        result: SaveReceipt | FsFailure | SaveInputFailure | JSONResponse
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

    @router.post("/api/render", response_model=None)
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

    @router.post("/api/export/{fmt}", response_model=None)
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

    @router.post("/api/save-server/image/{fmt}", response_model=None)
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
            return refusal_response(result)
        return {
            "status": "ok",
            "path": result.primary_display,
            "filename": result.primary,
            "copied_to": list(result.copy_displays),
        }

    return router
