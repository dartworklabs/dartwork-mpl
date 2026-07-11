#!/usr/bin/env python3
"""Build the registry-backed data region in the interactive font browser."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont

from dartwork_mpl import font

SCRIPT_DIR = Path(__file__).resolve().parent
TARGET = SCRIPT_DIR.parent / "fonts_browser.frag.html"

BEGIN_MARKER = "// DM_FONT_DATA:BEGIN — GENERATED, do not edit."
END_MARKER = "// DM_FONT_DATA:END"

LATIN = "The dartwork designs beautiful data artworks since 2021."
HERO_LATIN = "Aa Gg Rr 0123"
LADDER_LATIN = "Beautiful data graphs 0123"
LADDER_KOREAN = "아름다운 데이터 그래프 0123"
LADDER_MONO = "plot(fig=dm) # 0123"

COVERAGE_BY_SCRIPT = {
    "Latin": "Latin",
    "Latin (monospace)": "Latin",
    "Latin + pan-script": "Multiscript",
    "한글 + Latin": "한글+Latin",
    "한글 + Latin (mono)": "한글+Latin",
    "CJK (한·중·일)": "CJK",
    "Math symbols": "Math",
    "Symbols": "Symbols",
}

# Editorial fields are deliberately curated, but their keys must exactly match
# the live registry. All technical fields are measured from bundled font files.
META: dict[str, dict[str, str]] = {
    "Roboto": {
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "Google's flagship sans-serif and dartwork's default body face.",
        "intent": "The default. A mechanical skeleton with friendly, humanist curves that disappears into the data so the chart does the talking.",
        "application": "Body text, axis labels, and any figure where the type should stay invisible.",
        "pairing": "Stands alone, or takes titles from Inter Display for a display/body split.",
        "personality": "Neutral · geometric-humanist",
        "foundry": "Google",
        "source": "Google Fonts",
    },
    "Inter": {
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "A screen-native grotesque built for interface text.",
        "intent": "Tall x-height and open apertures keep it razor-legible at small sizes — engineered for dense dashboards and on-screen figures.",
        "application": "Interface labels, legends, presentation slides, and any figure viewed on a screen.",
        "pairing": "Its natural partner is Inter Display for headings.",
        "personality": "Neutral · high-legibility",
        "foundry": "Rasmus Andersson",
        "source": "rsms/inter",
    },
    "IBM Plex Sans": {
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "IBM's corporate humanist grotesque.",
        "intent": "A precise, engineered voice with a full weight range — a distinct alternative to Inter's neutrality for technical work.",
        "application": "Technical dashboards, interface labels, engineering figures.",
        "pairing": "Pairs with IBM Plex Mono for text-and-data layouts.",
        "personality": "Engineered · corporate",
        "foundry": "IBM",
        "source": "IBM Plex",
    },
    "Source Sans 3": {
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "Adobe's humanist sans, tuned for extended reading.",
        "intent": "Warmer and more open than the grotesques — the natural choice when a figure carries real body copy or long captions.",
        "application": "Captions, annotations, and report body text.",
        "pairing": "Reads well beside Inter or Roboto for a UI/body split.",
        "personality": "Humanist · readable",
        "foundry": "Adobe",
        "source": "adobe-fonts/source-sans",
    },
    "Noto Sans": {
        "script": "Latin + pan-script",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "Google's pan-script workhorse with harmonized metrics.",
        "intent": "One font whose weights and proportions match across scripts — the safe choice whenever a figure mixes languages.",
        "application": "Multi-language documents, international reports, and neutral fallback body.",
        "pairing": "Pairs with Paperlogy for KR/EN and Noto Sans Math for symbols.",
        "personality": "Neutral · universal",
        "foundry": "Google",
        "source": "Google Fonts",
    },
    "Inter Display": {
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "Inter's display cut, tuned for large sizes.",
        "intent": "Tighter spacing and more delicate detail give titles presence at poster scale — without introducing a second typeface.",
        "application": "Chart titles, section headings, and poster-scale numbers.",
        "pairing": "Set titles here, body in Inter or Roboto.",
        "personality": "Confident · display-optimized",
        "foundry": "Rasmus Andersson",
        "source": "rsms/inter",
    },
    "Paperlogy": {
        "script": "한글 + Latin",
        "hero": "가나다 Ag 0123",
        "sample": "데이터 시각화를 위한 아름다운 한글 타이포그래피, 2021년부터.",
        "desc": "A clean, professional 한글 font — dartwork's Korean default.",
        "intent": "Even color and open counters keep Hangul crisp at chart sizes, and its Latin set sits naturally beside the workhorses.",
        "application": "Korean (한글) titles and labels, and mixed KR/EN figures.",
        "pairing": "Pairs with Inter or Roboto for the Latin run in bilingual charts.",
        "personality": "Clean · bilingual",
        "foundry": "Freesentation",
        "source": "Freesentation/Paperlogy",
    },
    "Pretendard": {
        "script": "한글 + Latin",
        "hero": "가나다 Ag 0123",
        "sample": "데이터 시각화를 위한 아름다운 한글 타이포그래피, 2021년부터.",
        "desc": "A modern KR + Latin superfamily built on Inter's metrics.",
        "intent": "Hangul and Latin share one rhythm, so bilingual figures never clash — nine weights from Thin to Black.",
        "application": "Korean and mixed KR/EN titles, labels, and UI.",
        "pairing": "Self-contained KR+Latin; also sits naturally beside Inter.",
        "personality": "Modern · bilingual",
        "foundry": "길형진 (orioncactus)",
        "source": "orioncactus/pretendard",
    },
    "Noto Sans CJK KR": {
        "script": "한글 + Latin",
        "hero": "한글 가나다 0123",
        "sample": "데이터 시각화를 위한 한국어 글꼴 2021",
        "desc": "Noto Sans CJK's Korean regional face with broad Hangul coverage.",
        "intent": "A Korean fallback with Noto's neutral proportions for figures that need dependable Hangul coverage.",
        "application": "Korean labels and mixed KR/EN figures.",
        "pairing": "Sits under the Latin workhorses as a Korean fallback.",
        "personality": "Korean · comprehensive",
        "foundry": "Google · Adobe",
        "source": "notofonts/noto-cjk",
    },
    "Source Serif 4": {
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "Adobe's serif body face for journal- and book-matched figures.",
        "intent": "A contemporary serif with even color at text sizes — print gravitas for figures, opt-in only (never wired into a preset chain).",
        "application": "Journal, report, and book figures that need a serif voice.",
        "pairing": "Pairs with Source Sans 3 and Source Code Pro in the Source superfamily.",
        "personality": "Editorial · print-rooted",
        "foundry": "Adobe",
        "source": "adobe-fonts/source-serif",
    },
    "Noto Serif": {
        "script": "Latin + pan-script",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "Noto Sans's serif sibling with harmonized pan-script metrics.",
        "intent": "A multilingual serif that keeps Noto's measured rhythm while adding an editorial voice, opt-in only.",
        "application": "Journal-matched multilingual figures, reports, and serif-led annotations.",
        "pairing": "Pairs with Noto Sans and Noto Sans Math for a matched fallback system.",
        "personality": "Multilingual · editorial",
        "foundry": "Google",
        "source": "Google Fonts",
    },
    "IBM Plex Serif": {
        "script": "Latin",
        "hero": HERO_LATIN,
        "sample": LATIN,
        "desc": "IBM's serif voice for the Plex superfamily.",
        "intent": "Distinctive engineered details carry the Plex identity into editorial figures, opt-in only.",
        "application": "Technical reports and editorial figures that pair serif text with Plex Sans or Mono.",
        "pairing": "Pairs with IBM Plex Sans and IBM Plex Mono.",
        "personality": "Engineered · editorial",
        "foundry": "IBM",
        "source": "IBM Plex",
    },
    "JetBrains Mono": {
        "script": "Latin (monospace)",
        "hero": "il1 O0 =>",
        "sample": "def render(fig): return dm.save_formats(fig, 'out')",
        "desc": "A developer monospace with a tall x-height.",
        "intent": "Increased letter height and disambiguated shapes (il1, O0) keep code and dense numeric columns readable at small sizes.",
        "application": "Code blocks, log output, and tightly packed data tables.",
        "pairing": "Stands alone; sits well beside Inter for docs.",
        "personality": "Monospace · developer",
        "foundry": "JetBrains",
        "source": "JetBrains/JetBrainsMono",
    },
    "IBM Plex Mono": {
        "script": "Latin (monospace)",
        "hero": "Ag 012 {}",
        "sample": LATIN,
        "desc": "A fixed-width companion to IBM Plex Sans.",
        "intent": "Aligns digits and code so tabular numbers and inline snippets line up column-perfect.",
        "application": "Tabular figures, code, and fixed-width axis labels.",
        "pairing": "Pairs with IBM Plex Sans for text next to data.",
        "personality": "Monospace · aligned",
        "foundry": "IBM",
        "source": "IBM Plex",
    },
    "Roboto Mono": {
        "script": "Latin (monospace)",
        "hero": "il1 O0 =>",
        "sample": "2021-07-01  12:00:00  +02.5%",
        "desc": "The monospace cut of Roboto.",
        "intent": "Shares Roboto's mechanical skeleton, so mono labels sit seamlessly next to Roboto body text.",
        "application": "Timestamps, fixed-width tick labels, and inline figures.",
        "pairing": "Pairs with Roboto for a unified text+data look.",
        "personality": "Monospace · neutral",
        "foundry": "Google",
        "source": "Google Fonts",
    },
    "Source Code Pro": {
        "script": "Latin (monospace)",
        "hero": "il1 O0 =>",
        "sample": "sum([x for x in range(2021)])  # 2041210",
        "desc": "Adobe's monospace companion to Source Sans 3.",
        "intent": "Even color and clear punctuation make it a calm, neutral fixed-width face for code and figures alike.",
        "application": "Code, fixed-width labels, and numeric tables.",
        "pairing": "Pairs with Source Sans 3 for a full text+code system.",
        "personality": "Monospace · neutral",
        "foundry": "Adobe",
        "source": "adobe-fonts/source-code-pro",
    },
    "D2Coding": {
        "script": "한글 + Latin (mono)",
        "hero": "가나 012 {}",
        "sample": "데이터 시각화 코드 정렬 0123456789",
        "desc": "Naver's monospaced Hangul for code and aligned Korean tables.",
        "intent": "Fixed-pitch Hangul keeps mixed KR/EN code and tables column-perfect — the only bundled mono that speaks Korean.",
        "application": "Korean code blocks and aligned Korean tables.",
        "pairing": "Trails a Latin mono: font.family = ['JetBrains Mono', 'D2Coding'].",
        "personality": "Monospace · bilingual",
        "foundry": "Naver",
        "source": "naver/d2codingfont",
    },
    "Noto Sans Math": {
        "script": "Math symbols",
        "hero": "∑ ∫ √ π",
        "sample": "∑ ∫ √ ∞ ≈ ≠ ≤ ≥ ∂ Δ π θ α β γ ∈ ∪ ∩ ∀ ∃",
        "desc": "Comprehensive mathematical symbol coverage.",
        "intent": "Integrals, operators, Greek, and set theory in one face — so scientific notation renders correctly inside a figure.",
        "application": "Equations, symbol annotations, and scientific axis labels.",
        "pairing": "Drop symbols into a Noto Sans or Inter run.",
        "personality": "Technical · complete",
        "foundry": "Google",
        "source": "notofonts/math",
    },
    "Noto Sans Symbols": {
        "script": "Symbols",
        "hero": "← ↑ → ↓",
        "sample": "← ↑ → ↓ ♪ − × °",
        "desc": "Arrows, music, and miscellaneous signs — the first symbol fallback (← ↑ ♪ §).",
        "intent": "Keeps arrows, stars, and signs from rendering as tofu — a fallback tail, not a body face.",
        "application": "End-of-chain fallback for annotation symbols.",
        "pairing": "Sits after Noto Sans Math in every preset chain.",
        "personality": "Fallback · coverage",
        "foundry": "Google",
        "source": "notofonts/symbols",
    },
    "Noto Sans Symbols 2": {
        "script": "Symbols",
        "hero": "⚠ ☑ ◐ ⬟",
        "sample": "⚠ ☑ ◐ ⬟ ⌚ ⏱",
        "desc": "Dingbats, enclosed marks, and pictographs — the final symbol fallback (⚠ ☑ ◐ ⏱).",
        "intent": "Extends the fallback tail into dingbats, enclosed marks, and pictographs that text faces do not cover.",
        "application": "Final fallback for pictographic annotations and status marks.",
        "pairing": "Sits last in every preset font fallback chain.",
        "personality": "Fallback · pictographic",
        "foundry": "Google",
        "source": "notofonts/symbols",
    },
}

GROUPS: list[tuple[str, list[str]]] = [
    ("Workhorse", ["Roboto", "Inter", "Source Sans 3"]),
    ("Display", ["Inter Display"]),
    ("Technical", ["IBM Plex Sans"]),
    ("Multilingual", ["Noto Sans"]),
    ("Serif", ["Source Serif 4", "Noto Serif", "IBM Plex Serif"]),
    ("Korean & CJK", ["Pretendard", "Paperlogy", "Noto Sans CJK KR"]),
    (
        "Monospace",
        [
            "JetBrains Mono",
            "IBM Plex Mono",
            "Source Code Pro",
            "Roboto Mono",
            "D2Coding",
        ],
    ),
    (
        "Symbols & Math",
        ["Noto Sans Math", "Noto Sans Symbols", "Noto Sans Symbols 2"],
    ),
]


def slug(name: str) -> str:
    """Return the stable JavaScript key for a registry family name."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _weight_label(filename: str) -> str:
    token = Path(filename).stem.partition("-")[2] or Path(filename).stem
    label = re.sub(r"^\d+", "", token)
    return {"Semibold": "SemiBold"}.get(label, label)


