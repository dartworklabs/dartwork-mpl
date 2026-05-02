"""Prompt guide file management module.

Provides helper functions for finding, reading, listing, and copying
the prompt guide Markdown files bundled with the dartwork package.
"""

from __future__ import annotations

__all__ = ["copy_prompt", "get_prompt", "list_prompts", "prompt_path"]

import warnings
from pathlib import Path
from shutil import copy2

from ._helpers import create_parent_path

_PROMPT_DIR: Path = Path(__file__).parent / "asset/prompt"

# Canonical Markdown prompt corpus (T5). ``list_prompts`` warns when a
# ``.md`` file outside this set appears next to it. The YAML
# anti-pattern catalog (``02-anti-patterns.yaml``) and the
# ``05-templates/`` subdirectory are separate surfaces with their own
# loaders and are intentionally not listed here.
_CANONICAL_PROMPTS: frozenset[str] = frozenset({
    "00-index",
    "01-policy",
    "03-recipes",
})


def prompt_path(name: str) -> Path:
    """Get the absolute path to a prompt guide file.

    Parameters
    ----------
    name : str
        Name of the prompt guide to retrieve
        (e.g., ``'00-index'``, ``'01-policy'``, ``'03-recipes'``).

    Returns
    -------
    Path
        Path to the prompt guide Markdown file.

    Raises
    ------
    ValueError
        If the specified guide cannot be found in the library.
    """
    path: Path = _PROMPT_DIR / f"{name}.md"
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
    """List the bundled prompt guide files.

    The canonical corpus is exactly four entries — ``00-index``,
    ``01-policy``, ``02-anti-patterns`` (YAML, not surfaced here),
    ``03-recipes`` — plus the ``05-templates/`` subdirectory listed
    separately. If extra ``*.md`` files appear (stale leftovers, an
    in-progress addition, etc.), this function still returns them but
    emits a :class:`UserWarning` so drift surfaces immediately.

    Returns
    -------
    list[str]
        Sorted list of available prompt guide names.
    """
    if not _PROMPT_DIR.exists():
        return []
    found = sorted([p.stem for p in _PROMPT_DIR.glob("*.md")])
    unexpected = [name for name in found if name not in _CANONICAL_PROMPTS]
    if unexpected:
        warnings.warn(
            "Unexpected prompt guide(s) found alongside the canonical "
            f"corpus: {unexpected}. The canonical set is "
            f"{sorted(_CANONICAL_PROMPTS)}. Either fold the content into "
            "an existing canonical file or extend _CANONICAL_PROMPTS in "
            "dartwork_mpl/prompt.py.",
            UserWarning,
            stacklevel=2,
        )
    return found


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
