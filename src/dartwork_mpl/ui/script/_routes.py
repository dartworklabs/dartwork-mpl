"""The script routes: download the reproducing script, or save it below the script root.

Each route parses its own body language (the active model, or a save
request) before generating source. Surface (through the ``script`` package):
``routes`` and ``GRANTS``.
"""

import io
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from matplotlib.figure import Figure

from ..params import (
    Control,
    InputFailure,
    ModelRequest,
    ParamModel,
    parse_model_request,
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
    requested_name,
)
from ._generate import _generate_script

_Parsed = TypeVar("_Parsed")

# Local-only grants for the routes below (the entry point composes them).
GRANTS: dict[tuple[str, str], Grant] = {
    ("POST", "/api/script"): "local-effect",
    ("POST", "/api/save-server/script"): "local-effect",
}


def routes(
    *,
    figure_fn: Callable[[Any], Figure],
    param_model: type[ParamModel],
    descriptors: list[Control],
    script_root: Path,
    roots: Callable[[], RootScope | FsFailure],
) -> APIRouter:
    """Serve scripts for ``figure_fn``; ``roots`` borrows the lifespan-owned output roots."""
    router = APIRouter()

    async def parsed_body(
        request: Request,
        parse: Callable[[JsonValue], _Parsed | SaveInputFailure],
    ) -> _Parsed | JSONResponse:
        """Read the bounded body once and parse it with the route's own parser.

        Media, decoding and parser refusals come back as their error responses.
        """
        value = await request_json(request)
        if isinstance(value, JSONResponse):
            return value
        if isinstance(value, InputFailure):
            return refusal_response(value)
        parsed = parse(value)
        return (
            refusal_response(parsed)
            if isinstance(parsed, SaveInputFailure)
            else parsed
        )

    def model_request(value: JsonValue) -> ModelRequest | InputFailure:
        """Parse a body that is exactly the active parameters of ``param_model``."""
        return parse_model_request(value, param_model, descriptors)

    def save_request(value: JsonValue) -> SaveRequest | SaveInputFailure:
        """Parse a server-save body against ``param_model``."""
        return parse_save_request(value, param_model, descriptors)

    def save_script(
        parsed: SaveRequest,
    ) -> SaveReceipt | FsFailure | SaveInputFailure | JSONResponse:
        """Prepare the primary script sink before source generation and create it exclusively.

        The saved name always ends in a single ``.py``.
        """
        scope = roots()
        if not isinstance(scope, RootScope):
            return scope
        name = requested_name(parsed, figure_fn.__name__)
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
        parsed = await parsed_body(request, model_request)
        if isinstance(parsed, JSONResponse):
            return parsed
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
        parsed: SaveRequest | JSONResponse = await parsed_body(
            request, save_request
        )
        if isinstance(parsed, JSONResponse):
            return parsed
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
