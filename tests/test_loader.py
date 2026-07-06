"""Tests for color/_loader.py — palette registration."""

from __future__ import annotations

import typing

import matplotlib.colors as mcolors

from dartwork_mpl.colors import _generated
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

    def test_dc_v5_palettes_registered(self) -> None:
        """Dartwork Color v5 palette families (dc.* prefix) are available."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert "dc.blue0" in mapping
        assert "dc.blue9" in mapping
        assert "dc.teal5" in mapping
        assert "dc.0" not in mapping

    def test_dc_palette_count(self) -> None:
        """20 v5 families x10 + 20 curated categorical sets + 4 semantic tokens.

        Derived from the SSOT so adding/removing a palette can't silently
        drift the count out of sync.
        """
        from dartwork_mpl.colors import _curated, _generated

        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        dc_keys = [k for k in mapping if k.startswith("dc.")]
        families = sum(len(row) for row in _generated.PALETTE.values())
        curated = sum(len(row) for row in _curated.CURATED.values())
        semantic = 4  # dc.pos / dc.neg / dc.ref / dc.hl
        assert len(dc_keys) == families + curated + semantic

    def test_legacy_aliases_removed(self) -> None:
        """Genuinely-legacy ad-hoc palette names stay gone.

        The v5 clean break trims tw/oc-tier throwaway names; the curated
        ``dc.*`` categorical sets (vivid / trustworthy / cool_warm / ...) are
        deliberately preserved and are covered by
        ``TestCuratedPalettes`` instead.
        """
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        for name in ("dc.sunset2", "dc.ocean2", "dc.nordic0", "dc.cyber3"):
            assert name not in mapping

    def test_dc_color_values_are_hex(self) -> None:
        """dc.* colours are valid hex strings."""
        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        assert mapping["dc.blue6"].startswith("#")
        assert mapping["dc.orange2"].startswith("#")


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


class TestPaletteCleanBreak:
    """Removed pre-v5 palette tokens must stay gone; v5 families resolve."""

    def test_removed_tokens_do_not_resolve(self) -> None:
        import matplotlib.colors as mcolors

        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        # NOTE: the curated categorical sets (vivid / trustworthy / cool_warm
        # / ...) are NOT in this list — they were revived as first-class dc.*
        # palettes and are covered by ``TestCuratedPalettes``. Only genuinely
        # dead ad-hoc / renamed aliases must stay gone.
        for token in (
            "dc.spectrum1",
            "dc.bold1",
            "dc.coolwarm1",  # note: the curated diverging set is ``cool_warm``
            "dc.corporate1",
            "dc.warm_cool1",
        ):
            assert token not in mapping, f"{token} should be removed"

    def test_v5_family_tokens_resolve(self) -> None:
        import matplotlib.colors as mcolors

        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        for family in _generated.PALETTE:
            for step in range(10):
                token = f"dc.{family}{step}"
                assert token in mapping, f"{token} missing"


class TestCuratedPalettes:
    """The curated categorical dc.* sets are revived and integrated with v5."""

    def test_curated_tokens_resolve(self) -> None:
        """Every curated palette step registers as a ``dc.<name><step>``."""
        import matplotlib.colors as mcolors

        from dartwork_mpl.colors._curated import CURATED

        ensure_loaded()
        mapping = mcolors.get_named_colors_mapping()
        for name, row in CURATED.items():
            for step, hexval in enumerate(row):
                token = f"dc.{name}{step}"
                assert token in mapping, f"{token} missing"
                assert mapping[token].lower() == hexval.lower()

    def test_curated_never_shadows_a_v5_family(self) -> None:
        """Curated names must not collide with the generated v5 families."""
        from dartwork_mpl.colors._curated import CURATED
        from dartwork_mpl.colors._generated import PALETTE

        assert set(CURATED) & set(PALETTE) == set()

    def test_get_palette_resolves_curated_sets(self) -> None:
        """``get_palette`` / ``set_cycle`` accept curated names like families."""
        import matplotlib as mpl

        import dartwork_mpl as dm

        assert dm.get_palette("trustworthy", n=6) == [
            f"dc.trustworthy{i}" for i in range(6)
        ]
        dm.set_cycle("vivid")
        cyc = [c["color"] for c in mpl.rcParams["axes.prop_cycle"]]
        assert cyc == [f"dc.vivid{i}" for i in range(8)]

    def test_collision_name_resolves_to_v5_family(self) -> None:
        """A name shared with a v5 family (teal) resolves to the 10-step family,
        not an 8-step curated ramp."""
        import dartwork_mpl as dm

        assert len(dm.get_palette("teal")) == 10


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
