"""Verify removed tokens raise AttributeError with a migration hint.

The width tokens (``SW``/``MW``/``TW``/``DW``/``WIDTHS``), figure-size
tuples (``FS_*``), the ``cm2in`` helper, the figure constructors
(``subplots``/``figure``), and the ``agent_utils``/``xplot`` aliases
were removed across 0.4.x; the ``install_llm_txt`` installer
(``install_llm_txt``/``uninstall_llm_txt``/``INSTALL_TARGETS``) was
removed in 0.5. Each must raise ``AttributeError`` whose message names
the replacement API (the contract CLAUDE.md / AGENTS.md advertise).
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
    "subplots",
    "figure",
    "install_llm_txt",
    "uninstall_llm_txt",
    "INSTALL_TARGETS",
)

# Removed name → a substring its migration message must contain so the
# error actually points the caller at the replacement API.
REMOVED_NAME_HINTS: dict[str, str] = {
    "subplots": "plt.subplots",
    "figure": "plt.figure",
    "agent_utils": "dm.helpers",
    "xplot": "dm.templates",
    "install_llm_txt": "get_agent_doc",
    "uninstall_llm_txt": "get_agent_doc",
    "INSTALL_TARGETS": "get_agent_doc",
}


@pytest.mark.parametrize("name", REMOVED_NAMES)
def test_removed_names_raise_attribute_error(name):
    """Each removed name must raise ``AttributeError`` (not silently
    resolve, not emit a DeprecationWarning) in 0.4.x."""
    with pytest.raises(AttributeError, match=name):
        getattr(dm, name)


def test_unknown_attribute_still_raises():
    with pytest.raises(AttributeError, match="completely_made_up"):
        _ = dm.completely_made_up


def test_removed_width_token_message_names_new_api():
    """Accessing a removed width token names the replacement API (#231)."""
    with pytest.raises(AttributeError) as excinfo:
        _ = dm.SW
    msg = str(excinfo.value)
    assert "figsize" in msg or "col1" in msg
    assert "migration" in msg.lower()


def test_removed_cm2in_message_names_new_api():
    """``dm.cm2in`` points at ``dm.cm`` / ``dm.figsize`` (#231)."""
    with pytest.raises(AttributeError) as excinfo:
        _ = dm.cm2in
    msg = str(excinfo.value)
    assert "dm.cm" in msg or "figsize" in msg


def test_removed_fs_token_message_names_new_api():
    """A removed ``FS_*`` figure-size tuple points at ``dm.figsize`` (#231)."""
    with pytest.raises(AttributeError) as excinfo:
        _ = dm.FS_WIDE
    assert "figsize" in str(excinfo.value)


@pytest.mark.parametrize("name", sorted(REMOVED_NAME_HINTS))
def test_removed_name_message_names_replacement(name):
    """Each removed name's error must name its replacement API + migration.

    Guards the CLAUDE.md / AGENTS.md contract: accessing a removed name
    raises an error "naming the new API", not Python's bare
    "module has no attribute" string.
    """
    with pytest.raises(AttributeError) as excinfo:
        getattr(dm, name)
    msg = str(excinfo.value)
    assert REMOVED_NAME_HINTS[name] in msg
    assert "migration" in msg.lower()


def test_agent_utils_submodule_import_raises():
    with pytest.raises(ModuleNotFoundError):
        import dartwork_mpl.agent_utils  # noqa: F401


def test_xplot_submodule_import_raises():
    with pytest.raises(ModuleNotFoundError):
        import dartwork_mpl.xplot  # noqa: F401


def _removed_names_from_source() -> dict[str, tuple[str, str]]:
    """The runtime removal map itself — so this guard can never lag it."""
    from dartwork_mpl import _REMOVED_NAMES

    return _REMOVED_NAMES


@pytest.mark.parametrize("name", sorted(_removed_names_from_source()))
def test_every_removed_name_raises_with_version_and_hint(name):
    """Parametrized off ``_REMOVED_NAMES`` directly: a name added to the
    runtime map (e.g. ``auto_layout`` in 0.5.4, which this file's
    hand-written ``REMOVED_NAMES`` tuple previously missed) is
    automatically covered and can no longer silently lag."""
    version, hint = _removed_names_from_source()[name]
    with pytest.raises(AttributeError) as excinfo:
        getattr(dm, name)
    msg = str(excinfo.value)
    assert f"removed in {version}" in msg
    assert "migration" in msg.lower()
    # The message must carry the hint's leading replacement pointer.
    assert hint.split(" ")[0] in msg