def _chain(name: str, role: str) -> list[str]:
    if role in {"body", "display", "serif", "kr-body"}:
        return [name, "Noto Sans Math"]
    if role == "mono":
        return [name, "D2Coding"]
    if role == "mono-kr":
        return ["JetBrains Mono", "D2Coding"]
    if role == "fallback-tail":
        return ["Roboto", name]
    raise AssertionError(f"unknown font role for {name}: {role}")


def _coverage(name: str, script: str) -> str:
    # The current CJK KR editorial script is "한글 + Latin", so identify its
    # broader CJK coverage by family before normalizing the shared script text.
    if name == "Noto Sans CJK KR":
        return "CJK"
    try:
        return COVERAGE_BY_SCRIPT[script]
    except KeyError as exc:
        message = f"unrecognized coverage script for {name}: {script}"
        raise SystemExit(message) from exc


def _unique_faces(
    measurement: font.FontMeasurement,
) -> tuple[font.FontFaceMeasurement, ...]:
    """Return one measured record per bundled filename."""
    by_file: dict[str, font.FontFaceMeasurement] = {}
    for face in measurement.files:
        previous = by_file.setdefault(face.file, face)
        if previous != face:
            raise SystemExit(f"conflicting measurements for {face.file}")
    return tuple(by_file[filename] for filename in sorted(by_file))


