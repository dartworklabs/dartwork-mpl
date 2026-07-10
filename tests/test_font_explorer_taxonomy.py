"""Interactive font explorer taxonomy, fragment, and docs pins."""

from __future__ import annotations

import hashlib
import json
import re
import runpy
import shutil
import subprocess
from pathlib import Path

from fontTools.ttLib import TTFont
from matplotlib import font_manager

from dartwork_mpl import font

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "docs" / "_static" / "scripts"
_BUILDER = _SCRIPTS / "build_font_explorer.py"
_REALPLOT_BUILDER = _SCRIPTS / "build_font_realplots.py"
_EXPLORER = _REPO / "docs" / "_static" / "font_explorer.html"
_DESIGN_CSS = _REPO / "docs" / "_static" / "dartwork-design.css"

_SERIF_FAMILIES = ["Source Serif 4"]
_MONO_FAMILIES = [
    "D2Coding",
    "IBM Plex Mono",
    "JetBrains Mono",
    "Roboto Mono",
    "Source Code Pro",
]
_FONT_SUFFIXES = {".ttf", ".otf"}
_HANGUL_SAMPLE = "한글 데이터 축 값"
_COLOR_FRAGMENT_HASHES = {
    "categorical_explorer.html": (
        "3c7bbcbd1ed844f2618d1c46caf34b3bb07097f9957a4646371447eb33dc6236"
    ),
    "colormap_explorer.html": (
        "607a554e7da302c8efa24ae1c5b7000adf5cedf58b023216b4a411e38b315ed5"
    ),
}


def _payload_from_html() -> dict:
    html = _EXPLORER.read_text(encoding="utf-8")
    m = re.search(r"var D=(\{.*?\});\nvar FONTS", html, re.S)
    assert m, "font explorer payload (var D={...}) not found"
    return json.loads(m.group(1))


def _builder_payload() -> dict:
    return runpy.run_path(str(_BUILDER))["build_payload"]()


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _bundled_font_face_files() -> dict[str, Path]:
    font_dir = font.get_font_dir()
    return {
        font.css_font_face_name(path): path
        for path in font_dir.iterdir()
        if path.suffix.lower() in _FONT_SUFFIXES
    }


def _cmap_codepoints(path: Path) -> set[int]:
    ttfont = TTFont(str(path), lazy=True)
    codepoints: set[int] = set()
    try:
        for table in ttfont["cmap"].tables:
            if table.isUnicode():
                codepoints.update(table.cmap.keys())
    finally:
        ttfont.close()
    return codepoints


def _has_hangul(path: Path) -> bool:
    codepoints = _cmap_codepoints(path)
    return all(
        ord(char) in codepoints for char in _HANGUL_SAMPLE if char != " "
    )


def test_builder_payload_does_not_require_generated_font_assets(
    tmp_path,
) -> None:
    builder = runpy.run_path(str(_BUILDER))
    builder_globals = builder["build_payload"].__globals__
    builder_globals["FONT_FACE_CSS"] = tmp_path / "missing-font-face.css"
    builder_globals["STATIC_FONT_DIR"] = tmp_path / "missing-fonts"

    payload = builder["build_payload"]()

    assert payload["counts"]["families"] == 18


def _registered_weights_by_family() -> dict[str, set[int]]:
    font.ensure_loaded()
    bundle_dir = font.get_font_dir().resolve()
    out: dict[str, set[int]] = {}
    for entry in font_manager.fontManager.ttflist:
        try:
            if not Path(entry.fname).resolve().is_relative_to(bundle_dir):
                continue
        except (OSError, ValueError):
            continue
        out.setdefault(entry.name, set()).add(int(entry.weight))
    return out


def test_fragment_exists_without_inline_style_and_node_parses() -> None:
    html = _EXPLORER.read_text(encoding="utf-8")
    assert '<div id="dm-font-exp" class="yue">' in html
    assert "<style" not in html
    assert html.count("<script>") == 1
    assert html.count("</script>") == 1
    assert _EXPLORER.stat().st_size <= 200_000

    node = shutil.which("node")
    assert node, "node is required for the font explorer parse gate"
    script = re.search(r"<script>(.*)</script>", html, re.S)
    assert script, "single script tag not found"
    subprocess.run(
        [node, "--check", "-"],
        input=script.group(1),
        text=True,
        check=True,
        capture_output=True,
    )


