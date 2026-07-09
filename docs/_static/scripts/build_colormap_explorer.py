#!/usr/bin/env python3
"""Build the interactive continuous-colormap explorer fragment.

Sibling of ``build_categorical_explorer.py``; same architecture — Python
computes the 46-map payload from the color SSOT and injects it into an HTML
fragment (CSS in ``dartwork-design.css`` + vanilla JS), embedded by
``docs/color_system/colormaps.md`` via MyST ``{raw} html :file:``.

The payload holds, per map: a 64-stop hex ramp (the true 0-100% range, used
by the gradient strip and code example), a chroma-clipped 64-stop ``demo``
ramp (used only by the demo plots so no demo swatch desaturates toward black
— see ``_vivid_cutoff``), the per-map ``vivid_cutoff`` index, chip metrics,
and taxonomy grouping. The 16 demo plots generate their own geometry in JS
(like the categorical explorer).

Regenerate::

    python3 docs/_static/scripts/build_colormap_explorer.py
"""

from __future__ import annotations

import itertools
import json
import math
import re
import statistics
from pathlib import Path

from dartwork_mpl.colors._generated import CMAPS_256
from dartwork_mpl.colors._metrics import (
    cvd_rgb,
    de2000_hex,
    de2000_rgb,
    lab_from_rgb,
    lab_l_hex,
    lab_l_rgb,
    rgb_from_hex,
)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
OUT = SCRIPT_DIR.parent / "colormap_explorer.html"

# ── taxonomy (verified against CMAPS_256: 20 / 10 / 15 / 1 = 46) ───────────
SEQUENTIAL = [
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
    "gray",
]
MULTI_HUE = [
    "afterglow",
    "aurora",
    "blaze",
    "canopy",
    "coast",
    "glacier",
    "haze",
    "iris",
    "lagoon",
    "lava",
]
DIVERGING = [
    "blue_red",
    "blue_red_deep",
    "blue_red_soft",
    "blue_orange",
    "cyan_red",
    "teal_amber",
    "teal_rose",
    "indigo_amber",
    "green_purple",
    "purple_orange",
    "violet_lime",
    "gray_blue",
    "gray_red",
    "corona",
    "halo",
]
CYCLIC = ["hue"]
GROUPS = [
    ("Sequential", SEQUENTIAL),
    ("Multi-hue", MULTI_HUE),
    ("Diverging", DIVERGING),
    ("Cyclic", CYCLIC),
]

# 16 demo plots spanning raster fields, strokes, glyph grids, profiles, and mesh.
DEMO_LIBRARY = [
    ("heatmap", "Heatmap"),
    ("contours", "Contours"),
    ("isolines", "Isolines"),
    ("scatter", "Scatter"),
    ("signal", "Signal"),
    ("streamlines", "Streamlines"),
    ("hexbin", "Hexbin"),
    ("terrain", "Terrain"),
    ("bars", "Bars"),
    ("mosaic", "Mosaic"),
    ("lines", "Lines"),
    ("network", "Network"),
    ("ridgeline", "Ridgeline"),
    ("quiver", "Quiver"),
    ("polar_heat", "Polar heat"),
    ("waffle", "Waffle"),
]
# Default 3x3 selection: all five demos changed in this expansion round plus
# all four added grammars. This keeps the first view balanced across smooth
# raster, banded raster, flow strokes, series strokes, mesh, profiles, arrows,
# cyclic polar cells, and discrete tiles.
DEFAULT_9 = [
    "heatmap",
    "contours",
    "streamlines",
    "lines",
    "network",
    "ridgeline",
    "quiver",
    "polar_heat",
    "waffle",
]
DEFAULT_6 = [
    "heatmap",
    "contours",
    "streamlines",
    "lines",
    "network",
    "polar_heat",
]
DEFAULT_4 = ["heatmap", "contours", "streamlines", "polar_heat"]

LEVEL_VALUES = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 0]
FIELD_PARAMS = {
    "base": {"x": 0.32, "y": -0.2},
    "bumps": [
        {"cx": 0.30, "cy": 0.34, "sx": 0.22, "sy": 0.26, "amp": 1.10},
        {"cx": 0.72, "cy": 0.68, "sx": 0.20, "sy": 0.24, "amp": 0.82},
    ],
}
CONTOUR_FIELD_PARAMS = {
    "saddle": {"x": 0.58, "y": 0.48, "xx": 1.12, "yy": -0.92, "xy": 0.54},
    "ridge": {"cx": 0.68, "cy": 0.30, "sx": 0.16, "sy": 0.36, "amp": 1.10},
    "waves": {"x": 1.35, "y": 0.90, "amp": 0.16},
}
CYLINDER_FLOW_PARAMS = {"cx": 0.35, "cy": 0.50, "r": 0.18, "aspect": 1.6}
STREAMLINE_SEEDS = 28
VIEWBOX_WIDTH = 160.0
VIEWBOX_HEIGHT = 100.0
ISOLINE_GRID_COLS = 221
ISOLINE_GRID_ROWS = 141
ISOLINE_SIMPLIFY_EPSILON = 0.15
CURVE_ANGLE_GATE_DEGREES = 20.0
STREAMLINE_ARC_SPACING = 1.65
LINE_SERIES_SAMPLES = 201
HISTOGRAM_BINS = 28
RIDGELINE_ROWS = 11
RIDGELINE_GAP = 8.6
RIDGELINE_PROFILE_SAMPLES = 141
QUIVER_ROWS = 7
QUIVER_COLS = 10
QUIVER_MIN_LEN = 7.2
QUIVER_MAX_LEN = 13.8
QUIVER_HEAD_LEN = 4.6

# ── per-map English copy (no Hangul) ──────────────────────────────────────
FAMILY_REGISTER = {
    "red": "risk, severity, and alert",
    "rose": "warm editorial and recency",
    "coral": "human-scale warmth and moderate urgency",
    "tangerine": "high-attention warning and threshold",
    "orange": "operational caution and warm emphasis",
    "amber": "stable golden threshold and context",
    "yellow": "luminous highlight and attention field",
    "lime": "fresh biological and ecological",
    "green": "growth, health, progress, and success",
    "teal": "calm house analytical",
    "cyan": "cool technical secondary",
    "sky": "airy background quantity",
    "blue": "primary analytical",
    "cobalt": "institutional deep-blue",
    "indigo": "formal corporate and comparison",
    "violet": "premium exploratory",
    "purple": "expressive secondary",
    "fuchsia": "vivid editorial accent",
    "pink": "soft approachable emphasis",
    "gray": "neutral magnitude and reference",
}
MULTI_INTENT = {
    "afterglow": "Afterglow moves from violet shadow into warm peach light. Use it for scalar intensity fields that should feel atmospheric while still preserving ordered magnitude.",
    "aurora": "Aurora is the general-purpose multi-hue light ramp: violet, blue, green, and pale gold move through one ordered scalar sequence. It is the default heatmap map.",
    "blaze": "Blaze runs through ember, orange, and hot yellow for heat, activity, density, and other positive-only quantities that need immediate visual force.",
    "canopy": "Canopy shifts through shaded green into sunlit yellow-green, giving ecological and terrain-like fields a natural scalar voice.",
    "coast": "Coast joins a blue water ramp to a green land ramp, making a natural break readable while distance on either side still carries magnitude.",
    "glacier": "Glacier moves through deep blue, ice cyan, and pale cold highlights for frozen, precise, or technical scalar fields.",
    "haze": "Haze is a low-chroma multi-hue ramp for atmospheric gradients, background fields, and uncertainty surfaces that should stay quiet; it holds the largest CVD margin.",
    "iris": "Iris crosses violet, blue, and cyan in a controlled editorial register for continuous measurements that need more character than blue.",
    "lagoon": "Lagoon moves through deep teal and blue-green into clear tropical light for water, climate, and calm operational maps.",
    "lava": "Lava climbs from dark red through molten orange and yellow-white, matching the familiar thermal metaphor for heat, risk, load, or density.",
}
DIVERGING_INTENT = {
    "blue_red": "Blue Red is the canonical signed scale: blue for negative, red for positive, and a pale center for zero.",
    "blue_red_deep": "Blue Red Deep keeps the same signed semantics while pushing both poles darker and stronger for dense matrices and small cells.",
    "blue_red_soft": "Blue Red Soft is the gentler signed scale for editorial or presentation contexts where saturation should stay quiet.",
    "blue_orange": "Blue Orange separates cool negative from warm positive on a familiar colorblind-friendlier axis.",
    "cyan_red": "Cyan Red gives negative values a bright technical cyan and positive values a clear red pole for anomaly fields.",
    "teal_amber": "Teal Amber is the house signed scale, with teal below zero and amber above zero through a pale center.",
    "teal_rose": "Teal Rose pairs a calm negative pole with a softer warm positive pole when red would feel too alarmed.",
    "indigo_amber": "Indigo Amber gives signed data a formal cool pole and a high-visibility warm pole for institutional reports.",
    "green_purple": "Green Purple uses an uncommon signed axis when blue, red, or amber already carry separate meaning.",
    "purple_orange": "Purple Orange balances an expressive cool pole against a warm positive pole for editorial signed comparisons.",
    "violet_lime": "Violet Lime is a high-contrast signed map where polarity should remain obvious at small sizes.",
    "gray_blue": "Gray Blue anchors one side in neutral gray and the other in blue when only one direction should feel chromatic.",
    "gray_red": "Gray Red anchors one side in neutral gray and the other in red for one-sided alert semantics on a centered scale.",
    "corona": "Corona is a dark-center diverging map with pale green and orange ends around a dark neutral middle; it suits dark-background figures or cases where extremes should glow.",
    "halo": "Halo is a dark-center diverging map with pale blue and red ends around a dark neutral middle; it suits dark-background figures or cases where extremes should glow.",
}
CYCLIC_INTENT = {
    "hue": "Hue is the cyclic angle map: it holds one flat lightness so the first and last colors meet, letting phase, direction, and orientation wrap without a visible break."
}
KIND_RECIPE = {
    "family": "Single-hue family ramp sampled as a continuous colormap with an ordered lightness ladder.",
    "multi": "Multi-hue sequential ramp: hue moves for character while lightness carries scalar order.",
    "diverging": "Two arms meet at a neutral center, built for signed values around a meaningful baseline.",
    "cyclic": "Isoluminant hue circle with matched endpoints for angular and phase data.",
}
KIND_GOOD_FOR = {
    "family": "Ordered magnitude, grayscale-safe scalar legends, and related-series samples.",
    "multi": "Continuous magnitude that benefits from hue motion while preserving a clear scalar read.",
    "diverging": "Signed values with a meaningful zero or baseline; grayscale shows magnitude, not sign.",
    "cyclic": "Phase, angle, orientation, compass direction, and other circular values with no endpoint.",
}


# ── helpers ───────────────────────────────────────────────────────────────
def _display_name(key: str) -> str:
    return key.replace("_", " ").title()


def _kind_for(key: str) -> str:
    if key in SEQUENTIAL:
        return "family"
    if key in MULTI_HUE:
        return "multi"
    if key in DIVERGING:
        return "diverging"
    if key in CYCLIC:
        return "cyclic"
    raise KeyError(key)


def _intent_for(key: str) -> str:
    kind = _kind_for(key)
    if kind == "family":
        return (
            f"Single-hue {_display_name(key)} ramp for ordered data in a "
            f"{FAMILY_REGISTER[key]} voice. Use it when magnitude should read "
            "through one hue family and remain legible in grayscale."
        )
    if kind == "multi":
        return MULTI_INTENT[key]
    if kind == "diverging":
        return DIVERGING_INTENT[key]
    return CYCLIC_INTENT[key]


def _chroma(hex_color: str) -> float:
    _l, a, b = lab_from_rgb(rgb_from_hex(hex_color))
    return math.hypot(a, b)


def _lab_l_c(hex_color: str) -> tuple[float, float]:
    l_value, a_value, b_value = lab_from_rgb(rgb_from_hex(hex_color))
    return l_value, math.hypot(a_value, b_value)


def _subsample_64(hexes: tuple[str, ...]) -> list[str]:
    if len(hexes) != 256:
        raise AssertionError(f"expected 256 stops, got {len(hexes)}")
    idx = list(range(0, 256, 4))
    idx[-1] = 255
    return [hexes[i] for i in idx]


def _resample64(stops: list[str], start: int, end: int) -> list[str]:
    """Resample stops[start..end] (inclusive) back to 64 entries."""
    if not 0 <= start <= end <= len(stops) - 1:
        raise AssertionError(f"bad resample range: {start}..{end}")
    if start == end:
        return [stops[start]] * 64
    return [stops[round(start + i * (end - start) / 63)] for i in range(64)]


def _vivid_cutoff(stops64: list[str], kind: str) -> dict | None:
    """Chroma-based dark-tail clip (item 1).

    Walk from the peak-chroma index toward the dark-anchor end and take the
    LAST index whose chroma still holds >= 0.6 x peak. Demos map the most
    extreme data value onto this index instead of the true endpoint, so the
    darkest demo swatch stays a saturated dark hue rather than a near-black
    mush. Diverging / cyclic maps keep their true endpoints (their extremes
    are already saturated, or intentionally neutral — see the self-check).
    """
    if kind in ("diverging", "cyclic"):
        return None
    cs = [_chroma(h) for h in stops64]
    peak_i = max(range(len(cs)), key=lambda i: cs[i])
    peak = cs[peak_i]
    thr = 0.6 * peak
    dark_hi = lab_l_hex(stops64[-1]) < lab_l_hex(stops64[0])
    idx = peak_i
    if dark_hi:
        while idx + 1 <= len(cs) - 1 and cs[idx + 1] >= thr:
            idx += 1
    else:
        while idx - 1 >= 0 and cs[idx - 1] >= thr:
            idx -= 1
    dark_end = len(cs) - 1 if dark_hi else 0
    if idx == dark_end and len(cs) > 1:
        # Some dark-start maps, and some L*-refined variants, are already
        # above the chroma threshold at the dark endpoint. Still make the demo
        # range an actual clipped preview by stepping one stop toward the peak.
        idx = idx - 1 if dark_hi else idx + 1
    return {
        "idx": idx,
        "dark_hi": dark_hi,
        "peak_c": round(peak, 2),
        "cutoff_c": round(cs[idx], 2),
    }


def _demo_stops(stops64: list[str], cut: dict | None) -> list[str]:
    """The clipped 64-stop ramp the demo plots sample (item 1 step 4)."""
    if cut is None:
        return list(stops64)
    if cut["dark_hi"]:  # dark at the high index -> keep [0 .. idx]
        return _resample64(stops64, 0, cut["idx"])
    return _resample64(stops64, cut["idx"], 63)  # dark at low index


