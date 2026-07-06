"""Tests for colors._recipe — 107-number SSOT constants."""

from __future__ import annotations

import pytest

from dartwork_mpl.colors._recipe import (
    FAMILIES,
    FAMILY_PARAMS,
    FOURIER,
    GRAY_C_PROFILE,
    derive_family,
    fourier_eval,
    mid_hue,
)


def test_families_complete():
    assert len(FAMILIES) == 19
    assert FAMILIES == (
        "red",
        "rose",
        "coral",
        "tangerine",
        "orange",
        "amber",
        "yellow",
        "lime",
        "green",
        "teal",
        "cyan",
        "sky",
        "blue",
        "cobalt",
        "indigo",
        "violet",
        "purple",
        "fuchsia",
        "pink",
    )
    assert FAMILIES[0] == "red" and FAMILIES[-1] == "pink"
    assert set(FAMILY_PARAMS) == set(FAMILIES)


def test_params_match_ssot(v5_ssot):
    for fam, p in FAMILY_PARAMS.items():
        ref = v5_ssot["params"][fam]
        for field in ("h0", "dh", "gamma", "tp", "cmax", "floor", "cend", "c0"):
            assert getattr(p, field) == pytest.approx(ref[field]), (fam, field)


def test_fourier_match_ssot(v5_ssot):
    for key in ("cmax_k3", "floor_k3", "cend_k2", "c0_k2"):
        assert list(FOURIER[key]) == pytest.approx(v5_ssot["fourier"][key])


def test_derive_within_one_grid_step():
    # 스펙 §7: 곡선 유도값과 표는 그리드 1스텝(cmax 0.005·floor 1·c 0.05)까지
    # 어긋날 수 있고 표가 우선한다. 현행 60값 중 3값이 1스텝 차이.
    mismatch = 0
    for fam in FAMILIES:
        p = FAMILY_PARAMS[fam]
        d = derive_family(p.h0, p.dh, p.gamma, p.tp)
        assert abs(d.cmax - p.cmax) <= 0.005 + 1e-9, fam
        assert abs(d.floor - p.floor) <= 1.0 + 1e-9, fam
        assert abs(d.cend - p.cend) <= 0.05 + 1e-9, fam
        assert abs(d.c0 - p.c0) <= 0.05 + 1e-9, fam
        mismatch += sum(
            getattr(d, f) != getattr(p, f)
            for f in ("cmax", "floor", "cend", "c0")
        )
    assert mismatch <= 3


def test_gray_profile_len():
    assert len(GRAY_C_PROFILE) == 10


def test_fourier_eval_shape():
    # k=3 → 7계수, k=2 → 5계수
    assert fourier_eval((1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 123.0) == 1.0
    assert mid_hue(FAMILY_PARAMS["red"]) == pytest.approx(
        (16.0 + 11.0 * 0.5**1.10) % 360, abs=1e-9
    )
