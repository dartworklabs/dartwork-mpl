"""Curated dartwork discrete color sets (dc.*) — hand-tuned SSOT.

``CURATED`` contains two Model B surfaces:

- 11 qualitative sets shown in the categorical explorer rail.
- 4 absorbed diverging canonical 8-color forms. These stay here so
  ``dc.<name>0`` tokens and ``dm.colors("<name>", n=8)`` resolve through the
  existing loader, but explorer builders filter them out with
  ``CURATED_QUALITATIVE_ORDER``.

The single-hue sequential ladders live in ``_generated.PALETTE``.
"""

from __future__ import annotations

CURATED_QUALITATIVE_ORDER: tuple[str, ...] = (
    "trustworthy",
    "vivid",
    "neon",
    "pastel",
    "dusty",
    "ember",
    "earth",
    "jewel",
    "forest",
    "teal_accent",
    "coral_accent",
)

CURATED_DIVERGING_ORDER: tuple[str, ...] = (
    "blue_red",
    "blue_orange",
    "teal_amber",
    "green_purple",
)

CURATED_ORDER: tuple[str, ...] = (
    CURATED_QUALITATIVE_ORDER + CURATED_DIVERGING_ORDER
)

CURATED: dict[str, tuple[str, ...]] = {
    "trustworthy": (
        "#06655a",
        "#72a6db",
        "#8076a9",
        "#ffb8a5",
        "#467647",
        "#ef9dc2",
        "#83919c",
        "#d0dfeb",
    ),
    "vivid": (
        "#04696f",
        "#05a7f7",
        "#cb5a51",
        "#81d383",
        "#9455a6",
        "#cbac4d",
        "#8f82dd",
        "#51eabb",
    ),
    "neon": (
        "#045f5e",
        "#02a5f5",
        "#a357c4",
        "#ffa9db",
        "#5f6c02",
        "#e4a431",
        "#5584f8",
        "#08f2cc",
    ),
    "pastel": (
        "#538789",
        "#aeb9da",
        "#bc918b",
        "#c0e0c7",
        "#a68398",
        "#d3c8a7",
        "#8bafc8",
        "#dbeaf6",
    ),
    "dusty": (
        "#346162",
        "#8992ae",
        "#916d68",
        "#9cb8a2",
        "#7c5f71",
        "#aba285",
        "#69889e",
        "#b4c3cf",
    ),
    "ember": (
        "#942732",
        "#e6835f",
        "#9e6b29",
        "#d9c778",
        "#536a26",
        "#ff91ab",
        "#c17746",
        "#d0dfeb",
    ),
    "earth": (
        "#80443a",
        "#cb9375",
        "#94744b",
        "#d6c898",
        "#666a3d",
        "#e5a48e",
        "#a0895f",
        "#d1e3b7",
    ),
    "jewel": (
        "#02504f",
        "#25a88a",
        "#0375a0",
        "#b3bdfe",
        "#963c3e",
        "#caa65e",
        "#a26eb0",
        "#42ecfb",
    ),
    "forest": (
        "#475b26",
        "#8cac74",
        "#5b8554",
        "#a4daa8",
        "#37734d",
        "#80c6a0",
        "#619b70",
        "#c7eeb4",
    ),
    "teal_accent": (
        "#0a7b6e",
        "#767e85",
        "#868f96",
        "#97a0a7",
        "#a8b1b8",
        "#b9c3ca",
        "#cbd4dc",
        "#dde7ee",
    ),
    "coral_accent": (
        "#b54b43",
        "#767e85",
        "#868f96",
        "#97a0a7",
        "#a8b1b8",
        "#b9c3ca",
        "#cbd4dc",
        "#dde7ee",
    ),
    "blue_red": (
        "#055f8b",
        "#3b8bba",
        "#81b7db",
        "#bcdcf1",
        "#f5cec9",
        "#dfa19c",
        "#bb6f6e",
        "#943d45",
    ),
    "blue_orange": (
        "#036085",
        "#2485c2",
        "#17b2e3",
        "#b1cfff",
        "#a9532c",
        "#cb8043",
        "#fea18a",
        "#ffddba",
    ),
    "teal_amber": (
        "#06655c",
        "#209389",
        "#74bdb6",
        "#b4e0db",
        "#ebd3bc",
        "#d0a987",
        "#aa7951",
        "#844c21",
    ),
    "green_purple": (
        "#09581b",
        "#56875a",
        "#99b89e",
        "#d8e6da",
        "#e8dfee",
        "#b9abcc",
        "#8573aa",
        "#523f87",
    ),
}

