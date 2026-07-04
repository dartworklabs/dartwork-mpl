"""Recipe compiler — 스와치 솔버 + 연속(float) 공간 OKLab 등화 (스펙 §7).

등화는 반드시 float sRGB에서 한다: dense 경로를 hex로 평가하면 스텝당 dE가
8-bit 양자화 오차에 묻혀 호장 적분이 노이즈에 지배된다(스펙 §9 프로토콜 1).
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Callable

from ._color import Color
from ._metrics import de_ok_rgb, hex_from_rgb, lab_l_rgb
from ._recipe import (
    FAMILIES,
    FAMILY_PARAMS,
    GRAY_C_PROFILE,
    GRAY_FLOOR,
    GRAY_TINT_HUE,
    L_TOP,
    SHAPE_Q,
    SHAPE_R,
    FamilyParams,
)

__all__ = [
    "compile_family",
    "compile_gray",
    "compile_palette",
    "equalize",
    "gamut_max_chroma",
    "shape",
    "solve_swatch_rgb",
    "swatch",
]

Rgb = tuple[float, float, float]


def solve_swatch_rgb(hue_deg: float, chroma: float, l_target: float) -> Rgb:
    """OKLCH L 이진 탐색 — gamut-map된 float sRGB의 CIELAB L*가 타깃에 오도록."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if (
            lab_l_rgb(Color.from_oklch(mid, chroma, hue_deg).to_rgb())
            < l_target
        ):
            lo = mid
        else:
            hi = mid
    return Color.from_oklch((lo + hi) / 2, chroma, hue_deg).to_rgb()


def gamut_max_chroma(hue_deg: float, l_target: float) -> float:
    """해당 hue에서 CIELAB L* 타깃을 만족하는 최대 in-gamut OKLCH chroma (근사)."""
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        if lab_l_rgb(Color.from_oklch(mid, 0.04, hue_deg).to_rgb()) < l_target:
            lo = mid
        else:
            hi = mid
    l_ok = (lo + hi) / 2
    c_lo, c_hi = 0.0, 0.40
    for _ in range(22):
        c_mid = (c_lo + c_hi) / 2
        if Color.from_oklch(l_ok, c_mid, hue_deg).in_gamut():
            c_lo = c_mid
        else:
            c_hi = c_mid
    return c_lo


def shape(t: float, tp: float, c0: float, cend: float) -> float:
    """A3 공통 채도 형상 — sin^q 상승 → 정점 tp → t^r 하강."""
    if t <= tp:
        return float(
            c0
            + (1 - c0)
            * math.sin(math.pi / 2 * min(max(t / tp, 0.0), 1.0)) ** SHAPE_Q
        )
    u = min(max((t - tp) / (1 - tp), 0.0), 1.0)
    return float(1 - (1 - cend) * u**SHAPE_R)


def swatch(p: FamilyParams, t: float) -> Rgb:
    """A2(floor)·A3(채도)·A4(드리프트) 레시피 — t∈[0,1], 0=밝음 1=어두움."""
    l_t = L_TOP + (p.floor - L_TOP) * t
    h = (p.h0 + p.dh * t**p.gamma) % 360
    c = p.cmax * shape(t, p.tp, p.c0, p.cend)
    return solve_swatch_rgb(h, c, l_t)


def equalize(
    swatch_at: Callable[[float], Rgb], n: int, dense: int = 121
) -> list[Rgb]:
    """A5 — 누적 OKLab dE 역보간 배치 + 코드 dE 반복 등화 (엔드포인트 고정)."""
    ts_d = [i / (dense - 1) for i in range(dense)]
    pts = [swatch_at(t) for t in ts_d]
    cum = [0.0]
    for i in range(1, dense):
        cum.append(cum[-1] + de_ok_rgb(pts[i - 1], pts[i]))
    total = cum[-1]
    ts = []
    for k in range(n):
        tgt = total * k / (n - 1)
        i = min(max(bisect_left(cum, tgt), 1), dense - 1)
        f = (tgt - cum[i - 1]) / (cum[i] - cum[i - 1] or 1)
        ts.append(min(max(ts_d[i - 1] + f * (ts_d[i] - ts_d[i - 1]), 0.0), 1.0))
    ts[0], ts[-1] = 0.0, 1.0
    row = [swatch_at(t) for t in ts]
    for _ in range(14):
        d = [de_ok_rgb(row[i], row[i + 1]) for i in range(n - 1)]
        cumd = [0.0]
        for v in d:
            cumd.append(cumd[-1] + v)
        tot = cumd[-1]
        mean = tot / (n - 1)
        cv = (sum((x - mean) ** 2 for x in d) / (n - 1)) ** 0.5 / mean
        if cv < 0.015:
            break
        new_ts = [0.0]
        for k in range(1, n - 1):
            tgt = tot * k / (n - 1)
            i = min(max(bisect_left(cumd, tgt), 1), n - 1)
            f = (tgt - cumd[i - 1]) / (cumd[i] - cumd[i - 1] or 1)
            new_ts.append(ts[i - 1] + f * (ts[i] - ts[i - 1]))
        new_ts.append(1.0)
        ts = new_ts
        row = [row[0]] + [swatch_at(t) for t in ts[1:-1]] + [row[-1]]
    return row


def compile_family(p: FamilyParams) -> list[str]:
    return [hex_from_rgb(r) for r in equalize(lambda t: swatch(p, t), n=10)]


def compile_gray() -> list[str]:
    """A6 — L* 균등 사다리 + 약한 쿨 틴트 (등화 불필요: L* 균등이 곧 dE 균등)."""
    out = []
    for k in range(10):
        l_t = L_TOP + (GRAY_FLOOR - L_TOP) * k / 9
        out.append(
            hex_from_rgb(
                solve_swatch_rgb(GRAY_TINT_HUE, GRAY_C_PROFILE[k], l_t)
            )
        )
    return out


def compile_palette() -> dict[str, list[str]]:
    pal = {fam: compile_family(FAMILY_PARAMS[fam]) for fam in FAMILIES}
    pal["gray"] = compile_gray()
    return pal
