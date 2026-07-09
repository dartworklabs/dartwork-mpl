"""Docs must describe the live color, colormap, and font inventories."""

from __future__ import annotations

from pathlib import Path

import dartwork_mpl as dm
from dartwork_mpl import font
from dartwork_mpl._colors._families import QUALITATIVE
from dartwork_mpl._colors._generated import CMAPS_256
from dartwork_mpl._colors._loader import COLOR_LIBRARIES

_REPO = Path(__file__).resolve().parents[1]


def _read_doc(*parts: str) -> str:
    return (_REPO / "docs" / Path(*parts)).read_text(encoding="utf-8")


def _squash_ws(text: str) -> str:
    return " ".join(text.split())


def _font_file_count() -> int:
    return len(
        [
            p
            for p in font.get_font_dir().iterdir()
            if p.suffix.lower() in {".ttf", ".otf"}
        ]
    )


def _font_file_group_count() -> int:
    return len(
        {
            p.stem.split("-")[0]
            for p in font.get_font_dir().iterdir()
            if p.suffix.lower() in {".ttf", ".otf"}
        }
    )


def test_colormap_docs_explain_v5_inventory() -> None:
    text = _squash_ws(_read_doc("color_system", "colormaps.md"))
    v5_count = len(CMAPS_256)
    qualitative_count = len(QUALITATIVE)
    listed_count = len(dm.list_colors())

    assert f"**{v5_count} continuous colormaps**" in text
    assert f"**{qualitative_count} qualitative colormaps**" in text
    assert (
        f"`dm.list_colors()` returns the {listed_count} Model B family records"
        in text
    )


def test_cmap_api_docs_removed_from_index() -> None:
    text = _read_doc("api", "index.rst")

    assert "Colormap Registry <cmap>" not in text


def test_font_docs_distinguish_file_groups_from_registered_families() -> None:
    index = _squash_ws(_read_doc("fonts", "index.md"))
    families = _squash_ws(_read_doc("fonts", "families.md"))
    file_count = _font_file_count()
    group_count = _font_file_group_count()
    registered_count = len(font.list_registered())

    for text in (index, families):
        assert f"**{file_count} text font files**" in text
        assert f"**{group_count} documented file groups**" in text
        assert f"**{registered_count} matplotlib family names**" in text
        assert (
            "Condensed and SemiCondensed Noto Sans files register as Noto Sans"
            in text
        )


def test_color_api_intro_names_every_registered_library_prefix() -> None:
    text = _read_doc("api", "color.rst")

    for _key, prefix, _source, label in COLOR_LIBRARIES:
        assert prefix in text, f"{prefix} prefix missing from color API docs"
        assert label in text, f"{label} label missing from color API docs"
