"""Golden tests — single-hue/gray cmaps must reproduce SSOT swatches_32."""

from __future__ import annotations

import pytest

from dartwork_mpl._colors._cmaps import pchip, render, seq_gray, seq_single
from dartwork_mpl._colors._generate import solve_swatch_rgb


def test_pchip_monotone_no_overshoot():
    knots, vals = [0.0, 0.5, 1.0], [0.0, 9.0, 10.0]
    samples = [pchip(knots, vals, i / 100) for i in range(101)]
    assert all(samples[i] <= samples[i + 1] + 1e-9 for i in range(100))
    assert max(samples) <= 10.0 + 1e-9 and min(samples) >= -1e-9
    # 2-knot 폴백 = 선형
    assert pchip([0.0, 1.0], [2.0, 4.0], 0.5) == pytest.approx(3.0)


def test_render_endpoint_and_count():
    out = render(lambda t: solve_swatch_rgb(238, 0.10, 90 - 60 * t), n=32)
    assert len(out) == 32
    assert all(isinstance(h, str) and h.startswith("#") for h in out)


@pytest.mark.parametrize("fam", ["red", "blue", "teal", "yellow", "purple"])
def test_seq_single_matches_ssot(fam, v5_ssot):
    assert seq_single(fam, n=32) == v5_ssot["colormaps"]["swatches_32"][fam]


def test_seq_gray_matches_ssot(v5_ssot):
    assert seq_gray(n=32) == v5_ssot["colormaps"]["swatches_32"]["gray"]
