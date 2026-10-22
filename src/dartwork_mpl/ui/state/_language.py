"""The viewer-state languages: config/preset request bodies and the stored state files.

Pure: no function opens files. Each state route has its own request parser:
``/api/config`` bodies become a ``ParamsUpdate``, ``/api/save-state`` bodies a
``FullStateUpdate`` and ``/api/preset`` bodies a ``PresetRequest``. Stored
bytes are parsed structurally (model drift is not corruption) and projected
onto the current model's declared fields.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Literal, TypeAlias, cast

from ..params import (
    InputFailure,
    InvalidRequest,
    ParamModel,
    parse_active,
    request_object,
)
from ..platform.json_bounds import (
    MAX_REQUEST_BYTES,
    JsonValue,
    LimitExceeded,
    MalformedInput,
    bounded,
    decode_json,
)

if TYPE_CHECKING:
    from ..params import ParamDescriptor

StateKind: TypeAlias = Literal["config", "presets"]

MAX_CONFIG_BYTES = MAX_REQUEST_BYTES
MAX_PRESET_BYTES = 8 * 1024 * 1024
MAX_TABS = 64
MAX_PRESETS = 1000
MAX_LABEL_BYTES = 256
DEFAULT_FIG_WIDTH = 70


@dataclass(frozen=True)
class InvalidStoredState:
    """Existing state is structurally invalid and must retain its original bytes."""

    detail: str = "Stored viewer state is invalid; preserve the existing file."
    status_code: ClassVar[int] = 409
    code: ClassVar[str] = "invalid_stored_state"


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


@dataclass(frozen=True)
class Tab:
    """An inactive tab has structurally checked declared params, not active values."""

    id: int
    name: str
    params: dict[str, JsonValue]


@dataclass(frozen=True)
class FigWidth:
    """The active figure width the page shows, an integer percentage in 30..100."""

    value: int

    def __post_init__(self) -> None:
        """Reject a width outside 30..100 or a non-``int`` (``bool`` included)."""
        if type(self.value) is not int or not 30 <= self.value <= 100:
            raise ValueError("figWidth must be an integer in 30..100")


@dataclass(frozen=True)
class ParamsUpdate:
    """``/api/config``: replace the stored config with the active model alone (no tabs, no width)."""

    model: ParamModel


@dataclass(frozen=True)
class FullStateUpdate:
    """``/api/save-state``: the active model, every inactive tab and an optional width.

    ``tabs`` is empty when the body omitted it; ``fig_width`` is ``None`` when
    the body omitted ``figWidth``, and then the stored config has no width.
    """

    model: ParamModel
    tabs: tuple[Tab, ...]
    fig_width: FigWidth | None


StateUpdate: TypeAlias = ParamsUpdate | FullStateUpdate


@dataclass(frozen=True)
class PresetRequest:
    """A named preset carries a bounded label and validated active model."""

    label: str
    model: ParamModel


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


def parse_params_update(
    value: JsonValue,
    model_cls: type[ParamModel],
    descriptors: list[ParamDescriptor],
) -> ParamsUpdate | InputFailure:
    """Parse an ``/api/config`` body, which is exactly the active parameters; pure.

    Refusals: ``LimitExceeded`` over the size bounds, ``InvalidRequest`` for a
    non-object or parameters that do not validate.
    """
    body = request_object(value)
    if not isinstance(body, dict):
        return body
    model = parse_active(body, model_cls, descriptors)
    if isinstance(model, InvalidRequest):
        return model
    return ParamsUpdate(model)


def parse_full_state_update(
    value: JsonValue,
    model_cls: type[ParamModel],
    descriptors: list[ParamDescriptor],
) -> FullStateUpdate | InputFailure:
    """Parse an ``/api/save-state`` body: optional ``params``, ``tabs`` and ``figWidth``; pure.

    Omitted ``params`` means the model defaults, omitted ``tabs`` none.
    Refusals: ``LimitExceeded`` over the size bounds, more than 64 tabs or a
    label over 256 bytes; ``InvalidRequest`` for unknown keys, invalid
    parameters, malformed or duplicate tabs, tab params naming undeclared
    fields, or a width that is not an integer in 30..100.
    """
    body = request_object(value)
    if not isinstance(body, dict):
        return body
    if body.keys() - {"params", "tabs", "figWidth"}:
        return InvalidRequest()
    model = parse_active(body.get("params", {}), model_cls, descriptors)
    if isinstance(model, InvalidRequest):
        return model
    tabs = _tabs(body.get("tabs", []), frozenset(model_cls.model_fields))
    if isinstance(tabs, InputFailure):
        return tabs
    if "figWidth" not in body:
        return FullStateUpdate(model, tabs, None)
    width = body["figWidth"]
    if type(width) is not int or not 30 <= width <= 100:
        return InvalidRequest()
    return FullStateUpdate(model, tabs, FigWidth(width))


def parse_preset_request(
    value: JsonValue,
    model_cls: type[ParamModel],
    descriptors: list[ParamDescriptor],
) -> PresetRequest | InputFailure:
    """Parse an ``/api/preset`` body: exactly ``label`` and ``params``; pure.

    Refusals: ``LimitExceeded`` over the size bounds or for a label over 256
    bytes; ``InvalidRequest`` for other keys, a non-string label or invalid
    parameters.
    """
    body = request_object(value)
    if not isinstance(body, dict):
        return body
    if body.keys() != {"label", "params"}:
        return InvalidRequest()
    label = body["label"]
    if not isinstance(label, str):
        return InvalidRequest()
    label_refusal = _label(label)
    if label_refusal is not None:
        return label_refusal
    model = parse_active(body["params"], model_cls, descriptors)
    return (
        model
        if isinstance(model, InvalidRequest)
        else PresetRequest(label, model)
    )


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