def test_builder_inventory_comes_from_registered_font_ssot() -> None:
    payload = _builder_payload()
    families = payload["families"]
    registered = font.list_registered()

    assert payload["counts"]["families"] == 18
    assert payload["counts"]["families"] == len(registered)
    assert set(families) == set(registered)
    _grouped = set(_SERIF_FAMILIES) | set(_MONO_FAMILIES)
    assert payload["groups"] == [
        ["Sans", [name for name in payload["order"] if name not in _grouped]],
        ["Serif", _SERIF_FAMILIES],
        ["Mono", _MONO_FAMILIES],
    ]
    assert payload["order"][0] == "Roboto"

    weights_by_family = _registered_weights_by_family()
    bundled_faces = _bundled_font_face_files()
    for family, meta in families.items():
        assert meta["weights"], family
        segment_weights = {entry["weight"] for entry in meta["weights"]}
        assert segment_weights <= weights_by_family[family]
        assert any(entry["weight"] == 400 for entry in meta["weights"])
        assert meta["default_weight"] == 400
        assert isinstance(meta["italic"], bool)
        assert meta["regular_face"] in bundled_faces
        assert meta["hangul"] is _has_hangul(
            bundled_faces[meta["regular_face"]]
        )
        for entry in meta["weights"]:
            assert entry["face"] == font.css_font_face_name(entry["file"])


def test_payload_realplot_references_match_registry_slugs() -> None:
    payload = _builder_payload()
    families = payload["families"]
    expected = {_slug(family) for family in font.list_registered()}

    realplots = {
        Path(meta["realplot"]).stem: meta["realplot"]
        for meta in families.values()
    }

    assert set(realplots) == expected
    assert all(
        src == f"../_static/realplots/{slug}.svg"
        for slug, src in realplots.items()
    )
    assert len(realplots) == 18


def test_committed_fragment_payload_matches_builder() -> None:
    assert _payload_from_html() == _builder_payload()


def test_jetbrains_mono_weight_segments_are_standard_grid() -> None:
    payload = _builder_payload()
    weights = payload["families"]["JetBrains Mono"]["weights"]

    assert [entry["weight"] for entry in weights] == [
        100,
        200,
        300,
        400,
        500,
        600,
        700,
        800,
    ]
    assert [entry["offset"] for entry in weights] == [-2, -1, 0, 1, 2, 3, 4, 5]


def test_font_faces_referenced_by_weight_segments_exist() -> None:
    payload = _builder_payload()
    bundled_faces = _bundled_font_face_files()

    referenced = {
        weight["face"]
        for family in payload["families"].values()
        for weight in family["weights"]
    }
    referenced |= {
        weight["italic_face"]
        for family in payload["families"].values()
        for weight in family["weights"]
        if weight.get("italic_face")
    }
    assert referenced <= set(bundled_faces)
    assert all(bundled_faces[face].is_file() for face in referenced)
    assert all(face.startswith("dm-") for face in referenced)


def test_fragment_is_two_panel_realplot_and_specimen_ui() -> None:
    html = _EXPLORER.read_text(encoding="utf-8")
    payload = _payload_from_html()

    assert "library" not in payload
    assert "defaults" not in payload
    assert "실제 플롯" in html
    assert "타이포 스펙시멘" in html
    assert "실제 matplotlib 출력" in html
    assert "브라우저 렌더 (동일 TTF)" in html
    assert "font-realplot-img" in html
    assert "font-specimen-card" in html
    assert "data-weight" in html
    assert "data-size-step" in html
    assert 'data-tgl="italic"' in html
    assert "data-layout" not in html
    assert "data-demo-pick" not in html
    assert "demo-picker" not in html
    assert "demo-grid" not in html
    assert "capDemosToLayout" not in html
    assert "toggleDemo" not in html
    assert html.count("../_static/realplots/") == 18


def test_hangul_coverage_matrix_and_no_tofu_fallback_copy_are_pinned() -> None:
    payload = _builder_payload()
    bundled_faces = _bundled_font_face_files()
    matrix = {
        family: meta["hangul"] for family, meta in payload["families"].items()
    }
    expected = {
        family: _has_hangul(bundled_faces[meta["regular_face"]])
        for family, meta in payload["families"].items()
    }
    assert matrix == expected
    html = _EXPLORER.read_text(encoding="utf-8")
    assert "No bundled Hangul in this face" in html
    assert 'data-hangul="0"' in html
    assert 'data-hangul="1"' in html


