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

from dartwork_mpl import font

_REPO = Path(__file__).resolve().parents[1]
_BUILDER_PATH = (
    _REPO / "docs" / "_static" / "scripts" / "build_fonts_browser_data.py"
)
_FRAGMENT_PATH = _REPO / "docs" / "_static" / "fonts_browser.frag.html"


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
        "personality",
        "hero",
        "sample",
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
    assert "Numeric axes" in _FRAGMENT


def test_facet_rail_density_is_pinned() -> None:
    assert "grid-template-columns: 184px minmax(0, 1fr);" in _FRAGMENT
    assert "padding: 7px 28px 7px 30px;" in _FRAGMENT
    assert ".chips { display: flex; flex-wrap: wrap; gap: 4px; }" in _FRAGMENT
    assert "padding: 3px 8px; font-size: 11.5px;" in _FRAGMENT
    assert "margin-bottom: var(--dm-space-1);" in _FRAGMENT
