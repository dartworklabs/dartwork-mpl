"""Configuration persistence for the Dartwork UI module.

``ViewerState`` projects structurally checked historical state and performs
bounded edits through a confined fixed-file store. The module-level helpers
retain their legacy internal contracts for callers outside the HTTP boundary.

Viewer-owned names below the configured script directory:
    ``.dartwork_ui_config.json``
        Last-used parameter set — auto-loaded on startup.
    ``.dartwork_ui_presets.json``
        Named presets saved by the user (JSON array).
"""

import contextlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, TypeAlias, cast

from ._boundary import (
    MAX_CONFIG_BYTES,
    MAX_PRESET_BYTES,
    MAX_PRESETS,
    InputFailure,
    InvalidRequest,
    InvalidStoredState,
    PresetRequest,
    StateRequest,
    StoredConfig,
    StoredPresets,
    encode_state,
    parse_stored,
    project_stored,
)
from ._files import (
    FileFailure,
    FixedStateStore,
    MissingState,
    StateEditRefusal,
    StateUnchanged,
    StateWritten,
)
from .platform.json_bounds import JsonValue, LimitExceeded


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
    Legacy module helpers below retain their existing internal contracts.
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


def _atomic_write_text(path: Path, text: str) -> None:
    """Write *text* to *path* atomically (temp file + ``os.replace``).

    A plain ``path.write_text`` truncates then writes, so a second writer
    (or a reader) racing the call can observe a half-written / empty file.
    Writing to a sibling temp file and atomically renaming it means a
    reader always sees either the old or the new complete content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        # Best-effort cleanup of the temp file on any failure.
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


# Default file name
PRESET_FILENAME = ".dartwork_ui_presets.json"

# Base directory — set to the script's parent directory by ui.run()
_base_dir: Path | None = None


def set_base_dir(path: Path) -> None:
    """Set the base directory for config and preset files.

    Called by ``ui.run()`` with the script's parent directory so that
    files are stored next to the user script rather than in the CWD.

    Parameters
    ----------
    path : Path
        Base directory path.
    """
    global _base_dir
    _base_dir = Path(path)


def _get_base_dir() -> Path:
    """Return the configured base directory.

    Falls back to the current working directory if not set.

    Returns
    ----------
    Path
        Base directory path.
    """
    return _base_dir if _base_dir is not None else Path.cwd()


def _preset_path() -> Path:
    """Return the full path to the presets file.

    Returns
    ----------
    Path
        Path to ``.dartwork_ui_presets.json``.
    """
    return _get_base_dir() / PRESET_FILENAME


# ============================================================================
# Presets (JSON array)
# ============================================================================


def save_preset(label: str, params: dict[str, Any]) -> None:
    """Save a named preset to ``.dartwork_ui_presets.json``.

    Parameters
    ----------
    label : str
        User-defined name for this preset.
    params : dict
        Parameter values.
    """
    presets = _load_preset_file()
    presets.append(
        {
            "label": label,
            "params": _serializable(params),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    _write_preset_file(presets)


def load_presets() -> list[dict[str, Any]]:
    """Load all named presets.

    Returns
    -------
    list[dict]
        Each dict has ``label``, ``params``, and ``timestamp``.
    """
    return _load_preset_file()


def _load_preset_file() -> list[dict[str, Any]]:
    """Read the preset JSON file.

    Returns
    ----------
    list[dict[str, Any]]
        Preset list, or empty list if file is missing.
    """
    path = _preset_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _write_preset_file(presets: list[dict[str, Any]]) -> None:
    """Write the preset list to the JSON file.

    Parameters
    ----------
    presets : list[dict[str, Any]]
        Full preset list to write.
    """
    _atomic_write_text(
        _preset_path(), json.dumps(presets, indent=2, ensure_ascii=False) + "\n"
    )


# ============================================================================
# Helpers
# ============================================================================


def _serializable(params: dict[str, Any]) -> dict[str, Any]:
    """Convert parameter values to JSON-serializable types.

    Parameters
    ----------
    params : dict[str, Any]
        Original parameter dictionary.

    Returns
    ----------
    dict[str, Any]
        JSON-serializable parameter dictionary.
    """
    out: dict[str, Any] = {}
    for k, v in params.items():
        if isinstance(v, (int, float, str, bool, type(None))):
            out[k] = v
        elif isinstance(v, (list, tuple)):
            out[k] = list(v)
        else:
            out[k] = str(v)
    return out
