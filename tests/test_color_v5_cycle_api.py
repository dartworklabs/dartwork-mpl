from __future__ import annotations

import pytest

import dartwork_mpl as dm
from dartwork_mpl.colors import _generated
from dartwork_mpl.colors._cycle_api import cycle_cycler


def test_cycle_hexes():
    assert dm.cycle() == list(_generated.CYCLES["default"])
    assert dm.cycle("print") == list(_generated.CYCLES["print"])
    with pytest.raises(KeyError):
        dm.cycle("nope")


def test_cycler_product_color_first():
    cyc = list(cycle_cycler())
    n = len(_generated.CYCLES["default"])  # 7
    assert len(cyc) == n * 3
    # 처음 7개: solid + 7색 순환
    assert all(c["linestyle"] == "-" for c in cyc[:n])
    assert [c["color"] for c in cyc[:n]] == list(_generated.CYCLES["default"])
    # 8번째(색 재사용 시작)부터 dashed
    assert cyc[n]["linestyle"] == "--" and cyc[n]["color"] == cyc[0]["color"]
