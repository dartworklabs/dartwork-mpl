"""v5 cmap registration (matplotlib-native access)."""

from __future__ import annotations

import matplotlib as mpl
import pytest

import dartwork_mpl  # noqa: F401 — registers dc.* cmaps on import
from dartwork_mpl.colors import _generated


def test_registry_names():
    for name in ("aurora", "blue", "blue_red", "halo"):
        assert f"dc.{name}" in mpl.colormaps
        assert f"dc.{name}_r" in mpl.colormaps
    assert "dc.octave" in mpl.colormaps and "dc.octave_print" in mpl.colormaps
    assert "dc.cycle" not in mpl.colormaps
    assert "dc.cycle_print" not in mpl.colormaps
    for name in ("coast", "blue_red_deep", "blue_red_soft"):
        assert f"dc.{name}" not in mpl.colormaps
        assert f"dc.{name}_r" not in mpl.colormaps


def test_registry_access_matplotlib_native():
    cm = mpl.colormaps["dc.aurora"]
    assert cm.N == 256
    assert [mpl.colors.to_hex(c) for c in cm.colors] == list(
        _generated.CMAPS_256["aurora"]
    )
    assert (
        mpl.colors.to_hex(mpl.colormaps["dc.aurora_r"].colors[0])
        == _generated.CMAPS_256["aurora"][-1]
    )
    with pytest.raises(KeyError):
        mpl.colormaps["dc.no_such_map"]


def test_v5_coral_colormap_comes_from_generated_catalog():
    """Promoted v5 families own their ``dc.<family>`` colormap names."""
    cm = mpl.colormaps["dc.coral"]
    assert [mpl.colors.to_hex(c) for c in cm.colors] == list(
        _generated.CMAPS_256["coral"]
    )


def test_v5_cycle_cmap_tokens_stay_stable():
    """Cycle colormap tokens use the canonical octave names."""
    assert "dc.octave" in mpl.colormaps
    assert "dc.octave_print" in mpl.colormaps
    assert [
        mpl.colors.to_hex(c) for c in mpl.colormaps["dc.octave"].colors
    ] == list(_generated.CYCLES["octave"])
    assert [
        mpl.colors.to_hex(c) for c in mpl.colormaps["dc.octave_print"].colors
    ] == list(_generated.CYCLES["octave_print"])


def test_deleted_legacy_cmaps_are_absent():
    assert "dc.legacy_aurora" not in mpl.colormaps
    assert "dc.legacy_aurora_r" not in mpl.colormaps
    assert "dc.legacy_teal_rose" not in mpl.colormaps
    assert "dc.legacy_teal_rose_r" not in mpl.colormaps


def test_cmap_module_removed():
    import importlib

    import dartwork_mpl as dm

    assert not hasattr(dm, "cmap")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("dartwork_mpl" + ".cmap")
