"""Colormap catalog compiler — 42종 (스펙 §9).

프로토콜(§9 공통): float 경로 등화(hex 최종 1회) · pchip knot 보간 ·
게이트/스와치는 n-stop 직접 렌더.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Callable

from ._generate import gamut_max_chroma, solve_swatch_rgb
from ._metrics import de_ok_rgb, hex_from_rgb
from ._recipe import FAMILY_PARAMS

__all__ = ["pchip", "render", "seq_gray", "seq_single", "unwrap_hues"]

Rgb = tuple[float, float, float]


def render(
    swatch_at: Callable[[float], Rgb],
    n: int = 256,
    dense: int = 513,
    closed: bool = False,
) -> list[str]:
    """dense float 평가 → 누적 OKLab dE 역보간 → 정확한 t*에서 재평가 → hex 1회."""
    ts = [i / (dense - 1) for i in range(dense)]
    pts = [swatch_at(t) for t in ts]
    cum = [0.0]
    for i in range(1, dense):
        cum.append(cum[-1] + de_ok_rgb(pts[i - 1], pts[i]))
    if closed:
        cum.append(cum[-1] + de_ok_rgb(pts[-1], pts[0]))
    total = cum[-1]
    out: list[Rgb] = []
    m = n if not closed else n + 1
    for k in range(m):
        tgt = total * k / (m - 1)
        i = min(max(bisect_left(cum, tgt), 1), dense - 1)
        f = (tgt - cum[i - 1]) / (cum[i] - cum[i - 1] or 1)
        t_star = min(max(ts[i - 1] + f * (ts[i] - ts[i - 1]), 0.0), 1.0)
        out.append(swatch_at(t_star))
    return [hex_from_rgb(p) for p in (out[:n] if closed else out)]


def pchip(knots: list[float], vals: list[float], t: float) -> float:
    """단조 3차 Hermite (Fritsch-Carlson) — knot C1 연속, 오버슈트 없음."""
    n = len(knots)
    if n == 2:
        f = (t - knots[0]) / (knots[1] - knots[0])
        return vals[0] + f * (vals[1] - vals[0])
    h = [knots[i + 1] - knots[i] for i in range(n - 1)]
    d = [(vals[i + 1] - vals[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    t = min(max(t, knots[0]), knots[-1])
    i = min(max(bisect_left(knots, t) - 1, 0), n - 2)
    s = (t - knots[i]) / h[i]
    h00, h10 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s
    h01, h11 = -2 * s**3 + 3 * s**2, s**3 - s**2
    return (
        h00 * vals[i]
        + h10 * h[i] * m[i]
        + h01 * vals[i + 1]
        + h11 * h[i] * m[i + 1]
    )


def unwrap_hues(hs: list[float]) -> list[float]:
    """인접 knot이 최단경로(±180°)를 지나도록 언랩."""
    out = [hs[0]]
    for h in hs[1:]:
        d = ((h - out[-1] + 180) % 360) - 180
        out.append(out[-1] + d)
    return out


def seq_single(
    fam: str, L_top: float = 96.0, L_bot: float = 24.0, n: int = 256
) -> list[str]:
    """A8 — family 레시피의 광역 L* 연속 렌더링 (팔레트 floor 미상속)."""
    p = FAMILY_PARAMS[fam]

    def at(t: float) -> Rgb:
        l_t = L_top + (L_bot - L_top) * t
        h = (p.h0 + p.dh * t**p.gamma) % 360
        if t <= p.tp:
            c = p.cmax * (0.12 + 0.88 * math.sin(math.pi / 2 * t / p.tp) ** 1.2)
        else:
            u = (t - p.tp) / (1 - p.tp)
            c = p.cmax * (1 - 0.90 * u**1.4)
        c = min(c, gamut_max_chroma(h, l_t) * 0.97)
        return solve_swatch_rgb(h, c, l_t)

    return render(at, n=n)


def seq_gray(
    L_top: float = 97.0, L_bot: float = 16.0, n: int = 256
) -> list[str]:
    def at(t: float) -> Rgb:
        return solve_swatch_rgb(
            250,
            0.006 + 0.006 * math.sin(math.pi * t),
            L_top + (L_bot - L_top) * t,
        )

    return render(at, n=n)