def _monotone(profile: list[float], tol: float = 0.4) -> bool:
    inc = all(b >= a - tol for a, b in itertools.pairwise(profile))
    dec = all(b <= a + tol for a, b in itertools.pairwise(profile))
    return inc or dec


def _delta_e_cv(stops: list[str]) -> float:
    steps = [de2000_hex(a, b) for a, b in itertools.pairwise(stops)]
    mean = statistics.fmean(steps) if steps else 0.0
    return statistics.pstdev(steps) / mean if mean > 1e-9 else 0.0


def _cvd_worst(stops: list[str]) -> tuple[float, bool]:
    deciles = [stops[round(i * (len(stops) - 1) / 10)] for i in range(11)]
    worst = math.inf
    monotone_all = True
    for mode in ("deutan", "protan", "tritan"):
        dec_rgb = [cvd_rgb(rgb_from_hex(h), mode) for h in deciles]
        distances = [de2000_rgb(a, b) for a, b in itertools.pairwise(dec_rgb)]
        worst = min(worst, min(distances))
        sim = [lab_l_rgb(cvd_rgb(rgb_from_hex(h), mode)) for h in stops]
        monotone_all = monotone_all and _monotone(sim)
    return worst, monotone_all


def _chip(cls: str, label: str, num: str, tip: str) -> dict:
    return {"cls": cls, "label": label, "num": num, "tip": tip}


