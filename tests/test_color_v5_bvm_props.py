"""T4 - the BVM tritan half-plane matrices are idempotent projections (M2=M).

``_metrics.py`` documents each Brettel-Vienot-Mollon tritan matrix as an
idempotent projection whose two halves agree on the separation plane, but
nothing enforced it. A silent coefficient typo would move every tritan dE
without any test failing. This locks two BVM invariants directly on the
importable matrix constants:

1. ``max|M@M - M|`` is ~0 for each half-plane matrix (idempotent projection).
2. the HI and LO matrices agree on the separation plane (SEP . v == 0), as
   BVM's two-half-plane construction requires.

Note: the *applied* transform ``cvd_rgb(c, "tritan")`` is deliberately NOT
idempotent end-to-end, because out-of-gamut projections are clamped into
[0, 1] before the gamma round-trip; that clamp is a real, intended step, so
the invariants are asserted on the linear matrices, not on the clamped output.
"""

from __future__ import annotations

from dartwork_mpl.colors._metrics import (
    _BVM_TRITAN_HI,
    _BVM_TRITAN_LO,
    _BVM_TRITAN_SEP,
)

Mat = tuple[tuple[float, float, float], ...]
Vec = tuple[float, float, float]


def _matmul(a: Mat, b: Mat) -> list[list[float]]:
    return [
        [sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]


def _max_abs_diff(a: list[list[float]], b: Mat) -> float:
    return max(abs(a[i][j] - b[i][j]) for i in range(3) for j in range(3))


def _apply(m: Mat, v: Vec) -> list[float]:
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def test_bvm_tritan_matrices_are_idempotent() -> None:
    """M @ M == M (to 1e-4) for each half-plane projection matrix."""
    for name, m in (("HI", _BVM_TRITAN_HI), ("LO", _BVM_TRITAN_LO)):
        d = _max_abs_diff(_matmul(m, m), m)
        assert d < 1e-4, f"BVM tritan {name}: max|M@M - M| {d:.2e} >= 1e-4"


def test_bvm_halves_agree_on_separation_plane() -> None:
    """HI and LO map identically for any linear-RGB v with SEP . v == 0.

    That agreement is what makes the sign-of-dot-product branch in
    ``cvd_rgb`` continuous across the separation plane. Sweep several such v.
    """
    s = _BVM_TRITAN_SEP
    worst = 0.0
    for a in (0.2, 0.5, 0.8, 1.0):
        for b in (0.2, 0.5, 0.8, 1.0):
            # z chosen so s . (a, b, z) == 0 (s[2] != 0)
            z = -(s[0] * a + s[1] * b) / s[2]
            v: Vec = (a, b, z)
            assert abs(sum(si * vi for si, vi in zip(s, v, strict=True))) < 1e-9
            hi, lo = _apply(_BVM_TRITAN_HI, v), _apply(_BVM_TRITAN_LO, v)
            worst = max(
                worst, max(abs(x - y) for x, y in zip(hi, lo, strict=True))
            )
    assert worst < 1e-3, f"HI/LO disagree on separation plane: {worst:.2e}"
