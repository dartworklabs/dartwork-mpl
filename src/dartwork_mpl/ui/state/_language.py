"""The viewer-state languages: config/preset request bodies and the stored state files.

Pure: no function opens files. Each state route has its own request parser:
``/api/config`` bodies become a ``ParamsUpdate``, ``/api/save-state`` bodies a
``FullStateUpdate`` and ``/api/preset`` bodies a ``PresetRequest``. Stored
bytes are parsed once, structurally (model drift is not corruption), into
``StoredConfig`` / ``StoredPresets``; those remember the member order of the
JSON they came from, so a projected read or a rewrite of retained entries
spells every object as the file did.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

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
    from ..params import Control

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


def _in_order(
    keys: tuple[str, ...], members: dict[str, JsonValue]
) -> dict[str, JsonValue]:
    """Spell ``members`` as a JSON object in the member order ``keys``."""
    return {key: members[key] for key in keys}


def _check_order(keys: tuple[str, ...], members: dict[str, JsonValue]) -> None:
    """Reject a member order that is not exactly the present members, once each."""
    if len(keys) != len(set(keys)) or set(keys) != members.keys():
        raise ValueError(f"Member order {keys!r} does not list the members")


def _check_label(label: str) -> None:
    """Reject a label over ``MAX_LABEL_BYTES`` UTF-8 bytes (a caller defect)."""
    if len(label.encode("utf-8")) > MAX_LABEL_BYTES:
        raise ValueError("Label exceeds the label byte limit")


@dataclass(frozen=True)
class Tab:
    """An inactive tab: an id, a label of at most 256 bytes and structurally checked params.

    The params are raw JSON, not validated against the model. ``keys`` is the
    member order of the object the tab was parsed from; ``to_json`` spells the
    tab in that order.
    """

    id: int
    name: str
    params: dict[str, JsonValue]
    keys: tuple[str, ...] = ("id", "name", "params")

    def __post_init__(self) -> None:
        """Reject a long label or a member order other than a permutation of the three members."""
        _check_label(self.name)
        _check_order(self.keys, self._members())

    def _members(self) -> dict[str, JsonValue]:
        """The tab's JSON members in canonical order."""
        return {"id": self.id, "name": self.name, "params": self.params}

    def to_json(self) -> dict[str, JsonValue]:
        """The tab as the JSON object it was parsed from (shares ``params``)."""
        return _in_order(self.keys, self._members())


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


def _label(value: str) -> LimitExceeded | None:
    """Check a label against its own limit, smaller than the generic JSON string limit."""
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
            or not isinstance(name, str)
        ):
            return InvalidRequest()
        refusal = _label(name)
        if refusal is not None:
            return refusal
        if field_names is not None and params.keys() - field_names:
            return InvalidRequest()
        ids.add(tab_id)
        result.append(Tab(tab_id, name, params, tuple(entry)))
    return tuple(result)


