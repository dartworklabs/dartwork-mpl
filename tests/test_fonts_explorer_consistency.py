"""Fonts-explorer data parity (G7) — the palette twin's guard, for fonts.

``fonts_explorer_data.js`` is a committed generated artifact (like
``dc_palettes.json``) but had no parity test, so a font-file add/rename
could leave the docs explorer/picker silently stale. Sides checked:

1. builder ``build()`` output == committed JS, byte-for-byte;
2. every ``WEIGHT_SPEC`` token has a matching file in ``asset/font``;
3. every emitted face is derived by the shared package naming rule and has a
   bundled font file;
4. roman (non-italic) font stems not surfaced by any WEIGHT_SPEC entry
   are held against an explicit allowlist, so ADDing a family fails
   loudly until the explorer knows about it (or it is consciously
   waived).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from dartwork_mpl import font

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = (
    _REPO / "docs" / "_static" / "scripts" / "build_fonts_explorer_data.py"
)
_COMMITTED = _REPO / "docs" / "_static" / "fonts_explorer_data.js"
_FONT_DIR = _REPO / "src" / "dartwork_mpl" / "asset" / "font"

# Roman stems deliberately not surfaced in the explorer. Add entries here
# only as a conscious editorial waiver, with a justification comment.
_EXPLORER_UNSURFACED: list[str] = [
    # Pure symbol fallback faces — bundled for the plain-text scientific /
    # report fallback chain (arrows, ⚠ ✓ ★, dingbats), not selectable text
    # typefaces. They are intentionally left out of the font explorer/picker
    # (unlike Noto Sans Math, which is surfaced under "Monospace & Symbols").
    "NotoSansSymbols-Regular",
    "NotoSansSymbols2-Regular",
]


def _builder():
    spec = importlib.util.spec_from_file_location("_bfe", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _font_stems() -> set[str]:
    return {
        p.stem
        for p in _FONT_DIR.iterdir()
        if p.suffix.lower() in {".ttf", ".otf"}
    }


def test_committed_js_matches_builder_byte_for_byte() -> None:
    mod = _builder()
    built = mod.build()
    committed = _COMMITTED.read_text(encoding="utf-8")
    assert built == committed, (
        "fonts_explorer_data.js is stale — rerun "
        "docs/_static/scripts/build_fonts_explorer_data.py"
    )


def test_every_weight_spec_token_has_a_font_file() -> None:
    mod = _builder()
    stems = _font_stems()
    missing = {
        token
        for entries in mod.WEIGHT_SPEC.values()
        for _label, token in entries
        if token not in stems
    }
    assert not missing, (
        f"WEIGHT_SPEC tokens without font files: {sorted(missing)}"
    )


def test_every_emitted_face_uses_shared_naming_rule_and_has_a_font_file() -> (
    None
):
    mod = _builder()
    stems = _font_stems()
    wrong_names = {
        (slug, token, emitted["face"])
        for slug, entries in mod.WEIGHT_SPEC.items()
        for (_label, token), emitted in zip(
            entries, mod._weights(slug), strict=True
        )
        if emitted["face"] != font.css_font_face_name(token)
    }
    missing_files = {
        token
        for entries in mod.WEIGHT_SPEC.values()
        for _label, token in entries
        if token not in stems
    }
    assert not wrong_names, (
        f"faces not derived by shared naming rule: {sorted(wrong_names)}"
    )
    assert not missing_files, (
        f"emitted faces without bundled font files: {sorted(missing_files)}"
    )


def test_unsurfaced_roman_stems_are_consciously_waived() -> None:
    mod = _builder()
    surfaced = {
        token
        for entries in mod.WEIGHT_SPEC.values()
        for _label, token in entries
    }
    roman = {s for s in _font_stems() if "italic" not in s.lower()}
    unsurfaced = roman - surfaced
    assert unsurfaced == set(_EXPLORER_UNSURFACED), (
        f"roman font stems not in the explorer: "
        f"{sorted(unsurfaced - set(_EXPLORER_UNSURFACED))} — add them to "
        f"WEIGHT_SPEC (and regenerate the JS) or waive them explicitly "
        f"in _EXPLORER_UNSURFACED"
    )
