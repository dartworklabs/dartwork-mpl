"""Colormap catalog compiler — 42종 (스펙 §9).

프로토콜(§9 공통): float 경로 등화(hex 최종 1회) · pchip knot 보간 ·
게이트/스와치는 n-stop 직접 렌더.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Callable

from ._color import Color
from ._generate import gamut_max_chroma, solve_swatch_rgb
from ._metrics import de_ok_rgb, hex_from_rgb, lab_l_hex
from ._recipe import FAMILIES, FAMILY_PARAMS

__all__ = [
    "ANCHORS",
    "compile_cmaps",
    "cyclic_hue",
    "cyclic_twilight",
    "diverging_pair",
    "pchip",
    "render",
    "seq_gray",
    "seq_multi",
    "seq_single",
    "seq_topo",
    "unwrap_hues",
]

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
        # A closed map must genuinely close: the seam ΔE must be ~0. If it is
        # not, the arc-length resample below would duplicate tail colors near
        # the seam. Assert here so a future non-closing "closed" map fails
        # loudly at build instead of shipping a seam-clamped map silently.
        seam = de_ok_rgb(pts[-1], pts[0])
        assert seam < 1e-6, f"closed render: seam ΔE {seam:.4g} is not ~0"
        cum.append(cum[-1] + seam)
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


# --- 멀티휴 (자연광 장면 — 스펙 §9. knot은 family 앵커 h0에서만) ---
ANCHORS: dict[str, float] = {fam: FAMILY_PARAMS[fam].h0 for fam in FAMILIES}


def seq_multi(
    hue_knots: list[float],
    chroma_knots: list[float],
    L_start: float = 14.0,
    L_end: float = 96.0,
    n: int = 256,
) -> list[str]:
    """빛 계열 관례: t=0=어두움(저값) → t=1=밝음. knot은 pchip으로 C1 통과."""
    hk = unwrap_hues(hue_knots)
    nk = len(hk)
    tk = [i / (nk - 1) for i in range(nk)]

    def at(t: float) -> Rgb:
        h = pchip(tk, hk, t) % 360
        c = pchip(tk, chroma_knots, t)
        l_t = L_start + (L_end - L_start) * t
        c = min(c, gamut_max_chroma(h, l_t) * 0.97)
        return solve_swatch_rgb(h, c, l_t)

    return render(at, n=n)


TopoSpec = tuple[list[float], list[float], float, float]


def seq_topo(sea: TopoSpec, land: TopoSpec, n: int = 256) -> list[str]:
    """기준면 2단 — 반부별 독립 등화, 중앙 L* 불연속은 설계 (해안선)."""

    def half(
        hk: list[float], ck: list[float], l0: float, l1: float
    ) -> list[str]:
        hku = unwrap_hues(hk)
        tk = [i / (len(hku) - 1) for i in range(len(hku))]

        def at(t: float) -> Rgb:
            h = pchip(tk, hku, t) % 360
            l_t = l0 + (l1 - l0) * t
            c = min(pchip(tk, ck, t), gamut_max_chroma(h, l_t) * 0.97)
            return solve_swatch_rgb(h, c, l_t)

        return render(at, n=n // 2)

    return half(*sea) + half(*land)


def diverging_pair(
    hex_a: str,
    hex_b: str,
    l_end: float,
    l_center: float = 96.0,
    gamma: float = 0.85,
    half: int = 32,
) -> list[str]:
    """L* 대칭 diverging — 홀수 샘플(2·half-1)로 중심이 정확히 50%에 위치.

    양극 정체성은 dc.{a}6/dc.{b}6 hex의 OKLCH chroma·hue에서 유도한다.
    포인트별 독립 솔브(등화 없음)라 hex 직접 생성으로 충분하다.
    """
    arms: list[list[str]] = []
    for src in (hex_a, hex_b):
        _, c_max, hue = Color(src).to_oklch()
        pts = []
        for i in range(half):
            t = i / (half - 1)  # 0=끝(포화) → 1=중심(밝음)
            l_t = l_end + (l_center - l_end) * t
            c = c_max * (1 - t) ** gamma + 0.004 * t
            pts.append(hex_from_rgb(solve_swatch_rgb(hue, c, l_t)))
        arms.append(pts)
    return arms[0] + arms[1][:-1][::-1]


def cyclic_hue(L: float = 62.0, n: int = 256) -> list[str]:
    """등명도 색상환 — hue 균등(색상환은 hue가 지각축)."""
    c_safe = min(gamut_max_chroma(h, L) for h in range(0, 360, 5)) * 0.95
    return [
        hex_from_rgb(solve_swatch_rgb((i / n * 360) % 360, c_safe, L))
        for i in range(n)
    ]


def cyclic_twilight(hue_a: float, hue_b: float, n: int = 256) -> list[str]:
    """이중 로브 cyclic — 밝은 이음매 → A팔 → 어두운 중심 → B팔 → 이음매."""
    L_seam, L_center = 93.0, 18.0

    def at(t: float) -> Rgb:
        if t <= 0.5:
            u, h, cmax = t / 0.5, hue_a, 0.15
        else:
            u, h, cmax = 1 - (t - 0.5) / 0.5, hue_b, 0.16
        l_t = L_seam + (L_center - L_seam) * u
        c = cmax * math.sin(math.pi * u) ** 0.85
        c = min(c, gamut_max_chroma(h % 360, l_t) * 0.96)
        return solve_swatch_rgb(h % 360, c, l_t)

    return render(at, n=n, closed=True)


def compile_cmaps(
    palette: dict[str, list[str]], n: int = 256
) -> dict[str, list[str]]:
    """46종 카탈로그 — 키는 SSOT swatches_32와 동일한 평면 공개 이름."""
    A = ANCHORS
    cm: dict[str, list[str]] = {}

    # 단일색 20 (family명 그대로)
    for fam in FAMILIES:
        cm[fam] = seq_single(fam, n=n)
    cm["gray"] = seq_gray(n=n)

    # 멀티휴 9 (자연광 장면 — knot·chroma·L 범위는 스펙 §9 확정값)
    multi: dict[str, tuple[list[float], list[float], float, float]] = {
        "aurora": (
            [
                A["violet"],
                A["indigo"],
                A["sky"],
                A["teal"],
                A["lime"],
                A["yellow"],
            ],
            [0.08, 0.11, 0.13, 0.15, 0.16, 0.13],
            14.0,
            96.0,
        ),
        "afterglow": (
            [A["violet"], A["purple"], A["pink"], A["red"], A["orange"]],
            [0.10, 0.17, 0.20, 0.19, 0.16],
            16.0,
            92.0,
        ),
        "blaze": (
            [A["violet"], A["pink"], A["red"], A["orange"], A["yellow"]],
            [0.09, 0.18, 0.20, 0.18, 0.13],
            12.0,
            94.0,
        ),
        "lava": (
            [A["red"], A["orange"], A["amber"], A["yellow"]],
            [0.15, 0.18, 0.16, 0.13],
            12.0,
            95.0,
        ),
        "lagoon": (
            [A["blue"], A["cyan"], A["teal"], A["green"], A["lime"]],
            [0.10, 0.12, 0.14, 0.17, 0.15],
            14.0,
            96.0,
        ),
        "glacier": (
            [A["indigo"], A["blue"], A["sky"], A["cyan"], A["teal"]],
            [0.10, 0.15, 0.14, 0.12, 0.12],
            14.0,
            96.0,
        ),
        "canopy": (
            [A["teal"], A["green"], A["lime"], A["yellow"]],
            [0.09, 0.14, 0.16, 0.13],
            14.0,
            96.0,
        ),
        "haze": (
            [A["blue"], A["sky"], A["green"], A["yellow"]],
            [0.05, 0.07, 0.09, 0.13],
            14.0,
            96.0,
        ),
        "iris": (
            [
                A["violet"],
                A["blue"],
                A["cyan"],
                A["green"],
                A["yellow"],
                A["orange"],
            ],
            [0.14, 0.15, 0.11, 0.15, 0.16, 0.16],
            14.0,
            93.0,
        ),
    }
    for name, (hk, ck, l0, l1) in multi.items():
        cm[name] = seq_multi(hk, ck, L_start=l0, L_end=l1, n=n)

    # diverging 13 (저값_고값 pair — 양극 = dc.{a}6/dc.{b}6)
    # 샘플 수 규약: diverging_pair 는 홀수(2·half-1) 샘플 → endpoint-inclusive
    # 정수-stride 리샘플로 n에 맞춘다. n=32 golden 은 half=32(63→32, stride 2.0
    # 정확 — SSOT 생성 방식과 동일), n=256 export 는 half=128(255→256).
    def _resample(hexes: list[str], m: int) -> list[str]:
        last = len(hexes) - 1
        return [hexes[round(i * last / (m - 1))] for i in range(m)]

    half = max(32, n // 2)

    def dv(
        fa: str,
        fb: str,
        l_end: float,
        l_center: float = 96.0,
        gamma: float = 0.85,
    ) -> list[str]:
        return _resample(
            diverging_pair(
                palette[fa][6],
                palette[fb][6],
                l_end=l_end,
                l_center=l_center,
                gamma=gamma,
                half=half,
            ),
            n,
        )

    cm["blue_red"] = dv(
        "blue",
        "red",
        l_end=(lab_l_hex(palette["blue"][6]) + lab_l_hex(palette["red"][6]))
        / 2,
    )
    cm["blue_red_deep"] = dv("blue", "red", l_end=21, l_center=97.5)
    cm["blue_red_soft"] = dv("blue", "red", l_end=48, l_center=90, gamma=1.1)
    for a, b, le in (
        ("blue", "orange", 42),
        ("teal", "rose", 44),
        ("green", "purple", 40),
        ("purple", "orange", 42),
        ("cyan", "red", 44),
        ("teal", "amber", 44),
        ("violet", "lime", 42),
        ("indigo", "amber", 40),
        ("gray", "blue", 42),
        ("gray", "red", 42),
    ):
        cm[f"{a}_{b}"] = dv(a, b, l_end=le)

    # topo 1
    cm["coast"] = seq_topo(
        sea=(
            [A["indigo"], A["blue"], A["cyan"]],
            [0.09, 0.11, 0.10],
            16.0,
            84.0,
        ),
        land=(
            [A["green"], A["lime"], A["amber"]],
            [0.11, 0.09, 0.03],
            42.0,
            96.0,
        ),
        n=n,
    )

    # cyclic 3 (원형 빛 현상)
    def hue_of(fam: str) -> float:
        return Color(palette[fam][6]).to_oklch()[2]

    cm["hue"] = cyclic_hue(n=n)
    cm["halo"] = cyclic_twilight(hue_of("blue"), hue_of("red"), n=n)
    cm["corona"] = cyclic_twilight(hue_of("teal"), hue_of("orange"), n=n)
    return cm
