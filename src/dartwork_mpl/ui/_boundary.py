"""Pure viewer route grants and the bounded request/state languages.

No function opens files or sockets. The HTTP shell supplies decoded JSON and
route names; the filesystem shell consumes only parsed relative outputs.
Local access checks and the JSON decoder live in ``platform``.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Literal, TypeAlias, cast

from .params import InvalidRequest, ParamModel, parse_active
from .platform.access import Grant
from .platform.json_bounds import (
    MAX_REQUEST_BYTES,
    JsonValue,
    LimitExceeded,
    MalformedInput,
    bounded,
    decode_json,
)

if TYPE_CHECKING:
    from .params import ParamDescriptor

StateKind: TypeAlias = Literal["config", "presets"]

MAX_CONFIG_BYTES = MAX_REQUEST_BYTES
MAX_PRESET_BYTES = 8 * 1024 * 1024
MAX_TABS = 64
MAX_PRESETS = 1000
MAX_LABEL_BYTES = 256
MAX_OUTPUT_BYTES = 1024
DEFAULT_FIG_WIDTH = 70


@dataclass(frozen=True)
class InvalidOutput:
    """An output name cannot denote a safe portable relative path."""

    detail: str = "Filename must be a bounded safe relative path."
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "invalid_output_path"


InputFailure: TypeAlias = (
    MalformedInput | LimitExceeded | InvalidRequest | InvalidOutput
)


@dataclass(frozen=True)
class InvalidStoredState:
    """Existing state is structurally invalid and must retain its original bytes."""

    detail: str = "Stored viewer state is invalid; preserve the existing file."
    status_code: ClassVar[int] = 409
    code: ClassVar[str] = "invalid_stored_state"


# The approved local-only policy grants these effects to native local clients.
# Host and browser source checks constrain that grant; they are not identity.
ROUTE_POLICY: dict[tuple[str, str], Grant] = {
    ("GET", "/openapi.json"): "local-read",
    ("HEAD", "/openapi.json"): "local-read",
    ("GET", "/docs"): "local-read",
    ("HEAD", "/docs"): "local-read",
    ("GET", "/docs/oauth2-redirect"): "local-read",
    ("HEAD", "/docs/oauth2-redirect"): "local-read",
    ("GET", "/redoc"): "local-read",
    ("HEAD", "/redoc"): "local-read",
    ("GET", "/"): "local-read",
    ("GET", "/api/descriptors"): "local-read",
    ("GET", "/api/config"): "local-read",
    ("GET", "/api/meta"): "local-read",
    ("GET", "/api/presets"): "local-read",
    ("GET", "/api/defaults"): "local-read",
    ("GET", "/api/health"): "local-read",
    ("GET", "<unmatched>"): "local-read",
    ("HEAD", "<unmatched>"): "local-read",
    ("POST", "/api/render"): "local-effect",
    ("POST", "/api/export/{fmt}"): "local-effect",
    ("POST", "/api/script"): "local-effect",
    ("POST", "/api/save-state"): "local-effect",
    ("POST", "/api/config"): "local-effect",
    ("POST", "/api/preset"): "local-effect",
    ("DELETE", "/api/preset/{index}"): "local-effect",
    ("POST", "/api/save-server/image/{fmt}"): "local-effect",
    ("POST", "/api/save-server/script"): "local-effect",
    ("POST", "/api/reload"): "local-effect",
}


def encode_state(value: JsonValue, *, max_bytes: int) -> bytes | InputFailure:
    """Bound the complete next-state value and its UTF-8 serialization before writes."""
    refusal = bounded(value)
    if refusal is not None:
        return refusal
    try:
        raw = (
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeEncodeError):
        return MalformedInput()
    return raw if len(raw) <= max_bytes else LimitExceeded()


def _output_parts(filename: str) -> tuple[str, ...] | None:
    """Recognize portable relative paths without filesystem normalization or I/O."""
    try:
        if len(filename.encode("utf-8")) > MAX_OUTPUT_BYTES:
            return None
        parts = tuple(filename.split("/"))
        if not parts or any(
            not part.strip()
            or part in {".", ".."}
            or len(part.encode("utf-8")) > 255
            for part in parts
        ):
            return None
    except UnicodeEncodeError:
        return None
    if "\\" in filename or ":" in filename or "\x00" in filename:
        return None
    return parts


@dataclass(frozen=True)
class RelativeOutput:
    """A parsed portable relative filename; construction belongs to parse_output."""

    parts: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject illegal trusted construction in addition to the owner inventory."""
        if not self.parts or _output_parts("/".join(self.parts)) != self.parts:
            raise ValueError("Invalid relative output")

    @property
    def filename(self) -> str:
        """Return the accepted relative spelling for receipts and staging names."""
        return "/".join(self.parts)


