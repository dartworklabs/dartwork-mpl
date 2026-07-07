# tests/test_color_v5_presets.py
from __future__ import annotations

import matplotlib as mpl
import matplotlib.colors as mcolors

import dartwork_mpl as dm
from dartwork_mpl.colors import _generated


def _cycle_entries():
    return list(mpl.rcParams["axes.prop_cycle"])


def test_base_cycle_is_v5_colors_only():
    # Default prop_cycle is the 8 Octave colors, color-only (no linestyle product):
    # a linestyle in the default cycle breaks any ax.plot(lw=0) that inherits a
    # dashed linestyle (dash scaled by lw=0 → ValueError). The linestyle
    # extension for >8 line series is opt-in via dm.cycle_cycler() (tested in
    # test_color_v5_cycle_api.py).
    dm.style.use("scientific")
    entries = _cycle_entries()
    assert len(entries) == 8
    colors = [mcolors.to_hex(mcolors.to_rgb(e["color"])) for e in entries]
    assert colors == list(_generated.CYCLES["octave"])
    assert all("linestyle" not in e for e in entries)


def test_default_image_cmap_is_aurora():
    dm.style.use("scientific")
    assert mpl.rcParams["image.cmap"] == "dc.aurora"


def test_presets_inherit_base_cycle():
    for preset in ("report-kr", "presentation", "web", "minimal"):
        dm.style.use(preset)
        first = _cycle_entries()[0]["color"]
        assert (
            mcolors.to_hex(mcolors.to_rgb(first))
            == _generated.CYCLES["octave"][0]
        )


def test_dark_keeps_legacy_cycle():
    dm.style.use("dark")
    first = _cycle_entries()[0]["color"]
    assert (
        mcolors.to_hex(mcolors.to_rgb(first)) != _generated.CYCLES["octave"][0]
    )
