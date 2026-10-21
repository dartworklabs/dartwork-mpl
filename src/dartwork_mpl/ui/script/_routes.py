"""The script routes: download the reproducing script, or save it below the script root.

Surface (through the ``script`` package): ``routes`` and ``GRANTS``.
"""

import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from matplotlib.figure import Figure

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
from ._generate import _generate_script

# Local-only grants for the routes below (the entry point composes them).
GRANTS: dict[tuple[str, str], Grant] = {
    ("POST", "/api/script"): "local-effect",
    ("POST", "/api/save-server/script"): "local-effect",
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
    if route_template == "/api/script":
        return parse_model_request(body, model_cls, descriptors)
    if route_template == "/api/save-server/script":
        return parse_save_request(body, model_cls, descriptors)
    return InvalidRequest()


def routes(
    *,
    figure_fn: Callable[[Any], Figure],
    param_model: type[ParamModel],
    descriptors: list[ParamDescriptor],
    script_root: Path,
    roots: Callable[[], RootScope | FsFailure],
) -> APIRouter:
    """Serve scripts for ``figure_fn``; ``roots`` borrows the lifespan-owned output roots."""
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

    def save_script(
        parsed: SaveRequest,
    ) -> SaveReceipt | FsFailure | SaveInputFailure | JSONResponse:
        """Prepare the primary script sink before source generation and create it exclusively."""
        scope = roots()
        if not isinstance(scope, RootScope):
            return scope
        name = (
            parsed.output.filename
            if parsed.output
            else f"{figure_fn.__name__}_{timestamp_slug()}"
        )
        if name.lower().endswith(".py"):
            name = name[:-3]
        output = parse_output(f"{name}.py")
        if isinstance(output, SaveInputFailure):
            return output
        plan = prepare_save(scope, output, include_copies=False)
        if not isinstance(plan, PreparedSave):
            return plan
        result: SaveReceipt | FsFailure | SaveInputFailure | JSONResponse
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

    @router.post("/api/script", response_model=None)
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

    @router.post("/api/save-server/script", response_model=None)
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
            return refusal_response(result)
        return {
            "status": "ok",
            "path": result.primary_display,
            "filename": result.primary,
        }

    return router
