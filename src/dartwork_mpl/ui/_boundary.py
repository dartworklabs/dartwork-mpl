"""Pure local-viewer policy and bounded wire/state languages.

No function opens files or sockets. The HTTP shell supplies bytes, route names
and startup facts; the filesystem shell consumes only parsed relative outputs.
"""

from __future__ import annotations

import json
import math
import re
import types
from copy import copy, deepcopy
from dataclasses import dataclass
from functools import lru_cache
from ipaddress import ip_address
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    ForwardRef,
    Literal,
    TypeAlias,
    Union,
    cast,
    get_args,
    get_origin,
)
from urllib.parse import urlsplit

from pydantic import BaseModel, ValidationError, create_model

from ._param import ParamModel

if TYPE_CHECKING:
    from os import PathLike

    from ._widget import ParamDescriptor

CopyTo: TypeAlias = "str | PathLike[str] | list[str | PathLike[str]] | None"
StateKind: TypeAlias = Literal["config", "presets"]
JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)

MAX_REQUEST_BYTES = 1024 * 1024
MAX_CONFIG_BYTES = MAX_REQUEST_BYTES
MAX_PRESET_BYTES = 8 * 1024 * 1024
MAX_DEPTH = 16
MAX_VALUES = 65536
MAX_CONTAINER = 4096
MAX_STRING_BYTES = 65536
MAX_TABS = 64
MAX_PRESETS = 1000
MAX_LABEL_BYTES = 256
MAX_OUTPUT_BYTES = 1024
DEFAULT_FIG_WIDTH = 70


@dataclass(frozen=True)
class MalformedInput:
    """The bytes do not express one unambiguous finite UTF-8 JSON value."""

    detail: str = "Input must be unambiguous finite UTF-8 JSON."
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "invalid_json"


@dataclass(frozen=True)
class LimitExceeded:
    """An input or proposed serialized state exceeds an approved bound."""

    detail: str = "Input exceeds the viewer limits."
    status_code: ClassVar[int] = 413
    code: ClassVar[str] = "input_too_large"


@dataclass(frozen=True)
class InvalidRequest:
    """A complete decoded request does not match the endpoint/model schema."""

    detail: str = "Input does not match the viewer request schema."
    status_code: ClassVar[int] = 422
    code: ClassVar[str] = "invalid_request"


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
class AccessDenied:
    """The request has no local grant or contains an invalid authority."""

    detail: str = "Request is outside the local viewer policy."
    status_code: ClassVar[int] = 403
    code: ClassVar[str] = "local_access_denied"


@dataclass(frozen=True)
class StartupRejected:
    """The configured bind cannot grant approved loopback-only operation."""

    detail: str = "Use localhost or a loopback IP literal for the viewer host."
    code: ClassVar[str] = "invalid_bind"


@dataclass(frozen=True)
class InvalidStoredState:
    """Existing state is structurally invalid and must retain its original bytes."""

    detail: str = "Stored viewer state is invalid; preserve the existing file."
    status_code: ClassVar[int] = 409
    code: ClassVar[str] = "invalid_stored_state"


@dataclass(frozen=True)
class LocalAccess:
    """A named route is admitted by the startup-selected local-only grant."""

    scope: Literal["local-read", "local-effect"]


