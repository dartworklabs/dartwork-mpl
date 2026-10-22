"""Viewer-state semantics over the fixed-file store: projected reads and bounded edits.

Reads project historical keys without validating old values against the
current model or rewriting bytes. Edits run inside the store lock; separate
processes can still lose concurrent updates.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import ClassVar, TypeAlias, cast

from ..params import InputFailure, InvalidRequest
from ..platform.json_bounds import JsonValue, LimitExceeded
from ._language import (
    MAX_CONFIG_BYTES,
    MAX_PRESET_BYTES,
    MAX_PRESETS,
    InvalidStoredState,
    PresetRequest,
    StateRequest,
    StoredConfig,
    StoredPresets,
    encode_state,
    parse_stored,
    project_stored,
)
from ._store import (
    FileFailure,
    FixedStateStore,
    MissingState,
    StateEditRefusal,
    StateUnchanged,
    StateWritten,
)


@dataclass(frozen=True)
class ConfigLoaded:
    """A detached declared-field projection of structurally valid saved config."""

    value: dict[str, JsonValue]


@dataclass(frozen=True)
class PresetsLoaded:
    """Detached projected presets, including an empty list when no file exists."""

    value: list[dict[str, JsonValue]]


@dataclass(frozen=True)
class PresetNotFound:
    """A preset index has no entry; the fixed state file was not replaced."""

    index: int
    detail: str = "Preset index does not exist."
    status_code: ClassVar[int] = 404
    code: ClassVar[str] = "preset_not_found"


StateWriteResult: TypeAlias = StateWritten | InputFailure | FileFailure


class ViewerState:
    """State semantics over a borrowed confined fixed-file store.

    Reads project historical keys without validating old values against the current
    model or rewriting bytes. The store locks each read/edit/replacement across
    scopes in this process; separate processes can still lose concurrent updates.
    """

    def __init__(
        self, store: FixedStateStore, field_names: frozenset[str]
    ) -> None:
        """Borrow the store and declared names; neither raw paths nor requests enter here."""
        self._store = store
        self._field_names = field_names

    def load_config(self) -> ConfigLoaded | MissingState | FileFailure:
        """Read projected config or a named miss/refusal, preserving all stored bytes."""
        raw = self._store.read("config", max_bytes=MAX_CONFIG_BYTES)
        if not isinstance(raw, bytes):
            return raw
        stored = parse_stored("config", raw)
        if not isinstance(stored, StoredConfig):
            return InvalidStoredState()
        projected = project_stored(stored, self._field_names)
        # parse_stored established the config object before this projection.
        return ConfigLoaded(cast(dict[str, JsonValue], projected))

    def load_presets(self) -> PresetsLoaded | FileFailure:
        """Return projected presets (empty if missing), refusing structural corruption."""
        raw = self._store.read("presets", max_bytes=MAX_PRESET_BYTES)
        if isinstance(raw, MissingState):
            return PresetsLoaded([])
        if not isinstance(raw, bytes):
            return raw
        stored = parse_stored("presets", raw)
        if not isinstance(stored, StoredPresets):
            return InvalidStoredState()
        projected = project_stored(stored, self._field_names)
        # parse_stored established an array of preset objects, preserved by projection.
        return PresetsLoaded(cast(list[dict[str, JsonValue]], projected))

    def save_config(
        self, parsed: StateRequest, function_name: str
    ) -> StateWriteResult:
        """Persist declared parameter names; bounded edits preserve corrupt existing bytes."""

        def edit(raw: bytes | MissingState) -> bytes | StateEditRefusal:
            """Check historical structure while locked, then encode the complete new config."""
            if isinstance(raw, bytes) and isinstance(
                parse_stored("config", raw), InvalidStoredState
            ):
                return InvalidStoredState()
            try:
                value: dict[str, JsonValue] = {
                    "function": function_name,
                    "params": parsed.model.model_dump(
                        mode="json", by_alias=False
                    ),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            except (ValueError, TypeError, OverflowError, RecursionError):
                return InvalidRequest(
                    "Parameters cannot be serialized as finite JSON."
                )
            if parsed.tabs is not None:
                value["tabs"] = [
                    {"id": tab.id, "name": tab.name, "params": tab.params}
                    for tab in parsed.tabs
                ]
            if parsed.fig_width is not None:
                value["figWidth"] = parsed.fig_width
            return encode_state(value, max_bytes=MAX_CONFIG_BYTES)

        # This editor never returns the store's optional no-change outcome.
        return cast(
            StateWriteResult,
            self._store.update("config", max_bytes=MAX_CONFIG_BYTES, edit=edit),
        )

    def save_preset(self, parsed: PresetRequest) -> StateWriteResult:
        """Append declared parameter names under lock without projecting old entries."""

        def edit(raw: bytes | MissingState) -> bytes | StateEditRefusal:
            """Retain every old JSON value and refuse corruption or the preset count cap."""
            if isinstance(raw, MissingState):
                entries: list[dict[str, JsonValue]] = []
            else:
                stored = parse_stored("presets", raw)
                if not isinstance(stored, StoredPresets):
                    return InvalidStoredState()
                entries = stored.value
            if len(entries) >= MAX_PRESETS:
                return LimitExceeded()
            try:
                entries.append(
                    {
                        "label": parsed.label,
                        "params": parsed.model.model_dump(
                            mode="json", by_alias=False
                        ),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except (ValueError, TypeError, OverflowError, RecursionError):
                return InvalidRequest(
                    "Parameters cannot be serialized as finite JSON."
                )
            return encode_state(
                cast(list[JsonValue], entries), max_bytes=MAX_PRESET_BYTES
            )

        # This editor never returns the store's optional no-change outcome.
        return cast(
            StateWriteResult,
            self._store.update(
                "presets", max_bytes=MAX_PRESET_BYTES, edit=edit
            ),
        )

    def delete_preset(self, index: int) -> StateWriteResult | PresetNotFound:
        """Delete an existing index under the lock; misses and corrupt files keep their bytes."""

        def edit(
            raw: bytes | MissingState,
        ) -> bytes | StateEditRefusal | StateUnchanged:
            """Resolve the index only after parsing current state inside the store lock."""
            if isinstance(raw, MissingState):
                return StateUnchanged()
            stored = parse_stored("presets", raw)
            if not isinstance(stored, StoredPresets):
                return InvalidStoredState()
            if index < 0 or index >= len(stored.value):
                return StateUnchanged()
            entries = stored.value
            entries.pop(index)
            return encode_state(
                cast(list[JsonValue], entries), max_bytes=MAX_PRESET_BYTES
            )

        result = self._store.update(
            "presets", max_bytes=MAX_PRESET_BYTES, edit=edit
        )
        return (
            PresetNotFound(index)
            if isinstance(result, StateUnchanged)
            else result
        )
