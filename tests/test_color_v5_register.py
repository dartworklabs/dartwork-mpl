"""v5 cmap registration (matplotlib-native access) + legacy renames."""

from __future__ import annotations

import matplotlib as mpl
import pytest

import dartwork_mpl  # noqa: F401 — registers dc.* cmaps on import
from dartwork_mpl.cmap import ensure_loaded as _ensure_legacy_cmaps_loaded
from dartwork_mpl.colors import _generated


@pytest.fixture(scope="module", autouse=True)
def _load_legacy_cmaps() -> None:
    """The legacy ``asset/cmap/*.txt`` loader is lazy (only triggered by
    ``dm.style.use(...)`` / ``dm.list_colormaps()`` / an explicit call —
    unlike the v5 catalog, which registers eagerly at package import
    time). ``test_legacy_renames`` below asserts on ``dc.legacy_aurora``
    / ``dc.legacy_teal_rose``, so this module must trigger the legacy
    loader itself rather than depend on another test module (e.g.
    ``test_cmap.py``) having already done so first.
    """
    _ensure_legacy_cmaps_loaded()


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


def test_legacy_renames():
    assert "dc.legacy_aurora" in mpl.colormaps
    assert "dc.legacy_teal_rose" in mpl.colormaps
    # v5 aurora 가 이름을 가져감 — 레거시 hex 와 달라야 함
    assert list(mpl.colormaps["dc.aurora"].colors) != list(
        mpl.colormaps["dc.legacy_aurora"].colors
    )


def test_cmap_module_untouched():
    import dartwork_mpl.cmap as cmap_module

    assert hasattr(cmap_module, "ensure_loaded")
    from dartwork_mpl import cmap as pkg_attr

    assert pkg_attr is cmap_module
