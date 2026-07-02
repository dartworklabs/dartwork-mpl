"""``dm.__version__`` must track the installed package metadata (#230).

The version literal in ``__init__.py`` drifted (0.4.0) from the shipped
package metadata (0.4.1) because a release bumped ``pyproject.toml`` but
not the hand-maintained literal. Deriving it from
``importlib.metadata`` removes the second source of truth.
"""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest

import dartwork_mpl as dm

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_version_matches_installed_metadata() -> None:
    """``dm.__version__`` equals the distribution's metadata version.

    Guards against reintroducing a hand-maintained literal that could
    diverge from ``importlib.metadata``. Note this compares the two
    metadata-derived values, so it cannot by itself catch drift from
    ``pyproject.toml`` — see ``test_version_matches_pyproject``.
    """
    assert dm.__version__ == importlib.metadata.version("dartwork-mpl")


def test_version_matches_pyproject() -> None:
    """Installed metadata version matches ``pyproject.toml`` (the SSOT).

    Unlike the metadata-vs-metadata check above, this reads the version
    straight from ``pyproject.toml`` and so catches *real* drift: a
    release that bumped ``pyproject.toml`` without rebuilding, or a
    stale editable install (``pip install -e .`` captures the version at
    install time). Skipped when ``pyproject.toml`` isn't reachable
    (tests run against an installed wheel) or on Python < 3.11 where the
    stdlib ``tomllib`` parser is unavailable.
    """
    if not _PYPROJECT.is_file():
        pytest.skip("pyproject.toml not reachable (installed-wheel test run)")
    tomllib = pytest.importorskip("tomllib")  # py3.11+; skipped on 3.10
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    pyproject_version = data["project"]["version"]
    assert dm.__version__ == pyproject_version, (
        f"dm.__version__ ({dm.__version__}) != pyproject.toml "
        f"({pyproject_version}); rebuild or reinstall the package "
        "(`uv sync` / `pip install -e .`)."
    )


def test_version_is_nonempty_string() -> None:
    """``dm.__version__`` is a usable, non-placeholder string."""
    assert isinstance(dm.__version__, str)
    assert dm.__version__
    assert dm.__version__ != "0.0.0"
