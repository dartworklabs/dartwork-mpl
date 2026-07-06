"""107-number SSOT — 스펙 §7의 자유 76 + 푸리에 24 + 상수 7.

표(FAMILY_PARAMS)가 운영 SSOT이고 푸리에 곡선은 신규 family 확장 메커니즘이다
(유도값과 표가 그리드 1스텝 어긋날 수 있으며 표가 우선 — 스펙 §7).
값의 출처: docs/superpowers/specs/assets/2026-07-03-color-system-v5/color_v5_ssot.json
(tests/test_color_v5_recipe.py 가 코드↔JSON 일치를 강제한다).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "FAMILIES",
    "FAMILY_PARAMS",
    "FOURIER",
    "GAMUT_CHROMA_FRAC",
    "GRAY_C_PROFILE",
    "GRAY_FLOOR",
    "GRAY_TINT_HUE",
    "L_TOP",
    "SHAPE_Q",
    "SHAPE_R",
    "FamilyParams",
    "derive_family",
    "fourier_eval",
    "mid_hue",
]


@dataclass(frozen=True)
class FamilyParams:
    h0: float  # 색상 앵커 (step0 OKLCH hue)
    dh: float  # 드리프트 총량 (deg)
    gamma: float  # 드리프트 타이밍
    tp: float  # 채도 정점 위치
    cmax: float  # 정점 채도 (유도)
    floor: float  # 밝기 바닥 L* (유도)
    cend: float  # 어두운 끝 채도 잔존율 (유도)
    c0: float  # 파스텔 시작 채도 비율 (유도)


FAMILIES: tuple[str, ...] = (
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

# 스펙 §7 확정 파라미터 표 (반올림 SSOT) — h·dh 1°, gamma·tp·c 0.05,
# cmax 0.005, floor 정수 그리드.
FAMILY_PARAMS: dict[str, FamilyParams] = {
    "red": FamilyParams(16, +11, 1.10, 0.85, 0.210, 42, 0.90, 0.10),
    "rose": FamilyParams(3, +14, 1.00, 0.85, 0.210, 40, 0.85, 0.10),
    "coral": FamilyParams(27, +2, 1.15, 0.85, 0.205, 44, 0.90, 0.10),
    "tangerine": FamilyParams(52, -12, 1.20, 0.85, 0.195, 49, 0.95, 0.15),
    "orange": FamilyParams(77, -41, 1.30, 0.85, 0.190, 54, 1.00, 0.15),
    "amber": FamilyParams(88, -44, 1.40, 0.65, 0.185, 57, 1.00, 0.15),
    "yellow": FamilyParams(99, -46, 1.50, 0.45, 0.180, 60, 1.00, 0.15),
    "lime": FamilyParams(122, +11, 0.60, 0.45, 0.190, 56, 0.85, 0.15),
    "green": FamilyParams(149, -3, 0.60, 0.50, 0.185, 51, 0.75, 0.15),
    "teal": FamilyParams(176, -13, 0.60, 0.45, 0.155, 47, 0.70, 0.15),
    "cyan": FamilyParams(202, +13, 0.85, 0.45, 0.115, 44, 0.75, 0.15),
    "sky": FamilyParams(220, +14, 0.85, 0.60, 0.130, 43, 0.80, 0.15),
    "blue": FamilyParams(238, +15, 0.85, 0.75, 0.165, 42, 0.85, 0.15),
    "cobalt": FamilyParams(256, +5, 1.25, 0.80, 0.190, 40, 0.85, 0.15),
    "indigo": FamilyParams(273, -5, 1.65, 0.85, 0.210, 39, 0.85, 0.10),
    "violet": FamilyParams(298, -12, 1.25, 0.85, 0.230, 37, 0.85, 0.10),
    "purple": FamilyParams(319, +0, 1.00, 0.75, 0.220, 37, 0.85, 0.05),
    "fuchsia": FamilyParams(335, +9, 0.95, 0.80, 0.210, 37, 0.85, 0.05),
    "pink": FamilyParams(350, +18, 0.85, 0.85, 0.210, 39, 0.85, 0.05),
}

# 전역 hue 푸리에 곡선 (확장 유도용 — 상수항 + cos/sin 교대)
FOURIER: dict[str, tuple[float, ...]] = {
    "cmax_k3": (
        0.184409,
        0.036835,
        -7.1e-05,
        -0.011187,
        -0.022258,
        0.000429,
        0.014637,
    ),
    "floor_k3": (
        45.816711,
        -3.776384,
        9.500538,
        -4.011493,
        0.266656,
        0.687222,
        -1.346282,
    ),
    "cend_k2": (0.848962, 0.070533, 0.053148, -0.07045, 0.025104),
    "c0_k2": (0.128378, -0.049482, 0.02872, -0.015143, 0.011463),
}

# 전역 상수 (7)
L_TOP = 96.0
SHAPE_Q = 1.2
SHAPE_R = 1.5
GAMUT_CHROMA_FRAC = 0.97
GRAY_FLOOR = 28.0
GRAY_TINT_HUE = 250
GRAY_C_PROFILE: tuple[float, ...] = (
    0.003,
    0.005,
    0.007,
    0.009,
    0.010,
    0.011,
    0.011,
    0.010,
    0.008,
    0.006,
)


def fourier_eval(coef: tuple[float, ...], h_deg: float) -> float:
    h = math.radians(h_deg)
    k = (len(coef) - 1) // 2
    v = coef[0]
    for i in range(1, k + 1):
        v += coef[2 * i - 1] * math.cos(i * h) + coef[2 * i] * math.sin(i * h)
    return float(v)


def mid_hue(p: FamilyParams) -> float:
    return float((p.h0 + p.dh * 0.5**p.gamma) % 360)


def _grid(v: float, g: float) -> float:
    return round(round(v / g) * g, 10)


def derive_family(
    h0: float, dh: float, gamma: float, tp: float
) -> FamilyParams:
    """신규 family 확장 — 푸리에 곡선에서 유도 파라미터를 계산해 그리드 반올림."""
    hm = (h0 + dh * 0.5**gamma) % 360
    return FamilyParams(
        h0=h0,
        dh=dh,
        gamma=gamma,
        tp=tp,
        cmax=_grid(fourier_eval(FOURIER["cmax_k3"], hm), 0.005),
        floor=float(round(fourier_eval(FOURIER["floor_k3"], hm))),
        cend=_grid(fourier_eval(FOURIER["cend_k2"], hm), 0.05),
        c0=_grid(fourier_eval(FOURIER["c0_k2"], hm), 0.05),
    )
