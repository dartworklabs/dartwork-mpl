"""NeutralTone-based compiler for the 43-colormap catalog.

프로토콜(§9 공통): float 경로 등화(hex 최종 1회) · pchip knot 보간 ·
게이트/스와치는 n-stop 직접 렌더.
"""

import math
from bisect import bisect_left
from collections.abc import Callable
from typing import TypeAlias

from . import _conversion as conversion
from . import _tone as tone
from ._recipe import FAMILIES, FAMILY_PARAMS, GAMUT_CHROMA_FRAC

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
    "unwrap_hues",
]

Rgb: TypeAlias = tuple[float, float, float]


def _de_ok_rgb(first: Rgb, second: Rgb) -> float:
    """Return the established 100-scaled Euclidean OKLab distance."""
    return (
        math.dist(
            conversion._srgb_to_oklab(first), conversion._srgb_to_oklab(second)
        )
        * 100.0
    )


def _hex_from_rgb(rgb: Rgb) -> str:
    """Quantize one encoded sRGB triple with the canonical encoder."""
    return conversion._rgb_to_hex(*rgb)


def _oklch_from_hex(value: str) -> tuple[float, float, float]:
    """Decode one hex color into canonical degree-based OKLCH."""
    return conversion._oklab_to_oklch_degrees(
        *conversion._srgb_to_oklab(conversion._parse_hex(value))
    )


def _tone_from_hex(value: str) -> float:
    """Derive NeutralTone from the color's modeled relative CIE Y."""
    rgb = conversion._parse_hex(value)
    return float(tone.tone_from_relative_y(conversion.relative_y_srgb_d65(rgb)))


def _render_at_tone(
    tone_value: float, chroma: float, hue: float, *, luminance_lock: bool
) -> Rgb:
    """Render one compiler coordinate through the shared tone primitive."""
    return tone.render_oklch_at_tone(
        tone=tone_value, chroma=chroma, hue=hue, luminance_lock=luminance_lock
    )


def _max_chroma(hue: float, tone_value: float) -> float:
    """Return the geometric chroma boundary for one NeutralTone coordinate."""
    return tone.max_chroma_at_tone(hue, tone.neutral_tone(tone_value))


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
        cum.append(cum[-1] + _de_ok_rgb(pts[i - 1], pts[i]))
    if closed:
        # A closed map must genuinely close: the seam ΔE must be ~0. If it is
        # not, the arc-length resample below would duplicate tail colors near
        # the seam. Assert here so a future non-closing "closed" map fails
        # loudly at build instead of shipping a seam-clamped map silently.
        seam = _de_ok_rgb(pts[-1], pts[0])
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
    return [_hex_from_rgb(p) for p in (out[:n] if closed else out)]


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
    fam: str,
    tone_top: float = 0.9655172091954044,
    tone_bottom: float = 0.3448275747126444,
    n: int = 256,
    *,
    luminance_lock: bool = True,
) -> list[str]:
    """Render one family across its wide NeutralTone range."""
    p = FAMILY_PARAMS[fam]

    def at(fraction: float) -> Rgb:
        tone_value = tone_top + (tone_bottom - tone_top) * fraction
        hue = (p.h0 + p.dh * fraction**p.gamma) % 360
        if fraction <= p.tp:
            chroma = p.cmax * (
                0.12 + 0.88 * math.sin(math.pi / 2 * fraction / p.tp) ** 1.2
            )
        else:
            progress = (fraction - p.tp) / (1 - p.tp)
            chroma = p.cmax * (1 - 0.90 * progress**1.4)
        chroma = min(chroma, _max_chroma(hue, tone_value) * GAMUT_CHROMA_FRAC)
        return _render_at_tone(
            tone_value, chroma, hue, luminance_lock=luminance_lock
        )

    return render(at, n=n)


def seq_gray(
    tone_top: float = 0.9741378985632205,
    tone_bottom: float = 0.2758620597701155,
    n: int = 256,
    *,
    luminance_lock: bool = True,
) -> list[str]:
    """Render the weakly cool continuous gray ramp."""

    def at(fraction: float) -> Rgb:
        return _render_at_tone(
            tone_top + (tone_bottom - tone_top) * fraction,
            0.006 + 0.006 * math.sin(math.pi * fraction),
            250.0,
            luminance_lock=luminance_lock,
        )

    return render(at, n=n)


# --- 멀티휴 (자연광 장면 — 스펙 §9. knot은 family 앵커 h0에서만) ---
ANCHORS: dict[str, float] = {fam: FAMILY_PARAMS[fam].h0 for fam in FAMILIES}