def _width_variants(measurement: font.FontMeasurement) -> list[dict[str, str]]:
    def bucket(filename: str, stretch: str) -> str:
        if stretch == "normal":
            return "normal"
        if "_SemiCondensed-" in filename:
            return "semi-condensed"
        if "_Condensed-" in filename:
            return "condensed"
        raise SystemExit(
            f"unrecognized Noto Sans width metadata: {filename} ({stretch})"
        )

    labels = (
        ("normal", "Normal"),
        ("semi-condensed", "SemiCondensed"),
        ("condensed", "Condensed"),
    )
    variants: list[dict[str, str]] = []
    for stretch, label in labels:
        candidates = [
            face
            for face in _unique_faces(measurement)
            if not face.italic and bucket(face.file, face.stretch) == stretch
        ]
        if not candidates:
            raise SystemExit(f"Noto Sans width bucket missing: {stretch}")
        regular = min(
            candidates, key=lambda face: (abs(face.weight - 400), face.file)
        )
        variants.append(
            {"label": label, "face": font.css_font_face_name(regular.file)}
        )
    return variants


def _face_codepoints(filename: str) -> frozenset[int]:
    ttfont = TTFont(font.get_font_dir() / filename, lazy=True)
    try:
        return frozenset(font._cmap_mapping(ttfont))
    finally:
        ttfont.close()


