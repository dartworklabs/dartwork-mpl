"""Prompt guide file management module.

Provides helper functions for finding, reading, listing, and copying
the prompt guide Markdown files bundled with the dartwork package.
"""

from __future__ import annotations

__all__ = ["prompt_path", "get_prompt", "list_prompts", "copy_prompt"]

from pathlib import Path
from shutil import copy2

from ._helpers import create_parent_path


def prompt_path(name: str) -> Path:
    """Get the absolute path to a prompt guide file.

    Parameters
    ----------
    name : str
        Name of the prompt guide to retrieve
        (e.g., ``'layout-guide'``, ``'general-guide'``).

    Returns
    -------
    Path
        Path to the prompt guide Markdown file.

    Raises
    ------
    ValueError
        If the specified guide cannot be found in the library.
    """
    path: Path = Path(__file__).parent / f"asset/prompt/{name}.md"
    if not path.exists():
        raise ValueError(f"Prompt guide not found: {name}")
    return path


def get_prompt(name: str) -> str:
    """Read a prompt guide file and return its full content as a string.

    Parameters
    ----------
    name : str
        Name of the prompt guide to read.

    Returns
    -------
    str
        The Markdown content of the prompt guide.
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
    """Copy a bundled prompt guide file to the specified destination.

    Parameters
    ----------
    name : str
        Name of the prompt guide to copy.
    destination : str | Path
        Destination path.
        If a directory, the file is copied with its original name
        (``name.md``). If a file path, that name is used.

    Returns
    -------
    Path
        Absolute path of the newly copied file.

    Raises
    ------
    ValueError
        If the source prompt guide cannot be found.
    """
    source_path = prompt_path(name)
    dest_path = Path(destination)

    if dest_path.is_dir() or (not dest_path.exists() and not dest_path.suffix):
        dest_path = dest_path / f"{name}.md"

    create_parent_path(dest_path)
    copy2(source_path, dest_path)

    return dest_path