def _chips_for(key: str, stops: list[str]) -> list[dict]:
    kind = _kind_for(key)
    profile = [lab_l_hex(h) for h in stops]
    l_first, l_last = profile[0], profile[-1]
    l_span = max(profile) - min(profile)
    chips: list[dict] = []

    if kind in ("family", "multi"):
        cv = _delta_e_cv(stops)
        mono = _monotone(profile)
        cls = "ok" if (mono and cv <= 0.5) else ("mid" if mono else "bad")
        chips.append(
            _chip(
                cls,
                "Uniform",
                f"L* {l_first:.0f}->{l_last:.0f}",
                f"Monotone lightness carries order; adjacent-step Delta E00 CV is "
                f"{cv:.2f}, so equal data steps stay close to equal perceived steps.",
            )
        )
        chips.append(
            _chip(
                "ok" if l_span >= 40 else "bad",
                "B&W",
                f"span {l_span:.0f}",
                "Black-and-white readability uses L* span >= 40 as the print-clean "
                "threshold; lightness alone carries order in grayscale.",
            )
        )
        worst, mono_cvd = _cvd_worst(stops)
        chips.append(
            _chip(
                "ok"
                if (mono_cvd and worst >= 3)
                else ("mid" if worst >= 2 else "bad"),
                "CVD",
                f"min Delta E {worst:.1f}",
                "Order is carried by lightness, which color-vision deficiency does "
                f"not remove; worst simulated adjacent-step distance stays {worst:.1f}.",
            )
        )
    elif kind == "diverging":
        center = profile[len(profile) // 2]
        balance = abs(abs(center - l_first) - abs(center - l_last))
        chips.append(
            _chip(
                "ok" if balance <= 3 else ("mid" if balance <= 6 else "bad"),
                "Balanced",
                f"Delta L* {balance:.1f}",
                "Left and right arms travel a similar lightness distance from the "
                "neutral point, so magnitude reads evenly on both sides.",
            )
        )
        dark_center = center < min(l_first, l_last)
        headline = math.floor(center) if dark_center else round(center)
        chips.append(
            _chip(
                "info",
                "Center",
                f"{'dark' if dark_center else 'pale'} L* {headline:.0f}",
                "Dark-center diverging: pale ends and a dark middle suit "
                "dark-background figures or cases where extremes should glow."
                if dark_center
                else "Pale-center diverging: the neutral point recedes on light "
                "backgrounds while both signed extremes gain contrast.",
            )
        )
        chips.append(
            _chip(
                "mid",
                "B&W",
                "magnitude only",
                "In grayscale this family shows distance from the center, not "
                "which sign the value has.",
            )
        )
    else:  # cyclic
        endpoint_de = de2000_hex(stops[0], stops[-1])
        l_mean = statistics.fmean(profile)
        chips.append(
            _chip(
                "ok"
                if endpoint_de <= 2
                else ("mid" if endpoint_de <= 5 else "bad"),
                "Seamless",
                f"Delta E {endpoint_de:.1f}",
                "First and last stops match closely, so angle and phase data wrap "
                "without a visible endpoint break.",
            )
        )
        chips.append(
            _chip(
                "info",
                "Isoluminant",
                f"L* {l_mean:.0f} flat",
                "Hue-only encoding is intentional and becomes invisible in "
                "grayscale; pair with a sequential map when print matters.",
            )
        )

    if key == "coast":
        chips.append(
            _chip(
                "info",
                "Segmented",
                "2 ramps",
                "Two joined sequential segments meet at the midpoint seam, made "
                "for data with a natural bathymetry/topography break.",
            )
        )
    return chips


def _variant(key: str, stops: list[str]) -> dict:
    kind = _kind_for(key)
    cut = _vivid_cutoff(stops, kind)
    return {
        "stops": stops,
        "demo": _demo_stops(stops, cut),
        "vivid_cutoff": (cut["idx"] if cut else None),
        "chips": _chips_for(key, stops),
    }


def _self_check_row(key: str, variant: dict) -> dict:
    """Item 1 step 6: darkest demo swatch chroma vs the map's true peak."""
    peak_full = max(_chroma(h) for h in CMAPS_256[key])
    darkest = min(variant["demo"], key=lambda h: _lab_l_c(h)[0])
    dark_l, dark_c = _lab_l_c(darkest)
    return {
        "map": key,
        "group": _kind_for(key),
        "peak_c": round(peak_full, 2),
        "dark_hex": darkest,
        "dark_l": round(dark_l, 2),
        "dark_c": round(dark_c, 2),
        "ratio": round(dark_c / peak_full, 3) if peak_full > 1e-9 else 0.0,
    }


def _demo_field(x: float, y: float) -> float:
    value = FIELD_PARAMS["base"]["x"] * x + FIELD_PARAMS["base"]["y"] * y
    for bump in FIELD_PARAMS["bumps"]:
        value += bump["amp"] * math.exp(
            -(
                ((x - bump["cx"]) / bump["sx"]) ** 2
                + ((y - bump["cy"]) / bump["sy"]) ** 2
            )
        )
    return value


def _contour_field(x: float, y: float) -> float:
    saddle = CONTOUR_FIELD_PARAMS["saddle"]
    ridge = CONTOUR_FIELD_PARAMS["ridge"]
    waves = CONTOUR_FIELD_PARAMS["waves"]
    dx = x - saddle["x"]
    dy = y - saddle["y"]
    value = (
        saddle["xx"] * dx * dx + saddle["yy"] * dy * dy + saddle["xy"] * dx * dy
    )
    value += ridge["amp"] * math.exp(
        -(
            ((x - ridge["cx"]) / ridge["sx"]) ** 2
            + ((y - ridge["cy"]) / ridge["sy"]) ** 2
        )
    )
    value += waves["amp"] * math.sin(
        math.tau * (waves["x"] * x - waves["y"] * y)
    )
    return value


def _field_values(cols: int, rows: int) -> list[float]:
    return [
        _demo_field((c + 0.5) / cols, (r + 0.5) / rows)
        for r in range(rows)
        for c in range(cols)
    ]


def _contour_values(cols: int, rows: int) -> list[float]:
    return [
        _contour_field((c + 0.5) / cols, (r + 0.5) / rows)
        for r in range(rows)
        for c in range(cols)
    ]


def _signal_value(i: int, n: int) -> float:
    t = i / (n - 1)
    return (
        0.5
        + 0.26 * math.sin(t * math.tau * 2.1)
        + 0.15 * math.sin(t * math.tau * 5.3 + 0.8)
        + 0.07 * math.cos(t * math.tau * 9)
    )


def _flow_vec(x: float, y: float) -> tuple[float, float]:
    dx = x - 0.52
    dy = y - 0.50
    r2 = dx * dx + dy * dy + 0.045
    vx = -0.070 * dy / r2 + 0.28
    vy = 0.070 * dx / r2 - 0.02
    for cx, cy, strength in ((0.20, 0.80, 0.050), (0.86, 0.28, -0.060)):
        sx = x - cx
        sy = y - cy
        d2 = sx * sx + sy * sy + 0.030
        vx += strength * sx / d2
        vy += strength * sy / d2
    vx += 0.16 * math.sin(math.tau * (y * 0.92 + 0.10))
    vy += 0.13 * math.cos(math.tau * (x * 0.86 - 0.16))
    return vx, vy


def _flow_dir(x: float, y: float) -> tuple[float, float]:
    vx, vy = _flow_vec(x, y)
    mag = math.hypot(vx, vy) or 1.0
    return vx / mag, vy / mag


def _rk4_step(x: float, y: float, h: float) -> tuple[float, float]:
    k1x, k1y = _flow_dir(x, y)
    k2x, k2y = _flow_dir(x + 0.5 * h * k1x, y + 0.5 * h * k1y)
    k3x, k3y = _flow_dir(x + 0.5 * h * k2x, y + 0.5 * h * k2y)
    k4x, k4y = _flow_dir(x + h * k3x, y + h * k3y)
    return (
        x + h * (k1x + 2 * k2x + 2 * k3x + k4x) / 6,
        y + h * (k1y + 2 * k2y + 2 * k3y + k4y) / 6,
    )


def _cylinder_xy(x: float, y: float) -> tuple[float, float]:
    p = CYLINDER_FLOW_PARAMS
    return (x - p["cx"]) * p["aspect"], y - p["cy"]


def _inside_cylinder(x: float, y: float, pad: float = 0.0) -> bool:
    px, py = _cylinder_xy(x, y)
    radius = CYLINDER_FLOW_PARAMS["r"] + pad
    return px * px + py * py <= radius * radius


def _cylinder_velocity_physical(x: float, y: float) -> tuple[float, float]:
    px, py = _cylinder_xy(x, y)
    r2 = px * px + py * py
    a2 = CYLINDER_FLOW_PARAMS["r"] ** 2
    if r2 <= a2:
        return 0.0, 0.0
    r4 = r2 * r2
    ux = 1.0 - a2 * (px * px - py * py) / r4
    uy = -2.0 * a2 * px * py / r4
    return ux, uy


def _cylinder_vec(x: float, y: float) -> tuple[float, float]:
    ux, uy = _cylinder_velocity_physical(x, y)
    return ux / CYLINDER_FLOW_PARAMS["aspect"], uy


def _cylinder_speed(x: float, y: float) -> float:
    return math.hypot(*_cylinder_velocity_physical(x, y))


def _cylinder_angle(x: float, y: float) -> float:
    ux, uy = _cylinder_velocity_physical(x, y)
    return (math.atan2(uy, ux) + math.pi) / math.tau


def _cylinder_dir(x: float, y: float) -> tuple[float, float]:
    vx, vy = _cylinder_vec(x, y)
    mag = math.hypot(vx, vy)
    if mag <= 1e-12:
        return 1.0, 0.0
    return vx / mag, vy / mag


def _cylinder_rk4_step(x: float, y: float, h: float) -> tuple[float, float]:
    k1x, k1y = _cylinder_dir(x, y)
    k2x, k2y = _cylinder_dir(x + 0.5 * h * k1x, y + 0.5 * h * k1y)
    k3x, k3y = _cylinder_dir(x + 0.5 * h * k2x, y + 0.5 * h * k2y)
    k4x, k4y = _cylinder_dir(x + h * k3x, y + h * k3y)
    return (
        x + h * (k1x + 2 * k2x + 2 * k3x + k4x) / 6,
        y + h * (k1y + 2 * k2y + 2 * k3y + k4y) / 6,
    )


def _view_point(x: float, y: float) -> tuple[float, float]:
    return x * VIEWBOX_WIDTH, (1.0 - y) * VIEWBOX_HEIGHT


def _norm_from_view(point: tuple[float, float]) -> tuple[float, float]:
    return point[0] / VIEWBOX_WIDTH, 1.0 - point[1] / VIEWBOX_HEIGHT


def _resample_polyline(
    points: list[tuple[float, float]], spacing: float
) -> list[tuple[float, float]]:
    if len(points) < 2:
        return points[:]

    out = [points[0]]
    remaining = spacing
    prev = points[0]
    for target in points[1:]:
        dx = target[0] - prev[0]
        dy = target[1] - prev[1]
        seg_len = math.hypot(dx, dy)
        if seg_len <= 1e-12:
            prev = target
            continue
        while seg_len >= remaining:
            t = remaining / seg_len
            next_point = (prev[0] + dx * t, prev[1] + dy * t)
            out.append(next_point)
            prev = next_point
            dx = target[0] - prev[0]
            dy = target[1] - prev[1]
            seg_len = math.hypot(dx, dy)
            remaining = spacing
        remaining -= seg_len
        prev = target

    if (
        math.hypot(out[-1][0] - points[-1][0], out[-1][1] - points[-1][1])
        > 1e-6
    ):
        out.append(points[-1])
    return out


def _point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    denom = dx * dx + dy * dy
    if denom <= 1e-12:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / denom
    t = max(0.0, min(1.0, t))
    px = start[0] + dx * t
    py = start[1] + dy * t
    return math.hypot(point[0] - px, point[1] - py)


def _douglas_peucker_open(
    points: list[tuple[float, float]], epsilon: float
) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points[:]
    max_distance = -1.0
    split_index = 0
    for idx, point in enumerate(points[1:-1], start=1):
        distance = _point_segment_distance(point, points[0], points[-1])
        if distance > max_distance:
            max_distance = distance
            split_index = idx
    if max_distance > epsilon:
        left = _douglas_peucker_open(points[: split_index + 1], epsilon)
        right = _douglas_peucker_open(points[split_index:], epsilon)
        return left[:-1] + right
    return [points[0], points[-1]]


def _same_view_point(
    a: tuple[float, float], b: tuple[float, float], tol: float = 1e-6
) -> bool:
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol


def _simplify_polyline(
    points: list[tuple[float, float]], epsilon: float
) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points[:]
    if _same_view_point(points[0], points[-1]) and len(points) > 4:
        ring = points[:-1]
        anchor = max(
            range(len(ring)),
            key=lambda idx: math.hypot(
                ring[idx][0] - ring[0][0], ring[idx][1] - ring[0][1]
            ),
        )
        ordered = ring[anchor:] + ring[: anchor + 1]
        simplified = _douglas_peucker_open(ordered, epsilon)
        if not _same_view_point(simplified[0], simplified[-1]):
            simplified.append(simplified[0])
        return simplified
    return _douglas_peucker_open(points, epsilon)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def _turning_angle_distribution(
    paths: list[list[tuple[float, float]]],
) -> dict[str, float]:
    path_maxima: list[float] = []
    for points in paths:
        angles = []
        for a, b, c in zip(points, points[1:], points[2:], strict=False):
            v1 = (b[0] - a[0], b[1] - a[1])
            v2 = (c[0] - b[0], c[1] - b[1])
            n1 = math.hypot(*v1)
            n2 = math.hypot(*v2)
            if n1 <= 1e-9 or n2 <= 1e-9:
                continue
            dot = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
            angles.append(math.degrees(math.acos(max(-1.0, min(1.0, dot)))))
        if angles:
            path_maxima.append(max(angles))
    return {
        "p50": round(_percentile(path_maxima, 0.50), 2),
        "p95": round(_percentile(path_maxima, 0.95), 2),
        "max": round(max(path_maxima, default=0.0), 2),
    }


def _streamline_seed_points() -> list[tuple[float, float]]:
    return [
        (0.0, (r + 0.5) / STREAMLINE_SEEDS) for r in range(STREAMLINE_SEEDS)
    ]


def _streamline_points() -> list[dict]:
    lines = []
    for sx, sy in _streamline_seed_points():
        x, y = sx, sy
        parts: list[tuple[float, float]] = [(x, y)]
        for _ in range(190):
            nx, ny = _cylinder_rk4_step(x, y, 0.012)
            if _inside_cylinder(nx, ny, 0.0005):
                break
            if not (-0.04 <= nx <= 1.06 and -0.08 <= ny <= 1.08):
                break
            parts.append((nx, ny))
            x, y = nx, ny
            if x >= 1.02:
                break
        arc = sum(
            math.hypot(b[0] - a[0], b[1] - a[1])
            for a, b in itertools.pairwise(parts)
        )
        if arc < 0.94 or len(parts) < 22 or parts[-1][0] < 0.94:
            continue
        view_points = _resample_polyline(
            [_view_point(px, py) for px, py in parts], STREAMLINE_ARC_SPACING
        )
        resampled = [_norm_from_view(point) for point in view_points]
        lines.append(
            {
                "points": resampled,
                "speeds": [_cylinder_speed(px, py) for px, py in resampled],
                "angles": [_cylinder_angle(px, py) for px, py in resampled],
            }
        )
    return lines[:STREAMLINE_SEEDS]


def _streamline_path_stats() -> dict:
    lines = _streamline_points()
    c_segments = sum(max(0, len(line["points"]) - 1) for line in lines)
    return {"paths": len(lines), "c_segments": c_segments, "l_segments": 0}


def _streamline_view_paths() -> list[list[tuple[float, float]]]:
    return [
        [_view_point(x, y) for x, y in line["points"]]
        for line in _streamline_points()
    ]


def _point_key(point: tuple[float, float]) -> tuple[int, int]:
    return (round(point[0] * 1000), round(point[1] * 1000))


def _chain_segments(
    segments: list[tuple[tuple[float, float], tuple[float, float]]],
) -> list[list[tuple[float, float]]]:
    endpoints: dict[tuple[int, int], list[int]] = {}
    for idx, (start, end) in enumerate(segments):
        endpoints.setdefault(_point_key(start), []).append(idx)
        endpoints.setdefault(_point_key(end), []).append(idx)

    used = [False] * len(segments)

    def _next_unused(point: tuple[float, float]) -> int | None:
        for idx in endpoints.get(_point_key(point), []):
            if not used[idx]:
                return idx
        return None

    chains: list[list[tuple[float, float]]] = []
    for idx, segment in enumerate(segments):
        if used[idx]:
            continue
        used[idx] = True
        chain = [segment[0], segment[1]]

        while True:
            next_idx = _next_unused(chain[-1])
            if next_idx is None:
                break
            used[next_idx] = True
            start, end = segments[next_idx]
            chain.append(
                end if _point_key(start) == _point_key(chain[-1]) else start
            )

        while True:
            next_idx = _next_unused(chain[0])
            if next_idx is None:
                break
            used[next_idx] = True
            start, end = segments[next_idx]
            chain.insert(
                0, end if _point_key(start) == _point_key(chain[0]) else start
            )

        chains.append(chain)
    return chains


def _isoline_chains(
    cols: int = ISOLINE_GRID_COLS,
    rows: int = ISOLINE_GRID_ROWS,
    simplify_epsilon: float = ISOLINE_SIMPLIFY_EPSILON,
) -> list[list[tuple[float, float]]]:
    values = [
        _demo_field(c / (cols - 1), r / (rows - 1))
        for r in range(rows)
        for c in range(cols)
    ]
    lo, hi = min(values), max(values)
    span = hi - lo or 1.0
    scaled = [(value - lo) / span for value in values]
    table = [scaled[r * cols : (r + 1) * cols] for r in range(rows)]

    def fx(col: int) -> float:
        return col / (cols - 1) * VIEWBOX_WIDTH

    def fy(row: int) -> float:
        return row / (rows - 1) * VIEWBOX_HEIGHT

    def interp(
        xa: float,
        ya: float,
        va: float,
        xb: float,
        yb: float,
        vb: float,
        level: float,
    ) -> tuple[float, float]:
        t = 0.5 if abs(vb - va) < 1e-9 else (level - va) / (vb - va)
        t = max(0.0, min(1.0, t))
        return xa + (xb - xa) * t, ya + (yb - ya) * t

    def scaled_center(col: int, row: int) -> float:
        value = _demo_field((col + 0.5) / (cols - 1), (row + 0.5) / (rows - 1))
        return (value - lo) / span

    chains: list[list[tuple[float, float]]] = []
    for level_idx in range(12):
        level = (level_idx + 1) / 13
        segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
        for row in range(rows - 1):
            for col in range(cols - 1):
                v00 = table[row][col]
                v10 = table[row][col + 1]
                v11 = table[row + 1][col + 1]
                v01 = table[row + 1][col]
                edges: dict[str, tuple[float, float]] = {}
                if (v00 - level) * (v10 - level) < 0:
                    edges["top"] = interp(
                        fx(col), fy(row), v00, fx(col + 1), fy(row), v10, level
                    )
                if (v10 - level) * (v11 - level) < 0:
                    edges["right"] = interp(
                        fx(col + 1),
                        fy(row),
                        v10,
                        fx(col + 1),
                        fy(row + 1),
                        v11,
                        level,
                    )
                if (v01 - level) * (v11 - level) < 0:
                    edges["bottom"] = interp(
                        fx(col),
                        fy(row + 1),
                        v01,
                        fx(col + 1),
                        fy(row + 1),
                        v11,
                        level,
                    )
                if (v00 - level) * (v01 - level) < 0:
                    edges["left"] = interp(
                        fx(col), fy(row), v00, fx(col), fy(row + 1), v01, level
                    )
                if len(edges) == 2:
                    start, end = edges.values()
                    segments.append((start, end))
                elif len(edges) == 4:
                    case_id = (
                        (1 if v00 >= level else 0)
                        + (2 if v10 >= level else 0)
                        + (4 if v11 >= level else 0)
                        + (8 if v01 >= level else 0)
                    )
                    center_high = scaled_center(col, row) >= level
                    top_right_bottom_left = (
                        center_high if case_id == 5 else not center_high
                    )
                    if top_right_bottom_left:
                        segments.append((edges["top"], edges["right"]))
                        segments.append((edges["bottom"], edges["left"]))
                    else:
                        segments.append((edges["top"], edges["left"]))
                        segments.append((edges["right"], edges["bottom"]))
        chains.extend(
            _simplify_polyline(chain, simplify_epsilon)
            for chain in _chain_segments(segments)
            if len(chain) >= 2
        )
    return chains


def _isoline_path_stats() -> dict:
    chains = _isoline_chains()
    return {
        "paths": len(chains),
        "c_segments": sum(max(0, len(chain) - 1) for chain in chains),
        "l_segments": 0,
    }


def _line_paths(
    samples: int = LINE_SERIES_SAMPLES,
) -> list[list[tuple[float, float]]]:
    paths: list[list[tuple[float, float]]] = []
    for series_idx in range(6):
        raw = []
        lo = math.inf
        hi = -math.inf
        for sample_idx in range(samples):
            px = sample_idx * (VIEWBOX_WIDTH / (samples - 1))
            x = px / VIEWBOX_WIDTH
            value = (
                (series_idx - (6 - 1) / 2) * 0.38
                + 0.74
                * math.sin(
                    math.tau * ((1.05 + series_idx * 0.09) * x)
                    + series_idx * 0.72
                )
                + 0.34
                * math.cos(
                    math.tau * ((2.05 + series_idx * 0.13) * x)
                    - series_idx * 0.43
                )
                + 0.16 * math.sin(math.tau * (3.4 * x + series_idx * 0.11))
            )
            raw.append((px, value))
            lo = min(lo, value)
            hi = max(hi, value)
        span = hi - lo or 1.0
        paths.append(
            [
                (
                    x,
                    VIEWBOX_HEIGHT * 0.96
                    - ((value - lo) / span) * VIEWBOX_HEIGHT * 0.92,
                )
                for x, value in raw
            ]
        )
    return paths


def _ridgeline_paths(
    samples: int = RIDGELINE_PROFILE_SAMPLES,
) -> list[list[tuple[float, float]]]:
    paths: list[list[tuple[float, float]]] = []
    base0 = VIEWBOX_HEIGHT - RIDGELINE_GAP * (RIDGELINE_ROWS - 1)
    peak_h = RIDGELINE_GAP * 1.6
    for row in range(RIDGELINE_ROWS):
        profile = []
        peak = 0.0
        for sample_idx in range(samples):
            x = -0.04 + sample_idx * (1.08 / (samples - 1))
            value = _ridge_profile(row, x, RIDGELINE_ROWS)
            profile.append((x, value))
            peak = max(peak, value)
        base = base0 + row * RIDGELINE_GAP
        paths.append(
            [
                (x * VIEWBOX_WIDTH, base - (value / (peak or 1.0)) * peak_h)
                for x, value in profile
            ]
        )
    return paths


def _svg_curve_quality_stats() -> dict:
    quality = {
        "isolines": {
            "grid_points": [ISOLINE_GRID_COLS, ISOLINE_GRID_ROWS],
            "grid_cells": [ISOLINE_GRID_COLS - 1, ISOLINE_GRID_ROWS - 1],
            "simplify_epsilon": ISOLINE_SIMPLIFY_EPSILON,
            "angle_gate_degrees": CURVE_ANGLE_GATE_DEGREES,
        },
        "streamlines": {
            "arc_spacing": STREAMLINE_ARC_SPACING,
            "angle_gate_degrees": CURVE_ANGLE_GATE_DEGREES,
        },
        "lines": {
            "samples_per_series": LINE_SERIES_SAMPLES,
            "angle_gate_degrees": CURVE_ANGLE_GATE_DEGREES,
        },
        "ridgeline": {
            "samples_per_profile": RIDGELINE_PROFILE_SAMPLES,
            "angle_gate_degrees": CURVE_ANGLE_GATE_DEGREES,
        },
    }
    paths_by_demo = {
        "isolines": _isoline_chains(),
        "streamlines": _streamline_view_paths(),
        "lines": _line_paths(),
        "ridgeline": _ridgeline_paths(),
    }
    for demo, paths in paths_by_demo.items():
        quality[demo]["paths"] = len(paths)
        quality[demo]["c_segments"] = sum(
            max(0, len(path) - 1) for path in paths
        )
        quality[demo]["turning_angle_degrees"] = _turning_angle_distribution(
            paths
        )
    offenders = [
        demo
        for demo, row in quality.items()
        if row["turning_angle_degrees"]["max"] >= row["angle_gate_degrees"]
    ]
    if offenders:
        detail = ", ".join(
            f"{demo}={quality[demo]['turning_angle_degrees']['max']}"
            for demo in offenders
        )
        raise AssertionError(f"SVG curve turning-angle gate failed: {detail}")
    return quality


def _svg_path_stats() -> dict:
    return {
        "isolines": _isoline_path_stats(),
        "streamlines": _streamline_path_stats(),
        "lines": {
            "paths": 6,
            "c_segments": 6 * (LINE_SERIES_SAMPLES - 1),
            "l_segments": 0,
        },
        "ridgeline": {
            "paths": RIDGELINE_ROWS,
            "c_segments": RIDGELINE_ROWS * (RIDGELINE_PROFILE_SAMPLES - 1),
            "l_segments": RIDGELINE_ROWS * 2,
        },
    }


def _network_values() -> list[float]:
    rows, cols = 5, 8
    spacing = 0.175
    values = []
    for r in range(rows):
        for c in range(cols):
            jx = 0.10 * spacing * math.sin((r + 1) * 2.17 + c * 1.31)
            jy = 0.10 * spacing * math.cos((c + 1) * 1.73 + r * 1.19)
            x = -0.06 + c * 0.16 + (0.08 if r % 2 else 0.0) + jx
            y = 0.02 + r * 0.24 + jy
            values.append(_demo_field(x, y))
    return values


def _ridge_profile(row: int, x: float, rows: int = RIDGELINE_ROWS) -> float:
    drift = 0.34 + 0.26 * row / (rows - 1) + 0.035 * math.sin(row * 0.77)
    offsets = (-0.18, -0.045, 0.12, 0.27)
    value = 0.0
    bump_count = 2 + (row % 3)
    for j in range(bump_count):
        center = (
            drift + offsets[j] + 0.025 * math.sin((row + 1) * (j + 1) * 0.83)
        )
        width = 0.070 + 0.020 * ((row + j) % 4) + 0.012 * j
        height = 0.46 + 0.18 * ((row * 2 + j * 3) % 5) / 4 + 0.20 * (j == 1)
        value += height * math.exp(-(((x - center) / width) ** 2))
    value += 0.035 * math.sin(math.tau * (x * 1.5 + row * 0.07))
    return max(0.0, value)


def _ridgeline_values(rows: int = RIDGELINE_ROWS) -> list[float]:
    return [r / (rows - 1) for r in range(rows)]


def _histogram_value(t: float) -> float:
    left = 0.84 * math.exp(-(((t - 0.33) / 0.145) ** 2))
    right = 1.00 * math.exp(-(((t - 0.68) / 0.175) ** 2))
    bridge = 0.25 * math.exp(-(((t - 0.51) / 0.34) ** 2))
    ripple = 0.025 * math.sin(math.tau * (t * 3.0 + 0.08))
    return max(0.0, left + right + bridge + ripple)


def _histogram_values(n: int = HISTOGRAM_BINS) -> list[float]:
    values = [_histogram_value((i + 0.5) / n) for i in range(n)]
    peak = max(values) or 1.0
    return [v / peak for v in values]


def _quiver_values() -> list[float]:
    values = []
    for r in range(QUIVER_ROWS):
        for c in range(QUIVER_COLS):
            x = (c + 0.5 + (0.5 if r % 2 else 0.0)) / (QUIVER_COLS + 0.5)
            y = (r + 0.5) / QUIVER_ROWS
            values.append(math.hypot(*_flow_vec(x, y)))
    return values


def _quiver_arrows() -> list[dict]:
    raw = []
    for r in range(QUIVER_ROWS):
        for c in range(QUIVER_COLS):
            x = (c + 0.5 + (0.5 if r % 2 else 0.0)) / (QUIVER_COLS + 0.5)
            y = (r + 0.5) / QUIVER_ROWS
            vx, vy = _flow_vec(x, y)
            mag = math.hypot(vx, vy) or 1.0
            raw.append((r, c, x, y, vx / mag, -vy / mag, mag))
    vals = [a[6] for a in raw]
    lo, hi = min(vals), max(vals)
    span = hi - lo or 1.0
    arrows = []
    for r, c, x, y, ux, uy, mag in raw:
        t = (mag - lo) / span
        length = QUIVER_MIN_LEN + t * (QUIVER_MAX_LEN - QUIVER_MIN_LEN)
        cx, cy = x * 160.0, y * 100.0
        tip_x = cx + ux * length * 0.5
        tip_y = cy + uy * length * 0.5
        tail_x = cx - ux * length * 0.5
        tail_y = cy - uy * length * 0.5
        base_x = tip_x - ux * QUIVER_HEAD_LEN
        base_y = tip_y - uy * QUIVER_HEAD_LEN
        arrows.append(
            {
                "row": r,
                "col": c,
                "tail": (tail_x, tail_y),
                "base": (base_x, base_y),
                "tip": (tip_x, tip_y),
                "dir": (ux, uy),
                "length": length,
            }
        )
    return arrows


def _quiver_geometry_stats() -> dict:
    arrows = _quiver_arrows()
    overshoots = 0
    for arrow in arrows:
        ux, uy = arrow["dir"]
        tail_x, tail_y = arrow["tail"]
        base_x, base_y = arrow["base"]
        tip_x, tip_y = arrow["tip"]
        shaft_projection = (base_x - tail_x) * ux + (base_y - tail_y) * uy
        allowed_projection = arrow["length"] - QUIVER_HEAD_LEN
        head_projection = (tip_x - base_x) * ux + (tip_y - base_y) * uy
        if shaft_projection - allowed_projection > 1e-9:
            overshoots += 1
        if abs(head_projection - QUIVER_HEAD_LEN) > 1e-9:
            overshoots += 1
    return {
        "arrows": len(arrows),
        "rows": QUIVER_ROWS,
        "cols": QUIVER_COLS,
        "min_length": round(min(a["length"] for a in arrows), 1),
        "max_length": round(max(a["length"] for a in arrows), 1),
        "head_length": round(QUIVER_HEAD_LEN, 1),
        "head_half_width": round(QUIVER_HEAD_LEN / 2.6, 2),
        "overshoots": overshoots,
    }


def _polar_value(radial: float, theta: float) -> float:
    return (
        0.46 * radial
        + 0.26 * math.sin(math.tau * (theta * 2.0 + radial * 0.34))
        + 0.18 * math.cos(math.tau * (theta * 3.0 - radial * 0.22))
        + 0.10 * math.sin(math.tau * radial * 2.1)
    )


def _polar_values() -> list[float]:
    return [
        _polar_value((r + 0.5) / 72, (a + 0.5) / 144)
        for r in range(72)
        for a in range(144)
    ]


def _waffle_values() -> list[float]:
    return [
        _demo_field((c + 0.5) / 14, (r + 0.5) / 9)
        for r in range(9)
        for c in range(14)
    ]


def _demo_values(demo: str) -> list[float]:
    """Raw demo values mirrored from the JS renderer for build-time coverage."""
    if demo == "heatmap":
        return _field_values(256, 160)
    if demo == "contours":
        return _contour_values(256, 160)
    if demo == "terrain":
        return _field_values(256, 160)
    if demo == "isolines":
        return [0.0, 0.16, 0.28, 0.4, 0.52, 0.64, 0.76, 0.88, 1.0]
    if demo == "scatter":
        values = []
        for i in range(90):
            x = ((i * 37 + 11) % 97) / 97
            y = ((i * 53 + 29) % 97) / 97
            x = max(0, min(1, x + 0.03 * math.sin(i * 1.7)))
            y = max(0, min(1, y + 0.03 * math.cos(i * 2.1)))
            values.append(_demo_field(x, y))
        return values
    if demo == "signal":
        return [_signal_value(i, 320) for i in range(320)]
    if demo == "streamlines":
        values = []
        for line in _streamline_points():
            speeds = line["speeds"]
            values.extend(
                (speeds[i] + speeds[i + 1]) / 2 for i in range(len(speeds) - 1)
            )
        return values
    if demo == "hexbin":
        return [
            _demo_field((c + 0.5 + (r % 2) * 0.5) / 9, (r + 0.6) / 6)
            for r in range(6)
            for c in range(9)
        ]
    if demo == "bars":
        return _histogram_values()
    if demo == "mosaic":
        rects = [[0.0, 0.0, 1.0, 1.0, 0]]
        for step in range(39):
            bi = max(
                range(len(rects)), key=lambda idx: rects[idx][2] * rects[idx][3]
            )
            x, y, w, h, sd = rects.pop(bi)
            ratio = 0.38 + 0.24 * ((math.sin((sd + step + 1) * 1.71) + 1) / 2)
            if w >= h:
                rects.append([x, y, w * ratio, h, sd * 2 + 1])
                rects.append([x + w * ratio, y, w - w * ratio, h, sd * 2 + 2])
            else:
                rects.append([x, y, w, h * ratio, sd * 2 + 1])
                rects.append([x, y + h * ratio, w, h - h * ratio, sd * 2 + 2])
        return [_demo_field(x + w / 2, y + h / 2) for x, y, w, h, _ in rects]
    if demo == "lines":
        return [i / 5 for i in range(6)]
    if demo == "network":
        return _network_values()
    if demo == "ridgeline":
        return _ridgeline_values()
    if demo == "quiver":
        return _quiver_values()
    if demo == "polar_heat":
        return _polar_values()
    if demo == "waffle":
        return _waffle_values()
    raise KeyError(demo)


def _demo_coverage_table(red_demo_ramp: list[str]) -> list[dict]:
    """Item 2b guard: every red demo uses both clipped-ramp LUT endpoints."""
    target0, target1 = red_demo_ramp[0], red_demo_ramp[-1]
    rows = []
    for key, _label in DEMO_LIBRARY:
        values = _demo_values(key)
        lo, hi = min(values), max(values)
        span = hi - lo
        if span <= 1e-12:
            used_lut = {128}
        else:
            used_lut = set()
            for value in values:
                t = (value - lo) / span
                if key == "contours":
                    bands = 10
                    band = min(bands - 1, max(0, math.floor(t * bands)))
                    t = band / (bands - 1)
                used_lut.add(round(t * 255))
        used = {
            red_demo_ramp[round(index / 255 * (len(red_demo_ramp) - 1))]
            for index in used_lut
        }
        t0_hit = 0 in used_lut or any(
            de2000_hex(color, target0) <= 2 for color in used
        )
        t1_hit = 255 in used_lut or any(
            de2000_hex(color, target1) <= 2 for color in used
        )
        rows.append(
            {
                "demo": key,
                "t0_hit": t0_hit,
                "t1_hit": t1_hit,
                "distinct": len(used_lut),
            }
        )
    offenders = [r for r in rows if not (r["t0_hit"] and r["t1_hit"])]
    if offenders:
        raise AssertionError(
            "red demo spectrum coverage failed: "
            + ", ".join(r["demo"] for r in offenders)
        )
    return rows


def build_payload() -> dict:
    order = [key for _, keys in GROUPS for key in keys]
    actual = set(CMAPS_256)
    missing = sorted(actual - set(order))
    extra = sorted(set(order) - actual)
    if missing or extra or len(order) != len(set(order)) or len(order) != 46:
        raise AssertionError(
            f"colormap taxonomy partition mismatch: count={len(order)} "
            f"missing={missing} extra={extra}"
        )

    maps: dict[str, dict] = {}
    self_check: list[dict] = []
    for group, keys in GROUPS:
        for key in keys:
            original = _subsample_64(CMAPS_256[key])
            variants = {"original": _variant(key, original)}
            maps[key] = {
                "name": _display_name(key),
                "key": f"dc.{key}",
                "group": group,
                "kind": _kind_for(key),
                "default_variant": "original",
                "variants": variants,
                "intent": _intent_for(key),
                "recipe": KIND_RECIPE[_kind_for(key)],
                "good_for": KIND_GOOD_FOR[_kind_for(key)],
            }
            self_check.append(_self_check_row(key, variants["original"]))

    # Item 1 step 6 guard: every clipped (sequential + multi-hue) map keeps its
    # darkest demo swatch at >= 0.55 x the map's own peak chroma.
    seq_multi = [r for r in self_check if r["group"] in ("family", "multi")]
    offenders = [r for r in seq_multi if r["ratio"] < 0.55]
    if offenders:
        raise AssertionError(
            "vivid-clip self-check failed (< 0.55): "
            + ", ".join(f"{r['map']}={r['ratio']}" for r in offenders)
        )
    red_default = maps["red"]["variants"][maps["red"]["default_variant"]]
    demo_coverage = _demo_coverage_table(red_default["demo"])
    svg_curve_quality = _svg_curve_quality_stats()

    return {
        "maps": maps,
        "groups": GROUPS,
        "order": order,
        "library": [{"key": k, "name": n} for k, n in DEMO_LIBRARY],
        "levels": LEVEL_VALUES,
        "field": FIELD_PARAMS,
        "contour_field": CONTOUR_FIELD_PARAMS,
        "defaults": {"4": DEFAULT_4, "6": DEFAULT_6, "9": DEFAULT_9},
        "counts": {
            "sequential": len(SEQUENTIAL),
            "multi_hue": len(MULTI_HUE),
            "diverging": len(DIVERGING),
            "cyclic": len(CYCLIC),
            "total": len(order),
        },
        "self_check": self_check,
        "demo_coverage": demo_coverage,
        "streamline_path_stats": _streamline_path_stats(),
        "svg_path_stats": _svg_path_stats(),
        "svg_curve_quality": svg_curve_quality,
        "quiver_geometry_stats": _quiver_geometry_stats(),
    }


def main() -> None:
    payload = build_payload()
    html = TEMPLATE.replace(
        "__PAYLOAD__",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )
    if re.search(r"[가-힣]", html):
        raise AssertionError(
            "output HTML contains Hangul; must be English only"
        )
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"fragment bytes: {OUT.stat().st_size}")
    print(
        "taxonomy: "
        + ", ".join(f"{label}={len(keys)}" for label, keys in GROUPS)
        + f", total={len(payload['order'])}"
    )
    print("\nvivid-clip self-check (item 1 step 6) — darkest demo swatch:")
    print(
        f"  {'map':14s} {'grp':6s} {'peakC':>6s} {'darkHex':8s} "
        f"{'darkL':>6s} {'darkC':>6s} {'ratio':>6s} flag"
    )
    for r in payload["self_check"]:
        seqmulti = r["group"] in ("family", "multi")
        flag = (
            ""
            if r["ratio"] >= 0.55
            else (
                "  <- intentional-neutral (design)"
                if not seqmulti
                else "  <- FAIL"
            )
        )
        print(
            f"  {r['map']:14s} {r['group']:6s} {r['peak_c']:6.1f} "
            f"{r['dark_hex']:8s} {r['dark_l']:6.1f} {r['dark_c']:6.1f} "
            f"{r['ratio']:6.2f}{flag}"
        )
    sm = [r for r in payload["self_check"] if r["group"] in ("family", "multi")]
    print(
        f"\nsequential+multi ({len(sm)}): all ratios >= 0.55 -> "
        f"{all(r['ratio'] >= 0.55 for r in sm)} (min {min(r['ratio'] for r in sm):.2f})"
    )
    print("\nSVG curve quality gate (path-max turning angle degrees):")
    print(
        f"  {'demo':12s} {'sample/grid':>14s} {'p50':>6s} {'p95':>6s} {'max':>6s}"
    )
    for demo in ("isolines", "streamlines", "lines", "ridgeline"):
        row = payload["svg_curve_quality"][demo]
        angles = row["turning_angle_degrees"]
        if demo == "isolines":
            sample = f"{row['grid_cells'][0]}x{row['grid_cells'][1]}"
        elif demo == "streamlines":
            sample = f"{row['arc_spacing']:.2f}vu"
        elif demo == "lines":
            sample = f"{row['samples_per_series']}pts"
        else:
            sample = f"{row['samples_per_profile']}pts"
        print(
            f"  {demo:12s} {sample:>14s} "
            f"{angles['p50']:6.2f} {angles['p95']:6.2f} {angles['max']:6.2f}"
        )
    print("\nred demo spectrum coverage (item 2b):")
    print(f"  {'demo':12s} {'t0':>4s} {'t1':>4s} {'n':>4s}")
    for r in payload["demo_coverage"]:
        print(
            f"  {r['demo']:12s} {r['t0_hit']!s:>4s} "
            f"{r['t1_hit']!s:>4s} {r['distinct']:4d}"
        )
    print("\nSVG curve path stats:")
    print(f"  {'demo':12s} {'paths':>5s} {'C':>5s} {'L':>5s}")
    for name, stats in payload["svg_path_stats"].items():
        print(
            f"  {name:12s} {stats['paths']:5d} "
            f"{stats['c_segments']:5d} {stats['l_segments']:5d}"
        )


