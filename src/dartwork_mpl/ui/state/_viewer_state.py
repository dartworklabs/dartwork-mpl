"""Viewer-state semantics over the fixed-file store: projected reads and bounded edits.

Reads project historical keys without validating old values against the
current model or rewriting bytes. Edits run inside the store lock; separate
processes can still lose concurrent updates.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import ClassVar, TypeAlias

from ..params import InputFailure, InvalidRequest
from ..platform.json_bounds import JsonValue, LimitExceeded
from ._files import StateFile
from ._language import (
    MAX_CONFIG_BYTES,
    MAX_PRESET_BYTES,
    MAX_PRESETS,
    FullStateUpdate,
    InvalidStoredState,
    ParamsUpdate,
    Preset,
    PresetRequest,
    StateUpdate,
    StoredPresets,
    encode_state,
    parse_config,
    parse_presets,
    project_config,
    project_presets,
)
from ._store import (
    FileFailure,
    FixedStateStore,
    MissingState,
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
        raw = self._store.read(StateFile.CONFIG, max_bytes=MAX_CONFIG_BYTES)
        if not isinstance(raw, bytes):
            return raw
        stored = parse_config(raw)
        if isinstance(stored, InvalidStoredState):
            return stored
        return ConfigLoaded(project_config(stored, self._field_names))

    def load_presets(self) -> PresetsLoaded | FileFailure:
        """Return projected presets (empty if missing), refusing structural corruption."""
        raw = self._store.read(StateFile.PRESETS, max_bytes=MAX_PRESET_BYTES)
        if isinstance(raw, MissingState):
            return PresetsLoaded([])
        if not isinstance(raw, bytes):
            return raw
        stored = parse_presets(raw)
        if isinstance(stored, InvalidStoredState):
            return stored
        return PresetsLoaded(project_presets(stored, self._field_names))

    def save_config(
        self, update: StateUpdate, function_name: str
    ) -> StateWriteResult:
        """Replace the stored config with ``update``; corrupt existing bytes are kept and refused.

        A ``ParamsUpdate`` writes ``function``, ``params`` and ``updated_at``; a
        ``FullStateUpdate`` adds ``tabs`` and, when given, ``figWidth``.
        """

        def edit(
            raw: bytes | MissingState,
        ) -> bytes | InvalidStoredState | InputFailure:
            """Check historical structure while locked, then encode the complete new config."""
            if isinstance(raw, bytes) and isinstance(
                parse_config(raw), InvalidStoredState
            ):
                return InvalidStoredState()
            try:
                value: dict[str, JsonValue] = {
                    "function": function_name,
                    "params": update.model.model_dump(
                        mode="json", by_alias=False
                    ),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            except (ValueError, TypeError, OverflowError, RecursionError):
                return InvalidRequest(
                    "Parameters cannot be serialized as finite JSON."
                )
            match update:
                case ParamsUpdate():
                    pass
                case FullStateUpdate(tabs=tabs, fig_width=fig_width):
                    value["tabs"] = [
                        {"id": tab.id, "name": tab.name, "params": tab.params}
                        for tab in tabs
                    ]
                    if fig_width is not None:
                        value["figWidth"] = fig_width.value
            return encode_state(value, max_bytes=MAX_CONFIG_BYTES)

        return self._store.update(
            StateFile.CONFIG, max_bytes=MAX_CONFIG_BYTES, edit=edit
        )

    def save_preset(self, parsed: PresetRequest) -> StateWriteResult:
        """Append declared parameter names under lock without projecting old entries."""

        def edit(
            raw: bytes | MissingState,
        ) -> bytes | InvalidStoredState | InputFailure:
            """Retain every old entry as stored and refuse corruption or the preset count cap."""
            if isinstance(raw, MissingState):
                entries: tuple[Preset, ...] = ()
            else:
                stored = parse_presets(raw)
                if isinstance(stored, InvalidStoredState):
                    return stored
                entries = stored.entries
            if len(entries) >= MAX_PRESETS:
                return LimitExceeded()
            try:
                params = parsed.model.model_dump(mode="json", by_alias=False)
            except (ValueError, TypeError, OverflowError, RecursionError):
                return InvalidRequest(
                    "Parameters cannot be serialized as finite JSON."
                )
            added = Preset(
                parsed.label, params, datetime.now(timezone.utc).isoformat()
            )
            return encode_state(
                StoredPresets((*entries, added)).to_json(),
                max_bytes=MAX_PRESET_BYTES,
            )

        return self._store.update(
            StateFile.PRESETS, max_bytes=MAX_PRESET_BYTES, edit=edit
        )

    def delete_preset(self, index: int) -> StateWriteResult | PresetNotFound:
        """Delete an existing index under the lock; misses and corrupt files keep their bytes."""

        def edit(
            raw: bytes | MissingState,
        ) -> bytes | InvalidStoredState | InputFailure | StateUnchanged:
            """Resolve the index only after parsing current state inside the store lock."""
            if isinstance(raw, MissingState):
                return StateUnchanged()
            stored = parse_presets(raw)
            if isinstance(stored, InvalidStoredState):
                return stored
            if index < 0 or index >= len(stored.entries):
                return StateUnchanged()
            kept = stored.entries[:index] + stored.entries[index + 1 :]
            return encode_state(
                StoredPresets(kept).to_json(), max_bytes=MAX_PRESET_BYTES
            )

        result: StateWriteResult | StateUnchanged = self._store.update(
            StateFile.PRESETS, max_bytes=MAX_PRESET_BYTES, edit=edit
        )
        if isinstance(result, StateUnchanged):
            return PresetNotFound(index)
        return result