def _validate_description_glyphs(
    name: str, regular: font.FontFaceMeasurement
) -> None:
    if name not in {"Noto Sans Symbols", "Noto Sans Symbols 2"}:
        return
    match = re.search(r"\(([^()]*)\)\.$", META[name]["desc"])
    if match is None:
        raise SystemExit(f"symbol description examples missing for {name}")
    codepoints = _face_codepoints(regular.file)
    missing = {
        char
        for char in match.group(1)
        if not char.isspace() and ord(char) not in codepoints
    }
    if missing:
        raise SystemExit(
            f"symbol description glyphs not covered by {name}: "
            f"{sorted(missing)}"
        )


def _ladder_sample(
    name: str,
    role: str,
    measurement: font.FontMeasurement,
    regular: font.FontFaceMeasurement,
) -> str:
    codepoints = _face_codepoints(regular.file)
    if measurement.fixed_pitch:
        candidate = LADDER_MONO
    elif role == "fallback-tail":
        glyphs = [
            glyph
            for glyph in measurement.chart_glyphs
            if ord(glyph) in codepoints
        ][:14]
        candidate = " ".join(glyphs)
        if all(ord(char) in codepoints for char in "0123"):
            candidate += " 0123"
    elif measurement.hangul:
        candidate = LADDER_KOREAN
    else:
        candidate = LADDER_LATIN

    for text in (candidate.strip(), META[name]["hero"]):
        if text and all(ord(char) in codepoints for char in text):
            return text
    raise SystemExit(f"no coverage-safe ladder sample for {name}")


