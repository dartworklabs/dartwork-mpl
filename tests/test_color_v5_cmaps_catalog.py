"""Golden tests — full 42-map catalog must reproduce SSOT swatches_32."""

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
    assert counts["total"] == 42
    assert counts == {
        "single": 16,
        "multi": 9,
        "diverging": 13,
        "topo": 1,
        "cyclic": 3,
        "total": 42,
        "qualitative_registered": 2,
    }
