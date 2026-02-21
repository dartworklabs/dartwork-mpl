"""Configuration persistence for the Dartwork UI module.

Handles saving/loading the current parameter state and maintaining
an append-only history file in the working directory.

Files created (in CWD):
    ``.dartwork_ui_config.json``
        Last-used parameter set — auto-loaded on startup.
    ``.dartwork_ui_history.jsonl``
        Append-only log of every parameter set used, one JSON
        object per line.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Default file names
CONFIG_FILENAME = ".dartwork_ui_config.json"
HISTORY_FILENAME = ".dartwork_ui_history.jsonl"

# Base directory — set to the script's parent directory by ui.run()
_base_dir: Path | None = None


def set_base_dir(path: Path) -> None:
    """Set the base directory for config/history files.

    Called by ``ui.run()`` with the script's parent directory
    so that files are saved alongside the user's script, not in CWD.
    """
    global _base_dir
    _base_dir = Path(path)


def _get_base_dir() -> Path:
    """Return the configured base dir, falling back to CWD."""
    return _base_dir if _base_dir is not None else Path.cwd()


def _config_path() -> Path:
    return _get_base_dir() / CONFIG_FILENAME


def _history_path() -> Path:
    return _get_base_dir() / HISTORY_FILENAME


# ============================================================================
# Save / Load current config
# ============================================================================


def save_config(
    params: dict[str, Any],
    function_name: str = "",
) -> None:
    """Persist the current parameter set to ``.dartwork_ui_config.json``.

    Parameters
    ----------
    params : dict
        Current parameter values.
    function_name : str
        Name of the figure generator function.
    """
    data = {
        "function": function_name,
        "params": _serializable(params),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _config_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_config() -> dict[str, Any] | None:
    """Load parameters from ``.dartwork_ui_config.json`` if it exists.

    Returns
    -------
    dict or None
        The ``params`` mapping, or ``None`` if the file doesn't exist.
    """
    path = _config_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("params")
    except (json.JSONDecodeError, KeyError):
        return None


# ============================================================================
# History (append-only JSONL)
# ============================================================================


def append_history(
    params: dict[str, Any],
    label: str | None = None,
) -> None:
    """Append a parameter snapshot to ``.dartwork_ui_history.jsonl``.

    Parameters
    ----------
    params : dict
        Parameter values.
    label : str, optional
        User-defined label for this snapshot (preset name).
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "params": _serializable(params),
    }
    if label:
        record["label"] = label

    with open(_history_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_history() -> list[dict[str, Any]]:
    """Load all history records.

    Returns
    -------
    list[dict]
        Each dict has ``timestamp``, ``params``, and optionally ``label``.
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


def load_presets() -> list[dict[str, Any]]:
    """Load only labelled history records (user-saved presets).

    Returns
    -------
    list[dict]
        Records that have a non-empty ``label`` field.
    """
    return [r for r in load_history() if r.get("label")]


# ============================================================================
# Helpers
# ============================================================================


def _serializable(params: dict[str, Any]) -> dict[str, Any]:
    """Convert parameter values to JSON-serializable types."""
    out: dict[str, Any] = {}
    for k, v in params.items():
        if isinstance(v, (int, float, str, bool, type(None))):
            out[k] = v
        elif isinstance(v, (list, tuple)):
            out[k] = list(v)
        else:
            out[k] = str(v)
    return out
