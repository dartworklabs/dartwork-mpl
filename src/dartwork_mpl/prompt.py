"""Prompt guide file management module.

Provides helper functions for finding, reading, listing, and copying
the prompt guide Markdown files bundled with the dartwork package.
"""

from __future__ import annotations

__all__ = [
    "copy_prompt",
    "find_template",
    "get_prompt",
    "list_prompts",
    "prompt_path",
]

import json
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
_CANONICAL_PROMPTS: frozenset[str] = frozenset(
    {"00-index", "01-policy", "03-recipes"}
)


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


_TEMPLATE_INDEX_PATH: Path = _PROMPT_DIR / "05-templates" / "_index.json"


def find_template(
    intent: str, top_k: int = 5, tier: str | None = None
) -> list[dict[str, object]]:
    """Rank the bundled AI plot templates against a free-text intent.

    Mirrors the MCP ``find_template`` tool so the same ranking is
    reachable natively from Python without the MCP server. Each
    template's metadata text (``use_case`` + ``data_shape`` +
    ``difficulty`` + ``tags``) is scanned for occurrences of every
    whitespace-separated lowercase token in ``intent``; the count of
    matched tokens is the score.

    Parameters
    ----------
    intent : str
        Free-text description, e.g. ``"horizontal bar comparison"``.
    top_k : int, optional
        Maximum number of matches to return, by default 5.
    tier : str | None, optional
        ``"basic"`` (default-equivalent) scans only the tier-1 minimal
        templates. ``"advanced"`` scans only the tier-2 narrative
        templates (story-led titles, reference lines, value labels).
        ``"all"`` (or any other non-None string) scans both tiers and
        returns ``"tier"`` on each match so the caller can tell which
        bucket a hit came from. ``None`` (default) preserves the
        original surface: basic tier only, no ``"tier"`` field.

    Returns
    -------
    list[dict]
        Each match is ``{"template_id", "score", **metadata}``.
        When ``tier`` is non-``None`` each entry also carries
        ``"tier"`` so callers using ``"all"`` can distinguish.
        Empty list when ``intent`` is blank or no template overlaps.
    """
    if not _TEMPLATE_INDEX_PATH.exists():
        return []
    index = json.loads(_TEMPLATE_INDEX_PATH.read_text(encoding="utf-8"))

    tokens = [t for t in intent.lower().split() if t]
    if not tokens:
        return []

    # Build the (template_id, meta, source_tier) iter based on tier arg.
    advanced_section: dict[str, dict[str, object]] = index.get("advanced", {})

    def _basic_items() -> list[tuple[str, dict[str, object], str]]:
        return [
            (tid, meta, "basic")
            for tid, meta in index.items()
            if tid != "advanced"
        ]

    def _advanced_items() -> list[tuple[str, dict[str, object], str]]:
        return [
            (tid, meta, "advanced") for tid, meta in advanced_section.items()
        ]

    if tier is None or tier == "basic":
        items = _basic_items()
    elif tier == "advanced":
        items = _advanced_items()
    else:
        # "all" (or any other string) -> both tiers.
        items = _basic_items() + _advanced_items()

    scored: list[tuple[int, str, dict[str, object], str]] = []
    for template_id, meta, source_tier in items:
        raw_tags = meta.get("tags", [])
        tag_str = (
            " ".join(str(t) for t in raw_tags)
            if isinstance(raw_tags, list)
            else str(raw_tags)
        )
        haystack = " ".join(
            [
                str(meta.get("use_case", "")),
                str(meta.get("data_shape", "")),
                str(meta.get("difficulty", "")),
                tag_str,
                str(meta.get("narrative", "")),
            ]
        ).lower()
        score = sum(1 for t in tokens if t in haystack)
        if score > 0:
            scored.append((score, template_id, meta, source_tier))

    scored.sort(key=lambda item: (-item[0], item[1]))

    # Preserve the original output shape when no tier arg was supplied —
    # callers that pre-date the tier system don't suddenly see a new
    # field they don't know about.
    if tier is None:
        return [
            {"template_id": template_id, "score": score, **meta}
            for score, template_id, meta, _ in scored[:top_k]
        ]
    return [
        {
            "template_id": template_id,
            "score": score,
            "tier": source_tier,
            **meta,
        }
        for score, template_id, meta, source_tier in scored[:top_k]
    ]


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
