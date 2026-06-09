"""Tests for icon module."""

from __future__ import annotations

from pathlib import Path

import pytest
from matplotlib.font_manager import FontProperties

from dartwork_mpl.icon import icon_font, icon_font_path, list_icon_fonts


class TestListIconFonts:
    """Tests for list_icon_fonts()."""

    def test_returns_list(self) -> None:
        result = list_icon_fonts()
        assert isinstance(result, list)

    def test_contains_mdi(self) -> None:
        assert "mdi" in list_icon_fonts()

    def test_contains_font_awesome(self) -> None:
        fonts = list_icon_fonts()
        assert "fa-solid" in fonts
        assert "fa-regular" in fonts
        assert "fa-brands" in fonts

    def test_sorted(self) -> None:
        result = list_icon_fonts()
        assert result == sorted(result)

    def test_count(self) -> None:
        assert len(list_icon_fonts()) == 4


class TestIconFontPath:
    """Tests for icon_font_path()."""

    def test_mdi_path_exists(self) -> None:
        p = icon_font_path("mdi")
        assert isinstance(p, Path)
        assert p.exists()

    def test_fa_solid_path_exists(self) -> None:
        p = icon_font_path("fa-solid")
        assert p.exists()

    def test_unknown_name_raises(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            icon_font_path("nonexistent_font")

    def test_unknown_name_lists_available(self) -> None:
        """The error must enumerate available icon fonts so the
        caller doesn't need to guess or grep."""
        with pytest.raises(ValueError, match="Available icon fonts: \\["):
            icon_font_path("nonexistent_font")

    def test_unknown_name_did_you_mean(self) -> None:
        """A near-miss (typo of an existing font) should get a
        ``Did you mean`` hint."""
        with pytest.raises(ValueError, match="Did you mean"):
            icon_font_path("fasolid")  # typo of "fa-solid"

    def test_default_is_mdi(self) -> None:
        p = icon_font_path()
        assert "materialdesignicons" in p.name.lower()


class TestIconFont:
    """Tests for icon_font()."""

    def test_returns_font_properties(self) -> None:
        fp = icon_font("mdi")
        assert isinstance(fp, FontProperties)

    def test_default_is_mdi(self) -> None:
        fp = icon_font()
        assert isinstance(fp, FontProperties)

    def test_fa_solid(self) -> None:
        fp = icon_font("fa-solid")
        assert isinstance(fp, FontProperties)