# ---------------------------------------------------------------------------
# The widget: HTML skeleton + JS. CSS lives in dartwork-design.css so the
# fragment can be regenerated without reviving page-local inline style tags.
# Colours come only from __PAYLOAD__; demo geometry is generated in JS.
# ---------------------------------------------------------------------------
TEMPLATE = r"""<!-- GENERATED FILE - do not edit by hand.
     Source: docs/_static/scripts/build_colormap_explorer.py
     Data:   src/dartwork_mpl/colors/_generated.py (CMAPS_256)
             src/dartwork_mpl/colors/_metrics.py (Lab / chroma / CVD metrics)
     Regenerate: python3 docs/_static/scripts/build_colormap_explorer.py -->
<div id="dm-cmap-exp" class="yue">
<p class="cx-count" id="cx-count"></p>
<div class="md"><nav class="rail" id="cx-rail" aria-label="Colormap list"></nav><main class="detail" id="cx-detail"></main></div>
<script>(function(){
"use strict";
var D=__PAYLOAD__;
var MAPS=D.maps,GROUPS=D.groups,DEMOS=D.library,LEVELS=D.levels,FIELD=D.field,CONTOUR_FIELD=D.contour_field;
var LEVEL_LABEL=["5","10","15","20","25","30","35","40","45","50","∞"];
var DEFAULT={4:D.defaults["4"],6:D.defaults["6"],9:D.defaults["9"]};
var CANVAS_DEMOS={heatmap:1,contours:1,terrain:1,signal:1,polar_heat:1},CANVAS_TIMINGS=[],MAX_CANVAS_PIXELS=1600000;
var state={key:D.order[0],rev:false,bw:false,level:LEVELS.length-1,
  layout:9,demos:DEFAULT[9].slice()};

function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function map(){return MAPS[state.key];}
function variant(){return map().variants.original;}
function stops(){var s=variant().stops.slice();return state.rev?s.reverse():s;}
function demoArr(){var s=variant().demo.slice();return state.rev?s.reverse():s;}

// ── colour math ──
function hexToRgb(h){h=h.replace("#","");return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)];}
function rgbToHex(r,g,b){function c(v){v=Math.max(0,Math.min(255,Math.round(v)));var s=v.toString(16);return s.length<2?"0"+s:s;}return "#"+c(r)+c(g)+c(b);}
function lin(v){v/=255;return v<=0.04045?v/12.92:Math.pow((v+0.055)/1.055,2.4);}
function unlin(v){v=v<=0.0031308?v*12.92:1.055*Math.pow(v,1/2.4)-0.055;return v*255;}
function gray(hex){var p=hexToRgb(hex),Y=0.2126*lin(p[0])+0.7152*lin(p[1])+0.0722*lin(p[2]),g=unlin(Y);return rgbToHex(g,g,g);}
function clamp01(v){return Math.max(0,Math.min(1,v));}
function quantT(t){var lev=LEVELS[state.level];t=clamp01(t);return lev?Math.round(t*(lev-1))/(lev-1):t;}
function bandIndex(t,bands){return Math.max(0,Math.min(bands-1,Math.floor(clamp01(t)*bands)));}
function bandT(t,bands){var b=bandIndex(t,bands);return bands>1?b/(bands-1):0;}
function interpHex(a,t){t=clamp01(t);var p=t*(a.length-1),i=Math.floor(p),j=Math.min(a.length-1,i+1),f=p-i,c0=hexToRgb(a[i]),c1=hexToRgb(a[j]);
  return rgbToHex(c0[0]+(c1[0]-c0[0])*f,c0[1]+(c1[1]-c0[1])*f,c0[2]+(c1[2]-c0[2])*f);}
// The strip uses the TRUE full ramp (stops); demos use the clipped ramp (demo).
function rampColorAt(t,opt){opt=opt||{};var s=stops(),i=Math.max(0,Math.min(s.length-1,Math.round(clamp01(t)*(s.length-1)))),c=s[i];if(opt.gray||(!opt.gray&&state.bw))c=gray(c);return c;}
function demoLookup(t){var c=interpHex(demoArr(),quantT(t));if(state.bw)c=gray(c);return c;}
function demoLUT(opt){opt=opt||{};var a=demoArr(),bands=opt.bands||0,lut=new Uint8ClampedArray(256*3);
  for(var i=0;i<256;i++){var t=i/255,c=hexToRgb(interpHex(a,bands?bandT(t,bands):quantT(t)));if(state.bw)c=hexToRgb(gray(rgbToHex(c[0],c[1],c[2])));
    lut[i*3]=c[0];lut[i*3+1]=c[1];lut[i*3+2]=c[2];}
  return lut;}
function divergeT(v){return (Math.max(-1,Math.min(1,v))+1)/2;}
// value in [0,1] (seq/multi), [-1,1] (diverging dv), or an angle (cyclic).
function valueColor(v,kind){if(kind==="diverging")return demoLookup(divergeT(v));if(kind==="cyclic")return demoLookup(((v%1)+1)%1);return demoLookup(clamp01(v));}
function demoScale(vals,opt){opt=opt||{};var k=map().kind,lo=Infinity,hi=-Infinity;
  vals.forEach(function(v){if(v<lo)lo=v;if(v>hi)hi=v;});
  if(k==="diverging"){var center=opt.center==null?(lo+hi)/2:opt.center,den=0;
    vals.forEach(function(v){den=Math.max(den,Math.abs(v-center));});
    return {kind:k,lo:lo,hi:hi,span:hi-lo||1,center:center,den:den||1,angles:opt.angles||null};}
  return {kind:k,lo:lo,hi:hi,span:hi-lo||1,center:(lo+hi)/2,den:(hi-lo)||1,angles:opt.angles||null};}
function scaledT(v,sc,i){if(sc.kind==="cyclic"){if(sc.angles)return ((sc.angles[i]%1)+1)%1;return clamp01((v-sc.lo)/sc.span);}
  if(sc.kind==="diverging")return clamp01(0.5+0.5*(v-sc.center)/sc.den);
  return clamp01((v-sc.lo)/sc.span);}
function scaledColor(v,sc,i){return demoLookup(scaledT(v,sc,i));}

// ── deterministic analytic field F(x,y) shared by field demos ──
function field(x,y){var raw=FIELD.base.x*x+FIELD.base.y*y,bs=FIELD.bumps;
  for(var i=0;i<bs.length;i++){var b=bs[i],dx=(x-b.cx)/b.sx,dy=(y-b.cy)/b.sy;raw+=b.amp*Math.exp(-(dx*dx+dy*dy));}
  return raw;}
function fieldDeriv(x,y){var gx=FIELD.base.x,gy=FIELD.base.y,bs=FIELD.bumps;
  for(var i=0;i<bs.length;i++){var b=bs[i],dx=(x-b.cx)/b.sx,dy=(y-b.cy)/b.sy,e=b.amp*Math.exp(-(dx*dx+dy*dy));gx+=e*(-2*(x-b.cx)/(b.sx*b.sx));gy+=e*(-2*(y-b.cy)/(b.sy*b.sy));}
  return [gx,gy];}
function contourField(x,y){var s=CONTOUR_FIELD.saddle,r=CONTOUR_FIELD.ridge,w=CONTOUR_FIELD.waves,dx=x-s.x,dy=y-s.y;
  var raw=s.xx*dx*dx+s.yy*dy*dy+s.xy*dx*dy;
  raw+=r.amp*Math.exp(-(((x-r.cx)/r.sx)*((x-r.cx)/r.sx)+((y-r.cy)/r.sy)*((y-r.cy)/r.sy)));
  raw+=w.amp*Math.sin(6.283*(w.x*x-w.y*y));return raw;}
function signalValue(t){return 0.5+0.26*Math.sin(t*6.283*2.1)+0.15*Math.sin(t*6.283*5.3+0.8)+0.07*Math.cos(t*6.283*9);}
function flowVec(x,y){var dx=x-.52,dy=y-.50,r2=dx*dx+dy*dy+.045,vx=-.070*dy/r2+.28,vy=.070*dx/r2-.02;
  [[.20,.80,.050],[.86,.28,-.060]].forEach(function(p){var sx=x-p[0],sy=y-p[1],d2=sx*sx+sy*sy+.030;vx+=p[2]*sx/d2;vy+=p[2]*sy/d2;});
  vx+=.16*Math.sin(6.283*(y*.92+.10));vy+=.13*Math.cos(6.283*(x*.86-.16));return [vx,vy];}
function flowDir(x,y){var v=flowVec(x,y),m=Math.hypot(v[0],v[1])||1;return [v[0]/m,v[1]/m];}
function rk4(x,y,h){var k1=flowDir(x,y),k2=flowDir(x+.5*h*k1[0],y+.5*h*k1[1]),k3=flowDir(x+.5*h*k2[0],y+.5*h*k2[1]),k4=flowDir(x+h*k3[0],y+h*k3[1]);
  return [x+h*(k1[0]+2*k2[0]+2*k3[0]+k4[0])/6,y+h*(k1[1]+2*k2[1]+2*k3[1]+k4[1])/6];}
var CYL={cx:.35,cy:.5,r:.18,aspect:1.6};
function cylinderXY(x,y){return [(x-CYL.cx)*CYL.aspect,y-CYL.cy];}
function insideCylinder(x,y,pad){var p=cylinderXY(x,y),rr=CYL.r+(pad||0);return p[0]*p[0]+p[1]*p[1]<=rr*rr;}
function cylinderFlowPhysical(x,y){var p=cylinderXY(x,y),r2=p[0]*p[0]+p[1]*p[1],a2=CYL.r*CYL.r;if(r2<=a2)return [0,0];var r4=r2*r2;
  return [1-a2*(p[0]*p[0]-p[1]*p[1])/r4,-2*a2*p[0]*p[1]/r4];}
function cylinderFlowVec(x,y){var v=cylinderFlowPhysical(x,y);return [v[0]/CYL.aspect,v[1]];}
function cylinderSpeed(x,y){var v=cylinderFlowPhysical(x,y);return Math.hypot(v[0],v[1]);}
function cylinderAngle(x,y){var v=cylinderFlowPhysical(x,y);return (Math.atan2(v[1],v[0])+Math.PI)/6.283;}
function cylinderDir(x,y){var v=cylinderFlowVec(x,y),m=Math.hypot(v[0],v[1]);return m>1e-12?[v[0]/m,v[1]/m]:[1,0];}
function cylinderRk4(x,y,h){var k1=cylinderDir(x,y),k2=cylinderDir(x+.5*h*k1[0],y+.5*h*k1[1]),k3=cylinderDir(x+.5*h*k2[0],y+.5*h*k2[1]),k4=cylinderDir(x+h*k3[0],y+h*k3[1]);
  return [x+h*(k1[0]+2*k2[0]+2*k3[0]+k4[0])/6,y+h*(k1[1]+2*k2[1]+2*k3[1]+k4[1])/6];}
function catmullRomPath(pts){if(pts.length<2)return "";var d="M"+pts[0][0].toFixed(2)+" "+pts[0][1].toFixed(2),c=0;
  for(var i=0;i<pts.length-1;i++){var p0=pts[Math.max(0,i-1)],p1=pts[i],p2=pts[i+1],p3=pts[Math.min(pts.length-1,i+2)];
    var c1x=p1[0]+(p2[0]-p0[0])/6,c1y=p1[1]+(p2[1]-p0[1])/6,c2x=p2[0]-(p3[0]-p1[0])/6,c2y=p2[1]-(p3[1]-p1[1])/6;
    d+=' C '+c1x.toFixed(2)+" "+c1y.toFixed(2)+" "+c2x.toFixed(2)+" "+c2y.toFixed(2)+" "+p2[0].toFixed(2)+" "+p2[1].toFixed(2);c++;}
  catmullRomPath.lastSegments=c;return d;}
function catmullRomSegmentPath(pts,i){if(i<0||i>=pts.length-1)return "";var p0=pts[Math.max(0,i-1)],p1=pts[i],p2=pts[i+1],p3=pts[Math.min(pts.length-1,i+2)];
  var c1x=p1[0]+(p2[0]-p0[0])/6,c1y=p1[1]+(p2[1]-p0[1])/6,c2x=p2[0]-(p3[0]-p1[0])/6,c2y=p2[1]-(p3[1]-p1[1])/6;
  return "M"+p1[0].toFixed(2)+" "+p1[1].toFixed(2)+" C "+c1x.toFixed(2)+" "+c1y.toFixed(2)+" "+c2x.toFixed(2)+" "+c2y.toFixed(2)+" "+p2[0].toFixed(2)+" "+p2[1].toFixed(2);}
function resamplePath(pts,spacing){if(pts.length<2)return pts.slice();var out=[pts[0]],rem=spacing,prev=pts[0];
  for(var i=1;i<pts.length;i++){var target=pts[i],dx=target[0]-prev[0],dy=target[1]-prev[1],seg=Math.hypot(dx,dy);if(seg<=1e-12){prev=target;continue;}
    while(seg>=rem){var t=rem/seg,next=[prev[0]+dx*t,prev[1]+dy*t];out.push(next);prev=next;dx=target[0]-prev[0];dy=target[1]-prev[1];seg=Math.hypot(dx,dy);rem=spacing;}
    rem-=seg;prev=target;}
  var last=pts[pts.length-1];if(Math.hypot(out[out.length-1][0]-last[0],out[out.length-1][1]-last[1])>1e-6)out.push(last);return out;}
function pointSegmentDistance(p,a,b){var dx=b[0]-a[0],dy=b[1]-a[1],den=dx*dx+dy*dy;if(den<=1e-12)return Math.hypot(p[0]-a[0],p[1]-a[1]);
  var t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den;t=Math.max(0,Math.min(1,t));return Math.hypot(p[0]-(a[0]+dx*t),p[1]-(a[1]+dy*t));}
function simplifyOpen(pts,eps){if(pts.length<=2)return pts.slice();var md=-1,mi=0;
  for(var i=1;i<pts.length-1;i++){var d=pointSegmentDistance(pts[i],pts[0],pts[pts.length-1]);if(d>md){md=d;mi=i;}}
  if(md>eps){var left=simplifyOpen(pts.slice(0,mi+1),eps),right=simplifyOpen(pts.slice(mi),eps);return left.slice(0,-1).concat(right);}
  return [pts[0],pts[pts.length-1]];}
function closeEnough(a,b){return Math.hypot(a[0]-b[0],a[1]-b[1])<=1e-6;}
function simplifyPath(pts,eps){if(pts.length<=2)return pts.slice();
  if(closeEnough(pts[0],pts[pts.length-1])&&pts.length>4){var ring=pts.slice(0,-1),anchor=0,far=-1;
    for(var i=0;i<ring.length;i++){var d=Math.hypot(ring[i][0]-ring[0][0],ring[i][1]-ring[0][1]);if(d>far){far=d;anchor=i;}}
    var ordered=ring.slice(anchor).concat(ring.slice(0,anchor+1)),out=simplifyOpen(ordered,eps);if(!closeEnough(out[0],out[out.length-1]))out.push(out[0]);return out;}
  return simplifyOpen(pts,eps);}
function pointKey(p){return p[0].toFixed(3)+","+p[1].toFixed(3);}
function samePoint(a,b){return pointKey(a)===pointKey(b);}
function chainSegments(segs){var ends={},used=new Array(segs.length),chains=[];
  function add(p,i){var k=pointKey(p);(ends[k]||(ends[k]=[])).push(i);}
  segs.forEach(function(s,i){add(s[0],i);add(s[1],i);});
  function next(p){var a=ends[pointKey(p)]||[];for(var i=0;i<a.length;i++)if(!used[a[i]])return a[i];return -1;}
  segs.forEach(function(s,i){if(used[i])return;used[i]=1;var ch=[s[0],s[1]],n;
    while((n=next(ch[ch.length-1]))>=0){used[n]=1;var q=segs[n];ch.push(samePoint(q[0],ch[ch.length-1])?q[1]:q[0]);}
    while((n=next(ch[0]))>=0){used[n]=1;var q2=segs[n];ch.unshift(samePoint(q2[0],ch[0])?q2[1]:q2[0]);}
    chains.push(ch);});
  return chains;}
function polarValue(r,t){return .46*r+.26*Math.sin(6.283*(t*2+r*.34))+.18*Math.cos(6.283*(t*3-r*.22))+.10*Math.sin(6.283*r*2.1);}
var VW=160,VH=100;
var ISOC=221,ISOR=141,ISOEPS=.15,STREAM_ARC=1.65,LINE_SAMPLES=201,RIDGE_SAMPLES=141;
function openArea(label){return '<svg class="demo-svg" viewBox="0 0 '+VW+' '+VH+'" preserveAspectRatio="none" aria-label="'+esc(label)+'">';}
function openStroke(label){return '<svg class="demo-svg" viewBox="0 0 '+VW+' '+VH+'" preserveAspectRatio="xMidYMid meet" aria-label="'+esc(label)+'">';}

function canvasShell(t){return '<canvas class="demo-canvas" data-canvas-demo="'+esc(t)+'" aria-label="'+esc(demoName(t))+'"></canvas>';}
function sizeCanvas(cv){var r=cv.getBoundingClientRect(),cw=Math.max(1,Math.round(r.width||cv.parentNode.clientWidth||320)),ch=Math.max(1,Math.round(r.height||cv.parentNode.clientHeight||200)),
  dpr=Math.min(Math.max(window.devicePixelRatio||1,1),2),scale=Math.min(dpr,Math.sqrt(MAX_CANVAS_PIXELS/(cw*ch))),w=Math.max(1,Math.round(cw*scale)),h=Math.max(1,Math.round(ch*scale));
  if(cv.width!==w)cv.width=w;if(cv.height!==h)cv.height=h;cv.dataset.dpr=scale.toFixed(3);return {w:w,h:h,cssW:cw,cssH:ch,dpr:scale};}
function putRgb(data,p,lut,idx,shade){idx=Math.max(0,Math.min(255,idx|0))*3;shade=shade==null?1:shade;data[p]=Math.max(0,Math.min(255,lut[idx]*shade));data[p+1]=Math.max(0,Math.min(255,lut[idx+1]*shade));data[p+2]=Math.max(0,Math.min(255,lut[idx+2]*shade));data[p+3]=255;}
function valueGrid(fw,fh,fn){var gw=fw,gh=fh,vals=new Float32Array(gw*gh),lo=Infinity,hi=-Infinity,idx=0;
  for(var y=0;y<gh;y++)for(var x=0;x<gw;x++,idx++){var v=fn((x+.5)/fw,(y+.5)/fh);vals[idx]=v;if(v<lo)lo=v;if(v>hi)hi=v;}
  return {w:gw,h:gh,vals:vals,lo:lo,hi:hi};}
function sampleGrid(g,x,y,fw,fh){if(g.w===fw&&g.h===fh)return g.vals[y*fw+x];var gx=(x+.5)/fw*(g.w-1),gy=(y+.5)/fh*(g.h-1),x0=Math.max(0,Math.min(g.w-1,Math.floor(gx))),y0=Math.max(0,Math.min(g.h-1,Math.floor(gy))),
  x1=Math.min(g.w-1,x0+1),y1=Math.min(g.h-1,y0+1),tx=gx-x0,ty=gy-y0,row0=y0*g.w,row1=y1*g.w,
  a=g.vals[row0+x0],b=g.vals[row0+x1],c=g.vals[row1+x0],d=g.vals[row1+x1];
  return (a+(b-a)*tx)*(1-ty)+(c+(d-c)*tx)*ty;}
function contourBandAt(vals,i,lo,span,bands){return bandIndex((vals[i]-lo)/span,bands);}
function contourEdgeShade(vals,i,x,y,fw,fh,lo,span,bands){var b=contourBandAt(vals,i,lo,span,bands);
  if(x+1<fw&&contourBandAt(vals,i+1,lo,span,bands)!==b)return .82;
  if(y+1<fh&&contourBandAt(vals,i+fw,lo,span,bands)!==b)return .82;
  return 1;}
function renderRaster(cv,kind,lut,bands){var sz=sizeCanvas(cv),ctx=cv.getContext("2d"),fw=sz.w,fh=sz.h,
  img=ctx.createImageData(fw,fh),vals=new Float32Array(fw*fh),grid=valueGrid(fw,fh,kind==="contours"?contourField:field),idx=0;
  for(var y=0;y<fh;y++)for(var x=0;x<fw;x++,idx++)vals[idx]=sampleGrid(grid,x,y,fw,fh);
  var lo=grid.lo,span=grid.hi-grid.lo||1,p=0;for(var yy=0;yy<fh;yy++)for(var xx=0;xx<fw;xx++,p+=4){var t=clamp01((vals[yy*fw+xx]-lo)/span),li=Math.round((bands?bandT(t,bands):t)*255),shade=1;
    if(kind==="terrain"){var g=fieldDeriv((xx+.5)/fw,(yy+.5)/fh);shade=Math.max(.64,Math.min(1.16,.9-g[0]*.08+g[1]*.06));}
    if(kind==="contours"&&bands)shade=contourEdgeShade(vals,yy*fw+xx,xx,yy,fw,fh,lo,span,bands);
    putRgb(img.data,p,lut,li,shade);}
  var scratch=renderRaster._scratch||(renderRaster._scratch=document.createElement("canvas"));scratch.width=fw;scratch.height=fh;scratch.getContext("2d").putImageData(img,0,0);
  ctx.clearRect(0,0,sz.w,sz.h);ctx.imageSmoothingEnabled=false;ctx.drawImage(scratch,0,0,fw,fh,0,0,sz.w,sz.h);}
function polarHeatFieldRange(){var vals=[];for(var r=0;r<72;r++)for(var a=0;a<144;a++)vals.push(polarValue((r+.5)/72,(a+.5)/144));return demoScale(vals);}
function polarHeat(cv,lut){var sz=sizeCanvas(cv),ctx=cv.getContext("2d"),fw=sz.w,fh=sz.h,
  img=ctx.createImageData(fw,fh),p=0;
  var cyclic=map().kind==="cyclic",sc=cyclic?null:polarHeatFieldRange(),R=Math.hypot(fw,fh)*.53,cx=fw/2,cy=fh/2,grid=cyclic?null:valueGrid(fw,fh,function(nx,ny){var dx=(nx*fw-cx)/R,dy=(ny*fh-cy)/R,rr=clamp01(Math.hypot(dx,dy)),th=(Math.atan2(dy,dx)/6.283+1)%1;return polarValue(rr,th);});
  for(var y=0;y<fh;y++)for(var x=0;x<fw;x++,p+=4){var ti;if(cyclic){var dx=(x+.5-cx)/R,dy=(y+.5-cy)/R;ti=(Math.atan2(dy,dx)/6.283+1)%1;}
    else{var v=sampleGrid(grid,x,y,fw,fh);ti=scaledT(v,sc,p/4);}
    putRgb(img.data,p,lut,Math.round(ti*255),1);}
  var scratch=polarHeat._scratch||(polarHeat._scratch=document.createElement("canvas"));scratch.width=fw;scratch.height=fh;scratch.getContext("2d").putImageData(img,0,0);
  ctx.clearRect(0,0,sz.w,sz.h);ctx.imageSmoothingEnabled=false;ctx.drawImage(scratch,0,0,fw,fh,0,0,sz.w,sz.h);}
function renderSignal(cv,lut){var sz=sizeCanvas(cv),ctx=cv.getContext("2d"),fw=sz.w,fh=sz.h,
  vals=[],angs=[],img=ctx.createImageData(fw,fh),rowData=new Uint8ClampedArray(fw*4),p=0;
  for(var x=0;x<fw;x++){var t=fw===1?0:x/(fw-1);vals.push(signalValue(t));angs.push(t+0.09*Math.sin(t*6.283*3));}
  var sc=demoScale(vals,{angles:angs});for(var xx=0;xx<fw;xx++,p+=4)putRgb(rowData,p,lut,Math.round(scaledT(vals[xx],sc,xx)*255),1);
  for(var y=0;y<fh;y++)img.data.set(rowData,y*fw*4);
  var scratch=renderSignal._scratch||(renderSignal._scratch=document.createElement("canvas"));scratch.width=fw;scratch.height=fh;scratch.getContext("2d").putImageData(img,0,0);
  ctx.clearRect(0,0,sz.w,sz.h);ctx.imageSmoothingEnabled=!LEVELS[state.level];ctx.drawImage(scratch,0,0,fw,fh,0,0,sz.w,sz.h);
  ctx.beginPath();for(var i=0;i<sz.w;i++){var tx=sz.w===1?0:i/(sz.w-1),v=signalValue(tx),a=tx+0.09*Math.sin(tx*6.283*3),t=scaledT(v,{kind:sc.kind,lo:sc.lo,hi:sc.hi,span:sc.span,center:sc.center,den:sc.den,angles:[a]},0),
    py=sz.h-(t*sz.h*.9+sz.h*.05);if(i)ctx.lineTo(i,py);else ctx.moveTo(i,py);}
  ctx.strokeStyle="rgba(31,41,51,.52)";ctx.lineWidth=Math.max(1,sz.w/320);ctx.stroke();}
function nowMs(){return window.performance&&performance.now?performance.now():Date.now();}
function noteCanvasTiming(name,ms){var row={demo:name,ms:Math.round(ms*100)/100};CANVAS_TIMINGS.push(row);if(CANVAS_TIMINGS.length>80)CANVAS_TIMINGS.splice(0,CANVAS_TIMINGS.length-80);window.dmCmapExplorerLastCanvasMs=CANVAS_TIMINGS.slice(-visibleDemos().length);}
function renderCanvasDemo(cv,t){var start=nowMs(),lev=LEVELS[state.level],bands=t==="contours"?(lev||10):0,lut=demoLUT({bands:bands});
  if(t==="signal")renderSignal(cv,lut);else if(t==="polar_heat")polarHeat(cv,lut);else renderRaster(cv,t,lut,bands);var ms=nowMs()-start;cv.dataset.renderMs=ms.toFixed(2);noteCanvasTiming(t,ms);}
function renderCanvases(root){root.querySelectorAll("canvas.demo-canvas").forEach(function(cv){renderCanvasDemo(cv,cv.dataset.canvasDemo);});}
function rerenderVisibleCanvases(){var host=document.querySelector("#cx-detail .demo-host");if(host)renderCanvases(host);}
function watchCanvasDpr(){var last=window.devicePixelRatio||1,timer=0;
  function changed(){var cur=window.devicePixelRatio||1;if(Math.abs(cur-last)>.001){last=cur;rerenderVisibleCanvases();}}
  window.addEventListener("resize",function(){clearTimeout(timer);timer=setTimeout(function(){changed();rerenderVisibleCanvases();},80);});
  if(window.matchMedia)[1,1.25,1.5,1.75,2].forEach(function(v){var mq=window.matchMedia("(resolution: "+v+"dppx)"),cb=changed;if(mq.addEventListener)mq.addEventListener("change",cb);else if(mq.addListener)mq.addListener(cb);});}
// marching-squares isolines (no fill, no frame rect)
function isolinesSVG(){var cols=ISOC,rows=ISOR,s=openStroke("isolines");
  function fx(c){return c/(cols-1)*VW;}function fy(r){return r/(rows-1)*VH;}
  var vals=[];for(var r=0;r<rows;r++)for(var c=0;c<cols;c++)vals.push(field(c/(cols-1),r/(rows-1)));
  var sc=demoScale(vals),T=[],idx=0;for(var rr=0;rr<rows;rr++){T[rr]=[];for(var cc=0;cc<cols;cc++,idx++)T[rr][cc]=scaledT(vals[idx],sc,idx);}
  var isoN=LEVELS[state.level]?Math.min(16,Math.max(2,LEVELS[state.level])):12,levels=[],colorT=[];
  for(var li0=0;li0<isoN;li0++){levels.push((li0+1)/(isoN+1));colorT.push(isoN>1?li0/(isoN-1):0);}
  var pathCount=0,cSeg=0;
  levels.forEach(function(L,li){var segs=[],d="";
    for(var r=0;r<rows-1;r++)for(var c=0;c<cols-1;c++){var v00=T[r][c],v10=T[r][c+1],v11=T[r+1][c+1],v01=T[r+1][c];var e={};
      function ip(xa,ya,va,xb,yb,vb){var t=Math.abs(vb-va)<1e-9?0.5:(L-va)/(vb-va);t=Math.max(0,Math.min(1,t));return [xa+(xb-xa)*t,ya+(yb-ya)*t];}
      if((v00-L)*(v10-L)<0)e.top=ip(fx(c),fy(r),v00,fx(c+1),fy(r),v10);
      if((v10-L)*(v11-L)<0)e.right=ip(fx(c+1),fy(r),v10,fx(c+1),fy(r+1),v11);
      if((v01-L)*(v11-L)<0)e.bottom=ip(fx(c),fy(r+1),v01,fx(c+1),fy(r+1),v11);
      if((v00-L)*(v01-L)<0)e.left=ip(fx(c),fy(r),v00,fx(c),fy(r+1),v01);
      var ks=Object.keys(e);
      if(ks.length===2)segs.push([e[ks[0]],e[ks[1]]]);
      else if(ks.length===4){var caseId=(v00>=L?1:0)+(v10>=L?2:0)+(v11>=L?4:0)+(v01>=L?8:0),
        center=scaledT(field((c+.5)/(cols-1),(r+.5)/(rows-1)),sc,0)>=L,trbl=caseId===5?center:!center;
        if(trbl){segs.push([e.top,e.right]);segs.push([e.bottom,e.left]);}
        else{segs.push([e.top,e.left]);segs.push([e.right,e.bottom]);}}}
    chainSegments(segs).forEach(function(ch){ch=simplifyPath(ch,ISOEPS);if(ch.length<2)return;d+=catmullRomPath(ch);pathCount++;cSeg+=Math.max(0,ch.length-1);});
    s+='<path d="'+d+'" fill="none" stroke="'+demoLookup(colorT[li])+'" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>';});
  window.dmCmapExplorerIsolineStats={paths:pathCount,cSegments:cSeg,lSegments:0};
  return s+"</svg>";}
function scatterSVG(){var s=openStroke("scatter"),pts=[],vals=[],n=90,minX=1,maxX=0,minY=1,maxY=0;
  for(var i=0;i<n;i++){var x=((i*37+11)%97)/97,y=((i*53+29)%97)/97;x=clamp01(x+0.03*Math.sin(i*1.7));y=clamp01(y+0.03*Math.cos(i*2.1));pts.push([x,y]);vals.push(field(x,y));minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
  var dx=maxX-minX||1,dy=maxY-minY||1,sc=demoScale(vals);pts.forEach(function(p,i){p.push((p[0]-minX)/dx,(p[1]-minY)/dy);s+='<circle cx="'+(p[2]*VW).toFixed(2)+'" cy="'+(p[3]*VH).toFixed(2)+'" r="2.7" fill="'+scaledColor(vals[i],sc,i)+'" opacity=".92"/>';});
  return s+"</svg>";}
function streamlineData(){var lines=[];
  for(var r=0;r<28;r++){var sx=0,sy=(r+.5)/28,x=sx,y=sy,parts=[[x,y]],speeds=[cylinderSpeed(x,y)],angs=[cylinderAngle(x,y)];
    for(var it=0;it<190;it++){var p=cylinderRk4(x,y,.012),nx=p[0],ny=p[1];if(insideCylinder(nx,ny,.0005))break;if(!(nx>=-.04&&nx<=1.06&&ny>=-.08&&ny<=1.08))break;
      parts.push([nx,ny]);speeds.push(cylinderSpeed(nx,ny));angs.push(cylinderAngle(nx,ny));x=nx;y=ny;if(x>=1.02)break;}
    var arc=0;for(var i=1;i<parts.length;i++)arc+=Math.hypot(parts[i][0]-parts[i-1][0],parts[i][1]-parts[i-1][1]);
    if(arc<.94||parts.length<22||parts[parts.length-1][0]<.94)continue;
    var pts=resamplePath(parts.map(function(p){return [p[0]*VW,(1-p[1])*VH];}),STREAM_ARC);
    speeds=[];angs=[];pts.forEach(function(p){var nx=p[0]/VW,ny=1-p[1]/VH;speeds.push(cylinderSpeed(nx,ny));angs.push(cylinderAngle(nx,ny));});
    lines.push({pts:pts,speeds:speeds,angles:angs});}
  return lines.slice(0,28);}
function streamlinesSVG(){var s=openStroke("streamlines"),lines=streamlineData(),vals=[],angs=[],segs=[],cSeg=0;
  lines.forEach(function(L){for(var j=0;j<L.pts.length-1;j++){vals.push((L.speeds[j]+L.speeds[j+1])*.5);angs.push((L.angles[j]+L.angles[j+1])*.5);segs.push([L,j]);}});
  var sc=demoScale(vals,{angles:angs});segs.forEach(function(S,i){var L=S[0],j=S[1],d=catmullRomSegmentPath(L.pts,j);cSeg++;
    s+='<path d="'+d+'" fill="none" stroke="'+scaledColor(vals[i],sc,i)+'" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" opacity=".92" vector-effect="non-scaling-stroke"/>';});
  window.dmCmapExplorerStreamlineStats={paths:lines.length,cSegments:cSeg,lSegments:0};return s+"</svg>";}
function hexbinSVG(){var s=openArea("hexbin"),cols=9,rows=6,vals=[],cells=[],rx=VW/(cols*1.55),ry=VH/(rows*1.35),rr=Math.min(rx,ry)*0.78;
  for(var r=0;r<rows;r++)for(var c=0;c<cols;c++){var ux=(c+0.5+(r%2)*0.5)/cols,uy=(r+0.6)/rows;if(ux>1.03)continue;cells.push([ux,uy]);vals.push(field(ux,uy));}
  var sc=demoScale(vals);s+='<rect x="0" y="0" width="'+VW+'" height="'+VH+'" fill="'+demoLookup(0)+'"/>';
  cells.forEach(function(cell,idx){var cx=cell[0]*VW,cy=cell[1]*VH,pts=[];
    for(var i=0;i<6;i++){var a=Math.PI/6+i*Math.PI/3;pts.push((cx+Math.cos(a)*rr).toFixed(2)+","+(cy+Math.sin(a)*rr*1.02).toFixed(2));}
    s+='<polygon points="'+pts.join(" ")+'" fill="'+scaledColor(vals[idx],sc,idx)+'" stroke="var(--dm-bg-page,#fff)" stroke-width="0.7" vector-effect="non-scaling-stroke"/>';});
  return s+"</svg>";}
function histValue(t){return Math.max(0,.84*Math.exp(-((t-.33)/.145)*((t-.33)/.145))+Math.exp(-((t-.68)/.175)*((t-.68)/.175))+.25*Math.exp(-((t-.51)/.34)*((t-.51)/.34))+.025*Math.sin(6.283*(t*3+.08)));}
function medianValue(a){var s=a.slice().sort(function(x,y){return x-y;}),m=Math.floor(s.length/2);return s.length%2?s[m]:(s[m-1]+s[m])*.5;}
function barsSVG(){var n=28,gap=1,colW=(VW-gap*(n-1))/n,s=openStroke("bars"),vals=[];
  for(var i=0;i<n;i++)vals.push(histValue((i+.5)/n));
  var peak=Math.max.apply(null,vals)||1,sc=demoScale(vals,{center:medianValue(vals)});
  for(var j=0;j<n;j++){var h=vals[j]/peak*VH,x=j*(colW+gap),y=VH-h;
    s+='<rect x="'+x.toFixed(2)+'" y="'+y.toFixed(2)+'" width="'+colW.toFixed(2)+'" height="'+h.toFixed(2)+'" fill="'+scaledColor(vals[j],sc,j)+'"/>';}
  return s+"</svg>";}
function mosaicSVG(){var s=openArea("mosaic"),rects=[[0,0,1,1,0]];
  for(var step=0;step<39;step++){var bi=0,ba=-1;for(var i=0;i<rects.length;i++){var a=rects[i][2]*rects[i][3];if(a>ba){ba=a;bi=i;}}
    var R=rects.splice(bi,1)[0],x=R[0],y=R[1],w=R[2],h=R[3],sd=R[4],ratio=0.38+0.24*((Math.sin((sd+step+1)*1.71)+1)/2);
    if(w>=h){rects.push([x,y,w*ratio,h,sd*2+1]);rects.push([x+w*ratio,y,w-w*ratio,h,sd*2+2]);}
    else{rects.push([x,y,w,h*ratio,sd*2+1]);rects.push([x,y+h*ratio,w,h-h*ratio,sd*2+2]);}}
  var vals=rects.map(function(R){return field(R[0]+R[2]/2,R[1]+R[3]/2);}),sc=demoScale(vals);
  rects.forEach(function(R,i){s+='<rect x="'+(R[0]*VW).toFixed(2)+'" y="'+(R[1]*VH).toFixed(2)+'" width="'+(R[2]*VW+0.25).toFixed(2)+'" height="'+(R[3]*VH+0.25).toFixed(2)+'" rx="0" fill="'+scaledColor(vals[i],sc,i)+'" stroke="var(--dm-bg-page,#fff)" stroke-width="0.55" vector-effect="non-scaling-stroke"/>';});
  return s+"</svg>";}
function linesSVG(){var n=6,s=openStroke("lines"),vals=[],series=[],lo=Infinity,hi=-Infinity;
  for(var j=0;j<n;j++){vals.push(j/(n-1));var pts=[];
    for(var i=0;i<LINE_SAMPLES;i++){var px=i*(VW/(LINE_SAMPLES-1)),x=px/VW,v=(j-(n-1)/2)*.38+.74*Math.sin(6.283*((1.05+j*.09)*x)+j*.72)+.34*Math.cos(6.283*((2.05+j*.13)*x)-j*.43)+.16*Math.sin(6.283*(3.4*x+j*.11));pts.push([px,v]);lo=Math.min(lo,v);hi=Math.max(hi,v);}
    series.push(pts);}
  var span=hi-lo||1,sc=demoScale(vals,{angles:vals});
  series.forEach(function(pts,j){var p=pts.map(function(q){return [q[0],VH*.96-((q[1]-lo)/span)*VH*.92];}),d=catmullRomPath(p);
    s+='<path d="'+d+'" fill="none" stroke="'+scaledColor(vals[j],sc,j)+'" stroke-width="1.95" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>';});
  return s+"</svg>";}
function networkSVG(){var s=openStroke("network"),rows=5,cols=8,spacing=28,rowH=spacing*Math.sqrt(3)/2,x0=-18,y0=2,nodes=[],vals=[],edges=[],jit=spacing*.10;
  for(var r=0;r<rows;r++)for(var c=0;c<cols;c++){var jx=jit*Math.sin((r+1)*2.17+c*1.31),jy=jit*Math.cos((c+1)*1.73+r*1.19),x=x0+c*spacing+(r%2)*spacing*.5+jx,y=y0+r*rowH+jy,v=field(x/VW,y/VH);nodes.push([x,y,v]);vals.push(v);}
  for(var a=0;a<nodes.length;a++)for(var b=a+1;b<nodes.length;b++){var d=Math.hypot(nodes[a][0]-nodes[b][0],nodes[a][1]-nodes[b][1]);if(d<=spacing*1.2)edges.push([a,b]);}
  var sc=demoScale(vals);edges.forEach(function(e){s+='<line x1="'+nodes[e[0]][0].toFixed(2)+'" y1="'+nodes[e[0]][1].toFixed(2)+'" x2="'+nodes[e[1]][0].toFixed(2)+'" y2="'+nodes[e[1]][1].toFixed(2)+'" stroke="var(--dm-gray-7,#adb5bd)" stroke-width=".72" stroke-linecap="round" opacity=".72" vector-effect="non-scaling-stroke"/>';});
  nodes.forEach(function(nd,i){s+='<circle cx="'+nd[0].toFixed(2)+'" cy="'+nd[1].toFixed(2)+'" r="3.55" fill="'+scaledColor(vals[i],sc,i)+'" stroke="var(--dm-bg-page,#fff)" stroke-width=".7" vector-effect="non-scaling-stroke"/>';});
  return s+"</svg>";}
function ridgeProfile(row,x,rows){var drift=.34+.26*row/(rows-1)+.035*Math.sin(row*.77),offs=[-.18,-.045,.12,.27],v=0,bn=2+(row%3);
  for(var j=0;j<bn;j++){var ctr=drift+offs[j]+.025*Math.sin((row+1)*(j+1)*.83),w=.070+.020*((row+j)%4)+.012*j,h=.46+.18*((row*2+j*3)%5)/4+(j===1?.20:0);v+=h*Math.exp(-((x-ctr)/w)*((x-ctr)/w));}
  return Math.max(0,v+.035*Math.sin(6.283*(x*1.5+row*.07)));}
function ridgelineSVG(){var rows=11,rowGap=8.6,peakH=rowGap*1.6,s=openStroke("ridgeline"),profiles=[],rowVals=[];
  for(var r=0;r<rows;r++){var prof=[],peak=0;for(var i=0;i<RIDGE_SAMPLES;i++){var x=-.04+i*(1.08/(RIDGE_SAMPLES-1)),v=ridgeProfile(r,x,rows);prof.push([x,v]);peak=Math.max(peak,v);}profiles.push({p:prof,peak:peak||1});rowVals.push(r/(rows-1));}
  var sc=demoScale(rowVals,{angles:rowVals}),base0=VH-rowGap*(rows-1);
  profiles.forEach(function(row,r){var base=base0+r*rowGap,pts=row.p.map(function(p){return [p[0]*VW,base-(p[1]/row.peak)*peakH];}),d=catmullRomPath(pts);
    d+="L"+(row.p[row.p.length-1][0]*VW).toFixed(2)+" "+base.toFixed(2)+"L"+(row.p[0][0]*VW).toFixed(2)+" "+base.toFixed(2)+"Z";
    s+='<path d="'+d+'" fill="'+scaledColor(rowVals[r],sc,r)+'" stroke="var(--dm-bg-page,#fff)" stroke-width="1" opacity=".96" vector-effect="non-scaling-stroke"/>';});
  return s+"</svg>";}
function quiverSVG(){var rows=7,cols=10,s=openStroke("quiver"),arrows=[],vals=[],angs=[];
  for(var r=0;r<rows;r++)for(var c=0;c<cols;c++){var x=(c+.5+(r%2)*.5)/(cols+.5),y=(r+.5)/rows,v=flowVec(x,y),m=Math.hypot(v[0],v[1])||1;arrows.push([x*VW,y*VH,v[0]/m,-v[1]/m,m]);vals.push(m);angs.push((Math.atan2(v[1],v[0])+Math.PI)/6.283);}
  var sc=demoScale(vals,{angles:angs}),lo=Math.min.apply(null,vals),hi=Math.max.apply(null,vals),span=hi-lo||1;
  arrows.forEach(function(a,i){var magT=(vals[i]-lo)/span,len=7.2+magT*(13.8-7.2),ux=a[2],uy=a[3],tailX=a[0]-ux*len*.5,tailY=a[1]-uy*len*.5,tipX=a[0]+ux*len*.5,tipY=a[1]+uy*len*.5,headLen=4.6,headHalf=headLen/2.6,xBase=tipX-ux*headLen,yBase=tipY-uy*headLen,px=-uy,py=ux,col=scaledColor(vals[i],sc,i);
    s+='<path d="M'+tailX.toFixed(2)+' '+tailY.toFixed(2)+'L'+xBase.toFixed(2)+' '+yBase.toFixed(2)+'" fill="none" stroke="'+col+'" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>';
    s+='<polygon points="'+tipX.toFixed(2)+','+tipY.toFixed(2)+' '+(xBase+px*headHalf).toFixed(2)+','+(yBase+py*headHalf).toFixed(2)+' '+(xBase-px*headHalf).toFixed(2)+','+(yBase-py*headHalf).toFixed(2)+'" fill="'+col+'"/>';});
  return s+"</svg>";}
function waffleSVG(){var rows=9,cols=14,s=openArea("waffle"),vals=[],cells=[];
  for(var r=0;r<rows;r++)for(var c=0;c<cols;c++){var x=(c+.5)/cols,y=(r+.5)/rows;cells.push([c,r]);vals.push(field(x,y));}
  var sc=demoScale(vals),cw=VW/cols,ch=VH/rows,gap=1.45;
  cells.forEach(function(cell,i){var x=cell[0]*cw+gap*.5,y=cell[1]*ch+gap*.5;s+='<rect x="'+x.toFixed(2)+'" y="'+y.toFixed(2)+'" width="'+(cw-gap).toFixed(2)+'" height="'+(ch-gap).toFixed(2)+'" rx="1.5" fill="'+scaledColor(vals[i],sc,i)+'"/>';});
  return s+"</svg>";}

var RENDER={isolines:isolinesSVG,scatter:scatterSVG,streamlines:streamlinesSVG,hexbin:hexbinSVG,
  bars:barsSVG,mosaic:mosaicSVG,lines:linesSVG,network:networkSVG,ridgeline:ridgelineSVG,quiver:quiverSVG,waffle:waffleSVG};
function demoName(t){for(var i=0;i<DEMOS.length;i++)if(DEMOS[i].key===t)return DEMOS[i].name;return t;}
function glyph(t){var c='viewBox="0 0 24 16" aria-hidden="true"';
  if(t==="scatter")return '<svg '+c+'><circle cx="6" cy="11" r="2" fill="currentColor"/><circle cx="12" cy="6" r="2" fill="currentColor"/><circle cx="18" cy="10" r="2" fill="currentColor"/></svg>';
  if(t==="signal")return '<svg '+c+'><path d="M2 10C5 2 8 14 11 8S17 2 22 9" fill="none" stroke="currentColor" stroke-width="2"/></svg>';
  if(t==="streamlines")return '<svg '+c+'><path d="M2 12C6 2 10 14 14 6S20 4 22 10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  if(t==="isolines")return '<svg '+c+'><path d="M3 12C8 4 14 14 21 5M3 7C9 2 14 10 21 3" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>';
  if(t==="bars")return '<svg '+c+'><rect x="4" y="7" width="3" height="6" fill="currentColor"/><rect x="10" y="3" width="3" height="10" fill="currentColor" opacity=".75"/><rect x="16" y="9" width="3" height="4" fill="currentColor" opacity=".55"/></svg>';
  if(t==="hexbin")return '<svg '+c+'><polygon points="8,3 14,3 18,8 14,13 8,13 4,8" fill="currentColor"/></svg>';
  if(t==="mosaic")return '<svg '+c+'><rect x="3" y="3" width="7" height="10" fill="currentColor"/><rect x="11" y="3" width="10" height="5" fill="currentColor"/><rect x="11" y="9" width="10" height="4" fill="currentColor"/></svg>';
  if(t==="lines")return '<svg '+c+'><path d="M2 12 8 5 14 9 22 3" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M2 8 8 12 14 6 22 10" fill="none" stroke="currentColor" stroke-width="1.7" opacity=".6"/></svg>';
  if(t==="network")return '<svg '+c+'><line x1="5" y1="4" x2="18" y2="6" stroke="currentColor" stroke-width="1"/><line x1="18" y1="6" x2="9" y2="13" stroke="currentColor" stroke-width="1"/><circle cx="5" cy="4" r="2" fill="currentColor"/><circle cx="18" cy="6" r="2" fill="currentColor"/><circle cx="9" cy="13" r="2" fill="currentColor"/></svg>';
  if(t==="ridgeline")return '<svg '+c+'><path d="M2 12C6 5 9 8 12 4S18 6 22 2L22 14L2 14Z" fill="currentColor"/><path d="M2 15H22" stroke="currentColor" stroke-width="1" opacity=".55"/></svg>';
  if(t==="quiver")return '<svg '+c+'><path d="M4 12L10 7M9 7L10 7L10 8M14 11L20 5M19 5L20 5L20 6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>';
  if(t==="polar_heat")return '<svg '+c+'><path d="M12 8m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" fill="currentColor" opacity=".35"/><path d="M12 8L12 1A7 7 0 0 1 19 8Z" fill="currentColor"/></svg>';
  if(t==="waffle")return '<svg '+c+'><rect x="4" y="3" width="4" height="4" rx="1" fill="currentColor"/><rect x="10" y="3" width="4" height="4" rx="1" fill="currentColor" opacity=".75"/><rect x="16" y="3" width="4" height="4" rx="1" fill="currentColor" opacity=".55"/><rect x="4" y="9" width="4" height="4" rx="1" fill="currentColor" opacity=".6"/><rect x="10" y="9" width="4" height="4" rx="1" fill="currentColor"/><rect x="16" y="9" width="4" height="4" rx="1" fill="currentColor" opacity=".8"/></svg>';
  if(t==="contours")return '<svg '+c+'><rect x="3" y="3" width="18" height="10" fill="currentColor" opacity=".3"/><rect x="6" y="5" width="12" height="6" fill="currentColor" opacity=".55"/><rect x="9" y="6" width="6" height="4" fill="currentColor"/></svg>';
  if(t==="terrain")return '<svg '+c+'><rect x="3" y="3" width="18" height="10" fill="currentColor" opacity=".35"/><rect x="7" y="4" width="10" height="8" fill="currentColor" opacity=".7"/></svg>';
  return '<svg '+c+'><rect x="3" y="3" width="5" height="10" fill="currentColor"/><rect x="9.5" y="3" width="5" height="10" fill="currentColor" opacity=".72"/><rect x="16" y="3" width="5" height="10" fill="currentColor" opacity=".44"/></svg>';}

// ── strip ──
function gradientCSS(){var s=stops(),lev=LEVELS[state.level],parts=[];
  if(lev){for(var i=0;i<lev;i++){var col=rampColorAt(i/(lev-1),{});parts.push(col+" "+(i/lev*100).toFixed(3)+"%");parts.push(col+" "+((i+1)/lev*100).toFixed(3)+"%");}}
  else{s.forEach(function(col,i){parts.push((state.bw?gray(col):col)+" "+(i/(s.length-1)*100).toFixed(3)+"%");});}
  return "linear-gradient(90deg,"+parts.join(",")+")";}

// ── rail ──
function mini(key){var m=MAPS[key],v=m.variants[m.default_variant],s=v.stops,parts=[];
  for(var i=0;i<12;i++)parts.push(s[Math.round(i*(s.length-1)/11)]+" "+(i/11*100).toFixed(2)+"%");
  return '<span class="mini" style="background-image:linear-gradient(90deg,'+parts.join(",")+')"></span>';}
function railHTML(){var h="";GROUPS.forEach(function(g){h+='<div class="fh">'+esc(g[0])+'</div>';
  g[1].forEach(function(k){h+='<button class="ri'+(k===state.key?" on":"")+'" type="button" data-k="'+k+'">'+mini(k)+'<span class="nm">'+esc(MAPS[k].name)+'</span></button>';});});return h;}
function wireRail(){document.querySelectorAll("#dm-cmap-exp .ri").forEach(function(e){e.onclick=function(){
  state.key=e.dataset.k;state.rev=false;state.bw=false;
  document.getElementById("cx-rail").innerHTML=railHTML();wireRail();renderDetail();};});}

// ── chips + demos ──
function chipHTML(){return variant().chips.map(function(c){return '<span class="a11y-chip '+esc(c.cls)+'" tabindex="0" role="note" data-tip="'+esc(c.tip)+'"><span class="a-dot" aria-hidden="true"></span><span class="a-label">'+esc(c.label)+'</span><span class="a-num">'+esc(c.num)+'</span></span>';}).join("");}
function visibleDemos(){return state.demos.slice(0,state.layout);}
function demoCard(t){var body=CANVAS_DEMOS[t]?canvasShell(t):(RENDER[t]||scatterSVG)();return '<div class="demo-card"><span class="demo-label">'+esc(demoName(t))+'</span><div class="demo-flex">'+body+'</div></div>';}
function demoGridHTML(){return '<div class="demo-grid layout-'+state.layout+(state.bw?" gs":"")+'">'+visibleDemos().map(demoCard).join("")+'</div>';}
function demoToolsHTML(){var chips=DEMOS.map(function(d){return '<button class="demo-chip'+(state.demos.indexOf(d.key)>=0?" on":"")+'" type="button" data-demo-pick="'+esc(d.key)+'">'+glyph(d.key)+'<span>'+esc(d.name)+'</span></button>';}).join("");
  return '<div class="demo-tools"><span class="field demo-field"><span class="cl">Demos</span><span class="demo-picker">'+chips+'</span></span>'
    +'<span class="field"><span class="cl">Layout</span><span class="seg"><button type="button" data-layout="4" class="'+(state.layout===4?"on":"")+'">2×2</button><button type="button" data-layout="6" class="'+(state.layout===6?"on":"")+'">2×3</button><button type="button" data-layout="9" class="'+(state.layout===9?"on":"")+'">3×3</button></span></span></div>';}

// ── code snippet + syntax highlight ──
function codeText(){var name=map().key+(state.rev?"_r":""),lev=LEVELS[state.level],lines=["import matplotlib.pyplot as plt","import dartwork_mpl as dm  # registers dc.* colormaps",""];
  if(lev){lines.push('cmap = plt.get_cmap("'+name+'", '+lev+')');lines.push("plt.imshow(Z, cmap=cmap)");}
  else lines.push('plt.imshow(Z, cmap="'+name+'")');
  if(state.bw)lines.push("# B&W toggle is a grayscale preview of the same cmap.");
  return lines.join("\n");}
function hi(code){return esc(code).replace(/^#.*$/gm,function(s){return '<span class="c1">'+s+"</span>";})
  .replace(/\b(import|as)\b/g,'<span class="kn">$1</span>').replace(/\b(True|False|None)\b/g,'<span class="k">$1</span>')
  .replace(/(&quot;[^&]*?&quot;|'[^']*?')/g,'<span class="s1">$1</span>').replace(/\b(\d+)\b/g,'<span class="mi">$1</span>');}

// ── controls ──
function controlsHTML(){var label="Levels "+LEVEL_LABEL[state.level];
  return '<button class="tgl'+(state.rev?" on":"")+'" data-tgl="rev" type="button"><span class="tgl-l">Reverse</span><span class="tgl-tr"><span class="tgl-kn"></span></span></button>'
    +'<span class="field"><span class="cl">Levels</span><input type="range" min="0" max="'+(LEVELS.length-1)+'" step="1" value="'+state.level+'" id="lev" class="crng"><b class="cval" id="levv">'+esc(label)+'</b></span>'
    +'<button class="tgl'+(state.bw?" on":"")+'" data-tgl="bw" type="button"><span class="tgl-l">B&amp;W</span><span class="tgl-tr"><span class="tgl-kn"></span></span></button>';}
function metaHTML(){var m=map();return '<div class="meta"><div><span class="m-l">How it&rsquo;s built</span> '+esc(m.recipe)+'</div><div><span class="m-l">Good for</span> '+esc(m.good_for)+'</div></div>';}

// ── toast + copy ──
function toast(msg){var el=document.getElementById("cx-toast");if(!el){el=document.createElement("div");el.id="cx-toast";el.className="dm-toast";document.body.appendChild(el);}el.textContent=msg;el.classList.add("show");clearTimeout(window._cmapToast);window._cmapToast=setTimeout(function(){el.classList.remove("show");},1100);}
function copy(txt,el){if(navigator.clipboard)navigator.clipboard.writeText(txt);toast(txt+" copied");if(el){el.classList.add("copied");setTimeout(function(){el.classList.remove("copied");},900);}}

function paint(){var d=document.getElementById("cx-detail");
  d.querySelector(".a11y-chips").innerHTML=chipHTML();
  var g=d.querySelector(".grad");g.style.backgroundImage=gradientCSS();g.classList.toggle("gs",state.bw);
  var host=d.querySelector(".demo-host");host.innerHTML=demoGridHTML();renderCanvases(host);
  d.querySelector(".code").innerHTML="<pre>"+hi(codeText())+"</pre>";
  d.querySelector(".meta-host").innerHTML=metaHTML();}
function sameList(a,b){return a.length===b.length&&a.every(function(v,i){return v===b[i];});}
function setLayout(n){var wasDefault=sameList(state.demos,DEFAULT[4])||sameList(state.demos,DEFAULT[6])||sameList(state.demos,DEFAULT[9]);
  state.layout=n;if(wasDefault)state.demos=DEFAULT[n].slice();renderDetail();}
function wireControls(d){
  d.querySelectorAll(".tgl[data-tgl]").forEach(function(b){b.onclick=function(){var k=b.dataset.tgl;
    if(k==="rev")state.rev=!state.rev;if(k==="bw")state.bw=!state.bw;renderDetail();};});
  d.querySelectorAll("[data-layout]").forEach(function(b){b.onclick=function(){setLayout(+b.dataset.layout);};});
  d.querySelectorAll("[data-demo-pick]").forEach(function(b){b.onclick=function(){var k=b.dataset.demoPick,idx=state.demos.indexOf(k);
    if(idx>=0){if(state.demos.length===1)return;state.demos.splice(idx,1);}else state.demos.push(k);renderDetail();};});
  var lev=d.querySelector("#lev");if(lev)lev.oninput=function(){state.level=+lev.value;var v=d.querySelector("#levv");if(v)v.textContent="Levels "+LEVEL_LABEL[state.level];paint();};}
function renderDetail(){var m=map(),d=document.getElementById("cx-detail");
  d.innerHTML='<div class="d-ey">'+esc(m.group)+'</div><div class="d-title"><h3>'+esc(m.name)+'</h3><button class="d-key" type="button" title="copy the colormap name">'+esc(m.key)+'</button><span class="a11y-chips"></span></div>'
    +'<p class="d-use">'+esc(m.intent)+'</p><div class="d-bar">'+controlsHTML()+'</div>'+demoToolsHTML()
    +'<div class="grad-wrap"><div class="grad"></div></div><div class="demo-host"></div><div class="code highlight"></div><div class="meta-host"></div>';
  d.querySelector(".d-key").onclick=function(){copy(m.key,this);};wireControls(d);paint();}

document.getElementById("cx-count").textContent=D.counts.total+" colormaps — "+D.counts.sequential+" sequential, "+D.counts.multi_hue+" multi-hue, "+D.counts.diverging+" diverging, "+D.counts.cyclic+" cyclic";
document.getElementById("cx-rail").innerHTML=railHTML();wireRail();renderDetail();watchCanvasDpr();
})();</script>
</div>
"""


if __name__ == "__main__":
    main()
