"""Verify 0.3 deprecated tokens raise AttributeError in 0.4.x.

The width tokens (``SW``/``MW``/``TW``/``DW``/``WIDTHS``), figure-size
tuples (``FS_*``), the ``cm2in`` helper, and the ``agent_utils``/``xplot``
submodule aliases were all deprecated in 0.4.0 and removed in 0.4.x.
"""

from __future__ import annotations

import pytest

import dartwork_mpl as dm

REMOVED_NAMES: tuple[str, ...] = (
    "SW",
    "MW",
    "TW",
    "DW",
    "WIDTHS",
    "FS_SINGLE",
    "FS_DOUBLE",
    "FS_SQUARE",
    "FS_WIDE",
    "FS_TALL",
    "FS_GOLDEN",
    "FS_SLIDE",
    "FS_A4",
    "cm2in",
    "agent_utils",
    "xplot",
)


@pytest.mark.parametrize("name", REMOVED_NAMES)
def test_removed_names_raise_attribute_error(name):
    """Each removed name must raise ``AttributeError`` (not silently
    resolve, not emit a DeprecationWarning) in 0.4.x."""
    with pytest.raises(AttributeError, match=name):
        getattr(dm, name)


def test_unknown_attribute_still_raises():
    with pytest.raises(AttributeError, match="completely_made_up"):
        _ = dm.completely_made_up


def test_agent_utils_submodule_import_raises():
    with pytest.raises(ModuleNotFoundError):
        import dartwork_mpl.agent_utils  # noqa: F401


def test_xplot_submodule_import_raises():
    with pytest.raises(ModuleNotFoundError):
        import dartwork_mpl.xplot  # noqa: F401
