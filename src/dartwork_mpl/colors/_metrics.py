"""Perceptual metric kernel — CIELAB L*, OKLab dE, CIEDE2000, Machado CVD.

스펙 §6 지표 3원화: 등화=OKLab dE, 접근성 게이트=CIEDE2000, 밝기·그레이=CIELAB L*.
모든 함수는 float sRGB(0..1 tuple)를 1급 입력으로 받는다 — 등화 파이프라인이
8-bit hex 양자화 노이즈에 오염되지 않게 하기 위함(스펙 §9 공통 프로토콜 1).
"""

from __future__ import annotations

import math

__all__ = [
    "cvd_rgb",
    "de2000_hex",
    "de2000_rgb",
    "de_ok_rgb",
    "hex_from_rgb",
    "lab_from_rgb",
    "lab_l_hex",
    "lab_l_rgb",
    "oklab_from_rgb",
    "rgb_from_hex",
]

_M_RGB2XYZ = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)
_WHITE = (0.95047, 1.0, 1.08883)

# Machado, Oliveira & Fernandes (2009), severity 1.0.
# NOTE: tritan 행렬은 스펙 §12 판정에 따라 Brettel-Viénot-Mollon(1997)로 교체
# 예정이나 v5 게이트 산출값은 Machado 기준으로 확정되었다 — SSOT 재현을 위해
# Machado를 유지하고, BVM 교체는 게이트 재산출과 함께 별도 사이클에서 수행한다.
_MACHADO = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritan": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _delin(c: float) -> float:
    c = min(max(c, 0.0), 1.0)
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def rgb_from_hex(hexstr: str) -> tuple[float, float, float]:
    h = hexstr.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def hex_from_rgb(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(
        f"{round(min(max(v, 0.0), 1.0) * 255):02x}" for v in rgb
    )


def lab_from_rgb(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    lin = [_lin(c) for c in rgb]
    xyz = [
        sum(m * v for m, v in zip(row, lin, strict=True)) for row in _M_RGB2XYZ
    ]
    f = []
    for v, w in zip(xyz, _WHITE, strict=True):
        t = v / w
        f.append(
            t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
        )
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def lab_l_rgb(rgb: tuple[float, float, float]) -> float:
    return lab_from_rgb(rgb)[0]


def lab_l_hex(hexstr: str) -> float:
    return lab_l_rgb(rgb_from_hex(hexstr))


def oklab_from_rgb(
    rgb: tuple[float, float, float],
) -> tuple[float, float, float]:
    r, g, b = (_lin(c) for c in rgb)
    lm = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    mm = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    sm = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    lm, mm, sm = lm ** (1 / 3), mm ** (1 / 3), sm ** (1 / 3)
    return (
        0.2104542553 * lm + 0.7936177850 * mm - 0.0040720468 * sm,
        1.9779984951 * lm - 2.4285922050 * mm + 0.4505937099 * sm,
        0.0259040371 * lm + 0.7827717662 * mm - 0.8086757660 * sm,
    )


def de_ok_rgb(
    rgb1: tuple[float, float, float], rgb2: tuple[float, float, float]
) -> float:
    """OKLab 유클리드 거리 x100 (등화·설계 지표 — 스펙 §6)."""
    return math.dist(oklab_from_rgb(rgb1), oklab_from_rgb(rgb2)) * 100


def de2000_rgb(
    rgb1: tuple[float, float, float], rgb2: tuple[float, float, float]
) -> float:
    """CIEDE2000 (접근성 게이트 지표 — 스펙 §6)."""
    L1, a1, b1 = lab_from_rgb(rgb1)
    L2, a2, b2 = lab_from_rgb(rgb2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb**7 / (Cb**7 + 25**7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        dh = h2p - h1p
        dhp = dh - 360 if dh > 180 else (dh + 360 if dh < -180 else dh)
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    else:
        s, d = h1p + h2p, abs(h1p - h2p)
        hbp = (
            (s + 360) / 2
            if (d > 180 and s < 360)
            else ((s - 360) / 2 if (d > 180 and s >= 360) else s / 2)
        )
    T = (
        1
        - 0.17 * math.cos(math.radians(hbp - 30))
        + 0.24 * math.cos(math.radians(2 * hbp))
        + 0.32 * math.cos(math.radians(3 * hbp + 6))
        - 0.20 * math.cos(math.radians(4 * hbp - 63))
    )
    dth = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp**7 / (Cbp**7 + 25**7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dth)) * Rc
    return math.sqrt(
        (dLp / Sl) ** 2
        + (dCp / Sc) ** 2
        + (dHp / Sh) ** 2
        + Rt * (dCp / Sc) * (dHp / Sh)
    )


def de2000_hex(h1: str, h2: str) -> float:
    return de2000_rgb(rgb_from_hex(h1), rgb_from_hex(h2))


def cvd_rgb(
    rgb: tuple[float, float, float], kind: str
) -> tuple[float, float, float]:
    """CVD 시뮬레이션 (protan/deutan/tritan) 또는 등L* 그레이 변환."""
    if kind == "gray":
        l_star = lab_l_rgb(rgb)
        fy = (l_star + 16) / 116
        y = fy**3 if fy**3 > 216 / 24389 else (116 * fy - 16) * 27 / 24389
        v = _delin(y)
        return (v, v, v)
    lin = [_lin(c) for c in rgb]
    out = [
        sum(m * v for m, v in zip(row, lin, strict=True))
        for row in _MACHADO[kind]
    ]
    return tuple(_delin(c) for c in out)  # type: ignore[return-value]
