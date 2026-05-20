"""Bundled agent-onboarding files (``AGENTS.md``, ``CLAUDE.md``,
``llms.txt``, ``llms-full.txt``).

These four documents live at the repo root for human/GitHub-Raw consumption,
but the wheel re-bundles them under ``dartwork_mpl/asset/agent/`` (see
``[tool.hatch.build.targets.wheel.force-include]`` in ``pyproject.toml``)
so installed users can read them through ``importlib.resources`` rather
than reaching outside the package directory.

This module exposes a single public helper, :func:`get_agent_doc`, which
returns the file contents as a string. It also defines a constant
:data:`AGENT_DOCS` listing the four supported document names so agents
can enumerate them programmatically.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["AGENT_DOCS", "agent_doc_path", "get_agent_doc"]

# Canonical bundle of agent-onboarding documents shipped with the wheel.
# These names map to repo-root files of the same suffix and to entries in
# ``[tool.hatch.build.targets.wheel.force-include]``.
AGENT_DOCS: tuple[str, ...] = ("AGENTS", "CLAUDE", "llms", "llms-full")

# In the wheel these land under ``dartwork_mpl/asset/agent/``; in an
# editable checkout they live at the repo root instead. The lookup
# falls back to the repo-root location so editable installs still work.
_BUNDLED_DIR: Path = Path(__file__).parent / "asset" / "agent"
_REPO_ROOT: Path = Path(__file__).resolve().parents[2]

_SUFFIXES: dict[str, str] = {
    "AGENTS": ".md",
    "CLAUDE": ".md",
    "llms": ".txt",
    "llms-full": ".txt",
}


def agent_doc_path(name: str) -> Path:
    """Return the absolute path to a bundled agent-onboarding file.

    The wheel install path (``asset/agent/``) is preferred. If the
    package is being used from an editable checkout, the repo-root copy
    is returned instead so developers still see the canonical source.

    Parameters
    ----------
    name : str
        One of :data:`AGENT_DOCS` — ``"AGENTS"``, ``"CLAUDE"``,
        ``"llms"``, or ``"llms-full"``.

    Returns
    -------
    Path
        Absolute filesystem path to the document.

    Raises
    ------
    ValueError
        If ``name`` is not a recognised agent document.
    FileNotFoundError
        If neither the wheel-bundled copy nor the repo-root copy exists.
    """
    if name not in _SUFFIXES:
        raise ValueError(
            f"Unknown agent doc {name!r}; expected one of {AGENT_DOCS}."
        )
    filename = f"{name}{_SUFFIXES[name]}"
    bundled = _BUNDLED_DIR / filename
    if bundled.exists():
        return bundled
    fallback = _REPO_ROOT / filename
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        f"Agent doc {name!r} not found at {bundled} or {fallback}. "
        f"If you installed from a wheel, reinstall the package; from a "
        f"checkout, the file should live at the repository root."
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
