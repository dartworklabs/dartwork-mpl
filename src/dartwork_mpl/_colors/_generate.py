"""Recipe compiler — NeutralTone rendering + continuous OKLab equalization.

등화는 반드시 float sRGB에서 한다: dense 경로를 hex로 평가하면 스텝당 dE가
8-bit 양자화 오차에 묻혀 호장 적분이 노이즈에 지배된다(스펙 §9 프로토콜 1).
"""

import math
from bisect import bisect_left
from collections.abc import Callable
from typing import TypeAlias

from . import _conversion as conversion
from . import _tone as tone
from ._recipe import (
    FAMILIES,
    FAMILY_PARAMS,
    GRAY_C_PROFILE,
    GRAY_TINT_HUE,
    GRAY_TONE_FLOOR,
    SHAPE_Q,
    SHAPE_R,
    TONE_TOP,
    FamilyParams,
)

__all__ = [
    "compile_family",
    "compile_gray",
    "compile_palette",
    "equalize",
    "shape",
    "swatch",
]

Rgb: TypeAlias = tuple[float, float, float]


def de_ok_rgb(first: Rgb, second: Rgb) -> float:
    """Return the established 100-scaled Euclidean OKLab distance."""
    return (
        math.dist(
            conversion._srgb_to_oklab(first), conversion._srgb_to_oklab(second)
        )
        * 100.0
    )


def hex_from_rgb(rgb: Rgb) -> str:
    """Quantize one encoded sRGB triple with the canonical encoder."""
    return conversion._rgb_to_hex(*rgb)


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


def swatch(p: FamilyParams, t: float, *, luminance_lock: bool = True) -> Rgb:
    """Render one family recipe point, with zero as light and one as dark."""
    tone_value = float(TONE_TOP + (p.tone_floor - TONE_TOP) * t)
    h = (p.h0 + p.dh * t**p.gamma) % 360
    c = p.cmax * shape(t, p.tp, p.c0, p.cend)
    return tone.render_oklch_at_tone(
        tone=tone_value, chroma=c, hue=h, luminance_lock=luminance_lock
    )


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
        if mean == 0:
            # Degenerate all-identical swatch: zero total arc length, so the
            # normalized cv is undefined. Treat as maximal non-uniformity
            # (inf) rather than dividing by zero — nothing to equalize, and
            # the downstream gate_ladder cv check flags the broken output.
            cv = float("inf")
        else:
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


def compile_family(
    p: FamilyParams, *, luminance_lock: bool = True
) -> list[str]:
    """Compile one ten-stop family ladder through the selected tone policy."""
    return [
        hex_from_rgb(rgb)
        for rgb in equalize(
            lambda fraction: swatch(p, fraction, luminance_lock=luminance_lock),
            n=10,
        )
    ]


def compile_gray(*, luminance_lock: bool = True) -> list[str]:
    """Compile the evenly spaced, weakly cool NeutralTone ladder."""
    out: list[str] = []
    for k in range(10):
        tone_value = float(TONE_TOP + (GRAY_TONE_FLOOR - TONE_TOP) * k / 9)
        out.append(
            hex_from_rgb(
                tone.render_oklch_at_tone(
                    tone=tone_value,
                    chroma=GRAY_C_PROFILE[k],
                    hue=GRAY_TINT_HUE,
                    luminance_lock=luminance_lock,
                )
            )
        )
    return out


def compile_palette(*, luminance_lock: bool = True) -> dict[str, list[str]]:
    """Compile all palette families with one explicit luminance-lock policy."""
    pal = {
        fam: compile_family(FAMILY_PARAMS[fam], luminance_lock=luminance_lock)
        for fam in FAMILIES
    }
    pal["gray"] = compile_gray(luminance_lock=luminance_lock)
    return pal