# The approved local-only policy grants these effects to native local clients.
# Host and browser source checks constrain that grant; they are not identity.
ROUTE_POLICY: dict[tuple[str, str], Literal["local-read", "local-effect"]] = {
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


def normalize_bind(host: str) -> str | StartupRejected:
    """Normalize approved literal loopback binds without consulting DNS."""
    if host.lower() == "localhost":
        return "127.0.0.1"
    if "%" in host:
        return StartupRejected()
    try:
        address = ip_address(host)
    except ValueError:
        return StartupRejected()
    return str(address) if address.is_loopback else StartupRejected()


def _authority(value: str) -> tuple[str, str | None] | None:
    """Recognize the entire ASCII HTTP authority, including a valid optional port."""
    match = re.fullmatch(
        r"(\[[0-9A-Fa-f:]+\]|[A-Za-z0-9.]+)(?::([1-9][0-9]{0,4}))?", value
    )
    if match is None:
        return None
    name, port = match.groups()
    if port is not None and int(port) > 65535:
        return None
    if name.startswith("["):
        try:
            address = ip_address(name[1:-1])
        except ValueError:
            return None
        if address.version != 6:
            return None
        name = str(address)
    else:
        name = name.lower()
    return name, port


def _source_matches(
    value: str, authority: tuple[str, str | None], *, origin: bool
) -> bool:
    """Match a complete HTTP source URL without browser/parser ambiguity."""
    if (
        any(ord(char) <= 32 or ord(char) >= 127 for char in value)
        or "\\" in value
        or "#" in value
    ):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if parsed.scheme != "http" or _authority(parsed.netloc) != authority:
        return False
    return not origin or (not parsed.path and "?" not in value)


def authorize_request(
    method: str,
    route_template: str | None,
    raw_headers: list[tuple[bytes, bytes]],
    bind_host: str,
) -> LocalAccess | AccessDenied:
    """Admit only classified routes with a valid local Host and each effect source."""
    scope = ROUTE_POLICY.get((method.upper(), route_template or ""))
    normalized = normalize_bind(bind_host)
    if scope is None or isinstance(normalized, StartupRejected):
        return AccessDenied()
    selected: dict[bytes, list[str]] = {
        b"host": [],
        b"origin": [],
        b"referer": [],
    }
    for name, value in raw_headers:
        if name.lower() in selected:
            try:
                selected[name.lower()].append(value.decode("ascii"))
            except UnicodeDecodeError:
                return AccessDenied()
    if len(selected[b"host"]) != 1:
        return AccessDenied()
    authority = _authority(selected[b"host"][0])
    if authority is None or authority[0] not in {
        "localhost",
        "127.0.0.1",
        "::1",
        normalized,
    }:
        return AccessDenied()
    if scope == "local-effect":
        for name in (b"origin", b"referer"):
            values = selected[name]
            if len(values) > 1 or (
                values
                and not _source_matches(
                    values[0], authority, origin=name == b"origin"
                )
            ):
                return AccessDenied()
    return LocalAccess(scope)


class _BadJson(ValueError):
    """Internal stdlib parser signal converted to a named malformed-input value."""


class _JsonLimit(ValueError):
    """Internal stdlib parser signal converted to a named limit refusal."""


def _pairs(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    """Reject duplicate object keys at every nesting level during JSON decoding."""
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise _BadJson
        result[key] = value
    return result


def _integer(token: str) -> int:
    """Bound integer work independently of the interpreter-wide digit setting."""
    if len(token.lstrip("-")) > 640:
        raise _JsonLimit
    return int(token)


def _float(token: str) -> float:
    """Reject numeric overflow as well as explicit nonfinite JSON constants."""
    value = float(token)
    if not math.isfinite(value):
        raise _BadJson
    return value


def _constant(token: str) -> JsonValue:
    """Stdlib's permissive NaN/Infinity tokens are outside this JSON language."""
    raise _BadJson


def _bounded(value: object) -> MalformedInput | LimitExceeded | None:
    """Iteratively bound full JSON trees, including object keys and Unicode bytes."""
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > MAX_VALUES or depth > MAX_DEPTH:
            return LimitExceeded()
        if isinstance(item, str):
            try:
                if len(item.encode("utf-8")) > MAX_STRING_BYTES:
                    return LimitExceeded()
            except UnicodeEncodeError:
                return MalformedInput()
        elif isinstance(item, (list, dict)):
            if len(item) > MAX_CONTAINER:
                return LimitExceeded()
            if isinstance(item, dict):
                for key in item:
                    if not isinstance(key, str):
                        return MalformedInput()
                    try:
                        if len(key.encode("utf-8")) > MAX_STRING_BYTES:
                            return LimitExceeded()
                    except UnicodeEncodeError:
                        return MalformedInput()
                pending.extend((child, depth + 1) for child in item.values())
            else:
                pending.extend((child, depth + 1) for child in item)
        elif isinstance(item, float):
            if not math.isfinite(item):
                return MalformedInput()
        elif isinstance(item, int):
            if abs(item) >= 10**640:
                return LimitExceeded()
        elif item is not None and not isinstance(item, (int, bool)):
            return MalformedInput()
    return None


def decode_json(raw: bytes, *, max_bytes: int) -> JsonValue | InputFailure:
    """Decode one bounded JSON value; malformed syntax is 400 and bounds are 413."""
    if len(raw) > max_bytes:
        return LimitExceeded()
    try:
        value: JsonValue = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_int=_integer,
            parse_float=_float,
            parse_constant=_constant,
        )
    except _JsonLimit:
        return LimitExceeded()
    except (UnicodeDecodeError, json.JSONDecodeError, _BadJson, RecursionError):
        return MalformedInput()
    refusal = _bounded(value)
    return refusal if refusal is not None else value


def encode_state(value: JsonValue, *, max_bytes: int) -> bytes | InputFailure:
    """Bound the complete next-state value and its UTF-8 serialization before writes."""
    refusal = _bounded(value)
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


@lru_cache(maxsize=128)
def _declared_model(model_cls: type[BaseModel]) -> type[BaseModel]:
    """Derive one alias-free model graph so nested hooks run only in native validation."""
    names: dict[type[BaseModel], str] = {}

    def collect(annotation: Any) -> None:
        """Name the finite model graph before resolving any recursive references."""
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if annotation in names:
                return
            names[annotation] = f"{annotation.__name__}ViewerInput{len(names)}"
            for field in annotation.model_fields.values():
                collect(field.annotation)
        else:
            for arg in get_args(annotation):
                collect(arg)

    def rewrite(annotation: Any) -> Any:
        """Retain declared container/union semantics and defer model graph references."""
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return ForwardRef(names[annotation])
        origin, args = get_origin(annotation), get_args(annotation)
        if origin is Annotated:
            return Annotated[(rewrite(args[0]), *args[1:])]
        if origin in (Union, types.UnionType):
            return Union[tuple(rewrite(arg) for arg in args)]  # noqa: UP007 -- runtime union reconstruction
        if origin in (list, tuple, dict):
            return origin[tuple(rewrite(arg) for arg in args)]
        return annotation

    collect(model_cls)
    models: dict[str, type[BaseModel]] = {}
    for original_cls, name in names.items():
        fields: dict[str, Any] = {}
        for field_name, original in original_cls.model_fields.items():
            field = copy(original)
            field.alias = None
            field.validation_alias = None
            fields[field_name] = (rewrite(field.annotation), field)
        derived = create_model(
            name, __base__=original_cls, __module__=__name__, **fields
        )
        # Only the private class changes. Keep older Pydantic 2.x support
        # without its newer by_name/by_alias model_validate arguments.
        derived.model_config = {
            **derived.model_config,
            "extra": "forbid",
            "alias_generator": None,
        }
        for field in derived.model_fields.values():
            field.alias = None
            field.validation_alias = None
        models[name] = derived
    for derived in models.values():
        derived.model_rebuild(force=True, _types_namespace=models)
    return models[names[model_cls]]


def _nested(annotation: Any, value: Any) -> Any:
    """Check raw declared names without constructing or validating nested models."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Annotated:
        return _nested(args[0], value)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if (
            not isinstance(value, dict)
            or value.keys() - annotation.model_fields.keys()
        ):
            raise ValueError("Parameters must use declared field names")
        return {
            name: _nested(annotation.model_fields[name].annotation, child)
            for name, child in value.items()
        }
    if origin in (Union, types.UnionType):
        for branch in args:
            # A nonmatching scalar arm must not pass a raw object on to an
            # extra-allowing model arm in Pydantic's later union selection.
            base = (
                get_args(branch)[0]
                if get_origin(branch) is Annotated
                else branch
            )
            shape = get_origin(base) or base
            if (
                isinstance(value, dict)
                and shape not in (dict, Any)
                and not (
                    isinstance(shape, type) and issubclass(shape, BaseModel)
                )
            ):
                continue
            if isinstance(value, (list, tuple)) and shape not in (
                list,
                tuple,
                Any,
            ):
                continue
            try:
                return _nested(branch, value)
            except (ValueError, TypeError):
                continue
        raise ValueError("No declared nested shape matches")
    if origin in (list, tuple) and isinstance(value, (list, tuple)):
        item_types = (
            args
            if origin is tuple and args and args[-1] is not Ellipsis
            else None
        )
        return [
            _nested(
                item_types[index]
                if item_types and index < len(item_types)
                else args[0]
                if args
                else Any,
                child,
            )
            for index, child in enumerate(value)
        ]
    if origin is dict and isinstance(value, dict) and len(args) == 2:
        return {key: _nested(args[1], child) for key, child in value.items()}
    return value


def _validate_model(model_cls: type[BaseModel], value: Any) -> BaseModel:
    """Check raw field names, then run one complete native Pydantic validation pass."""
    return _declared_model(model_cls).model_validate(_nested(model_cls, value))


def _active(
    value: JsonValue,
    model_cls: type[ParamModel],
    descriptors: list[ParamDescriptor],
) -> ParamModel | InvalidRequest:
    """Apply documented list-text coercion once, preserve defaults and reject value drift."""
    if not isinstance(value, dict):
        return InvalidRequest()
    coerced: dict[str, Any] = dict(value)
    try:
        for descriptor in descriptors:
            item = coerced.get(descriptor.name)
            if descriptor.type_name.startswith("list_") and isinstance(
                item, str
            ):
                convert = {
                    "list_int": int,
                    "list_float": float,
                    "list_str": str,
                }[descriptor.type_name]
                coerced[descriptor.name] = [
                    convert(part.strip())
                    for part in item.split(",")
                    if part.strip()
                ]
        model = _validate_model(model_cls, coerced)
        if _bounded(model.model_dump(mode="json", by_alias=False)) is not None:
            return InvalidRequest(
                "Parameters must remain bounded finite JSON values."
            )
    except (
        ValidationError,
        ValueError,
        TypeError,
        OverflowError,
        RecursionError,
    ):
        return InvalidRequest(
            "Parameters must use declared names and satisfy their types and constraints."
        )
    return cast(ParamModel, model)


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
    refusal = _bounded(value)
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
        model = _active(value, model_cls, descriptors)
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
        model = _active(value.get("params", {}), model_cls, descriptors)
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
        model = _active(value["params"], model_cls, descriptors)
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
        model = _active(value["params"], model_cls, descriptors)
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