CURATED_META: dict[str, dict[str, str]] = {
    "trustworthy": {
        "label": "Trustworthy",
        "family": "Qualitative",
        "band": "medium-wide · teal + neutrals",
        "intent": "The everyday DEFAULT — reach for this first for 4 to 8 "
        "unrelated categories. Six evenly-spaced hues anchored on "
        "house teal plus two neutrals, muted enough to stay "
        "report-grade yet distinct enough that the series never "
        "tangle or shout.",
        "design": "6 evenly-spaced hues anchored on house teal + 2 neutrals, "
        "muted chroma (no neon), staggered even L* ladder 38→88.",
        "application": "Everything — line, bar, scatter; works on white pages "
        "and in tables. The general-purpose cycle.",
        "bw": "min ΔL* 7.1",
        "cvd": "d11.7 / p9.9 / t6.8",
        "kind": "qualitative",
    },
    "vivid": {
        "label": "Vivid",
        "family": "Qualitative",
        "band": "widest · full wheel",
        "intent": "MANY unrelated categories — up to eight — where color alone must "
        "separate everything and maximum distinctness matters more than "
        "restraint. An even, vivid rainbow spread for legends, maps, and "
        "crowded categorical charts that need every series apart.",
        "design": "8 hues evenly spaced 45° around the full wheel (teal-anchored), "
        "high chroma, staggered even L* ladder 40→88 so it still survives "
        "B&W.",
        "application": "8-category scatter, side-by-side bars, editorial "
        "infographics. Vivid, confident tone.",
        "bw": "min ΔL* 6.1",
        "cvd": "d4.9 / p9.5 / t10.9",
        "kind": "qualitative",
    },
    "neon": {
        "label": "Neon",
        "family": "Qualitative",
        "band": "max chroma · electric",
        "intent": "MAXIMUM chroma — the loudest legal categorical, at the sRGB gamut "
        "edge. Up to 8 vivid categories on dark UI or hero moments.",
        "design": "Electric hues at the per-rung gamut ceiling; CVD-confusable pairs "
        "thrown far apart in L* so loudness never costs separability.",
        "application": "Dark-mode dashboards, brand hero charts, few-category small "
        "multiples.",
        "bw": "min ΔL* 7.0",
        "cvd": "d8.3 / p10.4 / t8.9",
        "kind": "qualitative",
    },
    "pastel": {
        "label": "Pastel",
        "family": "Muted",
        "band": "medium-wide · low chroma",
        "intent": "A soft, editorial categorical set for dense dashboards or "
        "backgrounds where vivid color would shout. High-key pastels "
        "carry 4 to 8 categories quietly, keeping the data readable "
        "without competing for attention on an already busy page.",
        "design": "Same 8-hue spread as the default but low chroma (~18) and a "
        "higher L* band 52→90. Calm, magazine-like. (B&W is softer by "
        "design.)",
        "application": "Dashboards, small multiples, annotation-heavy figures. "
        "Pair with one vivid accent for emphasis.",
        "bw": "min ΔL* 5.4",
        "cvd": "d5.9 / p4.8 / t6.3",
        "kind": "qualitative",
    },
    "dusty": {
        "label": "Dusty",
        "family": "Muted",
        "band": "deep · vintage muted",
        "intent": "A deeper, more vintage muted set — lower lightness than the "
        "high-key Pastel. Built for moody editorial, dark-on-cream "
        "layouts, and retro themes where soft-but-saturated tones suit "
        "the page better than bright, high-key color.",
        "design": "Same 8-hue spread as Muted but a mid L* band 40→78 and low "
        "chroma ~16. Calm but with more body than pastel.",
        "application": "Dense editorial, atmospheric dashboards, retro / vintage "
        "themes. (B&W softer by design.)",
        "bw": "min ΔL* 5.5",
        "cvd": "d6.2 / p5.1 / t6.5",
        "kind": "qualitative",
    },
    "ember": {
        "label": "Ember",
        "family": "Tone",
        "band": "warm · vibrant",
        "intent": "The saturated WARM categorical — brick, coral, ochre, gold, "
        "olive, pink, and clay plus a cool-neutral anchor. Golden-hour "
        "energy without earth's muteness.",
        "design": "All-warm hues carry little CVD margin, so the even L* stagger + "
        "a cool anchor + one green do the separating.",
        "application": "Warmth-themed dashboards, seasonal / energy / hospitality "
        "decks.",
        "bw": "min ΔL* 7.6",
        "cvd": "d5.3 / p4.9 / t8.1",
        "kind": "qualitative",
    },
    "earth": {
        "label": "Earth",
        "family": "Tone",
        "band": "warm · earthy",
        "intent": "Categorical series in a warm, organic register — ESG and "
        "sustainability, geography, agriculture, or premium-natural "
        "brands. Earthy, grounded hues that feel editorial and separate a "
        "handful of categories without ever looking corporate.",
        "design": "Terracotta, ochre, olive, sand, sage, clay (h 35→125, muted "
        "chroma ~26-30), staggered even L* ladder 36→88.",
        "application": "Multi-series line/bar/area for environmental or earthy "
        "topics. Calm, grounded, magazine-like.",
        "bw": "min ΔL* 7.2",
        "cvd": "d6.1 / p6.3 / t7.5",
        "kind": "qualitative",
    },
    "jewel": {
        "label": "Jewel",
        "family": "Tone",
        "band": "deep · rich saturation",
        "intent": "Rich, deep, saturated variety for premium or luxury editorial. "
        "Distinct from Vivid by going darker and deeper rather than "
        "brighter, so many categories stay separable while the whole set "
        "keeps an upscale, high-contrast mood.",
        "design": "Emerald, sapphire, indigo, vermilion, topaz, amethyst, deep "
        "teal/cyan (high chroma 42), even L* ladder 30→86. Retuned to "
        "clear the protanopia collapse.",
        "application": "Up to 8 categories where you want depth + luxury. ⚠ Softest "
        "CVD of the set (protan ~4) — for strict accessibility use "
        "Accessible or a Duo.",
        "bw": "min ΔL* 7.8",
        "cvd": "d7.6 / p4.2 / t16.3",
        "kind": "qualitative",
    },
    "forest": {
        "label": "Forest",
        "family": "Qualitative",
        "band": "narrow · green arc",
        "intent": "A few related series in a natural, organic register — ESG, "
        "agriculture, environment, growth themes. A green arc held to "
        "one hue family and separated by lightness, so the lines read as "
        "cohesive and calm rather than scattered or noisy.",
        "design": "A ~40° green arc (yellow-green→teal-green) on a staggered even "
        "L* ladder 36→90 — one hue family, lightness-separated.",
        "application": "Multi-series line / area for environmental or organic "
        "topics. Calm, cohesive.",
        "bw": "min ΔL* 7.7",
        "cvd": "d7.8 / p6.8 / t8.7",
        "kind": "qualitative",
    },
    "teal_accent": {
        "label": "Teal Accent",
        "family": "Emphasis",
        "band": "1 teal accent + 7 neutrals",
        "intent": "Highlight ONE series while everything else recedes to gray "
        "— the storytelling staple, color the one thing. House teal "
        "marks the salient series and graded neutrals carry the "
        "rest, keeping attention exactly where you point it.",
        "design": "Slot 0 = house teal (salient), slots 1-7 = graded neutrals "
        "on an even L* ladder 46→91. Pair with Coral Accent for the "
        "warm-highlight version, or combine the two accent colors "
        "to highlight a second series.",
        "application": "Single-series emphasis in line / bar charts, "
        "explanatory figures, slide builds.",
        "bw": "min ΔL* 6.2",
        "cvd": "d5.8 / p5.7 / t5.8",
        "kind": "qualitative",
    },
    "coral_accent": {
        "label": "Coral Accent",
        "family": "Emphasis",
        "band": "1 warm accent + 7 neutrals",
        "intent": "Highlight one series with a WARM coral accent instead of "
        "teal — for warmth, alerts, or when teal clashes with the "
        "content. Coral marks the salient line and graded neutrals "
        "mute everything else quietly into the background.",
        "design": "Slot 0 = coral (h≈32, salient), slots 1-7 = graded "
        "neutrals, even L* ladder 46→91.",
        "application": "Single-series emphasis where a warm highlight reads "
        "better (e.g., risk / attention).",
        "bw": "min ΔL* 6.2",
        "cvd": "d5.8 / p5.7 / t5.8",
        "kind": "qualitative",
    },
    "blue_red": {
        "label": "Blue ↔ Red",
        "family": "Diverging",
        "band": "two-ended · pale center",
        "intent": "Blue ↔ Red is the designed 8-color canonical discrete form "
        "for the continuous dc.blue_red diverging family. Use it for "
        "signed or centered quantities where both direction and "
        "magnitude matter.",
        "design": "Symmetric L* tent (dark ends → pale center), blue (h≈250) ↔ "
        "red (h≈25). Excellent CVD. NOT a categorical set — the order "
        "IS the meaning.",
        "application": "Correlation matrices, change heatmaps, anomaly scales, "
        "and other midpoint-aware encodings.",
        "bw": "min ΔL* 0.0",
        "cvd": "d12.6 / p13.6 / t14.2",
        "kind": "diverging",
    },
    "blue_orange": {
        "label": "Blue ↔ Orange",
        "family": "Diverging",
        "band": "two-ended · pale center",
        "intent": "Blue ↔ Orange is the designed 8-color canonical discrete "
        "form for the continuous dc.blue_orange diverging family. "
        "Use it for signed or centered quantities where both "
        "direction and magnitude matter.",
        "design": "4 blue + 4 orange hues (~180° apart), each an internal L* "
        "ramp; even ladder 38→90.",
        "application": "Correlation matrices, change heatmaps, anomaly "
        "scales, and other midpoint-aware encodings.",
        "bw": "min ΔL* 7.3",
        "cvd": "d12.6 / p12.2 / t14.8",
        "kind": "diverging",
    },
    "teal_amber": {
        "label": "Teal ↔ Amber",
        "family": "Diverging",
        "band": "two-ended · pale center",
        "intent": "Teal ↔ Amber is the designed 8-color canonical discrete "
        "form for the continuous dc.teal_amber diverging family. Use "
        "it for signed or centered quantities where both direction "
        "and magnitude matter.",
        "design": "Symmetric L* tent, teal (h≈186) ↔ amber (h≈66). The "
        "blue-yellow axis is CVD-robust.",
        "application": "Correlation matrices, change heatmaps, anomaly scales, "
        "and other midpoint-aware encodings.",
        "bw": "min ΔL* 0.0",
        "cvd": "d13.1 / p8.8 / t13.9",
        "kind": "diverging",
    },
    "green_purple": {
        "label": "Green ↔ Purple",
        "family": "Diverging",
        "band": "two-ended · pale center",
        "intent": "Green ↔ Purple is the designed 8-color canonical discrete "
        "form for the continuous dc.green_purple diverging family. "
        "Use it for signed or centered quantities where both "
        "direction and magnitude matter.",
        "design": "Symmetric even-L* tent: dark saturated ends, pale "
        "low-chroma centre; both arms separable under all three "
        "CVD types.",
        "application": "Correlation matrices, change heatmaps, anomaly "
        "scales, and other midpoint-aware encodings.",
        "bw": "min ΔL* 0.0",
        "cvd": "d8.6 / p10.4 / t8.1",
        "kind": "diverging",
    },
}

__all__ = [
    "CURATED",
    "CURATED_DIVERGING_ORDER",
    "CURATED_META",
    "CURATED_ORDER",
    "CURATED_QUALITATIVE_ORDER",
]
