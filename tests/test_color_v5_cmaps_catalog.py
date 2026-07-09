"""Golden tests — full 43-map catalog must reproduce SSOT swatches_32."""

from __future__ import annotations

from dartwork_mpl.colors._cmaps import compile_cmaps


def test_full_catalog_matches_ssot(v5_ssot):
    cm = compile_cmaps(v5_ssot["palette"], n=32)
    expected = v5_ssot["colormaps"]["swatches_32"]
    assert set(cm) == set(expected)
    for name in expected:
        assert cm[name] == expected[name], name


def test_counts(v5_ssot):
    counts = v5_ssot["colormaps"]["counts"]
    assert counts["total"] == 43
    assert counts == {
        "single": 20,
        "multi": 9,
        "diverging": 11,
        "cyclic": 3,
        "total": 43,
        "qualitative_registered": 2,
    }


def test_l1_deleted_colormaps_absent(v5_ssot):
    cm = compile_cmaps(v5_ssot["palette"], n=32)
    for name in ("coast", "blue_red_deep", "blue_red_soft"):
        assert name not in cm
        assert name not in v5_ssot["colormaps"]["swatches_32"]
        assert name not in v5_ssot["colormaps"]["gates"]
