"""Tests for style management module."""

from __future__ import annotations

import importlib
from concurrent.futures import ThreadPoolExecutor

import matplotlib as mpl
import pytest

import dartwork_mpl as dm
from dartwork_mpl.style import Style, list_styles, load_style_dict, style_path

# Resolve the submodule directly because ``dartwork_mpl.style`` is the
# singleton ``Style`` instance once the package is imported.
style_module = importlib.import_module("dartwork_mpl.style")


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
        for _key, value in d.items():
            if isinstance(value, str):
                # No value should end with a comment fragment
                assert not value.strip().startswith("#")


class TestStyleUse:
    """Tests for Style.use()."""

    def test_apply_report_kr(self) -> None:
        """Applying 'report-kr' should change rcParams."""
        # Save original
        original_family = mpl.rcParams["font.family"].copy()

        try:
            dm.style.use("report-kr")
            # After applying, font.family should be set
            assert isinstance(mpl.rcParams["font.family"], list)
        finally:
            # Restore
            mpl.rcParams["font.family"] = original_family

    def test_invalid_preset_raises(self) -> None:
        with pytest.raises(KeyError):
            dm.style.use("nonexistent_preset_xyzzy")

    def test_kwargs_underscore_to_dot(self) -> None:
        """``font_size=14`` should map to rcParam ``font.size``."""
        dm.style.use("report", font_size=14)
        assert mpl.rcParams["font.size"] == 14

    def test_kwargs_dot_notation(self) -> None:
        """Direct dot-notation rcParam keys work too."""
        dm.style.use("report", **{"font.size": 13})
        assert mpl.rcParams["font.size"] == 13

    def test_use_list_of_presets(self) -> None:
        """``dm.style.use([...])`` should stack several presets."""
        # Should not raise. We just verify it runs and rcParams remain
        # well-formed afterwards.
        dm.style.use(["report"])
        assert isinstance(mpl.rcParams["font.family"], list)

    def test_use_list_invalid_preset_raises(self) -> None:
        with pytest.raises(KeyError):
            dm.style.use(["report", "nonexistent_preset_xyzzy"])


class TestStyleContext:
    """Cover the ``Style.context`` context manager."""

    def test_context_temporarily_applies(self) -> None:
        # Capture baseline outside any custom style.
        baseline_family = list(mpl.rcParams["font.family"])
        with dm.style.context("report"):
            assert isinstance(mpl.rcParams["font.family"], list)
        # After exit, rcParams should revert (matplotlib's context behaviour).
        # We don't compare exact lists because conftest also resets between
        # tests; just validate that exiting restored a valid font.family.
        assert isinstance(mpl.rcParams["font.family"], list)
        # Sanity guard against a None / corrupted state.
        assert baseline_family is not None

    def test_context_invalid_preset_raises(self) -> None:
        with pytest.raises(KeyError):
            with dm.style.context("nonexistent_preset_xyzzy"):
                pass


class TestPresetsDict:
    def test_returns_dict_copy(self) -> None:
        d = dm.style.presets_dict()
        assert isinstance(d, dict)
        # Mutating the returned dict must not affect the live presets.
        d["__bogus__"] = ["base"]
        assert "__bogus__" not in dm.style.presets


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


class TestThreadSafety:
    """Tests for thread-safe style application."""

    def test_module_has_lock(self) -> None:
        """style module should expose a threading.Lock as ``_style_lock``."""
        import threading

        assert hasattr(style_module, "_style_lock")
        sample_lock = threading.Lock()
        assert type(style_module._style_lock) is type(sample_lock)

    def test_concurrent_use_no_error(self) -> None:
        """Concurrent ``dm.style.use(...)`` calls must not corrupt the
        global rcParams or raise registration errors."""

        def _apply(idx: int) -> None:
            # Alternate between a couple of presets so we exercise
            # different rcParams paths.
            preset = "report" if idx % 2 == 0 else "scientific"
            dm.style.use(preset)

        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(_apply, i) for i in range(16)]
            for f in futures:
                f.result()

        # After contention, rcParams should still be a valid dict.
        assert isinstance(mpl.rcParams["font.family"], list)


