"""Tests for color/_loader.py — palette registration."""

from __future__ import annotations

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

    def test_xkcd_removed(self) -> None:
        """xkcd colours are stripped from the mapping."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        xkcd_keys = [k for k in mapping if k.startswith("xkcd:")]
        assert len(xkcd_keys) == 0

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
        """24 curated × 8 + 7 deprecated-legacy × 6 + 8 default = 242."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        dc_keys = [k for k in mapping if k.startswith("dc.")]
        assert len(dc_keys) == 242

    def test_legacy_aliases_still_resolve(self) -> None:
        """Old ad-hoc palette names are kept (deprecated) for back-compat."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        for name in ("dc.vivid2", "dc.ocean2", "dc.nordic0", "dc.cyber3"):
            assert name in mapping

    def test_dc_color_values_are_hex(self) -> None:
        """dc.* colours are valid hex strings."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert mapping["dc.trustworthy0"].startswith("#")
        assert mapping["dc.coolwarm2"].startswith("#")


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
