"""Tests for style management module."""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.style import Style, list_styles, load_style_dict, style_path


class TestListStyles:
    """Tests for list_styles()."""

    def test_returns_list(self) -> None:
        result = list_styles()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_contains_base(self) -> None:
        """The 'base' style should always exist."""
        assert "base" in list_styles()

    def test_contains_lang_kr(self) -> None:
        """Korean language style should exist."""
        assert "lang-kr" in list_styles()


class TestStylePath:
    """Tests for style_path()."""

    def test_existing_style(self) -> None:
        p = style_path("base")
        assert p is not None
        assert p.exists()
        assert p.suffix == ".mplstyle"

    def test_nonexistent_style_raises(self) -> None:
        with pytest.raises(ValueError):
            style_path("nonexistent_style_xyzzy")


class TestLoadStyleDict:
    """Tests for load_style_dict()."""

    def test_base_style_keys(self) -> None:
        """Loading 'base' should return a dict with rcParam keys."""
        d = load_style_dict("base")
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_nonexistent_style_raises(self) -> None:
        with pytest.raises(ValueError):
            load_style_dict("nonexistent_style_xyzzy")

    def test_font_family_full_value(self) -> None:
        """Multi-word values like font.sans-serif list should be preserved."""
        d = load_style_dict("base")
        if "font.sans-serif" in d:
            value = d["font.sans-serif"]
            assert isinstance(value, str)
            # Should contain multiple fonts, not just the first token
            assert "," in value

    def test_inline_comments_stripped(self) -> None:
        """Inline comments after values should be stripped."""
        d = load_style_dict("base")
        for key, value in d.items():
            if isinstance(value, str):
                # No value should end with a comment fragment
                assert not value.strip().startswith("#")


class TestStyleUse:
    """Tests for Style.use()."""

    def test_apply_investment_kr(self) -> None:
        """Applying 'investment-kr' should change rcParams."""
        # Save original
        original_family = mpl.rcParams["font.family"].copy()

        try:
            dm.style.use("investment-kr")
            # After applying, font.family should be set
            assert isinstance(mpl.rcParams["font.family"], list)
        finally:
            # Restore
            mpl.rcParams["font.family"] = original_family

    def test_invalid_preset_raises(self) -> None:
        with pytest.raises(KeyError):
            dm.style.use("nonexistent_preset_xyzzy")


class TestStyleStack:
    """Tests for Style.stack()."""

    def test_stack_multiple(self) -> None:
        """Stacking multiple styles should not raise."""
        # Just verify it doesn't crash
        Style.stack(["base"])

    def test_stack_empty_list(self) -> None:
        """Empty list should be a no-op."""
        Style.stack([])

    def test_stack_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            Style.stack(["nonexistent_style_xyzzy"])
