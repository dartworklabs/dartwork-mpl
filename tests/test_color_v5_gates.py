"""Tests for colors._gates — A7 hard gates."""

from __future__ import annotations

from dartwork_mpl.colors._gates import (
    check_all,
    gate_cycle,
    gate_cyclic_cmap,
    gate_div_cmap,
    gate_ladder,
    gate_seq_cmap,
)


def test_palette_ladders_pass(v5_ssot):
    for fam, row in v5_ssot["palette"].items():
        g = gate_ladder(row)
        assert g["mono"], fam
        assert g["cv"] <= 0.08, (fam, g["cv"])


def test_cycle_gate_pass(v5_ssot):
    pal = v5_ssot["palette"]
    hexes = [pal[f][k] for f, k in v5_ssot["cycle_default"]["spec"]]
    g = gate_cycle(hexes)
    assert g["common_min"] >= 10.0  # normal + protan + deutan
    assert g["tritan"] >= 8.0  # rare S-cone deficiency, realistic floor


def test_gate_detects_violations():
    # 인위 실패: 비단조 사다리
    bad = ["#f0f0f0", "#101010", "#e0e0e0"] + ["#808080"] * 7
    assert not gate_ladder(bad)["mono"]
    # 인위 실패: 붕괴 cycle (tab10류 red-green) — deutan에서 common 게이트 실패
    assert gate_cycle(["#d62728", "#2ca02c", "#1f77b4"])["common_min"] < 10.0


def test_check_all_rejects_sub_floor_cycle_despite_rounding(v5_ssot):
    """A cycle whose TRUE CVD floor is in [9.95, 10.0) must FAIL check_all.

    ``gate_cycle`` rounds its display floors to 1 decimal, so a true minimum of
    9.9626 rounds up to 10.0. ``check_all`` must threshold on the UNROUNDED
    floor (``common_min_raw`` / ``tritan_raw``); otherwise a sub-floor cycle
    slips through the build gate with zero violations. This locks that.
    """
    pal = v5_ssot["palette"]
    shipped = {
        "cycle_default": [
            pal[f][k] for f, k in v5_ssot["cycle_default"]["spec"]
        ],
        "cycle_print": [pal[f][k] for f, k in v5_ssot["cycle_print"]["spec"]],
    }
    # ["#333333", "#515151"]: common-CVD min ≈ 9.9626 → rounds to 10.0.
    probe = ["#333333", "#515151"]
    g = gate_cycle(probe)
    assert g["common_min"] == 10.0  # rounded display hides the sub-floor
    assert 9.95 <= g["common_min_raw"] < 10.0  # raw exposes it

    # Shipped cycles pass; the sub-floor probe is rejected; and adding the
    # probe to the passing set still produces a violation (no silent skip).
    assert check_all({}, shipped, {}) == []
    assert check_all({}, {"probe": probe}, {}) != []
    assert check_all({}, {**shipped, "probe": probe}, {}) != []


def test_cmap_gates_pass_ssot(v5_ssot):
    sw = v5_ssot["colormaps"]["swatches_32"]
    gexp = v5_ssot["colormaps"]["gates"]
    for name, hexes in sw.items():
        exp = gexp[name]
        if "apex_pct" in exp:
            assert gate_div_cmap(hexes)["apex_pct"] == 50.0, name
        elif "seam_ratio" in exp:
            assert gate_cyclic_cmap(hexes)["seam_ratio"] <= 1.5, name
        else:
            g = gate_seq_cmap(hexes)
            assert g["mono"] and g["gray_mono"], name
