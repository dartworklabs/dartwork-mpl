"""``dm.__version__`` must track the installed package metadata (#230).

The version literal in ``__init__.py`` drifted (0.4.0) from the shipped
package metadata (0.4.1) because a release bumped ``pyproject.toml`` but
not the hand-maintained literal. Deriving it from
``importlib.metadata`` removes the second source of truth.
"""

from __future__ import annotations

import importlib.metadata

import dartwork_mpl as dm


def test_version_matches_installed_metadata() -> None:
    """``dm.__version__`` equals the distribution's metadata version."""
    assert dm.__version__ == importlib.metadata.version("dartwork-mpl")


def test_version_is_nonempty_string() -> None:
    """``dm.__version__`` is a usable, non-placeholder string."""
    assert isinstance(dm.__version__, str)
    assert dm.__version__
    assert dm.__version__ != "0.0.0"
