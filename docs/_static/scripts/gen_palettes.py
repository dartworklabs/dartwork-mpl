#!/usr/bin/env python3
"""Generate dartwork's discrete categorical palette family — CIELAB via the
battle-tested colorspacious lib (no hand-rolled color math).

LLM designers gave good hue families + intent but cannot compute lightness or
CVD reliably, so we GENERATE colors: per-band hue plan (narrow->wide spectral
width) + an EVEN L* ladder (8 distinct lightness => guaranteed grayscale/B&W
separability, which also confers most CVD-safety since CVD preserves luminance),
chroma reduced to fit the sRGB gamut (L* + hue kept exact). Then VERIFY min ΔL*
+ CVD (deuter/protan/tritan, severity 100) via colorspacious.

Output: /tmp/dm_palettes_gen.json + a verification table.
"""

from __future__ import annotations

import json
import math

import numpy as np
from colorspacious import cspace_convert


def hex_to_rgb1(hx):
    return np.array([int(hx[i : i + 2], 16) / 255 for i in (1, 3, 5)])


def rgb1_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(
        *(round(max(0, min(1, c)) * 255) for c in rgb)
    )


def hex_to_lab(hx):
    return cspace_convert(hex_to_rgb1(hx), "sRGB1", "CIELab")


def lab_LCh(hx):
    L, a, b = hex_to_lab(hx)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def lch_to_hex(L, C, h_deg):
    """CIELCh -> hex; reduce C until in sRGB gamut (L*, hue preserved exactly)."""
    h = math.radians(h_deg)
    rgb = None
    for _ in range(80):
        lab = np.array([L, C * math.cos(h), C * math.sin(h)])
        rgb = cspace_convert(lab, "CIELab", "sRGB1")
        if (rgb >= -0.003).all() and (rgb <= 1.003).all():
            break
        C *= 0.97
    return rgb1_to_hex(rgb), round(C, 2)


TEAL_L, TEAL_C, TEAL_H = lab_LCh("#12a594")  # house teal in CIELAB


def ladder(lo, hi, n=8):
    return [round(lo + (hi - lo) * i / (n - 1), 2) for i in range(n)]


STAG = [0, 4, 2, 6, 1, 5, 3, 7]  # staggered cycle order over 8 L* rungs


def build(band):
    if band == "sequential":  # very-narrow: single teal hue ramp
        Ls = ladder(32, 94)
        Hs = [TEAL_H] * 8
        Cs = [
            16 + 26 * math.sin(math.pi * i / 7) for i in range(8)
        ]  # chroma peaks mid
        order = list(range(8))  # monotonic ramp
    elif band == "analogous":  # narrow: teal->blue->indigo (cool arc)
        Ls = ladder(38, 90)
        Hs = [195, 215, 240, 258, 272, 288, 300, 315]
        Cs = [30] * 8
        order = STAG
    elif band == "duo":  # medium: 4 warm + 4 cool
        Ls = ladder(38, 90)
        Hs = [40, 55, 25, 65, 230, 255, 215, 270]
        Cs = [42, 42, 42, 42, 38, 38, 38, 38]
        order = [0, 4, 1, 5, 2, 6, 3, 7]
    elif (
        band == "balanced"
    ):  # medium-wide: teal-anchored even hues + 2 neutrals
        Ls = ladder(38, 88)
        Hs = [
            TEAL_H,
            264,
            300,
            40,
            142,
            350,
            None,
            None,
        ]  # teal,blue,purple,orange,green,red + 2 gray
        Cs = [34, 32, 30, 38, 34, 36, 4, 4]
        order = STAG
    elif band == "spectrum":  # widest: full wheel, vivid, teal-anchored
        Ls = ladder(40, 88)
        Hs = [(TEAL_H + 45 * i) % 360 for i in range(8)]
        Cs = [60] * 8
        order = STAG
    L_by_pos = [None] * 8
    for rung, pos in enumerate(order):
        L_by_pos[pos] = Ls[rung]
    cols = []
    for i in range(8):
        L, H, C = L_by_pos[i], Hs[i], Cs[i]
        hx, _ = lch_to_hex(
            L, (8 if H is None else C), (250 if H is None else H)
        )
        cols.append(hx)
    return cols


def verify(cols):
    Ls = sorted(hex_to_lab(c)[0] for c in cols)
    dmin = min(Ls[i + 1] - Ls[i] for i in range(len(Ls) - 1))
    out = {"bw_min_dLstar": round(dmin, 1)}
    rgb = np.array([hex_to_rgb1(c) for c in cols])
    for cvd in ("deuteranomaly", "protanomaly", "tritanomaly"):
        sim = cspace_convert(
            rgb,
            {"name": "sRGB1+CVD", "cvd_type": cvd, "severity": 100},
            "CAM02-UCS",
        )
        d = [
            np.linalg.norm(sim[i] - sim[j])
            for i in range(8)
            for j in range(i + 1, 8)
        ]
        out[cvd[:6]] = round(min(d), 1)
    return out


BANDS = ["sequential", "analogous", "duo", "balanced", "spectrum"]
res = {}
for b in BANDS:
    cols = build(b)
    res[b] = {
        "colors": cols,
        "verify": verify(cols),
        "Lstar": [round(hex_to_lab(c)[0], 1) for c in cols],
    }
with open("/tmp/dm_palettes_gen.json", "w") as _f:
    json.dump(res, _f, indent=1)
print(f"teal CIELAB: L*={TEAL_L:.1f} C*={TEAL_C:.1f} h={TEAL_H:.0f}\n")
print(f"{'band':<13}{'minΔL*':>7}{'deut':>6}{'prot':>6}{'trit':>6}   colors")
for b in BANDS:
    v = res[b]["verify"]
    print(
        f"{b:<13}{v['bw_min_dLstar']:>7.1f}{v['deuter']:>6.1f}{v['protan']:>6.1f}{v['tritan']:>6.1f}   {' '.join(res[b]['colors'])}"
    )
print("\nB&W ok: minΔL* >= ~8 ; CVD ok: min pairwise CAM02-UCS >= ~8-10")
