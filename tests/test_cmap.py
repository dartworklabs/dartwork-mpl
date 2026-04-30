"""Tests for cmap module."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

from dartwork_mpl import cmap as cmap_module
from dartwork_mpl.cmap import _parse_colormap, ensure_loaded

# The 16 curated colormaps (no _r variants).
EXPECTED_DC_NAMES = {
    # Sequential Single-Hue
    "obsidian",
    "sapphire",
    "emerald",
    "ruby",
    "amethyst",
    "topaz",
    "graphite",
    "coral",
    # Sequential Multi-Hue
    "aurora",
    "sunset_glow",
    "plasma_arc",
    "spring_bloom",
    "deep_sea",
    "autumn_leaf",
    "nebula_dust",
    "tropical_fruit",
    # Diverging
    "ice_fire",
    "earth_sky",
    "teal_rose",
    "purple_lime",
    "navy_gold",
    "forest_brick",
    "magenta_cyan",
    "slate_orange",
    "cool_warm",
    "arctic_heat",
    "frost_flame",
    "water_fire",
    "spring_autumn",
    "summer_winter",
    "electric_surge",
    "neon_pulse",
    # Additional Vibrant
    "neon_blue",
    "neon_green",
    "neon_pink",
    "neon_orange",
    "cyberpunk",
    "synthwave",
    "vivid_dusk",
    "toxic_glow",
    "neon_wheel",
    "electric_cycle",
    # Cyclical
    "twilight_oklch",
    "phase_wheel",
    "color_wheel",
    "seasons",
    "day_night",
    "rainbow_cycle",
    # Discrete
    "vivid",
    "lucid",
    "chalk",
    "vibrant",
    "pastel",
    "candy",
    "pop",
    "macaron",
}

EXPECTED_DC_CMAPS = set()
for name in EXPECTED_DC_NAMES:
    EXPECTED_DC_CMAPS.add(f"dc.{name}")
    EXPECTED_DC_CMAPS.add(f"dc.{name}_r")

assert len(EXPECTED_DC_NAMES) == 56
assert len(EXPECTED_DC_CMAPS) == 112


@pytest.fixture(scope="module", autouse=True)
def _load_colormaps() -> None:
    """Ensure colormaps are loaded once for all tests in this module."""
    ensure_loaded()


class TestEnsureLoaded:
    """Tests for ensure_loaded()."""

    def test_does_not_crash(self) -> None:
        # This is covered by the fixture, but good to have a direct test too.
        ensure_loaded()

    def test_idempotent(self) -> None:
        """Calling ensure_loaded() twice should not raise."""
        ensure_loaded()
        ensure_loaded()

    def test_registers_exactly_56_dc_colormaps(self) -> None:
        """After loading, exactly 56 dc.* colormaps (non-reversed) should exist."""
        dc_names = {
            name
            for name in mpl.colormaps
            if name.startswith("dc.") and not name.endswith("_r")
        }
        expected = {f"dc.{name}" for name in EXPECTED_DC_NAMES}
        assert dc_names == expected, (
            f"Missing: {expected - dc_names}, Extra: {dc_names - expected}"
        )

    def test_reversed_variants_exist(self) -> None:
        """Every dc.* cmap should have a dc.*_r reversed variant."""
        for name in EXPECTED_DC_NAMES:
            assert f"dc.{name}_r" in mpl.colormaps, (
                f"Reversed variant dc.{name}_r not found"
            )

    def test_cmap_count_and_names(self) -> None:
        """Verify exactly 112 `dc.*` colormaps exist (56 base + 56 reversed)."""
        # 1. Get all colormaps currently registered in Matplotlib
        all_mpl_cmaps = set(plt.colormaps())

        # 2. Filter for only those starting with 'dc.'
        dc_cmaps_registered = {
            name for name in all_mpl_cmaps if name.startswith("dc.")
        }

        # 3. Assert the count is exactly 112
        assert len(dc_cmaps_registered) == 112, (
            f"Expected exactly 112 'dc.' colormaps, but found {len(dc_cmaps_registered)}."
        )
        assert dc_cmaps_registered == EXPECTED_DC_CMAPS, (
            f"Missing: {EXPECTED_DC_CMAPS - dc_cmaps_registered}, "
            f"Extra: {dc_cmaps_registered - EXPECTED_DC_CMAPS}"
        )

    def test_discrete_cmap_colors(self) -> None:
        """Test that the discrete (categorical) maps have a reasonable number of colors."""
        discrete_names = [
            "vivid",
            "lucid",
            "chalk",
            "vibrant",
            "pastel",
            "candy",
            "pop",
            "macaron",
        ]
        for name in discrete_names:
            cmap = mpl.colormaps[f"dc.{name}"]
            assert isinstance(cmap, mpl.colors.ListedColormap)
            assert len(cmap.colors) >= 5, (
                f"Expected >=5 colors for dc.{name}, got {len(cmap.colors)}"
            )


class TestParseColormap:
    """Tests for _parse_colormap()."""

    def test_parse_existing_file(self) -> None:
        cmap_dir = Path(__file__).parent.parent / (
            "src/dartwork_mpl/asset/cmap"
        )
        txt_files = list(cmap_dir.glob("*.txt"))
        if not txt_files:
            return  # skip if no cmap files

        cmap = _parse_colormap(txt_files[0])
        assert cmap.name.startswith("dc.")
        assert len(cmap.colors) > 0

    def test_parse_reverse(self) -> None:
        cmap_dir = Path(__file__).parent.parent / (
            "src/dartwork_mpl/asset/cmap"
        )
        txt_files = list(cmap_dir.glob("*.txt"))
        if not txt_files:
            return

        cmap = _parse_colormap(txt_files[0], reverse=True)
        assert cmap.name.endswith("_r")

    def test_reverse_has_flipped_colors(self) -> None:
        cmap_dir = Path(__file__).parent.parent / (
            "src/dartwork_mpl/asset/cmap"
        )
        txt_files = list(cmap_dir.glob("*.txt"))
        if not txt_files:
            return

        cmap_fwd = _parse_colormap(txt_files[0], reverse=False)
        cmap_rev = _parse_colormap(txt_files[0], reverse=True)
        assert cmap_fwd.colors[0] == cmap_rev.colors[-1]
        assert cmap_fwd.colors[-1] == cmap_rev.colors[0]

    def test_file_count_is_56(self) -> None:
        """asset/cmap/ should contain exactly 56 .txt files."""
        cmap_dir = Path(__file__).parent.parent / (
            "src/dartwork_mpl/asset/cmap"
        )
        txt_files = list(cmap_dir.glob("*.txt"))
        assert len(txt_files) == 56, (
            f"Expected 56 .txt files, got {len(txt_files)}: "
            f"{sorted(f.name for f in txt_files)}"
        )


class TestThreadSafety:
    """Tests for thread-safe ensure_loaded()."""

    def test_module_has_lock(self) -> None:
        """cmap module should expose a threading.Lock as ``_lock``."""
        import threading

        assert hasattr(cmap_module, "_lock")
        # ``threading.Lock()`` returns an internal class, but it implements
        # the lock protocol — both ``acquire`` and ``release``.
        assert hasattr(cmap_module._lock, "acquire")
        assert hasattr(cmap_module._lock, "release")
        # Sanity: matches the type returned by threading.Lock factory.
        sample_lock = threading.Lock()
        assert type(cmap_module._lock) is type(sample_lock)

    def test_concurrent_ensure_loaded_no_error(self) -> None:
        """Concurrent ensure_loaded() calls must be safe even when many
        threads enter simultaneously. Once loaded, subsequent calls take
        the fast path; this test verifies the fast path is also race-free.
        """
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(ensure_loaded) for _ in range(32)]
            # Re-raises any exception from worker threads.
            for f in futures:
                f.result()

        assert cmap_module._loaded is True

    def test_double_checked_locking_prevents_duplicate_registration(
        self,
    ) -> None:
        """Simulate the unloaded state and verify only one thread runs
        the loader. We monkey-patch ``_load_colormaps`` to count how
        many times it executes when many threads race in.
        """
        original_loaded = cmap_module._loaded
        original_loader = cmap_module._load_colormaps

        call_count = {"n": 0}

        def _counting_loader() -> None:
            call_count["n"] += 1
            # No actual matplotlib mutations — we just verify the lock
            # gates execution to a single call.

        cmap_module._loaded = False
        cmap_module._load_colormaps = _counting_loader  # type: ignore[assignment]
        try:
            with ThreadPoolExecutor(max_workers=16) as ex:
                futures = [ex.submit(ensure_loaded) for _ in range(64)]
                for f in futures:
                    f.result()
            assert call_count["n"] == 1, (
                f"Loader called {call_count['n']} times; "
                "double-checked lock failed"
            )
            assert cmap_module._loaded is True
        finally:
            cmap_module._load_colormaps = original_loader  # type: ignore[assignment]
            cmap_module._loaded = original_loaded
