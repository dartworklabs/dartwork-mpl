"""Bundled agent-onboarding files (``AGENTS``, ``CLAUDE``, ``llms``,
``llms-full``).

``AGENTS`` and ``CLAUDE`` both hold the short consumer entry for coding
agents working in a project that has dartwork-mpl installed, pointing to the
bundled skill (:mod:`dartwork_mpl.skills`). They are package data at
``dartwork_mpl/asset/agent/AGENTS.md`` and ``CLAUDE.md`` (identical, the
same asset paths as before). The repository's own root ``AGENTS.md`` /
``CLAUDE.md`` are contributor documents and are not shipped.

``llms`` and ``llms-full`` live at the repo root for GitHub-raw consumption;
the wheel re-bundles them under ``dartwork_mpl/asset/agent/`` (see
``[tool.hatch.build.targets.wheel.force-include]`` in ``pyproject.toml``)
so installed users can read them through ``importlib.resources``.

This module exposes :func:`get_agent_doc`, which returns a document as a
string, :func:`agent_doc_path`, and the constant :data:`AGENT_DOCS` listing
the four supported names so agents can enumerate them programmatically.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["AGENT_DOCS", "agent_doc_path", "get_agent_doc"]

# Canonical names of the agent-onboarding documents shipped with the wheel.
AGENT_DOCS: tuple[str, ...] = ("AGENTS", "CLAUDE", "llms", "llms-full")

# Name -> file name under ``asset/agent/``.
_FILENAMES: dict[str, str] = {
    "AGENTS": "AGENTS.md",
    "CLAUDE": "CLAUDE.md",
    "llms": "llms.txt",
    "llms-full": "llms-full.txt",
}

# Files that are package data in ``src/dartwork_mpl/asset/agent/`` in every
# install (the consumer entry, mirrored under both names); the rest are
# force-included from the repo root into the wheel.
_PACKAGE_DOCS: frozenset[str] = frozenset({"AGENTS.md", "CLAUDE.md"})

# In the wheel every file lands under ``dartwork_mpl/asset/agent/``; in an
# editable checkout the force-included ones live at the repo root instead,
# so the lookup falls back there for them.
_BUNDLED_DIR: Path = Path(__file__).parent / "asset" / "agent"
_REPO_ROOT: Path = Path(__file__).resolve().parents[2]


def agent_doc_path(name: str) -> Path:
    """Return the absolute path to a bundled agent-onboarding file.

    The packaged copy (``asset/agent/``) is preferred. For ``llms`` and
    ``llms-full`` in an editable checkout, the repo-root copy is returned
    instead so developers see the canonical source.

    Parameters
    ----------
    name : str
        One of :data:`AGENT_DOCS` — ``"AGENTS"``, ``"CLAUDE"`` (both the
        consumer entry), ``"llms"``, or ``"llms-full"``.

    Returns
    -------
    Path
        Absolute filesystem path to the document.

    Raises
    ------
    ValueError
        If ``name`` is not a recognised agent document.
    FileNotFoundError
        If neither the bundled copy nor the repo-root copy exists.
    """
    if name not in _FILENAMES:
        raise ValueError(
            f"Unknown agent doc {name!r}; expected one of {AGENT_DOCS}."
        )
    filename = _FILENAMES[name]
    bundled = _BUNDLED_DIR / filename
    if bundled.exists():
        return bundled
    fallback = _REPO_ROOT / filename
    if filename not in _PACKAGE_DOCS and fallback.exists():
        return fallback
    raise FileNotFoundError(
        f"Agent doc {name!r} not found at {bundled}"
        + ("" if filename in _PACKAGE_DOCS else f" or {fallback}")
        + ". If you installed from a wheel, reinstall the package."
    )


def get_agent_doc(name: str) -> str:
    """Return the contents of a bundled agent-onboarding document.

    Parameters
    ----------
    name : str
        One of :data:`AGENT_DOCS`.

    Returns
    -------
    str
        File contents as a UTF-8 string.
    """
    return agent_doc_path(name).read_text(encoding="utf-8")