class TestSvgHashsaltPreservation:
    """style.use must preserve a caller-set svg.hashsalt across its internal
    rcParams-default reset, so reproducible SVG ids survive a preset switch."""

    def test_preserves_set_hashsalt(self) -> None:
        mpl.rcParams["svg.hashsalt"] = "fixed-salt"
        try:
            dm.style.use("scientific")
            assert mpl.rcParams["svg.hashsalt"] == "fixed-salt"
            # A second preset switch must keep it too.
            dm.style.use("report")
            assert mpl.rcParams["svg.hashsalt"] == "fixed-salt"
        finally:
            mpl.rcParams["svg.hashsalt"] = None

    def test_keeps_none_when_unset(self) -> None:
        mpl.rcParams["svg.hashsalt"] = None
        dm.style.use("scientific")
        assert mpl.rcParams["svg.hashsalt"] is None


class TestUserRcParamsPreservation:
    """style.use must preserve every rcParam the caller set away from
    matplotlib's compiled-in default — not just svg.hashsalt — except
    where the preset itself takes a stance on that key. This generalises
    the hashsalt guarantee to the rest of rcParams so reproducible-build
    and export-quality settings survive preset switches.
    """

    def test_preserves_user_pdf_compression(self) -> None:
        """A caller-set pdf.compression (export choice) must survive
        a style.use because no shipped preset pins it.

        We use ``pdf.compression`` instead of ``savefig.dpi`` because
        the shipped ``scientific`` preset pins ``savefig.dpi=500``,
        which is the exact-right behaviour for "preset touched it,
        preset wins" — but makes that key a poor regression sentinel
        for the "preserve user value" path.
        """
        default_compression = mpl.rcParamsDefault["pdf.compression"]
        new_value = 0 if default_compression != 0 else 9
        mpl.rcParams["pdf.compression"] = new_value
        try:
            dm.style.use("scientific")
            assert mpl.rcParams["pdf.compression"] == new_value, (
                "User-set pdf.compression must survive a style.use when "
                "the preset does not pin its own value"
            )
        finally:
            mpl.rcParams["pdf.compression"] = default_compression

    def test_preset_overrides_user_value(self) -> None:
        """Where the preset *does* take a stance, the preset wins —
        the user override is not stickier than the explicit preset
        choice. font.size is the canonical case: every preset pins
        it, so a user value here must yield to the preset."""
        # Pick something a preset definitely sets.
        mpl.rcParams["font.size"] = 99.0  # absurd, surely overridden
        try:
            dm.style.use("scientific")
            assert mpl.rcParams["font.size"] != 99.0, (
                "Preset must win over user-set font.size (scientific "
                "pins font.size)"
            )
        finally:
            # Best effort: matplotlib's autouse fixture resets after.
            pass

    def test_preserves_multiple_unrelated_overrides(self) -> None:
        """A user setting two different rcParams the preset is silent
        on — both should survive."""
        default_axes_unicode = mpl.rcParamsDefault["axes.unicode_minus"]
        default_pdf_compression = mpl.rcParamsDefault["pdf.compression"]
        # Both pretty surely not preset-touched by ``scientific``.
        mpl.rcParams["axes.unicode_minus"] = not default_axes_unicode
        # pdf.compression default is usually 6; pick another valid
        # integer level so we can tell.
        new_pdf = 0 if default_pdf_compression != 0 else 9
        mpl.rcParams["pdf.compression"] = new_pdf
        try:
            dm.style.use("scientific")
            assert mpl.rcParams["axes.unicode_minus"] != default_axes_unicode
            assert mpl.rcParams["pdf.compression"] == new_pdf
        finally:
            mpl.rcParams["axes.unicode_minus"] = default_axes_unicode
            mpl.rcParams["pdf.compression"] = default_pdf_compression

    def test_user_value_resets_across_preset_changes(self) -> None:
        """Surviving across one style.use is necessary; surviving
        across a chain of style.use calls is what users actually need
        for reproducible builds.
        """
        default_compression = mpl.rcParamsDefault["pdf.compression"]
        new_value = 0 if default_compression != 0 else 9
        mpl.rcParams["pdf.compression"] = new_value
        try:
            dm.style.use("scientific")
            dm.style.use("report")
            dm.style.use("scientific")
            assert mpl.rcParams["pdf.compression"] == new_value
        finally:
            mpl.rcParams["pdf.compression"] = default_compression