def seq_multi(
    hue_knots: list[float],
    chroma_knots: list[float],
    tone_start: float = 0.2586206810344833,
    tone_end: float = 0.9655172091954044,
    n: int = 256,
    *,
    luminance_lock: bool = True,
) -> list[str]:
    """빛 계열 관례: t=0=어두움(저값) → t=1=밝음. knot은 pchip으로 C1 통과."""
    hk = unwrap_hues(hue_knots)
    nk = len(hk)
    tk = [i / (nk - 1) for i in range(nk)]

    def at(fraction: float) -> Rgb:
        hue = pchip(tk, hk, fraction) % 360
        chroma = pchip(tk, chroma_knots, fraction)
        tone_value = tone_start + (tone_end - tone_start) * fraction
        chroma = min(chroma, _max_chroma(hue, tone_value) * GAMUT_CHROMA_FRAC)
        return _render_at_tone(
            tone_value, chroma, hue, luminance_lock=luminance_lock
        )

    return render(at, n=n)


def diverging_pair(
    hex_a: str,
    hex_b: str,
    tone_end: float,
    tone_center: float = 0.9655172091954044,
    gamma: float = 0.85,
    half: int = 32,
    *,
    luminance_lock: bool = True,
) -> list[str]:
    """Render a symmetric odd-sample diverging pair around a bright center.

    양극 정체성은 dc.{a}6/dc.{b}6 hex의 OKLCH chroma·hue에서 유도한다.
    포인트별 독립 솔브(등화 없음)라 hex 직접 생성으로 충분하다.

    Notes
    -----
    Unlike ``seq_single``, ``seq_multi`` and ``cyclic_twilight``, this renderer
    applies **no** ``max_chroma_at_tone`` cap. Requested chroma near the
    saturated ends therefore leaves the sRGB gamut and is silently reduced by
    the gamut mapper instead of being clamped beforehand.

    This asymmetry is deliberate and load-bearing: adding the cap here changes
    approved shipped output, darkening the dark arm of the eleven diverging
    colormaps by up to 6 dEok. Do not "fix" it without an accepted colour
    change (ADR 0001, appendix A2). ``tests/test_shipped_colors_hash.py`` will
    fail if this is altered.
    """
    arms: list[list[str]] = []
    for src in (hex_a, hex_b):
        _, maximum_chroma, hue = _oklch_from_hex(src)
        points: list[str] = []
        for i in range(half):
            fraction = i / (half - 1)  # 0=끝(포화) → 1=중심(밝음)
            tone_value = tone_end + (tone_center - tone_end) * fraction
            chroma = maximum_chroma * (1 - fraction) ** gamma + 0.004 * fraction
            points.append(
                _hex_from_rgb(
                    _render_at_tone(
                        tone_value, chroma, hue, luminance_lock=luminance_lock
                    )
                )
            )
        arms.append(points)
    return arms[0] + arms[1][:-1][::-1]


def cyclic_hue(
    tone: float = 0.6724137706896566,
    n: int = 256,
    *,
    luminance_lock: bool = True,
) -> list[str]:
    """등명도 색상환 — hue 균등(색상환은 hue가 지각축)."""
    safe_chroma = min(_max_chroma(hue, tone) for hue in range(0, 360, 5)) * 0.95
    return [
        _hex_from_rgb(
            _render_at_tone(
                tone,
                safe_chroma,
                (i / n * 360) % 360,
                luminance_lock=luminance_lock,
            )
        )
        for i in range(n)
    ]


def cyclic_twilight(
    hue_a: float, hue_b: float, n: int = 256, *, luminance_lock: bool = True
) -> list[str]:
    """이중 로브 cyclic — 밝은 이음매 → A팔 → 어두운 중심 → B팔 → 이음매."""
    seam_tone = 0.939655141091956
    center_tone = 0.29310343850574777

    def at(fraction: float) -> Rgb:
        if fraction <= 0.5:
            progress, hue, maximum_chroma = fraction / 0.5, hue_a, 0.15
        else:
            progress = 1 - (fraction - 0.5) / 0.5
            hue = hue_b
            maximum_chroma = 0.16
        tone_value = (
            center_tone
            if progress == 1.0
            else seam_tone + (center_tone - seam_tone) * progress
        )
        chroma = maximum_chroma * math.sin(math.pi * progress) ** 0.85
        chroma = min(chroma, _max_chroma(hue % 360, tone_value) * 0.96)
        return _render_at_tone(
            tone_value, chroma, hue % 360, luminance_lock=luminance_lock
        )

    return render(at, n=n, closed=True)


