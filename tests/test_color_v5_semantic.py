# tests/test_color_v5_semantic.py
from __future__ import annotations

import matplotlib.colors as mcolors

import dartwork_mpl as dm
from dartwork_mpl._colors import _generated


def _named():
    return mcolors.get_named_colors_mapping()


def test_kr_semantics():
    dm.style.use("report-kr")
    assert _named()["dc.pos"] == _generated.PALETTE["red"][5]
    assert _named()["dc.neg"] == _generated.PALETTE["blue"][6]


def test_default_semantics():
    dm.style.use("scientific")
    assert _named()["dc.pos"] == _generated.PALETTE["green"][6]
    assert _named()["dc.neg"] == _generated.PALETTE["red"][6]
    assert _named()["dc.ref"] == _generated.PALETTE["gray"][6]
    assert _named()["dc.hl"] == _generated.PALETTE["violet"][6]


def test_stack_applies_kr_semantics():
    dm.style.stack(["base", "font-report", "lang-kr"])
    assert _named()["dc.pos"] == _generated.PALETTE["red"][5]
    dm.style.use("scientific")  # restore default for suite hygiene


def test_context_applies_and_restores_kr_semantics():
    dm.style.use("scientific")  # default baseline
    before = _named()["dc.pos"]
    assert before == _generated.PALETTE["green"][6]
    with dm.style.context("report-kr"):
        assert _named()["dc.pos"] == _generated.PALETTE["red"][5]
    assert _named()["dc.pos"] == before  # restored