def build_catalog() -> tuple[
    dict[str, dict[str, Any]], list[str], list[dict[str, Any]]
]:
    """Derive the complete browser catalog from the live font registry."""
    registry = font.font_families()
    registry_names = set(registry)
    if set(META) != registry_names:
        missing = sorted(registry_names - set(META))
        extra = sorted(set(META) - registry_names)
        raise SystemExit(
            f"META/registry drift: missing={missing}, extra={extra}"
        )

    grouped_names = [name for _title, names in GROUPS for name in names]
    if (
        len(grouped_names) != len(set(grouped_names))
        or set(grouped_names) != registry_names
    ):
        missing = sorted(registry_names - set(grouped_names))
        extra = sorted(set(grouped_names) - registry_names)
        raise SystemExit(
            f"GROUPS/registry drift: missing={missing}, extra={extra}"
        )

    order = [slug(name) for name in grouped_names]
    if len(order) != len(set(order)):
        raise SystemExit("registry family names produced duplicate slugs")

    catalog: dict[str, dict[str, Any]] = {}
    for name in grouped_names:
        record = registry[name]
        if record.name != name:
            raise SystemExit(
                f"registry key/name drift: {name!r} != {record.name!r}"
            )
        measurement = font._measure(name)
        if len(measurement.licenses) != 1:
            raise SystemExit(
                f"expected one measured license for {name}: "
                f"{measurement.licenses}"
            )
        measured_faces = _unique_faces(measurement)
        ladder_faces = sorted(
            (
                face
                for face in measured_faces
                if not face.italic and face.stretch == "normal"
            ),
            key=lambda face: (face.weight, face.file),
        )
        if not ladder_faces:
            raise SystemExit(f"no upright normal-stretch faces for {name}")
        weights = [
            {
                "label": _weight_label(face.file),
                "num": face.weight,
                "face": font.css_font_face_name(face.file),
            }
            for face in ladder_faces
        ]
        regular = min(
            ladder_faces, key=lambda face: (abs(face.weight - 400), face.file)
        )
        _validate_description_glyphs(name, regular)
        group = next(title for title, names in GROUPS if name in names)
        # The coverage badge intentionally repeats a word from vendor names
        # (Noto Sans Math/Symbols/CJK): uniform system plus intra-group
        # discrimination beats per-card suppression.
        entry: dict[str, Any] = {
            "name": name,
            "mpl": name,
            "role": record.role,
            "group": group,
            "script": META[name]["script"],
            "coverage": _coverage(name, META[name]["script"]),
            "hero": META[name]["hero"],
            "sample": META[name]["sample"],
            "desc": META[name]["desc"],
            "intent": META[name]["intent"],
            "application": META[name]["application"],
            "pairing": META[name]["pairing"],
            "personality": META[name]["personality"],
            "foundry": META[name]["foundry"],
            "source": META[name]["source"],
            "ladder_sample": _ladder_sample(
                name, record.role, measurement, regular
            ),
            "regular": font.css_font_face_name(regular.file),
            "weights": weights,
            "italic": measurement.italic,
            "mono": measurement.fixed_pitch,
            "hangul": measurement.hangul,
            "numeric_axes": record.numeric_axes,
            "tnum": record.tnum,
            "tnum_available": measurement.tnum_available,
            "chart_glyphs": "".join(measurement.chart_glyphs),
            "license": measurement.licenses[0],
            "licenses": list(measurement.licenses),
            "chain": _chain(name, record.role),
        }
        if name == "Noto Sans":
            entry["width_variants"] = _width_variants(measurement)
        catalog[slug(name)] = entry

    groups = [
        {"title": title, "items": [slug(name) for name in names]}
        for title, names in GROUPS
    ]
    return catalog, order, groups


