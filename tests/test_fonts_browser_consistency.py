"""Registry, generated-data, and fragment invariants for the font browser."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from fontTools.ttLib import TTFont

from dartwork_mpl import font

_REPO = Path(__file__).resolve().parents[1]
_BUILDER_PATH = (
    _REPO / "docs" / "_static" / "scripts" / "build_fonts_browser_data.py"
)
_FRAGMENT_PATH = _REPO / "docs" / "_static" / "fonts_browser.frag.html"
_POC_B_PATH = _REPO / "docs" / "_static" / "pocs" / "fonts_ux_b.frag.html"
_POC_A_PATH = _REPO / "docs" / "_static" / "pocs" / "fonts_ux_a.frag.html"
_POC_PAGE_PATH = _REPO / "docs" / "pocs_fonts_ux.md"


def _load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "build_fonts_browser_data", _BUILDER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BUILDER = _load_builder()
_FRAGMENT = _FRAGMENT_PATH.read_text(encoding="utf-8")
_POC_B = _POC_B_PATH.read_text(encoding="utf-8")


def _parse_payload() -> tuple[
    dict[str, dict[str, Any]], list[str], list[dict[str, Any]]
]:
    region = _FRAGMENT.split(_BUILDER.BEGIN_MARKER, 1)[1].split(
        _BUILDER.END_MARKER, 1
    )[0]

    def parse_variable(name: str) -> Any:
        match = re.search(rf"var {name} = (.*?);\n", region, re.DOTALL)
        assert match is not None, f"generated variable missing: {name}"
        return json.loads(match.group(1))

    return (
        parse_variable("DM_FONT_DATA"),
        parse_variable("DM_FONT_ORDER"),
        parse_variable("DM_FONT_GROUPS"),
    )


def test_generator_is_idempotent_and_matches_committed_bytes() -> None:
    first = _BUILDER.splice(_FRAGMENT)
    second = _BUILDER.splice(first)

    assert first == _FRAGMENT
    assert second == first
    assert _BUILDER.build_payload() in _FRAGMENT

    checked = subprocess.run(
        [sys.executable, str(_BUILDER_PATH), "--check"],
        cwd=_REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr


def test_generator_deduplicates_repeated_measured_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _BUILDER.build_payload()
    original_measure = _BUILDER.font._measure

    def duplicated_measurement(name: str) -> font.FontMeasurement:
        measurement = original_measure(name)
        return replace(measurement, files=measurement.files + measurement.files)

    monkeypatch.setattr(_BUILDER.font, "_measure", duplicated_measurement)

    assert _BUILDER.build_payload() == expected


def test_payload_names_and_groups_equal_registry() -> None:
    catalog, order, groups = _parse_payload()
    registered = set(font.list_registered())

    assert {entry["mpl"] for entry in catalog.values()} == registered
    assert registered == set(font.FONTS)
    assert all(entry["name"] == entry["mpl"] for entry in catalog.values())
    assert len(order) == len(set(order)) == len(registered)
    assert set(catalog) == set(order)
    assert {item for group in groups for item in group["items"]} == set(order)


def test_every_browser_face_maps_to_a_bundled_file() -> None:
    catalog, _order, _groups = _parse_payload()
    available = {
        font.css_font_face_name(path.name)
        for path in font.get_font_dir().iterdir()
        if path.suffix.lower() in {".ttf", ".otf"}
    }

    for entry in catalog.values():
        faces = [entry["regular"]]
        faces.extend(weight["face"] for weight in entry["weights"])
        faces.extend(
            variant["face"] for variant in entry.get("width_variants", [])
        )
        assert set(faces) <= available, entry["mpl"]


def test_payload_flags_and_ladders_match_measurements() -> None:
    catalog, _order, _groups = _parse_payload()
    styles: dict[str, list[str]] = {"Sans": [], "Serif": [], "Mono": []}

    for entry in catalog.values():
        name = entry["mpl"]
        record = font.FONTS[name]
        measurement = font._measure(name)
        measured_by_file = {face.file: face for face in measurement.files}
        expected_faces = sorted(
            (
                face
                for face in measured_by_file.values()
                if not face.italic and face.stretch == "normal"
            ),
            key=lambda face: (face.weight, face.file),
        )

        assert isinstance(entry["role"], str) and entry["role"]
        assert entry["role"] == record.role
        assert "tnum" in entry
        assert type(entry["tnum"]) is bool
        assert entry["tnum"] is record.tnum
        assert entry["italic"] is measurement.italic
        assert entry["mono"] is measurement.fixed_pitch
        assert entry["hangul"] is measurement.hangul
        assert entry["numeric_axes"] is record.numeric_axes
        assert entry["tnum_available"] is measurement.tnum_available
        assert entry["chart_glyphs"] == "".join(measurement.chart_glyphs)
        assert entry["licenses"] == list(measurement.licenses)
        assert entry["license"] == measurement.licenses[0]
        assert [weight["num"] for weight in entry["weights"]] == [
            face.weight for face in expected_faces
        ]
        assert [weight["face"] for weight in entry["weights"]] == [
            font.css_font_face_name(face.file) for face in expected_faces
        ]

        style = (
            "Mono"
            if measurement.fixed_pitch
            else "Serif"
            if record.role == "serif"
            else "Sans"
        )
        styles[style].append(name)

    assert styles["Serif"] == ["Source Serif 4"]
    assert styles["Mono"]
    assert styles["Sans"]
    assert "hasItalic: f.italic" in _FRAGMENT
    assert "isMono: f.mono" in _FRAGMENT
    assert 'f.role === "serif" ? "Serif" : "Sans"' in _FRAGMENT


def test_editorial_fields_and_sample_codepoints_are_honest() -> None:
    catalog, _order, _groups = _parse_payload()
    required = {
        "desc",
        "intent",
        "application",
        "pairing",
        "foundry",
        "source",
        "license",
        "personality",
        "hero",
        "sample",
        "ladder_sample",
        "chain",
    }

    for entry in catalog.values():
        assert all(entry[field] for field in required), entry["mpl"]
        codepoints = font._family_codepoints(entry["mpl"])
        for field in ("hero", "sample"):
            missing = {
                char
                for char in entry[field]
                if not char.isascii() and ord(char) not in codepoints
            }
            assert not missing, (entry["mpl"], field, missing)

        regular_face = next(
            face
            for face in font._measure(entry["mpl"]).files
            if font.css_font_face_name(face.file) == entry["regular"]
        )
        ttfont = TTFont(font.get_font_dir() / regular_face.file, lazy=True)
        try:
            regular_codepoints = set(font._cmap_mapping(ttfont))
        finally:
            ttfont.close()
        assert entry["ladder_sample"]
        assert all(
            ord(char) in regular_codepoints for char in entry["ladder_sample"]
        ), entry["mpl"]


def test_chains_and_noto_width_variants_are_registry_valid() -> None:
    catalog, _order, _groups = _parse_payload()
    registered = set(font.list_registered())

    for entry in catalog.values():
        assert set(entry["chain"]) <= registered, entry["mpl"]

    with_widths = {
        entry["mpl"]: entry["width_variants"]
        for entry in catalog.values()
        if "width_variants" in entry
    }
    assert list(with_widths) == ["Noto Sans"]
    assert [item["label"] for item in with_widths["Noto Sans"]] == [
        "Normal",
        "SemiCondensed",
        "Condensed",
    ]


def test_fragment_is_clean_and_has_one_complete_generated_region() -> None:
    lowered = _FRAGMENT.lower()

    assert 'id="dm-fontfacets"' in _FRAGMENT
    assert _FRAGMENT.count(_BUILDER.BEGIN_MARKER) == 1
    assert _FRAGMENT.count(_BUILDER.END_MARKER) == 1
    assert _FRAGMENT.index(_BUILDER.BEGIN_MARKER) < _FRAGMENT.index(
        _BUILDER.END_MARKER
    )
    assert not any(
        token in lowered
        for token in (
            "<!doctype",
            "<html",
            "<head",
            "<body",
            "dm.set_theme",
            'class="masthead"',
        )
    )
    assert 'dm.style.use("scientific")' in _FRAGMENT
    assert 'values: ["Sans", "Serif", "Mono"]' in _FRAGMENT
    assert "Numeric axes" not in _FRAGMENT


def test_search_has_one_custom_clear_and_uses_fonts_terminology() -> None:
    fragments = {"#dm-fontfacets": _FRAGMENT, "#dm-fbuxb": _POC_B}

    for root, fragment in fragments.items():
        assert (
            f'{root} .search-wrap input[type="search"]'
            "::-webkit-search-cancel-button"
        ) in fragment
        assert "-webkit-appearance: none; appearance: none;" in fragment
        assert fragment.count('class="search-clear"') == 1
        assert 'placeholder="Search fonts"' in fragment
        assert 'aria-label="Search fonts"' in fragment
        assert ">20</b> fonts</span>" in fragment
        assert ">20</b> of 20 fonts</span>" in fragment
        assert "No fonts match" in fragment
        assert "Browse visible fonts" in fragment
        assert "Broad script coverage in one font" in fragment
        assert "One font whose weights and proportions match" in fragment
        assert "A clean, professional 한글 font" in fragment

        for legacy in (
            "Search families",
            "Search font families",
            "No families match",
            "Browse visible font families",
            "</b> families</span>",
            "One family whose weights and proportions match",
            "A clean, professional 한글 family",
        ):
            assert legacy not in fragment

    index = (_REPO / "docs" / "fonts" / "index.md").read_text(encoding="utf-8")
    assert "**20 publication-ready fonts**" in index
    assert "open any font" in index
    assert "publication-ready font families" not in index


def test_facet_rail_density_is_pinned() -> None:
    assert "grid-template-columns: 184px minmax(0, 1fr);" in _FRAGMENT
    assert "padding: 7px 28px 7px 30px;" in _FRAGMENT
    assert ".chips { display: flex; flex-wrap: wrap; gap: 4px; }" in _FRAGMENT
    assert "padding: 3px 8px; font-size: 11.5px;" in _FRAGMENT
    assert "margin-bottom: var(--dm-space-1);" in _FRAGMENT


def test_card_copy_and_badge_contract_is_pinned() -> None:
    assert ".mono-name" not in _FRAGMENT
    assert 'querySelector(".mono-name")' not in _FRAGMENT
    assert 'escapeHtml(f.raw.desc + " " + f.raw.application)' in _FRAGMENT
    assert "Aligned digits" in _FRAGMENT
    assert (
        "Digits share one width, so numeric axis labels stay aligned "
        "(the registry's numeric-axes gate)."
    ) in _FRAGMENT

    for fragment in (_FRAGMENT, _POC_B):
        assert 'korean_body: "Body"' in fragment
        assert 'korean_mono: "Mono"' in fragment
        assert 'math: "Symbols"' in fragment
        assert '"kr-body": "Body"' in fragment
        assert '"mono-kr": "Mono"' in fragment
        assert '"Korean body"' not in fragment
        assert '"Korean mono"' not in fragment
        assert "var italicsBadge = f.hasItalic" in fragment
        assert ">Italics</span>" in fragment

        card_source = fragment.split("function makeCard(f)", 1)[1].split(
            "function markSelected", 1
        )[0]
        markup_source = card_source.split("card.innerHTML =", 1)[1]
        assert markup_source.index(
            'class="title-badges"'
        ) < markup_source.index('class="card-desc"')
        assert markup_source.index('class="card-desc"') < markup_source.index(
            'class="sample-line"'
        )
        assert markup_source.index('class="sample-line"') < markup_source.index(
            'class="badges capability-badges"'
        )
        assert markup_source.index("badge script") < markup_source.index(
            "f.weightCount"
        )
        assert markup_source.index("f.weightCount") < markup_source.index(
            "italicsBadge"
        )
        assert markup_source.index("italicsBadge") < markup_source.index(
            "axesBadge"
        )
        assert markup_source.index("axesBadge") < markup_source.index(
            "monoBadge"
        )


def test_drawer_composition_and_descenders_are_pinned() -> None:
    assert "width: min(640px, 94vw);" in _FRAGMENT
    assert "Agile 24" not in _FRAGMENT
    assert "flex: 0 0 112px;" in _FRAGMENT
    assert "align-items: center;" in _FRAGMENT
    assert "escapeHtml(f.raw.sample)" in _FRAGMENT

    sample_rule_match = re.search(
        r"#dm-fontfacets \.ladder-sample \{(.*?)\}", _FRAGMENT, re.DOTALL
    )
    assert sample_rule_match is not None
    sample_rule = sample_rule_match.group(1)
    assert "line-height: 1.4" in sample_rule
    assert "overflow" not in sample_rule
    assert "max-height" not in sample_rule
    assert "text-overflow: ellipsis" in _FRAGMENT

    drawer_source = _FRAGMENT.split("dBody.innerHTML =", 1)[1].split(
        'dBody.querySelector(".snippet-copy")', 1
    )[0]
    labels = [
        "Specimen",
        "Weight ladder",
        "Numerals &amp; symbols",
        "widthVariants +",
        "Why this face",
        "rcParams snippet",
        "About",
    ]
    positions = [drawer_source.index(label) for label in labels]
    assert positions == sorted(positions)
    assert '<p class="lbl">Width variants</p>' in _FRAGMENT
    assert 'class="specimen-line"' in drawer_source
    assert "f.raw.hero" not in drawer_source
    assert "escapeHtml(f.raw.application)" in drawer_source
    why_source = drawer_source.split("Why this face", 1)[1].split(
        "rcParams snippet", 1
    )[0]
    assert "f.raw.pairing" not in why_source
    about_source = drawer_source.split("About", 1)[1]
    about_labels = ["Foundry", "License", "Source", "Pairs well"]
    about_positions = [about_source.index(label) for label in about_labels]
    assert about_positions == sorted(about_positions)
    for field in ("foundry", "license", "source", "pairing"):
        assert f"f.raw.{field}" in about_source
    assert "width: 100%;" in _FRAGMENT
    assert "overflow-x: auto;" in _FRAGMENT


def test_poc_b_is_resynced_and_uses_a_stacked_specimen_tray() -> None:
    def generated_region(fragment: str) -> str:
        return fragment.split(_BUILDER.BEGIN_MARKER, 1)[1].split(
            _BUILDER.END_MARKER, 1
        )[0]

    assert 'id="dm-fbuxb"' in _POC_B
    assert "dm-fontfacets" not in _POC_B
    assert generated_region(_POC_B) == generated_region(_FRAGMENT)
    assert 'id="fbuxb-preview-text"' in _POC_B
    assert 'class="pin-toggle"' in _POC_B
    assert "pinnedKeys.length >= 3" in _POC_B

    assert "Finalists — same sentence, same size." in _POC_B
    assert "Clear pins" in _POC_B
    assert "max-height: 40vh" in _POC_B
    assert "overflow-y: auto" in _POC_B
    assert "font-size: 24px" in _POC_B
    assert "line-height: 1.4" in _POC_B
    assert "var COMPARE_SAMPLE" in _POC_B
    assert (
        "var compareText = previewText.trim() ? previewText : COMPARE_SAMPLE;"
        in _POC_B
    )
    assert "escapeHtml(compareText)" in _POC_B
    assert 'class="compare-copy">Copy chain</button>' in _POC_B
    assert 'class="compare-unpin"' in _POC_B
    assert ">\u00d7</button>" in _POC_B
    assert ".compare-item:hover .compare-copy" in _POC_B
    assert ".compare-item:focus-within .compare-copy" in _POC_B
    assert "compare-chain" not in _POC_B
    assert "grid-template-columns: repeat(auto-fit" not in _POC_B

    item_rule_match = re.search(
        r"#dm-fbuxb \.compare-item \{(.*?)\}", _POC_B, re.DOTALL
    )
    assert item_rule_match is not None
    item_rule = item_rule_match.group(1)
    assert "border-bottom" in item_rule
    assert "background:" not in item_rule
    assert "border-radius:" not in item_rule


def test_preview_page_keeps_only_the_chosen_b_direction() -> None:
    page = _POC_PAGE_PATH.read_text(encoding="utf-8")

    assert "# Fonts browser — B 리파인" in page
    assert "공통 개선(rail·카드·드로어)은" in page
    assert "B의 핀 비교는 이 페이지에서 확인" in page
    assert "fonts_ux_b.frag.html" in page
    assert "fonts_ux_a" not in page
    assert "## A" not in page
    assert not _POC_A_PATH.exists()
