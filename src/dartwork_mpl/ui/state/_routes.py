"""The viewer-state routes: the last-used config, the save-state snapshot and named presets.

Each route parses its own body language. ``/api/config`` and
``/api/save-state`` keep one operation name (``post_config``) and summary in
the OpenAPI document, as when one handler served both. Refusals go to the
injected ``refuse`` edge, which owns their HTTP status. Surface (through the
``state`` package): ``routes``, ``GRANTS`` and ``StateRefusal``.
"""

from collections.abc import Callable
from typing import TypeAlias, TypeVar

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..params import Control, InputFailure, ParamModel
from ..platform.access import Grant
from ..platform.http import UnsupportedMediaType, request_json
from ..platform.json_bounds import JsonValue
from ._language import (
    PresetRequest,
    StateUpdate,
    parse_full_state_update,
    parse_params_update,
    parse_preset_request,
)
from ._store import FileFailure, MissingState, StateWritten
from ._viewer_state import (
    ConfigLoaded,
    PresetNotFound,
    PresetsLoaded,
    ViewerState,
)

# Local-only grants for the routes below (the entry point composes them).
GRANTS: dict[tuple[str, str], Grant] = {
    ("GET", "/api/config"): "local-read",
    ("GET", "/api/presets"): "local-read",
    ("POST", "/api/save-state"): "local-effect",
    ("POST", "/api/config"): "local-effect",
    ("POST", "/api/preset"): "local-effect",
    ("DELETE", "/api/preset/{index}"): "local-effect",
}

_Parsed = TypeVar("_Parsed")

# Every refusal these routes can answer with.
StateRefusal: TypeAlias = (
    UnsupportedMediaType | InputFailure | FileFailure | PresetNotFound
)


def routes(
    *,
    param_model: type[ParamModel],
    descriptors: list[Control],
    function_name: str,
    state: Callable[[], ViewerState | FileFailure],
    refuse: Callable[[StateRefusal], JSONResponse],
) -> APIRouter:
    """Serve state for ``param_model``; ``state`` borrows the lifespan-owned store or its startup refusal.

    ``refuse`` turns each refusal into its error response.
    """
    router = APIRouter()

    async def parsed_body(
        request: Request,
        parse: Callable[
            [JsonValue, type[ParamModel], list[Control]], _Parsed | InputFailure
        ],
    ) -> _Parsed | JSONResponse:
        """Read the bounded body once and parse it with the route's own parser.

        Media, decoding and parser refusals come back as their error responses.
        """
        value = await request_json(request)
        if isinstance(value, UnsupportedMediaType | InputFailure):
            return refuse(value)
        parsed = parse(value, param_model, descriptors)
        return refuse(parsed) if isinstance(parsed, InputFailure) else parsed

    async def save_config(
        request: Request,
        parse: Callable[
            [JsonValue, type[ParamModel], list[Control]],
            StateUpdate | InputFailure,
        ],
    ) -> dict[str, str] | JSONResponse:
        """Parse one config update with ``parse`` and replace the stored config with it."""
        parsed: StateUpdate | JSONResponse = await parsed_body(request, parse)
        if isinstance(parsed, JSONResponse):
            return parsed
        store = state()
        if not isinstance(store, ViewerState):
            return refuse(store)
        result = store.save_config(parsed, function_name)
        return (
            {"status": "ok"}
            if isinstance(result, StateWritten)
            else refuse(result)
        )

    @router.get("/api/config", response_model=None)
    async def get_config() -> dict[str, JsonValue] | JSONResponse:
        """Project stored config without rewriting drift or malformed bytes."""
        store = state()
        if not isinstance(store, ViewerState):
            return refuse(store)
        result = store.load_config()
        if isinstance(result, MissingState):
            return {}
        return (
            result.value if isinstance(result, ConfigLoaded) else refuse(result)
        )

    # Registered before ``/api/config`` (as the stacked decorators did) so the
    # OpenAPI paths keep their order; the shared name and docstring keep the
    # operation id suffixes, summary and description.
    @router.post("/api/save-state", response_model=None, name="post_config")
    async def post_full_state(
        request: Request,
    ) -> dict[str, str] | JSONResponse:
        """Update only fixed config from a complete active/config-tab request."""
        return await save_config(request, parse_full_state_update)

    @router.post("/api/config", response_model=None, name="post_config")
    async def post_config(request: Request) -> dict[str, str] | JSONResponse:
        """Update only fixed config from a complete active/config-tab request."""
        return await save_config(request, parse_params_update)

    @router.post("/api/preset", response_model=None)
    async def save_preset_endpoint(
        request: Request,
    ) -> dict[str, str] | JSONResponse:
        """Append a validated preset without projecting unrelated historical entries."""
        parsed: PresetRequest | JSONResponse = await parsed_body(
            request, parse_preset_request
        )
        if isinstance(parsed, JSONResponse):
            return parsed
        store = state()
        if not isinstance(store, ViewerState):
            return refuse(store)
        result = store.save_preset(parsed)
        return (
            {"status": "ok"}
            if isinstance(result, StateWritten)
            else refuse(result)
        )

    @router.get("/api/presets", response_model=None)
    async def get_presets() -> list[dict[str, JsonValue]] | JSONResponse:
        """Preserve list success shape and explicitly refuse unsafe stored-state reads."""
        store = state()
        if not isinstance(store, ViewerState):
            return refuse(store)
        result = store.load_presets()
        return (
            result.value
            if isinstance(result, PresetsLoaded)
            else refuse(result)
        )

    @router.delete("/api/preset/{index}", response_model=None)
    async def delete_preset_endpoint(
        index: int,
    ) -> dict[str, str] | JSONResponse:
        """Delete one fixed-state preset, accepting a bodyless request and named misses."""
        store = state()
        if not isinstance(store, ViewerState):
            return refuse(store)
        result = store.delete_preset(index)
        return (
            {"status": "ok"}
            if isinstance(result, StateWritten)
            else refuse(result)
        )

    return router