def build_payload() -> str:
    """Return the deterministic marker-delimited JavaScript payload."""
    catalog, order, groups = build_catalog()
    return (
        f"{BEGIN_MARKER}\n"
        "// Source: docs/_static/scripts/build_fonts_browser_data.py\n"
        "// Regenerate: python3 docs/_static/scripts/build_fonts_browser_data.py\n"
        f"var DM_FONT_DATA = {json.dumps(catalog, ensure_ascii=False, indent=2)};\n"
        f"var DM_FONT_ORDER = {json.dumps(order, ensure_ascii=False)};\n"
        f"var DM_FONT_GROUPS = {json.dumps(groups, ensure_ascii=False)};\n"
        f"{END_MARKER}"
    )


def splice(source: str, payload: str | None = None) -> str:
    """Replace exactly one generated region in ``source``."""
    if source.count(BEGIN_MARKER) != 1 or source.count(END_MARKER) != 1:
        raise SystemExit("font browser must contain exactly one marker pair")
    start = source.index(BEGIN_MARKER)
    end = source.index(END_MARKER, start) + len(END_MARKER)
    return source[:start] + (payload or build_payload()) + source[end:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 2 when regenerating would change the committed fragment",
    )
    args = parser.parse_args()

    source = TARGET.read_text(encoding="utf-8")
    generated = splice(source)
    if args.check:
        if generated != source:
            print(f"out of date: {TARGET}")
            return 2
        print(f"OK - up to date: {TARGET}")
        return 0

    if generated != source:
        TARGET.write_text(generated, encoding="utf-8")
        print(f"OK - wrote {TARGET} ({len(generated):,} B)")
    else:
        print(f"OK - unchanged: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
