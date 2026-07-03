"""Tests for colors._metrics — CIELAB / OKLab dE / CIEDE2000 / CVD."""

from __future__ import annotations

import pytest

from dartwork_mpl.colors._metrics import (
    cvd_rgb,
    de2000_hex,
    de_ok_rgb,
    hex_from_rgb,
    lab_l_hex,
    lab_l_rgb,
    rgb_from_hex,
)


def test_lab_l_endpoints():
    assert lab_l_rgb((1.0, 1.0, 1.0)) == pytest.approx(100.0, abs=0.01)
    assert lab_l_rgb((0.0, 0.0, 0.0)) == pytest.approx(0.0, abs=0.01)
    # 18% gray card ≈ L* 46.6
    assert lab_l_hex("#777777") == pytest.approx(49.9, abs=0.5)


def test_de2000_sharma_pairs():
    # Sharma, Wu & Dalal (2005) 검증 벡터는 Lab 입력 기준이라 sRGB 왕복으로는
    # 재현 불가 — 대신 순서·스케일 불변식으로 검증한다.
    assert de2000_hex("#ff0000", "#ff0000") == 0.0
    d_small = de2000_hex("#ff0000", "#fe0000")
    d_large = de2000_hex("#ff0000", "#0000ff")
    assert 0.0 < d_small < 1.0 < d_large
    # 대칭성
    assert de2000_hex("#123456", "#654321") == pytest.approx(
        de2000_hex("#654321", "#123456"), abs=1e-9
    )


def test_de_ok_scale():
    # OKLab L 0→1 거리 = 100 (x100 스케일 규약)
    assert de_ok_rgb((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)) == pytest.approx(
        100.0, abs=0.5
    )


def test_cvd_gray_preserves_lightness():
    g = cvd_rgb(rgb_from_hex("#e03131"), "gray")
    assert g[0] == pytest.approx(g[1], abs=1e-6) and g[1] == pytest.approx(
        g[2], abs=1e-6
    )
    assert lab_l_rgb(g) == pytest.approx(lab_l_hex("#e03131"), abs=0.2)


def test_cvd_deutan_collapses_red_green():
    red, green = rgb_from_hex("#c22"), rgb_from_hex("#2a2")
    d_normal = de2000_hex("#cc2222", "#22aa22")
    d_deutan = de2000_hex(
        hex_from_rgb(cvd_rgb(red, "deutan")),
        hex_from_rgb(cvd_rgb(green, "deutan")),
    )
    assert d_deutan < d_normal * 0.5