def parse_output(filename: str) -> RelativeOutput | InputFailure:
    """Parse an output name once before directory-handle planning and effects."""
    parts = _output_parts(filename)
    return RelativeOutput(parts) if parts is not None else InvalidOutput()


@dataclass(frozen=True)
class Tab:
    """An inactive tab has structurally checked declared params, not active values."""

    id: int
    name: str
    params: dict[str, JsonValue]


@dataclass(frozen=True)
class ModelRequest:
    """A render/download request contains only the validated active model."""

    model: ParamModel


@dataclass(frozen=True)
class StateRequest:
    """A config edit distinguishes omitted tab/width fields from explicit values."""

    model: ParamModel
    tabs: tuple[Tab, ...] | None = None
    fig_width: int | None = None


@dataclass(frozen=True)
class PresetRequest:
    """A named preset carries a bounded label and validated active model."""

    label: str
    model: ParamModel


@dataclass(frozen=True)
class SaveRequest:
    """A server save carries a validated model and an optional parsed output name."""

    model: ParamModel
    output: RelativeOutput | None = None


ParsedRequest: TypeAlias = (
    ModelRequest | StateRequest | PresetRequest | SaveRequest
)


def _label(value: object) -> InvalidRequest | LimitExceeded | None:
    """Check string labels independently from the larger generic JSON string limit."""
    if not isinstance(value, str):
        return InvalidRequest()
    return (
        LimitExceeded()
        if len(value.encode("utf-8")) > MAX_LABEL_BYTES
        else None
    )


def _tabs(
    value: JsonValue, field_names: frozenset[str] | None
) -> tuple[Tab, ...] | InputFailure:
    """Parse unique integer tab ids and structural params without active-model validation."""
    if not isinstance(value, list):
        return InvalidRequest()
    if len(value) > MAX_TABS:
        return LimitExceeded()
    result = []
    ids = set()
    for entry in value:
        if not isinstance(entry, dict) or entry.keys() != {
            "id",
            "name",
            "params",
        }:
            return InvalidRequest()
        tab_id, name, params = entry["id"], entry["name"], entry["params"]
        if (
            type(tab_id) is not int
            or tab_id in ids
            or not isinstance(params, dict)
        ):
            return InvalidRequest()
        refusal = _label(name)
        if refusal is not None:
            return refusal
        if field_names is not None and params.keys() - field_names:
            return InvalidRequest()
        ids.add(tab_id)
        result.append(Tab(tab_id, cast(str, name), params))
    return tuple(result)


def parse_request(
    route_template: str,
    value: JsonValue,
    model_cls: type[ParamModel],
    descriptors: list[ParamDescriptor],
) -> ParsedRequest | InputFailure:
    """Consume the entire endpoint schema and return values the shell can use directly."""
    refusal = bounded(value)
    if refusal is not None:
        return (
            refusal if isinstance(refusal, LimitExceeded) else InvalidRequest()
        )
    if not isinstance(value, dict):
        return InvalidRequest()
    model_routes = {
        "/api/render",
        "/api/export/{fmt}",
        "/api/script",
        "/api/config",
    }
    if route_template in model_routes:
        model = parse_active(value, model_cls, descriptors)
        if isinstance(model, InvalidRequest):
            return model
        return (
            StateRequest(model)
            if route_template == "/api/config"
            else ModelRequest(model)
        )
    if route_template == "/api/save-state":
        if value.keys() - {"params", "tabs", "figWidth"}:
            return InvalidRequest()
        model = parse_active(value.get("params", {}), model_cls, descriptors)
        if isinstance(model, InvalidRequest):
            return model
        tabs = _tabs(value.get("tabs", []), frozenset(model_cls.model_fields))
        if isinstance(tabs, InputFailure):
            return tabs
        width = value.get("figWidth")
        if "figWidth" in value and (
            type(width) is not int or not 30 <= width <= 100
        ):
            return InvalidRequest()
        return StateRequest(model, tabs, cast(int | None, width))
    if route_template == "/api/preset":
        if value.keys() != {"label", "params"}:
            return InvalidRequest()
        label_refusal = _label(value["label"])
        if label_refusal is not None:
            return label_refusal
        model = parse_active(value["params"], model_cls, descriptors)
        return (
            model
            if isinstance(model, InvalidRequest)
            else PresetRequest(cast(str, value["label"]), model)
        )
    if route_template in {
        "/api/save-server/image/{fmt}",
        "/api/save-server/script",
    }:
        if "params" not in value or value.keys() - {"params", "filename"}:
            return InvalidRequest()
        model = parse_active(value["params"], model_cls, descriptors)
        if isinstance(model, InvalidRequest):
            return model
        filename = value.get("filename")
        if filename is None:
            return SaveRequest(model)
        if not isinstance(filename, str):
            return InvalidRequest()
        output = parse_output(filename)
        return (
            output
            if isinstance(output, InputFailure)
            else SaveRequest(model, output)
        )
    return InvalidRequest()


