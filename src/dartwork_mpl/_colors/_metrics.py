"""Validation-only metrics: private CIELAB/CIEDE2000 and CVD simulation.

Gamma, hex, and OKLab math delegate to ``_conversion``. The legacy raw XYZ
matrix remains isolated here solely for CIELAB/CIEDE2000 compatibility.
"""

from __future__ import annotations

import math

from . import _conversion as conversion

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

# Source-pinned Machado severity-1 matrices are used for the catalog's
# protan/deutan regression diagnostics. Tritan uses the project-adapted BVM
# matrices below. These choices preserve the named v5 validation protocol;
# neither path establishes correctness for every observer.
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
}

# Project-adapted BVM matrices implement a two-half-plane tritan projection.
# The linear-sRGB combined values originate from libDaltonLens and run in the
# same linear space as the Machado path. Tests verify algebraic projection
# invariants: each matrix is approximately idempotent and both agree on the
# separation plane. Those invariants do not verify observer or model
# correctness.
_BVM_TRITAN_SEP = (0.03901, -0.02788, -0.01113)
_BVM_TRITAN_HI = (  # dot(rgb_linear, SEP) >= 0
    (1.01277, 0.13548, -0.14826),
    (-0.01243, 0.86812, 0.14431),
    (0.07589, 0.80500, 0.11911),
)
_BVM_TRITAN_LO = (  # dot(rgb_linear, SEP) < 0
    (0.93678, 0.18979, -0.12657),
    (0.06154, 0.81526, 0.12320),
    (-0.37562, 1.12767, 0.24796),
)


def _lin(c: float) -> float:
    """Delegate sRGB gamma decoding to the canonical conversion kernel."""
    return float(conversion._srgb_to_linear(c))


def _delin(c: float) -> float:
    """Clamp a CVD channel, then delegate canonical sRGB gamma encoding."""
    clamped = min(max(c, 0.0), 1.0)
    return float(conversion._linear_to_srgb(clamped))


def rgb_from_hex(hexstr: str) -> tuple[float, float, float]:
    """Parse a supported hex spelling through the canonical strict parser."""
    return conversion._parse_hex(hexstr)


def hex_from_rgb(rgb: tuple[float, float, float]) -> str:
    """Quantize an sRGB triple through the canonical strict encoder."""
    return conversion._rgb_to_hex(*rgb)


def lab_from_rgb(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert encoded sRGB to validation-only legacy CIELAB."""
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
    """Return legacy CIELAB L* for an encoded sRGB triple."""
    return lab_from_rgb(rgb)[0]


def lab_l_hex(hexstr: str) -> float:
    """Return legacy CIELAB L* for a supported hex spelling."""
    return lab_l_rgb(rgb_from_hex(hexstr))


def oklab_from_rgb(
    rgb: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Delegate encoded-sRGB to OKLab conversion to the canonical kernel."""
    return conversion._srgb_to_oklab(rgb)


def de_ok_rgb(
    rgb1: tuple[float, float, float], rgb2: tuple[float, float, float]
) -> float:
    """OKLab 유클리드 거리 x100 (등화·설계 지표 — 스펙 §6)."""
    return math.dist(oklab_from_rgb(rgb1), oklab_from_rgb(rgb2)) * 100


def de2000_rgb(
    rgb1: tuple[float, float, float], rgb2: tuple[float, float, float]
) -> float:
    """Return a validation-only color-difference regression metric.

    CIEDE2000 is not an accessibility gate or observer guarantee.
    """
    return _de2000_lab(lab_from_rgb(rgb1), lab_from_rgb(rgb2))


def _de2000_lab(
    first: tuple[float, float, float], second: tuple[float, float, float]
) -> float:
    """Return CIEDE2000 for two validation-only CIELAB triples.

    Parameters
    ----------
    first, second : tuple[float, float, float]
        CIELAB ``(L*, a*, b*)`` coordinates.

    Returns
    -------
    float
        CIEDE2000 color difference with unit weighting factors.
    """
    L1, a1, b1 = first
    L2, a2, b2 = second
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
    """Return CIEDE2000 between two supported hex spellings."""
    return de2000_rgb(rgb_from_hex(h1), rgb_from_hex(h2))


def cvd_rgb(
    rgb: tuple[float, float, float], kind: str
) -> tuple[float, float, float]:
    """Simulate CVD or encode a modeled-relative-Y-preserving neutral gray."""
    if kind == "gray":
        relative_y = conversion.relative_y_srgb_d65(rgb)
        v = _delin(relative_y)
        return (v, v, v)
    lin = [_lin(c) for c in rgb]
    if kind == "tritan":
        # Brettel-Viénot-Mollon (1997): pick the half-plane projection by the
        # sign of the dot product with the separation-plane normal. The
        # projection can leave sRGB, so clamp before the gamma round-trip.
        dot = sum(s * v for s, v in zip(_BVM_TRITAN_SEP, lin, strict=True))
        matrix = _BVM_TRITAN_HI if dot >= 0 else _BVM_TRITAN_LO
        out = [
            sum(m * v for m, v in zip(row, lin, strict=True)) for row in matrix
        ]
        return tuple(  # type: ignore[return-value]
            _delin(min(max(c, 0.0), 1.0)) for c in out
        )
    out = [
        sum(m * v for m, v in zip(row, lin, strict=True))
        for row in _MACHADO[kind]
    ]
    return tuple(_delin(c) for c in out)  # type: ignore[return-value]
