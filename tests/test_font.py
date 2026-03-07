"""Tests for font module."""

from __future__ import annotations

from dartwork_mpl.font import _add_fonts, ensure_loaded


class TestEnsureLoaded:
    """Tests for ensure_loaded()."""

    def test_does_not_crash(self) -> None:
        ensure_loaded()

    def test_idempotent(self) -> None:
        """Calling ensure_loaded() twice should not raise."""
        ensure_loaded()
        ensure_loaded()


class TestAddFonts:
    """Tests for _add_fonts()."""

    def test_does_not_crash(self) -> None:
        _add_fonts()
