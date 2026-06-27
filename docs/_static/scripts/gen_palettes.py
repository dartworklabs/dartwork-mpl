#!/usr/bin/env python3
"""Generate dartwork's discrete categorical palette family — CIELAB via the
battle-tested colorspacious lib (no hand-rolled color math).

Colors are GENERATED (not eyeballed): per-band hue plan (narrow->wide spectral
width) + an EVEN L* lightness ladder (8 distinct lightness => guaranteed
grayscale/B&W separability, which also confers most CVD-safety since CVD
preserves luminance), chroma reduced to fit the sRGB gamut (L* + hue kept
exact). "fixed" palettes (e.g. Okabe-Ito) pass hex through and are only
verified. Then VERIFY min ΔL* + CVD (deuter/protan/tritan, severity 100).

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
    return rgb1_to_hex(rgb)


TEAL_L, TEAL_C, TEAL_H = lab_LCh("#12a594")  # house teal in CIELAB


def ladder(lo, hi, n=8):
    return [round(lo + (hi - lo) * i / (n - 1), 2) for i in range(n)]


STAG = [0, 4, 2, 6, 1, 5, 3, 7]  # staggered cycle order over 8 L* rungs
DUO = [0, 4, 1, 5, 2, 6, 3, 7]  # warm,cool,warm,cool... interleave
SEQ = list(range(8))  # monotonic ramp


def seq_chroma(peak=42, base=16):
    return [base + (peak - base) * math.sin(math.pi * i / 7) for i in range(8)]


# ---- the family: band -> plan. spectral width grows narrow -> wide ----
# Each: Ls (even L* ladder), Hs (CIELAB hues; None = neutral), Cs, order.
# "fixed": pass-through hex list (verify only).
PLANS = {
    # SEQUENTIAL single-hue ramps (very narrow)
    "teal_seq": {
        "Ls": ladder(32, 94),
        "Hs": [TEAL_H] * 8,
        "Cs": seq_chroma(),
        "order": SEQ,
    },
    "indigo_seq": {
        "Ls": ladder(32, 94),
        "Hs": [280] * 8,
        "Cs": seq_chroma(38),
        "order": SEQ,
    },
    "coral_seq": {
        "Ls": ladder(35, 93),
        "Hs": [32] * 8,
        "Cs": seq_chroma(46),
        "order": SEQ,
    },
    # NARROW ANALOGOUS arcs
    "teal_indigo": {
        "Ls": ladder(38, 90),
        "Hs": [195, 215, 240, 258, 272, 288, 300, 315],
        "Cs": [30] * 8,
        "order": STAG,
    },
    "forest": {
        "Ls": ladder(36, 90),
        "Hs": [122, 130, 138, 145, 152, 158, 150, 134],
        "Cs": [33] * 8,
        "order": STAG,
    },
    # MEDIUM duos (warm + cool)
    "warm_cool": {
        "Ls": ladder(38, 90),
        "Hs": [40, 55, 25, 65, 230, 255, 215, 270],
        "Cs": [42, 42, 42, 42, 38, 38, 38, 38],
        "order": DUO,
    },
    # warm side pushed to ORANGE (h≈42–64, not pure red) so teal↔warm becomes a
    # blue-yellow axis that survives protanopia (red side h<35 was the collapse).
    "teal_coral": {
        "Ls": ladder(38, 90),
        "Hs": [184, 194, 178, 200, 48, 60, 44, 68],
        "Cs": [42, 42, 42, 42, 54, 54, 54, 54],
        "order": DUO,
    },
    "blue_orange": {
        "Ls": ladder(38, 90),
        "Hs": [250, 262, 240, 272, 50, 62, 40, 72],
        "Cs": [40, 40, 40, 40, 50, 50, 50, 50],
        "order": DUO,
    },
    # MEDIUM-WIDE balanced default (teal-anchored + 2 neutrals)
    "trustworthy": {
        "Ls": ladder(38, 88),
        "Hs": [TEAL_H, 264, 300, 40, 142, 350, None, None],
        "Cs": [34, 32, 30, 38, 34, 36, 4, 4],
        "order": STAG,
    },
    # MUTED / pastel (soft editorial; low chroma, higher L*)
    "muted": {
        "Ls": ladder(52, 90),
        "Hs": [TEAL_H, 250, 300, 35, 140, 355, 75, 210],
        "Cs": [18] * 8,
        "order": STAG,
    },
    # WIDE spectrum (full hue wheel, vivid)
    "spectrum": {
        "Ls": ladder(40, 88),
        "Hs": [(TEAL_H + 45 * i) % 360 for i in range(8)],
        "Cs": [60] * 8,
        "order": STAG,
    },
    # FIXED accessible — Okabe-Ito CUD 8-color (gold standard; do NOT regenerate)
    "accessible": {
        "fixed": [
            "#000000",
            "#E69F00",
            "#56B4E9",
            "#009E73",
            "#F0E442",
            "#0072B2",
            "#D55E00",
            "#CC79A7",
        ]
    },
    # ── INTENT-based additions (organised by purpose, not spectral width) ──
    # NEUTRAL sequential — hue-free ordered ramp (amount/order, print-bulletproof)
    "gray_seq": {
        "Ls": ladder(22, 92),
        "Hs": [245] * 8,
        "Cs": [0] * 8,
        "order": SEQ,
    },
    # TONE — warm earth / natural (ESG, geography, organic premium)
    "earth": {
        "Ls": ladder(36, 88),
        "Hs": [35, 55, 75, 95, 110, 45, 85, 125],
        "Cs": [30, 30, 28, 26, 26, 30, 26, 24],
        "order": STAG,
    },
    # TONE — deep jewel / premium editorial (rich + dark, vs spectrum's brightness)
    "jewel": {
        "Ls": ladder(30, 86),
        "Hs": [195, 172, 250, 288, 26, 84, 320, 208],
        "Cs": [42] * 8,
        "order": STAG,
    },
    # DIVERGING — symmetric L* tent (ends dark, centre pale). B&W-exempt by design.
    "coolwarm": {
        "Ls": [38, 55, 72, 86, 86, 72, 55, 38],
        "Hs": [258, 254, 250, 246, 32, 28, 24, 20],
        "Cs": [40, 33, 25, 15, 15, 25, 33, 40],
        "order": SEQ,
    },
    "teal_amber_div": {
        "Ls": [38, 55, 72, 86, 86, 72, 55, 38],
        "Hs": [184, 186, 188, 190, 72, 68, 64, 60],
        "Cs": [40, 33, 25, 15, 15, 25, 33, 40],
        "order": SEQ,
    },
    # ── singleton families expanded to 2-3 siblings (each a distinct job) ──
    # NEUTRAL — warm + cool greys beside the pure neutral ramp
    "warm_gray": {
        "Ls": ladder(22, 92),
        "Hs": [70] * 8,
        "Cs": [5] * 8,
        "order": SEQ,
    },
    "cool_gray": {
        "Ls": ladder(22, 92),
        "Hs": [250] * 8,
        "Cs": [6] * 8,
        "order": SEQ,
    },
    # EMPHASIS — single teal-accent + warm-accent (highlight one series, mute rest)
    "focus": {
        "Ls": ladder(34, 90),
        "Hs": [TEAL_H, 250, 250, 250, 250, 250, 250, 250],
        "Cs": [40, 5, 5, 5, 5, 5, 5, 5],
        "order": SEQ,
    },
    "focus_warm": {
        "Ls": ladder(34, 90),
        "Hs": [32, 250, 250, 250, 250, 250, 250, 250],
        "Cs": [46, 5, 5, 5, 5, 5, 5, 5],
        "order": SEQ,
    },
    # BALANCED — corporate (cool/formal, teal-anchored) beside trustworthy
    "corporate": {
        "Ls": ladder(36, 86),
        "Hs": [185, 210, 255, 32, 150, 285, None, None],
        "Cs": [30, 28, 26, 30, 26, 24, 4, 4],
        "order": STAG,
    },
    # MUTED — dusty (deeper, vintage) beside the high-key pastel
    "dusty": {
        "Ls": ladder(40, 78),
        "Hs": [TEAL_H, 250, 300, 35, 140, 355, 75, 210],
        "Cs": [16] * 8,
        "order": STAG,
    },
    # SPECTRUM — bold (curated punchy, uneven hues) beside the full-wheel rainbow
    "bold": {
        "Ls": ladder(36, 84),
        "Hs": [188, 32, 145, 300, 70, 330, 248, 105],
        "Cs": [48] * 8,
        "order": STAG,
    },
}


def build(band):
    p = PLANS[band]
    if "fixed" in p:
        return list(p["fixed"])
    Ls, Hs, Cs, order = p["Ls"], p["Hs"], p["Cs"], p["order"]
    L_by_pos = [None] * 8
    for rung, pos in enumerate(order):
        L_by_pos[pos] = Ls[rung]
    cols = []
    for i in range(8):
        L, H, C = L_by_pos[i], Hs[i], Cs[i]
        cols.append(
            lch_to_hex(L, (8 if H is None else C), (250 if H is None else H))
        )
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


res = {}
for b in PLANS:
    cols = build(b)
    res[b] = {
        "colors": cols,
        "verify": verify(cols),
        "Lstar": [round(hex_to_lab(c)[0], 1) for c in cols],
    }
with open("/tmp/dm_palettes_gen.json", "w") as _f:
    json.dump(res, _f, indent=1)
    _f.write("\n")
print(f"teal CIELAB: L*={TEAL_L:.1f} C*={TEAL_C:.1f} h={TEAL_H:.0f}\n")
print(f"{'band':<13}{'minΔL*':>7}{'deut':>6}{'prot':>6}{'trit':>6}   colors")
for b in PLANS:
    v = res[b]["verify"]
    print(
        f"{b:<13}{v['bw_min_dLstar']:>7.1f}{v['deuter']:>6.1f}{v['protan']:>6.1f}{v['tritan']:>6.1f}   {' '.join(res[b]['colors'])}"
    )
print("\nB&W ok: minΔL* >= ~6 ; CVD ok: min pairwise CAM02-UCS >= ~6-8")