@dataclass(frozen=True)
class StoredConfig:
    """Structurally valid config preserves values from any historical model."""

    value: dict[str, JsonValue]


@dataclass(frozen=True)
class StoredPresets:
    """Structurally valid presets retain raw JSON params and metadata for edits."""

    value: list[dict[str, JsonValue]]


StoredState: TypeAlias = StoredConfig | StoredPresets


def parse_stored(
    kind: StateKind, raw: bytes
) -> StoredState | InvalidStoredState:
    """Parse stored structure only; model names/types/ranges do not define corruption."""
    value = decode_json(
        raw,
        max_bytes=MAX_CONFIG_BYTES if kind == "config" else MAX_PRESET_BYTES,
    )
    if isinstance(value, InputFailure):
        return InvalidStoredState()
    if kind == "config":
        if (
            not isinstance(value, dict)
            or "params" not in value
            or not isinstance(value["params"], dict)
            or value.keys()
            - {"params", "tabs", "figWidth", "function", "updated_at"}
        ):
            return InvalidStoredState()
        if any(
            key in value and not isinstance(value[key], str)
            for key in ("function", "updated_at")
        ):
            return InvalidStoredState()
        if "figWidth" in value and type(value["figWidth"]) is not int:
            return InvalidStoredState()
        if "tabs" in value and isinstance(
            _tabs(value["tabs"], None), InputFailure
        ):
            return InvalidStoredState()
        return StoredConfig(value)
    if not isinstance(value, list) or len(value) > MAX_PRESETS:
        return InvalidStoredState()
    for entry in value:
        if (
            not isinstance(entry, dict)
            or not {"label", "params"} <= entry.keys()
            or entry.keys() - {"label", "params", "timestamp"}
            or not isinstance(entry["params"], dict)
            or _label(entry["label"]) is not None
        ):
            return InvalidStoredState()
        if "timestamp" in entry and not isinstance(entry["timestamp"], str):
            return InvalidStoredState()
    return StoredPresets(cast(list[dict[str, JsonValue]], value))


def _project_entry(
    value: dict[str, JsonValue], field_names: frozenset[str]
) -> dict[str, JsonValue]:
    """Project declared keys on a detached read without altering retained stored JSON."""
    result = deepcopy(value)
    params = cast(dict[str, JsonValue], result["params"])
    result["params"] = {
        name: child for name, child in params.items() if name in field_names
    }
    result["dropped_fields"] = list(
        cast(list[JsonValue], sorted(params.keys() - field_names))
    )
    return result


def project_stored(
    state: StoredState, field_names: frozenset[str]
) -> JsonValue:
    """Return projected config/presets and dropped fields without storage side effects."""
    if isinstance(state, StoredPresets):
        return [_project_entry(entry, field_names) for entry in state.value]
    result = _project_entry(state.value, field_names)
    if "tabs" in result:
        result["tabs"] = [
            _project_entry(cast(dict[str, JsonValue], tab), field_names)
            for tab in cast(list[JsonValue], result["tabs"])
        ]
    width = result.get("figWidth")
    if isinstance(width, int) and not 30 <= width <= 100:
        result["figWidth"] = DEFAULT_FIG_WIDTH
    return result
