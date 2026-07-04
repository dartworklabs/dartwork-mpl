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


# The contract families: the primary chains of every preset (English
# head, Korean head, and the mathtext face every preset points at).
# Deleting any of these previously failed ZERO tests while silently
# swapping the typeface of every preset's math / Korean text. Extending
# this tuple is intended friction on deliberate font-set changes; the
# mplstyle staleness meta-test in ``test_mplstyle_fonts.py`` keeps it
# honest against the style files.
CONTRACT_FAMILIES: tuple[str, ...] = (
    "Inter",
    "Pretendard",
    "Roboto",
    "Paperlogy",
    "Noto Sans CJK KR",
    "Noto Sans Math",
    # Symbol fallback faces bundled for scientific/report special-character
    # coverage (arrows, ⚠ ✓ ★, dingbats). They sit in every preset's
    # font.family / font.sans-serif fallback chain. Deletion is caught by
    # this eager-registration contract; the glyph-coverage test catches
    # chain/coverage regressions via uniquely served symbol glyphs.
    "Noto Sans Symbols",
    "Noto Sans Symbols 2",
)


class TestEagerRegistrationContract:
    """``import dartwork_mpl`` must make the bundled families resolvable
    by bare rcParam name immediately — the documented contract behind
    the eager ``font.ensure_loaded()`` call in ``__init__``. Runs in a
    fresh interpreter so an earlier test import can't mask a regression."""

    def test_bundled_families_resolve_after_fresh_import(self) -> None:
        import subprocess
        import sys

        families = ", ".join(repr(f) for f in CONTRACT_FAMILIES)
        # ``findfont(fallback_to_default=False)`` + an asset-dir check:
        # a system-installed copy of a family on a dev machine must not
        # mask a bundle deletion.
        code = (
            "import dartwork_mpl\n"
            "from pathlib import Path\n"
            "from matplotlib import font_manager\n"
            "from matplotlib.font_manager import FontProperties\n"
            "asset = Path(dartwork_mpl.font._FONT_DIR).resolve()\n"
            f"for family in ({families},):\n"
            "    path = font_manager.findfont(\n"
            "        FontProperties(family=family), fallback_to_default=False\n"
            "    )\n"
            "    resolved = Path(path).resolve()\n"
            "    assert resolved.is_relative_to(asset), (\n"
            "        f'{family} resolved outside the bundle: {resolved}'\n"
            "    )\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
