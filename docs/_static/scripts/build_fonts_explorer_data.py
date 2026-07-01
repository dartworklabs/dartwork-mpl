#!/usr/bin/env python3
"""Build the *font explorer data SSOT* (``fonts_explorer_data.js``).

The single source of truth every Fonts-page interactive widget consumes.
It emits a plain (non-module) script that defines three globals:

    var DM_FONT_DATA   // {slug: {name, mpl, faceStem, group, weights[], …}}
    var DM_FONT_ORDER  // [slug, …]  canonical rail order
    var DM_FONT_GROUPS // [{title, items:[slug,…]}, …]  grouped rail

Each ``weights[]`` entry is ``{label, num, face}`` where ``face`` is the
``@font-face`` family declared in ``docs/_static/font-face.css`` (naming:
``dm-<ttf-basename-without-ext>``). Computing the faces here — rather than
hand-typing 60+ family strings across POCs — removes the silent-fallback
bug class where a typo'd face name renders in a system font.

Editorial copy (intent / application / pairing / personality) lives in
``META`` below; weights are derived from ``WEIGHT_SPEC``. Output is
deterministic (sorted, no timestamps) so it is committed and CI-safe.

    python3 build_fonts_explorer_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUT = SCRIPT_DIR.parent / "fonts_explorer_data.js"

# CIE-ish numeric weight per label (CSS font-weight scale).
WNUM = {
    "Thin": 100,
    "ExtraLight": 200,
    "Light": 300,
    "Regular": 400,
    "Medium": 500,
    "SemiBold": 600,
    "Bold": 700,
    "ExtraBold": 800,
    "Black": 900,
}

# The nine-weight Latin ladder shared by the Inter/Noto sans families.
NINE = [
    "Thin",
    "ExtraLight",
    "Light",
    "Regular",
    "Medium",
    "SemiBold",
    "Bold",
    "ExtraBold",
    "Black",
]

# Per-family weight spec: label -> ttf-basename-without-ext token.
# ``face`` becomes ``dm-<token>``. For the nine-weight families the token
# is ``<Stem>-<Label>``; Paperlogy uses numeric prefixes; Roboto is a
# four-weight subset; Math is a single upright.
_PLEX7 = [
    "Thin",
    "ExtraLight",
    "Light",
    "Regular",
    "Medium",
    "SemiBold",
    "Bold",
]
_SOURCE7 = [
    "ExtraLight",
    "Light",
    "Regular",
    "Medium",
    "SemiBold",
    "Bold",
    "Black",
]
_JETBRAINS8 = [
    "Thin",
    "ExtraLight",
    "Light",
    "Regular",
    "Medium",
    "SemiBold",
    "Bold",
    "ExtraBold",
]
_ROBOTOMONO5 = ["Thin", "Light", "Regular", "Medium", "Bold"]

WEIGHT_SPEC: dict[str, list[tuple[str, str]]] = {
    # Roboto ships 6 static weights upstream (no ExtraLight/SemiBold/ExtraBold).
    "roboto": [
        (w, f"Roboto-{w}")
        for w in ["Thin", "Light", "Regular", "Medium", "Bold", "Black"]
    ],
    "inter": [(w, f"Inter-{w}") for w in NINE],
    "inter_display": [(w, f"InterDisplay-{w}") for w in NINE],
    "source_sans": [(w, f"SourceSans3-{w}") for w in _SOURCE7],
    "ibm_plex_sans": [(w, f"IBMPlexSans-{w}") for w in _PLEX7],
    "noto_sans": [(w, f"NotoSans-{w}") for w in NINE],
    "noto_semicondensed": [(w, f"NotoSans_SemiCondensed-{w}") for w in NINE],
    "noto_condensed": [(w, f"NotoSans_Condensed-{w}") for w in NINE],
    "pretendard": [(w, f"Pretendard-{w}") for w in NINE],
    "paperlogy": [
        ("Thin", "Paperlogy-1Thin"),
        ("ExtraLight", "Paperlogy-2ExtraLight"),
        ("Light", "Paperlogy-3Light"),
        ("Regular", "Paperlogy-4Regular"),
        ("Medium", "Paperlogy-5Medium"),
        ("SemiBold", "Paperlogy-6SemiBold"),
        ("Bold", "Paperlogy-7Bold"),
        ("ExtraBold", "Paperlogy-8ExtraBold"),
        ("Black", "Paperlogy-9Black"),
    ],
    "noto_cjk": [("Regular", "NotoSansCJK-Regular")],
    "ibm_plex_mono": [(w, f"IBMPlexMono-{w}") for w in _PLEX7],
    "jetbrains_mono": [(w, f"JetBrainsMono-{w}") for w in _JETBRAINS8],
    "source_code_pro": [(w, f"SourceCodePro-{w}") for w in _SOURCE7],
    "roboto_mono": [(w, f"RobotoMono-{w}") for w in _ROBOTOMONO5],
    "noto_math": [("Regular", "NotoSansMath-Regular")],
}

# Weights surfaced in a compact (key-weight) view.
KEY_WEIGHTS = {"Light", "Regular", "Medium", "Bold", "Black"}

LATIN = "The dartwork designs beautiful data artworks since 2021."
HERO_LATIN = "Aa Gg Rr 0123"

META: dict[str, dict] = {
    "roboto": {
        "name": "Roboto",
        "mpl": "Roboto",
        "faceStem": "dm-Roboto",
        "group": "Workhorse",
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "Google's flagship sans-serif and dartwork's default body face.",
        "intent": "The default. A mechanical skeleton with friendly, humanist curves that disappears into the data so the chart does the talking.",
        "application": "Body text, axis labels, and any figure where the type should stay invisible.",
        "pairing": "Stands alone, or takes titles from Inter Display for a display/body split.",
        "personality": "Neutral · geometric-humanist",
    },
    "inter": {
        "name": "Inter",
        "mpl": "Inter",
        "faceStem": "dm-Inter",
        "group": "Workhorse",
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "A screen-native grotesque built for interface text.",
        "intent": "Tall x-height and open apertures keep it razor-legible at small sizes — engineered for dense dashboards and on-screen figures.",
        "application": "Interface labels, legends, presentation slides, and any figure viewed on a screen.",
        "pairing": "Its natural partner is Inter Display for headings.",
        "personality": "Neutral · high-legibility",
    },
    "inter_display": {
        "name": "Inter Display",
        "mpl": "Inter Display",
        "faceStem": "dm-InterDisplay",
        "group": "Display",
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "Inter's display cut, tuned for large sizes.",
        "intent": "Tighter spacing and more delicate detail give titles presence at poster scale — without introducing a second typeface.",
        "application": "Chart titles, section headings, and poster-scale numbers.",
        "pairing": "Set titles here, body in Inter or Roboto.",
        "personality": "Confident · display-optimized",
    },
    "noto_sans": {
        "name": "Noto Sans",
        "mpl": "Noto Sans",
        "faceStem": "dm-NotoSans",
        "group": "Multilingual",
        "script": "Latin + pan-script",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "Google's pan-script workhorse with harmonized metrics.",
        "intent": "One family whose weights and proportions match across scripts — the safe choice whenever a figure mixes languages.",
        "application": "Multi-language documents, international reports, and neutral fallback body.",
        "pairing": "Pairs with Paperlogy for KR/EN and Noto Sans Math for symbols.",
        "personality": "Neutral · universal",
    },
    "noto_semicondensed": {
        "name": "Noto Sans SemiCondensed",
        "mpl": "Noto Sans SemiCondensed",
        "faceStem": "dm-NotoSans_SemiCondensed",
        "group": "Condensed",
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "A gentle narrowing of Noto Sans.",
        "intent": "Recovers horizontal space in legends and tick labels without looking compressed — the middle width.",
        "application": "Legends, tick labels, and moderately tight tables.",
        "pairing": "Shares metrics with Noto Sans and Noto Sans Condensed — mix widths freely.",
        "personality": "Efficient · unobtrusive",
    },
    "noto_condensed": {
        "name": "Noto Sans Condensed",
        "mpl": "Noto Sans Condensed",
        "faceStem": "dm-NotoSans_Condensed",
        "group": "Condensed",
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "The tightest Noto width.",
        "intent": "Packs long labels and data tables into narrow columns while staying readable — for when horizontal space runs out.",
        "application": "Dense tables, small-multiple labels, and crowded axes.",
        "pairing": "Step up to Noto Sans SemiCondensed or Noto Sans when space allows.",
        "personality": "Compact · space-saving",
    },
    "paperlogy": {
        "name": "Paperlogy",
        "mpl": "Paperlogy",
        "faceStem": "dm-Paperlogy",
        "group": "Korean & CJK",
        "script": "한글 + Latin",
        "hero": "가나다 Ag 0123",
        "sample": "데이터 시각화를 위한 아름다운 한글 타이포그래피, 2021년부터.",
        "desc": "A clean, professional 한글 family — dartwork's Korean default.",
        "intent": "Even color and open counters keep Hangul crisp at chart sizes, and its Latin set sits naturally beside the workhorses.",
        "application": "Korean (한글) titles and labels, and mixed KR/EN figures.",
        "pairing": "Pairs with Inter or Roboto for the Latin run in bilingual charts.",
        "personality": "Clean · bilingual",
    },
    "noto_math": {
        "name": "Noto Sans Math",
        "mpl": "Noto Sans Math",
        "faceStem": "dm-NotoSansMath",
        "group": "Monospace & Symbols",
        "script": "Math symbols",
        "hero": "∑ ∫ √ π",
        "sample": "∑ ∫ √ ∞ ≈ ≠ ≤ ≥ ∂ Δ π θ α β γ ∈ ∪ ∩ ∀ ∃",
        "desc": "Comprehensive mathematical symbol coverage.",
        "intent": "Integrals, operators, Greek, and set theory in one face — so scientific notation renders correctly inside a figure.",
        "application": "Equations, symbol annotations, and scientific axis labels.",
        "pairing": "Drop symbols into a Noto Sans or Inter run.",
        "personality": "Technical · complete",
    },
    "source_sans": {
        "name": "Source Sans 3",
        "mpl": "Source Sans 3",
        "faceStem": "dm-SourceSans3",
        "group": "Workhorse",
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "Adobe's humanist sans, tuned for extended reading.",
        "intent": "Warmer and more open than the grotesques — the natural choice when a figure carries real body copy or long captions.",
        "application": "Captions, annotations, and report body text.",
        "pairing": "Reads well beside Inter or Roboto for a UI/body split.",
        "personality": "Humanist · readable",
    },
    "ibm_plex_sans": {
        "name": "IBM Plex Sans",
        "mpl": "IBM Plex Sans",
        "faceStem": "dm-IBMPlexSans",
        "group": "Technical",
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "IBM's corporate humanist grotesque.",
        "intent": "A precise, engineered voice with a full weight range — a distinct alternative to Inter's neutrality for technical work.",
        "application": "Technical dashboards, interface labels, engineering figures.",
        "pairing": "Pairs with IBM Plex Mono for text-and-data layouts.",
        "personality": "Engineered · corporate",
    },
    "pretendard": {
        "name": "Pretendard",
        "mpl": "Pretendard",
        "faceStem": "dm-Pretendard",
        "group": "Korean & CJK",
        "script": "한글 + Latin",
        "hero": "가나다 Ag 0123",
        "sample": "데이터 시각화를 위한 아름다운 한글 타이포그래피, 2021년부터.",
        "desc": "A modern KR + Latin superfamily built on Inter's metrics.",
        "intent": "Hangul and Latin share one rhythm, so bilingual figures never clash — nine weights from Thin to Black.",
        "application": "Korean and mixed KR/EN titles, labels, and UI.",
        "pairing": "Self-contained KR+Latin; also sits naturally beside Inter.",
        "personality": "Modern · bilingual",
    },
    "noto_cjk": {
        "name": "Noto Sans CJK KR",
        "mpl": "Noto Sans CJK KR",
        "faceStem": "dm-NotoSansCJK",
        "group": "Korean & CJK",
        "script": "CJK (한·중·일)",
        "hero": "한자 漢字 かな",
        "sample": "데이터 시각화 · データ可視化 · 数据可视化",
        "desc": "Full CJK coverage — 한국어, 日本語, 中文 in one face.",
        "intent": "The fallback that keeps East-Asian glyphs from going missing when a figure mixes scripts.",
        "application": "Japanese / Chinese labels and mixed CJK figures.",
        "pairing": "Sits under the Latin workhorses as a CJK fallback.",
        "personality": "Pan-CJK · complete",
    },
    "ibm_plex_mono": {
        "name": "IBM Plex Mono",
        "mpl": "IBM Plex Mono",
        "faceStem": "dm-IBMPlexMono",
        "group": "Monospace & Symbols",
        "script": "Latin (monospace)",
        "hero": "Ag 012 {}",
        "sample": "The dartwork designs beautiful data artworks since 2021.",
        "desc": "A fixed-width companion to IBM Plex Sans.",
        "intent": "Aligns digits and code so tabular numbers and inline snippets line up column-perfect.",
        "application": "Tabular figures, code, and fixed-width axis labels.",
        "pairing": "Pairs with IBM Plex Sans for text next to data.",
        "personality": "Monospace · aligned",
    },
    "jetbrains_mono": {
        "name": "JetBrains Mono",
        "mpl": "JetBrains Mono",
        "faceStem": "dm-JetBrainsMono",
        "group": "Monospace & Symbols",
        "script": "Latin (monospace)",
        "hero": "il1 O0 =>",
        "sample": "def render(fig): return dm.save_formats(fig, 'out')",
        "desc": "A developer monospace with a tall x-height.",
        "intent": "Increased letter height and disambiguated shapes (il1, O0) keep code and dense numeric columns readable at small sizes.",
        "application": "Code blocks, log output, and tightly packed data tables.",
        "pairing": "Stands alone; sits well beside Inter for docs.",
        "personality": "Monospace · developer",
    },
    "source_code_pro": {
        "name": "Source Code Pro",
        "mpl": "Source Code Pro",
        "faceStem": "dm-SourceCodePro",
        "group": "Monospace & Symbols",
        "script": "Latin (monospace)",
        "hero": "il1 O0 =>",
        "sample": "sum([x for x in range(2021)])  # 2041210",
        "desc": "Adobe's monospace companion to Source Sans 3.",
        "intent": "Even color and clear punctuation make it a calm, neutral fixed-width face for code and figures alike.",
        "application": "Code, fixed-width labels, and numeric tables.",
        "pairing": "Pairs with Source Sans 3 for a full text+code system.",
        "personality": "Monospace · neutral",
    },
    "roboto_mono": {
        "name": "Roboto Mono",
        "mpl": "Roboto Mono",
        "faceStem": "dm-RobotoMono",
        "group": "Monospace & Symbols",
        "script": "Latin (monospace)",
        "hero": "il1 O0 =>",
        "sample": "2021-07-01  12:00:00  +02.5%  ▲",
        "desc": "The monospace cut of Roboto.",
        "intent": "Shares Roboto's mechanical skeleton, so mono labels sit seamlessly next to Roboto body text.",
        "application": "Timestamps, fixed-width tick labels, and inline figures.",
        "pairing": "Pairs with Roboto for a unified text+data look.",
        "personality": "Monospace · neutral",
    },
}

GROUPS = [
    ("Workhorse", ["roboto", "inter", "source_sans"]),
    ("Display", ["inter_display"]),
    ("Technical", ["ibm_plex_sans"]),
    ("Multilingual", ["noto_sans"]),
    ("Condensed", ["noto_semicondensed", "noto_condensed"]),
    ("Korean & CJK", ["pretendard", "paperlogy", "noto_cjk"]),
    (
        "Monospace & Symbols",
        [
            "ibm_plex_mono",
            "jetbrains_mono",
            "source_code_pro",
            "roboto_mono",
            "noto_math",
        ],
    ),
]

# Canonical rail order — derived from the grouped rail so the two never drift.
ORDER = [k for _title, items in GROUPS for k in items]


def _weights(slug: str) -> list[dict]:
    out = []
    for label, token in WEIGHT_SPEC[slug]:
        out.append({"label": label, "num": WNUM[label], "face": f"dm-{token}"})
    return out


def build() -> str:
    fonts: dict[str, dict] = {}
    for slug in ORDER:
        m = META[slug]
        w = _weights(slug)
        key = [x for x in w if x["label"] in KEY_WEIGHTS] or w
        fonts[slug] = {
            "name": m["name"],
            "mpl": m["mpl"],
            "faceStem": m["faceStem"],
            "group": m["group"],
            "script": m["script"],
            "hero": m["hero"],
            "sample": m["sample"],
            "desc": m["desc"],
            "intent": m["intent"],
            "application": m["application"],
            "pairing": m["pairing"],
            "personality": m["personality"],
            "variants": len(w),
            "regular": next(
                (x["face"] for x in w if x["label"] == "Regular"), w[0]["face"]
            ),
            "weights": w,
            "keyWeights": [x["label"] for x in key],
        }

    groups = [{"title": t, "items": items} for t, items in GROUPS]
    banner = (
        "// GENERATED FILE - do not edit by hand.\n"
        "// Source: docs/_static/scripts/build_fonts_explorer_data.py\n"
        "// Regenerate: python3 build_fonts_explorer_data.py\n"
    )
    return (
        banner
        + "var DM_FONT_DATA = "
        + json.dumps(fonts, ensure_ascii=False, indent=2)
        + ";\n"
        + "var DM_FONT_ORDER = "
        + json.dumps(ORDER)
        + ";\n"
        + "var DM_FONT_GROUPS = "
        + json.dumps(groups, ensure_ascii=False)
        + ";\n"
    )


if __name__ == "__main__":
    js = build()
    OUT.write_text(js, encoding="utf-8")
    print(f"OK - wrote {OUT} ({len(js):,} B)")
