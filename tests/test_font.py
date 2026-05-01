"""Tests for font module."""

from __future__ import annotations

import warnings

import pytest

from dartwork_mpl import font as font_module
from dartwork_mpl.font import _EXPECTED_MIN_FONTS, _add_fonts, ensure_loaded


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

    def test_warns_when_bundle_looks_emptied(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ``findSystemFonts`` returns fewer than the sanity floor,
        ``_add_fonts`` should emit a :class:`UserWarning` so users can
        spot a degraded font bundle (slim install / accidental delete).
        """

        def fake_find(_paths: object) -> list[str]:
            return []  # zero fonts -> definitely below the threshold

        monkeypatch.setattr(
            font_module.font_manager, "findSystemFonts", fake_find
        )
        # Replace addfont with a no-op so we don't pollute matplotlib's
        # global font manager with mock entries during the test.
        monkeypatch.setattr(
            font_module.font_manager.fontManager, "addfont", lambda _path: None
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _add_fonts()

        bundle_warnings = [
            w
            for w in caught
            if issubclass(w.category, UserWarning)
            and "dartwork-mpl" in str(w.message)
        ]
        assert len(bundle_warnings) == 1
        msg = str(bundle_warnings[0].message)
        assert "0 bundled font file(s)" in msg
        # The user-facing remediation hint must be present.
        assert "Reinstall" in msg

    def test_no_warning_when_bundle_is_intact(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A healthy bundle (>= sanity floor) must NOT emit the
        degraded-bundle warning."""

        def fake_find(_paths: object) -> list[str]:
            # Fabricate exactly enough "paths" to clear the floor; the
            # ``addfont`` call is stubbed so values don't need to exist.
            return [f"/fake/font_{i}.ttf" for i in range(_EXPECTED_MIN_FONTS)]

        monkeypatch.setattr(
            font_module.font_manager, "findSystemFonts", fake_find
        )
        monkeypatch.setattr(
            font_module.font_manager.fontManager, "addfont", lambda _path: None
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _add_fonts()

        bundle_warnings = [
            w
            for w in caught
            if issubclass(w.category, UserWarning)
            and "dartwork-mpl" in str(w.message)
        ]
        assert bundle_warnings == []