def compile_cmaps(
    palette: dict[str, list[str]], n: int = 256, *, luminance_lock: bool = True
) -> dict[str, list[str]]:
    """43-map catalog — keys match SSOT swatches_32 public names."""
    anchors = ANCHORS
    cm: dict[str, list[str]] = {}

    # 단일색 20 (family명 그대로)
    for fam in FAMILIES:
        cm[fam] = seq_single(fam, n=n, luminance_lock=luminance_lock)
    cm["gray"] = seq_gray(n=n, luminance_lock=luminance_lock)

    # 멀티휴 9 (자연광 장면 — knot·chroma·L 범위는 스펙 §9 확정값)
    multi: dict[str, tuple[list[float], list[float], float, float]] = {
        "aurora": (
            [
                anchors["violet"],
                anchors["indigo"],
                anchors["sky"],
                anchors["teal"],
                anchors["lime"],
                anchors["yellow"],
            ],
            [0.08, 0.11, 0.13, 0.15, 0.16, 0.13],
            0.2586206810344833,
            0.9655172091954044,
        ),
        "afterglow": (
            [
                anchors["violet"],
                anchors["purple"],
                anchors["pink"],
                anchors["red"],
                anchors["orange"],
            ],
            [0.10, 0.17, 0.20, 0.19, 0.16],
            0.2758620597701155,
            0.9310344517241399,
        ),
        "blaze": (
            [
                anchors["violet"],
                anchors["pink"],
                anchors["red"],
                anchors["orange"],
                anchors["yellow"],
            ],
            [0.09, 0.18, 0.20, 0.18, 0.13],
            0.2413793022988511,
            0.9482758304597722,
        ),
        "lava": (
            [
                anchors["red"],
                anchors["orange"],
                anchors["amber"],
                anchors["yellow"],
            ],
            [0.15, 0.18, 0.16, 0.13],
            0.2413793022988511,
            0.9568965198275883,
        ),
        "lagoon": (
            [
                anchors["blue"],
                anchors["cyan"],
                anchors["teal"],
                anchors["green"],
                anchors["lime"],
            ],
            [0.10, 0.12, 0.14, 0.17, 0.15],
            0.2586206810344833,
            0.9655172091954044,
        ),
        "glacier": (
            [
                anchors["indigo"],
                anchors["blue"],
                anchors["sky"],
                anchors["cyan"],
                anchors["teal"],
            ],
            [0.10, 0.15, 0.14, 0.12, 0.12],
            0.2586206810344833,
            0.9655172091954044,
        ),
        "canopy": (
            [
                anchors["teal"],
                anchors["green"],
                anchors["lime"],
                anchors["yellow"],
            ],
            [0.09, 0.14, 0.16, 0.13],
            0.2586206810344833,
            0.9655172091954044,
        ),
        "haze": (
            [
                anchors["blue"],
                anchors["sky"],
                anchors["green"],
                anchors["yellow"],
            ],
            [0.05, 0.07, 0.09, 0.13],
            0.2586206810344833,
            0.9655172091954044,
        ),
        "iris": (
            [
                anchors["violet"],
                anchors["blue"],
                anchors["cyan"],
                anchors["green"],
                anchors["yellow"],
                anchors["orange"],
            ],
            [0.14, 0.15, 0.11, 0.15, 0.16, 0.16],
            0.2586206810344833,
            0.939655141091956,
        ),
    }
    for name, (hue_knots, chroma_knots, start_tone, end_tone) in multi.items():
        cm[name] = seq_multi(
            hue_knots,
            chroma_knots,
            tone_start=start_tone,
            tone_end=end_tone,
            n=n,
            luminance_lock=luminance_lock,
        )

    # diverging 11 (저값_고값 pair — 양극 = dc.{a}6/dc.{b}6)
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
        tone_end: float,
        tone_center: float = 0.9655172091954044,
        gamma: float = 0.85,
    ) -> list[str]:
        return _resample(
            diverging_pair(
                palette[fa][6],
                palette[fb][6],
                tone_end=tone_end,
                tone_center=tone_center,
                gamma=gamma,
                half=half,
                luminance_lock=luminance_lock,
            ),
            n,
        )

    cm["blue_red"] = dv(
        "blue",
        "red",
        tone_end=(
            _tone_from_hex(palette["blue"][6])
            + _tone_from_hex(palette["red"][6])
        )
        / 2.0,
    )
    for first, second, endpoint_tone in (
        ("blue", "orange", 0.4999999833333344),
        ("teal", "rose", 0.5172413620689666),
        ("green", "purple", 0.4827586045977022),
        ("purple", "orange", 0.4999999833333344),
        ("cyan", "red", 0.5172413620689666),
        ("teal", "amber", 0.5172413620689666),
        ("violet", "lime", 0.4999999833333344),
        ("indigo", "amber", 0.4827586045977022),
        ("gray", "blue", 0.4999999833333344),
        ("gray", "red", 0.4999999833333344),
    ):
        cm[f"{first}_{second}"] = dv(first, second, tone_end=endpoint_tone)

    # cyclic 3 (원형 빛 현상)
    def hue_of(fam: str) -> float:
        return _oklch_from_hex(palette[fam][6])[2]

    cm["hue"] = cyclic_hue(n=n, luminance_lock=luminance_lock)
    cm["halo"] = cyclic_twilight(
        hue_of("blue"), hue_of("red"), n=n, luminance_lock=luminance_lock
    )
    cm["corona"] = cyclic_twilight(
        hue_of("teal"), hue_of("orange"), n=n, luminance_lock=luminance_lock
    )
    return cm
