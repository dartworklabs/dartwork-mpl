"""v5 cmap registration (matplotlib-native access)."""

from __future__ import annotations

import matplotlib as mpl
import pytest

import dartwork_mpl  # noqa: F401 — registers dc.* cmaps on import
from dartwork_mpl.cmap import ensure_loaded as _ensure_asset_cmaps_loaded
from dartwork_mpl.colors import _generated


@pytest.fixture(scope="module", autouse=True)
def _load_asset_cmaps() -> None:
    """The ``asset/cmap/*.txt`` loader is lazy; load it for absence checks."""
    _ensure_asset_cmaps_loaded()


def test_registry_names():
    for name in ("aurora", "blue", "blue_red", "coast", "halo"):
        assert f"dc.{name}" in mpl.colormaps
        assert f"dc.{name}_r" in mpl.colormaps
    assert "dc.cycle" in mpl.colormaps and "dc.cycle_print" in mpl.colormaps


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


def test_v5_coral_colormap_wins_legacy_asset_collision():
    """Promoted v5 families own their ``dc.<family>`` colormap names.

    The legacy ``asset/cmap/coral.txt`` bundle is lazy-loaded through
    ``dartwork_mpl.cmap``; once coral is a generated v5 family, that loader
    must not overwrite or crash on the already-registered v5 ``dc.coral``.
    """
    cm = mpl.colormaps["dc.coral"]
    assert [mpl.colors.to_hex(c) for c in cm.colors] == list(
        _generated.CMAPS_256["coral"]
    )


def test_deleted_legacy_cmaps_are_absent():
    assert "dc.legacy_aurora" not in mpl.colormaps
    assert "dc.legacy_aurora_r" not in mpl.colormaps
    assert "dc.legacy_teal_rose" not in mpl.colormaps
    assert "dc.legacy_teal_rose_r" not in mpl.colormaps


def test_cmap_module_untouched():
    import dartwork_mpl.cmap as cmap_module

    assert hasattr(cmap_module, "ensure_loaded")
    from dartwork_mpl import cmap as pkg_attr

    assert pkg_attr is cmap_module
