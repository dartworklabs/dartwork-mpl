"""Golden tests — compile_palette() must reproduce the approved SSOT exactly."""

from __future__ import annotations

import pytest

from dartwork_mpl.colors._generate import (
    compile_family,
    compile_gray,
    compile_palette,
    solve_swatch_rgb,
)
from dartwork_mpl.colors._metrics import lab_l_rgb
from dartwork_mpl.colors._recipe import FAMILY_PARAMS


def test_solve_swatch_hits_l_target():
    for h, c, lt in (
        (238.0, 0.12, 55.0),
        (99.0, 0.15, 80.0),
        (16.0, 0.18, 45.0),
    ):
        rgb = solve_swatch_rgb(h, c, lt)
        assert lab_l_rgb(rgb) == pytest.approx(lt, abs=0.05)


def test_compile_blue_matches_ssot(v5_ssot):
    assert compile_family(FAMILY_PARAMS["blue"]) == v5_ssot["palette"]["blue"]


def test_compile_gray_matches_ssot(v5_ssot):
    assert compile_gray() == v5_ssot["palette"]["gray"]


def test_full_palette_matches_ssot(v5_ssot):
    pal = compile_palette()
    assert set(pal) == set(v5_ssot["palette"])
    for fam, row in pal.items():
        assert row == v5_ssot["palette"][fam], fam