def test_shared_css_layer_includes_font_explorer_only_for_shared_widgets() -> (
    None
):
    css = _DESIGN_CSS.read_text(encoding="utf-8")
    for selector in (
        "#dm-cat-exp *,#dm-cmap-exp *,#dm-font-exp *",
        "#dm-cat-exp,#dm-cmap-exp,#dm-font-exp {width:100%;max-width:100%;",
        "#dm-cat-exp .md,#dm-cmap-exp .md,#dm-font-exp .md",
        "#dm-cat-exp .demo-tools .demo-field,#dm-cmap-exp .demo-tools .demo-field",
        "#dm-cat-exp .demo-picker,#dm-cmap-exp .demo-picker",
        "#dm-cat-exp .demo-grid,#dm-cmap-exp .demo-grid",
        "#dm-cat-exp .demo-label,#dm-cmap-exp .demo-label",
    ):
        assert selector in css
    for removed in (
        "#dm-font-exp .demo-tools",
        "#dm-font-exp .demo-picker",
        "#dm-font-exp .demo-grid",
        "#dm-font-exp .demo-label",
    ):
        assert removed not in css

    css_no_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for m in re.finditer(
        r"([^{}]+)\{[^{}]*#dm-font-exp|([^{}]+#dm-font-exp[^{}]*)\{",
        css_no_comments,
    ):
        selector = (m.group(1) or m.group(2) or "").strip()
        if "#dm-font-exp" not in selector:
            continue
        if "#dm-cat-exp" in selector and "#dm-cmap-exp" in selector:
            continue
        assert selector.startswith(
            "#dm-font-exp .font-"
        ) or selector.startswith("#dm-font-exp .rail .font-"), selector


def test_docs_embed_font_explorer_and_drop_legacy_picker() -> None:
    index = (_REPO / "docs" / "fonts" / "index.md").read_text(encoding="utf-8")
    families = (_REPO / "docs" / "fonts" / "families.md").read_text(
        encoding="utf-8"
    )
    index_squashed = " ".join(index.split())
    families_squashed = " ".join(families.split())
    legacy = "fonts" + "_picker"

    assert ":file: ../_static/font_explorer.html" in index
    assert legacy not in index
    assert legacy not in families
    assert "chart-context font explorer" in index
    assert "real matplotlib chart" in index
    assert (
        "Weight, Size, and Italic controls apply only to the specimen"
        in index_squashed
    )
    for removed in ("demos", "layout picker", "data-layout"):
        assert removed not in index.lower()
    for text in (index_squashed, families_squashed):
        assert "**220 text font files**" in text
        assert "**20 documented file groups**" in text
        assert "**18 matplotlib family names**" in text


def test_realplot_generator_is_deterministic_and_cached_for_one_family(
    tmp_path,
) -> None:
    builder = runpy.run_path(str(_REALPLOT_BUILDER))
    build_realplots = builder["build_realplots"]

    rendered = build_realplots(tmp_path, family_names=("Roboto",), force=True)
    svg = tmp_path / "roboto.svg"
    first = svg.read_bytes()
    cached = build_realplots(tmp_path, family_names=("Roboto",))
    forced = build_realplots(tmp_path, family_names=("Roboto",), force=True)

    assert rendered["rendered"] == ["roboto"]
    assert cached["skipped"] == ["roboto"]
    assert forced["rendered"] == ["roboto"]
    assert svg.stat().st_size > 5_000
    assert svg.read_bytes() == first


def test_legacy_picker_artifacts_are_gone() -> None:
    assert not (
        _REPO / "docs" / "_static" / ("fonts" + "_picker.html")
    ).exists()
    assert not (_REPO / "scripts" / ("build_fonts" + "_picker.py")).exists()


def test_color_explorer_fragments_stay_byte_identical() -> None:
    for name, expected in _COLOR_FRAGMENT_HASHES.items():
        actual = hashlib.sha256(
            (_REPO / "docs" / "_static" / name).read_bytes()
        ).hexdigest()
        assert actual == expected
