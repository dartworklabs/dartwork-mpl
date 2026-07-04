# tests/test_color_v5_presets.py
from __future__ import annotations

import matplotlib as mpl
import matplotlib.colors as mcolors

import dartwork_mpl as dm
from dartwork_mpl.colors import _generated


def _cycle_entries():
    return list(mpl.rcParams["axes.prop_cycle"])


def test_base_cycle_is_v5_with_linestyle_extension():
    dm.style.use("scientific")
    entries = _cycle_entries()
    assert len(entries) == 21  # 7색 x 3 linestyle
    first7 = [mcolors.to_hex(mcolors.to_rgb(e["color"])) for e in entries[:7]]
    assert first7 == list(_generated.CYCLES["default"])
    assert entries[0]["linestyle"] == "-" and entries[7]["linestyle"] == "--"


def test_default_image_cmap_is_aurora():
    dm.style.use("scientific")
    assert mpl.rcParams["image.cmap"] == "dc.aurora"


def test_presets_inherit_base_cycle():
    for preset in ("report-kr", "presentation", "web", "minimal"):
        dm.style.use(preset)
        first = _cycle_entries()[0]["color"]
        assert (
            mcolors.to_hex(mcolors.to_rgb(first))
            == _generated.CYCLES["default"][0]
        )


def test_dark_keeps_legacy_cycle():
    dm.style.use("dark")
    first = _cycle_entries()[0]["color"]
    assert (
        mcolors.to_hex(mcolors.to_rgb(first)) != _generated.CYCLES["default"][0]
    )