def parse_params_update(
    value: JsonValue, model_cls: type[ParamModel], descriptors: list[Control]
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
    value: JsonValue, model_cls: type[ParamModel], descriptors: list[Control]
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
    value: JsonValue, model_cls: type[ParamModel], descriptors: list[Control]
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


_CONFIG_MEMBERS = frozenset(
    {"params", "tabs", "figWidth", "function", "updated_at"}
)
_PRESET_MEMBERS = frozenset({"label", "params", "timestamp"})


@dataclass(frozen=True)
class StoredConfig:
    """A structurally valid ``.dartwork_ui_config.json``, from any historical model.

    ``None`` means the file has no such member. ``fig_width`` is any stored
    integer (reads project an out-of-range one to the default). ``keys`` is
    the file's member order, kept so a projected read spells it the same way.
    """

    params: dict[str, JsonValue]
    tabs: tuple[Tab, ...] | None
    fig_width: int | None
    function: str | None
    updated_at: str | None
    keys: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a member order that does not list exactly the present members."""
        _check_order(self.keys, self._members())

    def _members(self) -> dict[str, JsonValue]:
        """The present members as JSON, tabs spelled as stored."""
        members: dict[str, JsonValue] = {"params": self.params}
        if self.tabs is not None:
            members["tabs"] = [tab.to_json() for tab in self.tabs]
        if self.fig_width is not None:
            members["figWidth"] = self.fig_width
        if self.function is not None:
            members["function"] = self.function
        if self.updated_at is not None:
            members["updated_at"] = self.updated_at
        return members

    def to_json(self) -> dict[str, JsonValue]:
        """The config as the JSON object it was parsed from (shares nested values)."""
        return _in_order(self.keys, self._members())


@dataclass(frozen=True)
class Preset:
    """One stored named preset: a label of at most 256 bytes, raw params, an optional timestamp.

    ``keys`` is the stored member order; ``to_json`` spells the entry in it,
    so retained entries are rewritten exactly as they were read.
    """

    label: str
    params: dict[str, JsonValue]
    timestamp: str | None
    keys: tuple[str, ...] = ("label", "params", "timestamp")

    def __post_init__(self) -> None:
        """Reject a long label or a member order that does not list the present members."""
        _check_label(self.label)
        _check_order(self.keys, self._members())

    def _members(self) -> dict[str, JsonValue]:
        """The present members in canonical order."""
        members: dict[str, JsonValue] = {
            "label": self.label,
            "params": self.params,
        }
        if self.timestamp is not None:
            members["timestamp"] = self.timestamp
        return members

    def to_json(self) -> dict[str, JsonValue]:
        """The preset as the JSON object it was parsed from (shares ``params``)."""
        return _in_order(self.keys, self._members())


@dataclass(frozen=True)
class StoredPresets:
    """A structurally valid ``.dartwork_ui_presets.json``: at most 1,000 presets in file order."""

    entries: tuple[Preset, ...]

    def __post_init__(self) -> None:
        """Reject more than ``MAX_PRESETS`` entries."""
        if len(self.entries) > MAX_PRESETS:
            raise ValueError("Too many presets")

    def to_json(self) -> list[JsonValue]:
        """The preset list as JSON, each entry spelled as stored."""
        return [entry.to_json() for entry in self.entries]


def _optional_text(
    value: dict[str, JsonValue], key: str
) -> str | None | InvalidStoredState:
    """Read an optional string member; a present non-string is corruption."""
    if key not in value:
        return None
    member = value[key]
    return member if isinstance(member, str) else InvalidStoredState()


def parse_config(raw: bytes) -> StoredConfig | InvalidStoredState:
    """Parse config bytes structurally; pure.

    Model names, types and ranges do not define corruption. Refuses bytes
    over 1 MiB, malformed JSON, a non-object, unknown members, non-object
    ``params``, non-string ``function``/``updated_at``, a non-``int``
    ``figWidth`` and malformed tabs.
    """
    value = decode_json(raw, max_bytes=MAX_CONFIG_BYTES)
    if not isinstance(value, dict) or value.keys() - _CONFIG_MEMBERS:
        return InvalidStoredState()
    params = value.get("params")
    if not isinstance(params, dict):
        return InvalidStoredState()
    function = _optional_text(value, "function")
    updated_at = _optional_text(value, "updated_at")
    if isinstance(function, InvalidStoredState) or isinstance(
        updated_at, InvalidStoredState
    ):
        return InvalidStoredState()
    fig_width: int | None = None
    if "figWidth" in value:
        width = value["figWidth"]
        if isinstance(width, bool) or not isinstance(width, int):
            return InvalidStoredState()
        fig_width = width
    tabs: tuple[Tab, ...] | None = None
    if "tabs" in value:
        parsed_tabs = _tabs(value["tabs"], None)
        if isinstance(parsed_tabs, InputFailure):
            return InvalidStoredState()
        tabs = parsed_tabs
    return StoredConfig(
        params, tabs, fig_width, function, updated_at, tuple(value)
    )


def _preset(entry: JsonValue) -> Preset | InvalidStoredState:
    """Parse one stored preset entry structurally."""
    if (
        not isinstance(entry, dict)
        or not {"label", "params"} <= entry.keys()
        or entry.keys() - _PRESET_MEMBERS
    ):
        return InvalidStoredState()
    label, params = entry["label"], entry["params"]
    timestamp = _optional_text(entry, "timestamp")
    if (
        not isinstance(label, str)
        or _label(label) is not None
        or not isinstance(params, dict)
        or isinstance(timestamp, InvalidStoredState)
    ):
        return InvalidStoredState()
    return Preset(label, params, timestamp, tuple(entry))


def parse_presets(raw: bytes) -> StoredPresets | InvalidStoredState:
    """Parse preset bytes structurally; pure.

    Refuses bytes over 8 MiB, malformed JSON, a non-array, more than 1,000
    entries, and any entry lacking ``label``/``params``, with other members,
    non-object params, a non-string or over-long label or a non-string
    ``timestamp``.
    """
    value = decode_json(raw, max_bytes=MAX_PRESET_BYTES)
    if not isinstance(value, list) or len(value) > MAX_PRESETS:
        return InvalidStoredState()
    entries = []
    for entry in value:
        preset = _preset(entry)
        if isinstance(preset, InvalidStoredState):
            return preset
        entries.append(preset)
    return StoredPresets(tuple(entries))


def _project_entry(
    entry: dict[str, JsonValue],
    params: dict[str, JsonValue],
    field_names: frozenset[str],
) -> dict[str, JsonValue]:
    """Keep only declared ``params`` in ``entry`` and append the sorted ``dropped_fields``."""
    entry["params"] = {
        name: child for name, child in params.items() if name in field_names
    }
    dropped: list[JsonValue] = []
    dropped.extend(sorted(params.keys() - field_names))
    entry["dropped_fields"] = dropped
    return entry


def project_config(
    config: StoredConfig, field_names: frozenset[str]
) -> dict[str, JsonValue]:
    """Return a detached read of ``config`` projected onto the declared fields; pure.

    Undeclared params (top level and per tab) move to ``dropped_fields``; an
    out-of-range ``figWidth`` reads as the default 70. The stored value is
    not changed.
    """
    result = _project_entry(config.to_json(), config.params, field_names)
    if config.tabs is not None:
        result["tabs"] = [
            _project_entry(tab.to_json(), tab.params, field_names)
            for tab in config.tabs
        ]
    if config.fig_width is not None and not 30 <= config.fig_width <= 100:
        result["figWidth"] = DEFAULT_FIG_WIDTH
    return deepcopy(result)


def project_presets(
    presets: StoredPresets, field_names: frozenset[str]
) -> list[dict[str, JsonValue]]:
    """Return a detached read of every preset projected onto the declared fields; pure."""
    return deepcopy(
        [
            _project_entry(entry.to_json(), entry.params, field_names)
            for entry in presets.entries
        ]
    )
