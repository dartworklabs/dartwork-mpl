"""Configuration persistence for the Dartwork UI module.

Handles saving/loading the current parameter state and maintaining
an append-only history file in the working directory.

Files created (in CWD):
    ``.dartwork_ui_config.json``
        Last-used parameter set — auto-loaded on startup.
    ``.dartwork_ui_presets.json``
        Named presets saved by the user (JSON array).
    ``.dartwork_ui_history.jsonl``
        Legacy append-only log (kept for backward compat).
"""

import contextlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


# Default file names
CONFIG_FILENAME = ".dartwork_ui_config.json"
PRESET_FILENAME = ".dartwork_ui_presets.json"
HISTORY_FILENAME = ".dartwork_ui_history.jsonl"

# Base directory — set to the script's parent directory by ui.run()
_base_dir: Path | None = None


def set_base_dir(path: Path) -> None:
    """Set the base directory for config and history files.

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


def _config_path() -> Path:
    """Return the full path to the config file.

    Returns
    ----------
    Path
        Path to ``.dartwork_ui_config.json``.
    """
    return _get_base_dir() / CONFIG_FILENAME


def _preset_path() -> Path:
    """Return the full path to the presets file.

    Returns
    ----------
    Path
        Path to ``.dartwork_ui_presets.json``.
    """
    return _get_base_dir() / PRESET_FILENAME


def _history_path() -> Path:
    """Return the full path to the history file.

    Returns
    ----------
    Path
        Path to ``.dartwork_ui_history.jsonl``.
    """
    return _get_base_dir() / HISTORY_FILENAME


# ============================================================================
# Save / Load current config
# ============================================================================


def save_config(
    params: dict[str, Any],
    function_name: str = "",
    tabs: list[dict[str, Any]] | None = None,
    fig_width: int | None = None,
) -> None:
    """Persist state to ``.dartwork_ui_config.json``.

    Parameters
    ----------
    params : dict
        Current parameter values.
    function_name : str
        Name of the figure generator function.
    tabs : list[dict], optional
        Tab state to persist.
    fig_width : int, optional
        Figure display width percentage.
    """
    data: dict[str, Any] = {
        "function": function_name,
        "params": _serializable(params),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if tabs is not None:
        data["tabs"] = tabs
    if fig_width is not None:
        data["figWidth"] = fig_width
    _atomic_write_text(
        _config_path(), json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )


def load_config() -> dict[str, Any] | None:
    """Load full config from ``.dartwork_ui_config.json``.

    Returns
    ----------
    dict or None
        The full config (``params``, ``tabs``, etc.),
        or ``None`` if the file doesn't exist.
    """
    path = _config_path()
    if not path.exists():
        return None
    try:
        from typing import cast

        data = json.loads(path.read_text(encoding="utf-8"))
        return cast(dict[str, Any], data)
    except (json.JSONDecodeError, KeyError):
        return None


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


def delete_preset(index: int) -> bool:
    """Delete a preset by its index.

    Parameters
    ----------
    index : int
        Zero-based index of the preset to delete.

    Returns
    -------
    bool
        ``True`` if the preset was deleted, ``False`` if
        the index is out of range.
    """
    presets = _load_preset_file()
    if index < 0 or index >= len(presets):
        return False
    presets.pop(index)
    _write_preset_file(presets)
    return True


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
# History — legacy (kept for backward compatibility)
# ============================================================================


def append_history(params: dict[str, Any], label: str | None = None) -> None:
    """Append a parameter snapshot to ``.dartwork_ui_history.jsonl``.

    .. deprecated::
        Use :func:`save_preset` for named presets instead.

    Parameters
    ----------
    params : dict
        Parameter values.
    label : str, optional
        User-defined label for this snapshot (preset name).
    """
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "params": _serializable(params),
    }
    if label:
        record["label"] = label

    with open(_history_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_history() -> list[dict[str, Any]]:
    """Load all history records.

    .. deprecated::
        Use :func:`load_presets` instead.

    Returns
    -------
    list[dict]
        Each dict has ``timestamp``, ``params``,
        and optionally ``label``.
    """
    path = _history_path()
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


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
