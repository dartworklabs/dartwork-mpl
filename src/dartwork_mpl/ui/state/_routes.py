"""The viewer-state routes: the last-used config, the save-state snapshot and named presets.

Surface (through the ``state`` package): ``routes`` and ``GRANTS``.
"""

from collections.abc import Callable
from typing import cast

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..params import InputFailure, ParamDescriptor, ParamModel
from ..platform.access import Grant
from ..platform.http import refusal_response, request_json
from ..platform.json_bounds import JsonValue
from ._language import PresetRequest, StateRequest, parse_request
from ._store import FileFailure, MissingState, StateWritten
from ._viewer_state import ConfigLoaded, PresetsLoaded, ViewerState

# Local-only grants for the routes below (the entry point composes them).
GRANTS: dict[tuple[str, str], Grant] = {
    ("GET", "/api/config"): "local-read",
    ("GET", "/api/presets"): "local-read",
    ("POST", "/api/save-state"): "local-effect",
    ("POST", "/api/config"): "local-effect",
    ("POST", "/api/preset"): "local-effect",
    ("DELETE", "/api/preset/{index}"): "local-effect",
}


def routes(
    *,
    param_model: type[ParamModel],
    descriptors: list[ParamDescriptor],
    function_name: str,
    state: Callable[[], ViewerState | FileFailure],
) -> APIRouter:
    """Serve state for ``param_model``; ``state`` borrows the lifespan-owned store or its startup refusal."""
    router = APIRouter()

    async def parsed_body(
        request: Request, template: str
    ) -> StateRequest | PresetRequest | JSONResponse:
        """Recognize the complete bounded endpoint language without downstream raw reads."""
        value = await request_json(request)
        if isinstance(value, JSONResponse):
            return value
        if isinstance(value, InputFailure):
            return refusal_response(value)
        parsed = parse_request(template, value, param_model, descriptors)
        return (
            refusal_response(parsed)
            if isinstance(parsed, InputFailure)
            else parsed
        )

    @router.get("/api/config", response_model=None)
    async def get_config() -> dict[str, JsonValue] | JSONResponse:
        """Project stored config without rewriting drift or malformed bytes."""
        store = state()
        if not isinstance(store, ViewerState):
            return refusal_response(store)
        result = store.load_config()
        if isinstance(result, MissingState):
            return {}
        return (
            result.value
            if isinstance(result, ConfigLoaded)
            else refusal_response(result)
        )

    @router.post("/api/config", response_model=None)
    @router.post("/api/save-state", response_model=None)
    async def post_config(request: Request) -> dict[str, str] | JSONResponse:
        """Update only fixed config from a complete active/config-tab request."""
        template = cast(str, request.scope["route"].path)
        parsed = await parsed_body(request, template)
        if isinstance(parsed, JSONResponse):
            return parsed
        assert isinstance(parsed, StateRequest)
        store = state()
        if not isinstance(store, ViewerState):
            return refusal_response(store)
        result = store.save_config(parsed, function_name)
        return (
            {"status": "ok"}
            if isinstance(result, StateWritten)
            else refusal_response(result)
        )

    @router.post("/api/preset", response_model=None)
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
            return refusal_response(store)
        result = store.save_preset(parsed)
        return (
            {"status": "ok"}
            if isinstance(result, StateWritten)
            else refusal_response(result)
        )

    @router.get("/api/presets", response_model=None)
    async def get_presets() -> list[dict[str, JsonValue]] | JSONResponse:
        """Preserve list success shape and explicitly refuse unsafe stored-state reads."""
        store = state()
        if not isinstance(store, ViewerState):
            return refusal_response(store)
        result = store.load_presets()
        return (
            result.value
            if isinstance(result, PresetsLoaded)
            else refusal_response(result)
        )

    @router.delete("/api/preset/{index}", response_model=None)
    async def delete_preset_endpoint(
        index: int,
    ) -> dict[str, str] | JSONResponse:
        """Delete one fixed-state preset, accepting a bodyless request and named misses."""
        store = state()
        if not isinstance(store, ViewerState):
            return refusal_response(store)
        result = store.delete_preset(index)
        return (
            {"status": "ok"}
            if isinstance(result, StateWritten)
            else refusal_response(result)
        )

    return router
