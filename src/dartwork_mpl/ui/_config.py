"""Legacy preset-file helpers kept for callers outside the viewer's HTTP routes.

``save_preset`` / ``load_presets`` replace the removed ``append_history`` /
``load_history`` (docs/migration.md). They read and write
``.dartwork_ui_presets.json`` in the directory set by ``set_base_dir``
(default: the current directory). The viewer itself uses ``state``.
"""

import contextlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .state import StateFile


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


# Default file name (the viewer's own presets file)
PRESET_FILENAME = StateFile.PRESETS.value

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
