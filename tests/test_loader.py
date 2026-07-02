"""Tests for color/_loader.py — palette registration."""

from __future__ import annotations

import typing

import matplotlib.colors as mcolors

from dartwork_mpl.colors._loader import _load_json_palette, ensure_loaded


class TestEnsureLoaded:
    """ensure_loaded registers all palette prefixes."""

    def test_idempotent(self) -> None:
        """Calling ensure_loaded twice does not raise."""
        ensure_loaded()
        ensure_loaded()

    def test_open_color_registered(self) -> None:
        """Open Color palette (oc.* prefix) is available."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert "oc.blue5" in mapping
        assert "oc.red5" in mapping

    def test_tailwind_registered(self) -> None:
        """Tailwind palette (tw.* prefix) is available."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert "tw.blue500" in mapping
        assert "tw.gray100" in mapping

    def test_material_registered(self) -> None:
        """Material Design palette (md.* prefix) is available."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert "md.blue500" in mapping

    def test_ant_design_registered(self) -> None:
        """Ant Design palette (ad.* prefix) is available."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert "ad.blue5" in mapping

    def test_chakra_registered(self) -> None:
        """Chakra UI palette (cu.* prefix) is available."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert "cu.blue500" in mapping

    def test_primer_registered(self) -> None:
        """Primer palette (pr.* prefix) is available."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert "pr.blue5" in mapping

    def test_xkcd_preserved(self) -> None:
        """matplotlib's built-in xkcd colours are NOT stripped.

        Deleting them from the process-global mapping to declutter our
        galleries broke unrelated code using ``color="xkcd:..."`` — the
        galleries filter ``xkcd:`` at display time instead.
        """
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert "xkcd:sky blue" in mapping

    def test_color_values_are_hex(self) -> None:
        """Registered colours are valid hex strings."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert mapping["oc.blue5"].startswith("#")
        assert mapping["tw.blue500"].startswith("#")

    def test_dc_palettes_registered(self) -> None:
        """Dartwork Color palettes (dc.* prefix) are available."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert "dc.trustworthy0" in mapping
        assert "dc.trustworthy7" in mapping
        # The unnamed default palette (the shared prop_cycle).
        assert "dc.0" in mapping
        assert "dc.5" in mapping

    def test_dc_palette_count(self) -> None:
        """24 curated × 8 + 8 default = 200 (legacy palettes removed in 0.5)."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        dc_keys = [k for k in mapping if k.startswith("dc.")]
        assert len(dc_keys) == 200

    def test_legacy_aliases_removed(self) -> None:
        """The old ad-hoc palette names were removed in 0.5 — they must not
        resolve (docs/examples/templates migrated to curated palettes)."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        for name in ("dc.sunset2", "dc.ocean2", "dc.nordic0", "dc.cyber3"):
            assert name not in mapping

    def test_dc_color_values_are_hex(self) -> None:
        """dc.* colours are valid hex strings."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert mapping["dc.trustworthy0"].startswith("#")
        assert mapping["dc.cool_warm2"].startswith("#")


class TestLoadJsonPalette:
    """_load_json_palette helper unit tests."""

    def test_returns_prefixed_dict(self, tmp_path) -> None:
        """Helper returns {prefix.name+weight: #hex} entries."""
        import json

        data = {"Blue": [[100, "aabbcc"], [200, "ddeeff"]]}
        json_file = tmp_path / "test_colors.json"
        json_file.write_text(json.dumps(data))

        result = _load_json_palette(tmp_path, "test_colors.json", "xx")
        assert result == {"xx.blue100": "#aabbcc", "xx.blue200": "#ddeeff"}

    def test_strips_spaces_from_names(self, tmp_path) -> None:
        """Spaces in colour names are removed."""
        import json

        data = {"Deep Purple": [[500, "112233"]]}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data))

        result = _load_json_palette(tmp_path, "test.json", "t")
        assert "t.deeppurple500" in result


class TestPaletteRenameLifecycle:
    """0.5.5 palette overhaul: removed/renamed dc tokens must be gone
    and their replacements present (regression guard for the rename
    map — spectrum/bold→vivid, coolwarm→cool_warm, corporate→
    trustworthy, warm_cool removed)."""

    def test_removed_tokens_do_not_resolve(self) -> None:
        import matplotlib.colors as mcolors

        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        for token in (
            "dc.spectrum1",
            "dc.bold1",
            "dc.coolwarm1",
            "dc.corporate1",
            "dc.warm_cool1",
        ):
            assert token not in mapping, f"{token} should be removed"

    def test_replacement_tokens_resolve(self) -> None:
        import matplotlib.colors as mcolors

        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        for token in (
            "dc.vivid1",
            "dc.cool_warm1",
            "dc.trustworthy1",
            "dc.neon1",
            "dc.ember1",
            "dc.purple_green1",
        ):
            assert token in mapping, f"{token} missing"


class TestVendoredLibraryCounts:
    """Per-prefix count pins for the vendored color libraries — the
    ``test_dc_palette_count`` pattern extended to every library, so a
    dropped family/shade in an upstream JSON can't pass silently (a
    malformed shape crashes loudly, but a shrunken one previously
    didn't)."""

    EXPECTED: typing.ClassVar[dict[str, int]] = {
        "oc.": 140,
        "tw.": 242,
        "md.": 190,
        "ad.": 130,
        "cu.": 100,
        "pr.": 90,
    }

    def test_per_prefix_counts(self) -> None:
        import matplotlib.colors as mcolors

        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        for prefix, expected in self.EXPECTED.items():
            actual = sum(1 for k in mapping if k.startswith(prefix))
            assert actual == expected, (
                f"{prefix} count {actual} != pinned {expected}; if this "
                f"change is deliberate, update the pin in the same PR"
            )
