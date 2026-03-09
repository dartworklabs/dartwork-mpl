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

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Default file names
CONFIG_FILENAME = ".dartwork_ui_config.json"
PRESET_FILENAME = ".dartwork_ui_presets.json"
HISTORY_FILENAME = ".dartwork_ui_history.jsonl"

# Base directory — set to the script's parent directory by ui.run()
_base_dir: Path | None = None


def set_base_dir(path: Path) -> None:
    """설정/이력 파일의 기본 디렉토리를 설정한다.

    ``ui.run()``이 스크립트의 상위 디렉토리를 전달하여
    파일이 CWD가 아닌 사용자 스크립트 옆에 저장되도록 한다.

    Parameters
    ----------
    path : Path
        기본 디렉토리 경로.
    """
    global _base_dir
    _base_dir = Path(path)


def _get_base_dir() -> Path:
    """설정된 기본 디렉토리를 반환한다.

    설정되지 않은 경우 현재 작업 디렉토리로 대체한다.

    Returns
    ----------
    Path
        기본 디렉토리 경로.
    """
    return _base_dir if _base_dir is not None else Path.cwd()


def _config_path() -> Path:
    """설정 파일의 전체 경로를 반환한다.

    Returns
    ----------
    Path
        ``.dartwork_ui_config.json`` 파일 경로.
    """
    return _get_base_dir() / CONFIG_FILENAME


def _preset_path() -> Path:
    """프리셋 파일의 전체 경로를 반환한다.

    Returns
    ----------
    Path
        ``.dartwork_ui_presets.json`` 파일 경로.
    """
    return _get_base_dir() / PRESET_FILENAME


def _history_path() -> Path:
    """이력 파일의 전체 경로를 반환한다.

    Returns
    ----------
    Path
        ``.dartwork_ui_history.jsonl`` 파일 경로.
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
    _config_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
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
        return json.loads(path.read_text(encoding="utf-8"))
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
    _preset_path().write_text(
        json.dumps(presets, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
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
    """파라미터 값을 JSON 직렬화 가능한 타입으로 변환한다.

    Parameters
    ----------
    params : dict[str, Any]
        원본 파라미터 딕셔너리.

    Returns
    ----------
    dict[str, Any]
        JSON 직렬화 가능한 파라미터 딕셔너리.
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
