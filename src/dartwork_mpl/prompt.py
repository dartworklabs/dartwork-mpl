"""Prompt guide file management.

Provides helpers to find, read, list, and copy prompt guide
Markdown files bundled with the package.
"""

from __future__ import annotations

__all__ = ["prompt_path", "get_prompt", "list_prompts", "copy_prompt"]

from pathlib import Path
from shutil import copy2

from ._helpers import create_parent_path


def prompt_path(name: str) -> Path:
    """Get the path to a prompt guide file.

    Parameters
    ----------
    name : str
        Name of the prompt guide
        (``'layout-guide'`` or ``'general-guide'``).

    Returns
    -------
    Path
        Path to the prompt guide file.

    Raises
    ------
    ValueError
        If the prompt guide is not found.
    """
    path: Path = Path(__file__).parent / f"asset/prompt/{name}.md"
    if not path.exists():
        raise ValueError(f"Prompt guide not found: {name}")
    return path


def get_prompt(name: str) -> str:
    """Read and return the content of a prompt guide file.

    Parameters
    ----------
    name : str
        Name of the prompt guide.

    Returns
    -------
    str
        Content of the prompt guide file.
    """
    path = prompt_path(name)
    return path.read_text(encoding="utf-8")


def list_prompts() -> list[str]:
    """List all available prompt guide files.

    Returns
    -------
    list[str]
        Sorted list of available prompt guide names.
    """
    path: Path = Path(__file__).parent / "asset/prompt"
    if not path.exists():
        return []
    return sorted([p.stem for p in path.glob("*.md")])


def copy_prompt(name: str, destination: str | Path) -> Path:
    """Copy a prompt guide file to the specified destination.

    Parameters
    ----------
    name : str
        Name of the prompt guide.
    destination : str or Path
        Destination path. If a directory, the file keeps its
        original name. If a file path, the file is copied there.

    Returns
    -------
    Path
        Path to the copied file.

    Raises
    ------
    ValueError
        If the prompt guide is not found.
    """
    source_path = prompt_path(name)
    dest_path = Path(destination)

    if dest_path.is_dir() or (not dest_path.exists() and not dest_path.suffix):
        dest_path = dest_path / f"{name}.md"

    create_parent_path(dest_path)
    copy2(source_path, dest_path)

    return dest_path
